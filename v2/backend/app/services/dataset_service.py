from __future__ import annotations

import hashlib
import json
from io import BytesIO
from pathlib import Path
from typing import Any, Optional

import pandas as pd
from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session

from app.models import (
    CoursePassingRule,
    DatasetVersion,
    EmailRosterEntry,
    EquivalentCourse,
    Major,
    MajorCodeMapping,
    StudentIntensiveAssignment,
    UploadBatch,
)
from app.services.grade_processing import (
    DEFAULT_CREDITS,
    DEFAULT_PASSING_GRADES,
    cell_status,
    determine_cell_value,
    match_rule,
    semester_to_ordinal,
)
from app.services.storage import StorageService

ROOT_DIR = Path(__file__).resolve().parents[4]
import sys
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# 'progress' kept as legacy fallback — new uploads should use 'progress_wide'.
DATASET_TYPES = {
    'courses',
    'progress',           # legacy wide c/cr/nc Excel (kept as fallback)
    'progress_wide',      # new registrar wide-format Excel
    'course_rules',
    'equivalent_courses',
    'intensive_assignments',
    'email_roster',
}


def _json_safe_records(df: pd.DataFrame) -> list[dict[str, Any]]:
    safe_df = df.where(pd.notnull(df), None)
    return json.loads(safe_df.to_json(orient='records', date_format='iso'))


# ---------------------------------------------------------------------------
# DB sync helpers (called after upload to keep lookup tables current)
# ---------------------------------------------------------------------------

def sync_course_rules_to_db(session: Session, major_id: int, rules: list[dict[str, Any]]) -> None:
    """Replace all CoursePassingRule rows for this major with the supplied rules."""
    session.execute(delete(CoursePassingRule).where(CoursePassingRule.major_id == major_id))
    for rule in rules:
        session.add(CoursePassingRule(
            major_id=major_id,
            course_code=str(rule['course_code']).strip().upper(),
            credits=int(rule.get('credits', 3)),
            passing_grades=str(rule.get('passing_grades', '')),
            from_ord=float(rule.get('from_ord', -1e18)),
            to_ord=float(rule.get('to_ord', 1e18)),
            course_type=str(rule.get('course_type', 'required')).lower(),
            rule_order=int(rule.get('rule_order', 0)),
        ))


def sync_equivalent_courses_to_db(session: Session, major_id: int, rows: list[dict[str, Any]]) -> None:
    """Replace all EquivalentCourse rows for this major."""
    session.execute(delete(EquivalentCourse).where(EquivalentCourse.major_id == major_id))
    for row in rows:
        session.add(EquivalentCourse(
            major_id=major_id,
            alt_code=str(row['alt_code']).strip().upper(),
            canonical_code=str(row['canonical_code']).strip().upper(),
        ))


def sync_intensive_assignments_to_db(session: Session, major_id: int, rows: list[dict[str, Any]]) -> None:
    """Upsert StudentIntensiveAssignment rows (additive — partial uploads allowed)."""
    for row in rows:
        student_id = str(row['student_id']).strip()
        slot_name = str(row['slot_name']).strip()
        course_code = str(row['course_code']).strip().upper()
        existing = session.scalar(
            select(StudentIntensiveAssignment).where(
                StudentIntensiveAssignment.major_id == major_id,
                StudentIntensiveAssignment.student_id == student_id,
                StudentIntensiveAssignment.slot_name == slot_name,
            )
        )
        if existing:
            existing.course_code = course_code
        else:
            session.add(StudentIntensiveAssignment(
                major_id=major_id,
                student_id=student_id,
                slot_name=slot_name,
                course_code=course_code,
            ))


# ---------------------------------------------------------------------------
# DB read helpers for progress_wide processing
# ---------------------------------------------------------------------------

def _get_rules_for_major(session: Session, major_id: int) -> dict[str, list[dict[str, Any]]]:
    """Return {course_code: [rule_dict, ...]} ordered by rule_order asc."""
    rows = session.scalars(
        select(CoursePassingRule)
        .where(CoursePassingRule.major_id == major_id)
        .order_by(CoursePassingRule.course_code, CoursePassingRule.rule_order)
    ).all()
    result: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        code = row.course_code.upper()
        result.setdefault(code, []).append({
            'course_code': code,
            'credits': row.credits,
            'passing_grades': row.passing_grades,
            'from_ord': row.from_ord,
            'to_ord': row.to_ord,
            'course_type': row.course_type,
            'rule_order': row.rule_order,
        })
    return result


def _get_equiv_map_for_major(session: Session, major_id: int) -> dict[str, str]:
    """Return {alt_code: canonical_code}."""
    rows = session.scalars(select(EquivalentCourse).where(EquivalentCourse.major_id == major_id)).all()
    return {r.alt_code.upper(): r.canonical_code.upper() for r in rows}


def _get_assignments_for_major(session: Session, major_id: int) -> dict[str, dict[str, str]]:
    """Return {student_id: {course_code: slot_name}} for quick lookup."""
    rows = session.scalars(
        select(StudentIntensiveAssignment).where(StudentIntensiveAssignment.major_id == major_id)
    ).all()
    result: dict[str, dict[str, str]] = {}
    for r in rows:
        result.setdefault(r.student_id, {})[r.course_code.upper()] = r.slot_name
    return result


# ---------------------------------------------------------------------------
# Config file parsers
# ---------------------------------------------------------------------------

def load_course_rules(file_bytes: bytes, filename: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Parse a course_rules CSV/Excel.

    Expected columns: Course, Credits, PassingGrades, Type, FromSemester, ToSemester
    FromSemester/ToSemester format: 'Fall-2018' or blank (open-ended).
    A course can have multiple rows (different eras).
    """
    if filename.lower().endswith('.csv'):
        df = pd.read_csv(BytesIO(file_bytes))
    else:
        df = pd.read_excel(BytesIO(file_bytes))

    df.columns = [str(c).strip() for c in df.columns]

    # Flexible column aliases
    col_map = {
        'course': 'Course',
        'credits': 'Credits',
        'passinggrades': 'PassingGrades',
        'type': 'Type',
        'fromsemester': 'FromSemester',
        'tosemester': 'ToSemester',
    }
    df.rename(columns={c: col_map.get(c.lower().replace(' ', ''), c) for c in df.columns}, inplace=True)

    records: list[dict[str, Any]] = []
    course_order: dict[str, int] = {}  # track rule_order per course

    for _, row in df.iterrows():
        code = str(row.get('Course', '')).strip().upper()
        if not code:
            continue
        from_sem = str(row.get('FromSemester', '')).strip()
        to_sem = str(row.get('ToSemester', '')).strip()

        from_ord = semester_to_ordinal(*_split_sem_year(from_sem)) if from_sem else float(-1e18)
        to_ord = semester_to_ordinal(*_split_sem_year(to_sem)) if to_sem else float(1e18)

        rule_order = course_order.get(code, 0)
        course_order[code] = rule_order + 1

        records.append({
            'course_code': code,
            'credits': int(float(str(row.get('Credits', 3)).strip() or 3)),
            'passing_grades': str(row.get('PassingGrades', '')).strip(),
            'from_ord': from_ord,
            'to_ord': to_ord,
            'course_type': str(row.get('Type', 'required')).strip().lower(),
            'rule_order': rule_order,
        })

    return records, {'rows': len(records), 'columns': list(df.columns)}


def load_equivalent_courses(file_bytes: bytes, filename: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Parse an equivalent_courses CSV/Excel.

    Expected columns: Course, Equivalent
    'Equivalent' may be a single course code or comma-separated list.
    """
    if filename.lower().endswith('.csv'):
        df = pd.read_csv(BytesIO(file_bytes))
    else:
        df = pd.read_excel(BytesIO(file_bytes))

    df.columns = [str(c).strip() for c in df.columns]

    records: list[dict[str, Any]] = []
    for _, row in df.iterrows():
        canonical = str(row.get('Course', row.get('Equivalent', ''))).strip().upper()
        alt_raw = str(row.get('Equivalent', row.get('Course', ''))).strip()
        # Support comma-separated alternatives
        for alt in alt_raw.split(','):
            alt = alt.strip().upper()
            if alt and alt != canonical:
                records.append({'alt_code': alt, 'canonical_code': canonical})

    return records, {'rows': len(records), 'columns': list(df.columns)}


def load_intensive_assignments(file_bytes: bytes, filename: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Parse an intensive_assignments CSV/Excel.

    Expected columns: student_id, assignment_type (= slot_name), course
    """
    if filename.lower().endswith('.csv'):
        df = pd.read_csv(BytesIO(file_bytes))
    else:
        df = pd.read_excel(BytesIO(file_bytes))

    df.columns = [str(c).strip().lower() for c in df.columns]

    records: list[dict[str, Any]] = []
    for _, row in df.iterrows():
        student_id = str(row.get('student_id', row.get('id', ''))).strip()
        slot_name = str(row.get('assignment_type', row.get('slot_name', ''))).strip()
        course_code = str(row.get('course', row.get('course_code', ''))).strip().upper()
        if student_id and slot_name and course_code:
            records.append({'student_id': student_id, 'slot_name': slot_name, 'course_code': course_code})

    return records, {'rows': len(records), 'columns': list(df.columns)}


# ---------------------------------------------------------------------------
# Progress wide-format parser
# ---------------------------------------------------------------------------

def _split_sem_year(sem_year: str) -> tuple[str, str]:
    """Split 'Fall-2018' → ('Fall', '2018').  Returns ('', '') on error."""
    parts = sem_year.strip().split('-')
    if len(parts) < 2:
        return ('', '')
    return (parts[0].strip(), parts[-1].strip())


def _read_wide_to_long(file_bytes: bytes, filename: str) -> pd.DataFrame:
    """Read an Excel/CSV progress report and return a long-format DataFrame.

    Handles both:
    - Long format: columns {ID, NAME, Course, Grade, Year, Semester}
    - Wide format: columns {ID, NAME, MAJOR, DEGREE, COURSE_1, COURSE_2 ...}
      where each cell is 'CODE/SEMESTER-YEAR/GRADE'
    """
    if filename.lower().endswith('.csv'):
        df_raw = pd.read_csv(BytesIO(file_bytes))
    else:
        io = BytesIO(file_bytes)
        # Check for 'Progress Report' sheet first
        xl = pd.ExcelFile(io)
        if 'Progress Report' in xl.sheet_names:
            df_raw = xl.parse('Progress Report')
        else:
            df_raw = xl.parse(xl.sheet_names[0])

    # Normalise column names for detection
    raw_cols = [str(c).strip() for c in df_raw.columns]
    df_raw.columns = raw_cols

    # Detect long format
    long_required = {'Course', 'Grade', 'Year', 'Semester'}
    if long_required.issubset(set(raw_cols)):
        # Normalise ID/NAME aliases
        for alias, canon in [('STUDENT ID', 'ID'), ('Name', 'NAME')]:
            if alias in df_raw.columns and canon not in df_raw.columns:
                df_raw.rename(columns={alias: canon}, inplace=True)
        return df_raw[['ID', 'NAME', 'Course', 'Grade', 'Year', 'Semester']].copy()

    # Detect wide format (any column starting with COURSE case-insensitive)
    course_cols = [c for c in raw_cols if c.upper().startswith('COURSE')]
    if not course_cols:
        raise ValueError('Cannot detect progress report format. Expected long-format columns or wide COURSE_* columns.')

    # Normalise ID/NAME
    id_col = next((c for c in raw_cols if c.upper() in ('ID', 'STUDENT ID')), None)
    name_col = next((c for c in raw_cols if c.upper() == 'NAME' or c == 'Name'), None)
    if not id_col or not name_col:
        raise ValueError('Progress report missing ID or NAME column.')

    # Detect optional MAJOR column
    major_col = next((c for c in raw_cols if c.upper() == 'MAJOR'), None)
    extra_id_vars = [major_col] if major_col else []

    # Melt
    melted = df_raw[[id_col, name_col] + extra_id_vars + course_cols].melt(
        id_vars=[id_col, name_col] + extra_id_vars,
        value_vars=course_cols,
        value_name='CourseData',
    )
    melted = melted.dropna(subset=['CourseData'])
    melted = melted[melted['CourseData'].astype(str).str.strip() != '']

    records = []
    for _, row in melted.iterrows():
        cell = str(row['CourseData']).strip()
        parts = cell.split('/')
        if len(parts) < 3:
            continue  # malformed cell — skip
        course = parts[0].strip().upper()
        sem_year = parts[1].strip()
        grade = parts[2].strip()
        # Normalise registrar-specific grade markers:
        #   P* = transfer/exemption pass  →  P
        #   T  = external transfer credit →  P
        grade = grade.rstrip('*')          # P* → P
        if grade.upper() == 'T':
            grade = 'P'
        sem_parts = sem_year.split('-')
        if len(sem_parts) < 2:
            continue
        semester = sem_parts[0].strip().title()  # e.g. 'Fall'
        year = sem_parts[-1].strip()
        records.append({
            'ID': str(row[id_col]).strip(),
            'NAME': str(row[name_col]).strip(),
            'MAJOR': str(row[major_col]).strip() if major_col else '',
            'Course': course,
            'Grade': grade,
            'Year': year,
            'Semester': semester,
        })

    long_df = pd.DataFrame(records).drop_duplicates()
    return long_df


def load_progress_wide(
    file_bytes: bytes,
    filename: str,
    rules_by_course: dict[str, list[dict[str, Any]]],
    equiv_map: dict[str, str],
    student_assignments: dict[str, dict[str, str]],
    *,
    pre_parsed_df: Optional[pd.DataFrame] = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Full progress report ingestion pipeline (ported from course_mapping).

    Steps:
    1. Parse wide/long Excel → long-format DataFrame
    2. Apply equivalent course substitution
    3. Apply intensive slot assignment override
    4. Match semester-bounded passing rule per row
    5. Determine cell value string for each attempt
    6. Pivot (student × course); multi-attempt cells joined with ', '
    7. Roster retention (left-join so all students appear)
    8. Split target courses vs. extra courses

    Returns (records, metadata).
    records: list of {student_id, student_name, section, course_code, cell_value}
    """
    long_df = pre_parsed_df if pre_parsed_df is not None else _read_wide_to_long(file_bytes, filename)

    if long_df.empty:
        return [], {'rows': 0, 'students': 0, 'target_courses': [], 'extra_courses': [], 'all_majors': []}

    # All known target courses (from loaded rules)
    target_course_set = set(rules_by_course.keys())

    # Build student → major map (first occurrence wins; MAJOR column optional)
    student_major_map: dict[str, str] = {}
    if 'MAJOR' in long_df.columns:
        for _, row in long_df[['ID', 'MAJOR']].drop_duplicates(subset=['ID']).iterrows():
            student_major_map[str(row['ID']).strip()] = str(row['MAJOR']).strip()

    # Build roster for left-join retention
    roster = long_df[['ID', 'NAME']].drop_duplicates().copy()

    processed_rows = []
    for _, row in long_df.iterrows():
        student_id = str(row['ID']).strip()
        student_name = str(row['NAME']).strip()
        original_code = str(row['Course']).strip().upper()
        grade = str(row['Grade']).strip() if pd.notna(row['Grade']) else ''
        semester = str(row['Semester']).strip().title()
        year_str = str(row['Year']).strip()

        # Step 2: equivalent substitution
        mapped_code = equiv_map.get(original_code, original_code)

        # Step 3: slot assignment override
        student_assigns = student_assignments.get(student_id, {})
        if original_code in student_assigns:
            mapped_code = student_assigns[original_code]

        # Step 4: rule matching
        try:
            term_ord = semester_to_ordinal(semester, int(year_str))
        except (ValueError, TypeError):
            term_ord = float('-inf')

        rules = rules_by_course.get(mapped_code, [])
        rule = match_rule(term_ord, rules)
        # Fall back to sensible defaults when no course_rules dataset is uploaded
        credits = rule['credits'] if rule else DEFAULT_CREDITS
        passing_grades = rule['passing_grades'] if rule else DEFAULT_PASSING_GRADES

        # Step 5: cell value (empty grade string = currently registered)
        cell_val = determine_cell_value(grade, credits, passing_grades)

        processed_rows.append({
            'ID': student_id,
            'NAME': student_name,
            'MappedCourse': mapped_code,
            'ProcessedValue': cell_val,
        })

    if not processed_rows:
        return [], {'rows': 0, 'students': 0, 'target_courses': [], 'extra_courses': []}

    proc_df = pd.DataFrame(processed_rows)

    # Step 6: pivot
    pivot = proc_df.pivot_table(
        index=['ID', 'NAME'],
        columns='MappedCourse',
        values='ProcessedValue',
        aggfunc=lambda vals: ', '.join(str(v) for v in vals),
    ).reset_index()
    pivot.columns.name = None

    # Step 7: roster retention
    full = roster.rename(columns={'ID': 'ID', 'NAME': 'NAME'}).merge(pivot, on=['ID', 'NAME'], how='left')
    # Fill NR for missing courses
    fill_cols = [c for c in full.columns if c not in ('ID', 'NAME')]
    full[fill_cols] = full[fill_cols].fillna('NR')

    # Step 8: split target vs extra
    all_course_cols = [c for c in full.columns if c not in ('ID', 'NAME')]
    target_courses = [c for c in all_course_cols if c.upper() in target_course_set]
    extra_courses = [c for c in all_course_cols if c.upper() not in target_course_set]

    records: list[dict[str, Any]] = []
    for _, row in full.iterrows():
        sid = str(row['ID'])
        sname = str(row['NAME'])
        smajor = student_major_map.get(sid, '')
        for course in target_courses:
            records.append({
                'student_id': sid,
                'student_name': sname,
                'student_major': smajor,
                'section': 'target',
                'course_code': course,
                'cell_value': str(row.get(course, 'NR')),
            })
        for course in extra_courses:
            records.append({
                'student_id': sid,
                'student_name': sname,
                'student_major': smajor,
                'section': 'extra',
                'course_code': course,
                'cell_value': str(row.get(course, 'NR')),
            })

    all_majors = sorted({r['student_major'] for r in records if r.get('student_major')})
    meta = {
        'rows': len(records),
        'students': int(roster.shape[0]),
        'target_courses': target_courses,
        'extra_courses': extra_courses,
        'all_majors': all_majors,
    }
    return records, meta


def _parse_dataset(
    dataset_type: str,
    file_bytes: bytes,
    filename: str,
    session: Optional[Session] = None,
    major_id: Optional[int] = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if dataset_type == 'courses':
        df = pd.read_excel(BytesIO(file_bytes))
        return _json_safe_records(df), {'rows': len(df), 'columns': list(map(str, df.columns))}
    if dataset_type == 'progress_wide':
        if session is None or major_id is None:
            raise ValueError('session and major_id required for progress_wide parsing')
        rules_by_course = _get_rules_for_major(session, major_id)
        equiv_map = _get_equiv_map_for_major(session, major_id)
        student_assignments = _get_assignments_for_major(session, major_id)
        return load_progress_wide(file_bytes, filename, rules_by_course, equiv_map, student_assignments)
    if dataset_type == 'course_rules':
        return load_course_rules(file_bytes, filename)
    if dataset_type == 'equivalent_courses':
        return load_equivalent_courses(file_bytes, filename)
    if dataset_type == 'intensive_assignments':
        return load_intensive_assignments(file_bytes, filename)
    if dataset_type == 'advising_selections':
        df = pd.read_csv(BytesIO(file_bytes)) if filename.lower().endswith('.csv') else pd.read_excel(BytesIO(file_bytes))
        return _json_safe_records(df), {'rows': len(df), 'columns': list(map(str, df.columns))}
    if dataset_type == 'email_roster':
        if filename.lower().endswith('.json'):
            payload = json.loads(file_bytes.decode('utf-8'))
            rows = [
                {'Student ID': str(student_id), 'Email': str(email).strip().lower()}
                for student_id, email in payload.items()
                if student_id and email
            ]
            return rows, {'rows': len(rows), 'columns': ['Student ID', 'Email']}
        if filename.lower().endswith('.csv'):
            df = pd.read_csv(BytesIO(file_bytes))
        else:
            df = pd.read_excel(BytesIO(file_bytes))
        return _json_safe_records(df), {'rows': len(df), 'columns': list(map(str, df.columns))}
    raise ValueError(f'Unsupported dataset type: {dataset_type}')


def _major_or_404(session: Session, major_code: str) -> Major:
    major = session.scalar(select(Major).where(Major.code == major_code))
    if not major:
        raise ValueError(f'Unknown major: {major_code}')
    return major


def upload_dataset(session: Session, *, major_code: str, dataset_type: str, filename: str, content: bytes, user_id: Optional[int]) -> DatasetVersion:
    if dataset_type not in DATASET_TYPES:
        raise ValueError(f'Unsupported dataset type: {dataset_type}')

    major = _major_or_404(session, major_code)
    storage = StorageService()
    parsed_payload, metadata = _parse_dataset(dataset_type, content, filename, session=session, major_id=major.id)
    checksum = hashlib.sha256(content).hexdigest()
    key = f'datasets/{major.code}/{dataset_type}/{checksum}-{filename}'
    storage.put_bytes(key, content)

    session.execute(
        update(DatasetVersion)
        .where(DatasetVersion.major_id == major.id, DatasetVersion.dataset_type == dataset_type)
        .values(is_active=False)
    )

    version = DatasetVersion(
        major_id=major.id,
        dataset_type=dataset_type,
        version_label=checksum[:12],
        storage_key=key,
        original_filename=filename,
        checksum=checksum,
        is_active=True,
        parsed_payload={'records': parsed_payload},
        metadata_json=metadata,
    )
    session.add(version)
    session.flush()

    batch = UploadBatch(
        major_id=major.id,
        uploaded_by_user_id=user_id,
        status='processed',
        manifest={'dataset_type': dataset_type, 'dataset_version_id': version.id, 'filename': filename},
    )
    session.add(batch)

    # Post-upload sync to DB lookup tables
    if dataset_type == 'email_roster':
        sync_email_roster_to_db(session, major.id, parsed_payload)
    elif dataset_type == 'course_rules':
        sync_course_rules_to_db(session, major.id, parsed_payload)
    elif dataset_type == 'equivalent_courses':
        sync_equivalent_courses_to_db(session, major.id, parsed_payload)
    elif dataset_type == 'intensive_assignments':
        sync_intensive_assignments_to_db(session, major.id, parsed_payload)

    session.commit()
    session.refresh(version)
    return version


def resolve_student_major(student_id: str, file_code: str, mappings: list[MajorCodeMapping]) -> Optional[int]:
    """Return the DB major_id for a student given their MAJOR column value and student ID.

    Iterates the configured mapping rules for that file_code. Each rule may carry
    id_year_min / id_year_max bounds (inclusive) which are compared against the
    first 4 digits of the student ID (i.e. the enrollment year).
    Returns None when no matching rule exists.
    """
    try:
        id_year = int(str(student_id)[:4])
    except (ValueError, TypeError):
        id_year = None

    normalized = file_code.strip().upper()
    for m in mappings:
        if m.file_code.upper() != normalized:
            continue
        if id_year is not None:
            min_ok = m.id_year_min is None or id_year >= m.id_year_min
            max_ok = m.id_year_max is None or id_year <= m.id_year_max
            if not (min_ok and max_ok):
                continue
        return m.major_id
    return None


def upload_multi_major_progress(
    session: Session,
    *,
    filename: str,
    content: bytes,
    user_id: Optional[int],
) -> list[DatasetVersion]:
    """Parse one multi-major progress file and create one DatasetVersion per resolved major.

    Students are routed to their target major via MajorCodeMapping rules.  A rule
    may restrict by the first 4 digits of the student ID (enrollment year) to
    support degree-plan splits (e.g. SPETHE→2016-plan vs SPETHE→2022-plan).
    """
    from collections import defaultdict

    long_df = _read_wide_to_long(content, filename)
    if long_df.empty:
        return []

    mappings = list(session.scalars(select(MajorCodeMapping)))

    # Build student_id → (file_code, major_id)
    student_file_code: dict[str, str] = {}
    if 'MAJOR' in long_df.columns:
        for _, row in long_df[['ID', 'MAJOR']].drop_duplicates(subset=['ID']).iterrows():
            student_file_code[str(row['ID']).strip()] = str(row['MAJOR']).strip().upper()

    major_students: dict[int, set[str]] = defaultdict(set)
    for sid, file_code in student_file_code.items():
        mid = resolve_student_major(sid, file_code, mappings)
        if mid is not None:
            major_students[mid].add(sid)

    if not major_students:
        raise ValueError(
            'No students could be mapped to a major. '
            'Ensure the file has a MAJOR column and mapping rules are configured.'
        )

    checksum = hashlib.sha256(content).hexdigest()
    storage = StorageService()

    versions: list[DatasetVersion] = []
    for major_id, student_ids in major_students.items():
        major = session.get(Major, major_id)
        if not major:
            continue

        filtered_df = long_df[long_df['ID'].astype(str).str.strip().isin(student_ids)].copy()
        rules_by_course = _get_rules_for_major(session, major_id)
        equiv_map = _get_equiv_map_for_major(session, major_id)
        student_assignments = _get_assignments_for_major(session, major_id)
        records, metadata = load_progress_wide(
            b'', '',
            rules_by_course, equiv_map, student_assignments,
            pre_parsed_df=filtered_df,
        )

        key = f'datasets/{major.code}/progress_wide/{checksum}-{filename}'
        storage.put_bytes(key, content)

        session.execute(
            update(DatasetVersion)
            .where(DatasetVersion.major_id == major_id, DatasetVersion.dataset_type == 'progress_wide')
            .values(is_active=False)
        )

        version = DatasetVersion(
            major_id=major_id,
            dataset_type='progress_wide',
            version_label=checksum[:12],
            storage_key=key,
            original_filename=filename,
            checksum=checksum,
            is_active=True,
            parsed_payload={'records': records},
            metadata_json={**metadata, 'source': 'multi_major'},
        )
        session.add(version)
        session.flush()

        batch = UploadBatch(
            major_id=major_id,
            uploaded_by_user_id=user_id,
            status='processed',
            manifest={'dataset_type': 'progress_wide', 'dataset_version_id': version.id, 'filename': filename},
        )
        session.add(batch)
        session.commit()
        session.refresh(version)
        versions.append(version)

    return versions


def sync_email_roster_to_db(session: Session, major_id: int, rows: list[dict[str, Any]]) -> None:
    session.query(EmailRosterEntry).filter(EmailRosterEntry.major_id == major_id).delete()
    for row in rows:
        student_id = str(row.get('Student ID') or row.get('ID') or row.get('student_id') or '').strip()
        email = str(row.get('Email') or row.get('email') or '').strip().lower()
        if not student_id or not email:
            continue
        session.add(
            EmailRosterEntry(
                major_id=major_id,
                student_id=student_id,
                student_name=str(row.get('Student Name') or row.get('NAME') or row.get('name') or '').strip() or None,
                email=email,
            )
        )


def get_active_dataset(session: Session, major_code: str, dataset_type: str) -> Optional[DatasetVersion]:
    major = _major_or_404(session, major_code)
    return session.scalar(
        select(DatasetVersion)
        .where(DatasetVersion.major_id == major.id, DatasetVersion.dataset_type == dataset_type, DatasetVersion.is_active.is_(True))
        .order_by(DatasetVersion.created_at.desc())
    )


def get_dataset_records(session: Session, major_code: str, dataset_type: str) -> list[dict[str, Any]]:
    dataset = get_active_dataset(session, major_code, dataset_type)
    if not dataset:
        return []
    return dataset.parsed_payload.get('records', [])


def dataset_dataframe(session: Session, major_code: str, dataset_type: str) -> pd.DataFrame:
    records = get_dataset_records(session, major_code, dataset_type)
    return pd.DataFrame(records)

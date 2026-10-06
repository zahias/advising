"""Intensive-course placement (bulk upload + manual Workspace edits).

The placement report is a spreadsheet with two columns:
  - student_id  (or 'ID')
  - placement_course  (or 'placed_course', 'course')

Multiple rows per student are supported (e.g. one for ARAB placement, one for ENGL).

For each student the system determines which intensive courses should remain
ACTIVE (= the placement course + all of its descendants in the prerequisite chain).
Every other intensive course is set as Excluded.

Example
-------
Intensive courses: ARAB101 → ARAB201 → ARAB301
Student placed at ARAB201  →  active = {ARAB201, ARAB301}  →  ARAB101 excluded.
Any other intensive tracks (ENGL100, ENGL200, …) are also excluded unless the
student also has a separate placement row for that track.

Excluded courses that sit *below* an active course in its chain (ARAB101 above)
are "placed out": they count as satisfied wherever they appear as a requisite,
so the placement course itself becomes eligible without a bypass.

Placements set manually in the Workspace are recorded with source 'manual' and
are left untouched by later bulk uploads unless ``overwrite_manual`` is set.
"""
from __future__ import annotations

import io
from collections import defaultdict
from typing import Any, Optional

import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import CourseExclusion, Major, StudentPlacement


def normalize_student_id(value: Any) -> str:
    """Return a clean student ID string ('' when missing).

    Excel stores IDs in a column with blank cells as floats (202012345.0);
    without this the exclusions would be saved under an ID no student has.
    """
    if value is None:
        return ''
    if isinstance(value, float):
        if pd.isna(value):
            return ''
        if value.is_integer():
            return str(int(value))
    text = str(value).strip()
    if text.lower() in {'nan', 'none'}:
        return ''
    if text.endswith('.0') and text[:-2].isdigit():
        text = text[:-2]
    return text


def normalize_code(value: Any) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ''
    text = str(value).strip().upper()
    return '' if text in {'NAN', 'NONE'} else text


def _parse_placement_file(content: bytes) -> pd.DataFrame:
    """Return a DataFrame with normalised columns student_id and placement_course.

    Multiple rows per student are preserved (one per intensive track).
    """
    try:
        df = pd.read_excel(io.BytesIO(content), dtype=object)
    except Exception:
        try:
            df = pd.read_csv(io.BytesIO(content), dtype=object)
        except Exception as exc:
            raise ValueError(f'Cannot parse file: {exc}') from exc

    # Normalise column names
    df.columns = [str(c).strip().lower().replace(' ', '_') for c in df.columns]

    # Accept common alternative spellings
    col_map = {
        'id': 'student_id',
        'student': 'student_id',
        'placed_course': 'placement_course',
        'course': 'placement_course',
        'course_code': 'placement_course',
        'placement': 'placement_course',
    }
    df = df.rename(columns={k: v for k, v in col_map.items() if k in df.columns})

    missing = {'student_id', 'placement_course'} - set(df.columns)
    if missing:
        raise ValueError(
            f'Missing columns: {", ".join(sorted(missing))}. '
            'Expected columns: student_id (or ID) and placement_course (or course, placed_course).'
        )

    df['student_id'] = df['student_id'].map(normalize_student_id)
    df['placement_course'] = df['placement_course'].map(normalize_code)
    df = df[(df['student_id'] != '') & (df['placement_course'] != '')]
    # Keep all rows — multiple placements per student are valid (one per track)
    return df[['student_id', 'placement_course']].drop_duplicates()


class IntensiveChains:
    """Intensive courses of a major and the prerequisite chains linking them."""

    def __init__(self, courses_df: pd.DataFrame):
        from app.legacy.eligibility_utils import parse_requirements  # noqa: PLC0415

        type_series = courses_df.get('Type', pd.Series(dtype=str, index=courses_df.index)).astype(str).str.strip().str.lower()
        # Normalised code -> code exactly as written in the courses dataset
        self.canonical: dict[str, str] = {}
        titles: dict[str, str] = {}
        for _, row in courses_df.loc[type_series == 'intensive'].iterrows():
            raw = str(row.get('Course Code', '') or '').strip()
            norm = normalize_code(raw)
            if norm:
                self.canonical[norm] = raw
                titles[norm] = str(row.get('Title', '') or row.get('Course Title', '') or raw)
        self.titles = titles
        self.codes: set[str] = set(self.canonical)

        # prereqs[C] = direct intensive prerequisites of C
        self.prereqs: dict[str, set[str]] = {c: set() for c in self.codes}
        for _, row in courses_df.iterrows():
            code = normalize_code(row.get('Course Code', ''))
            if code not in self.codes:
                continue
            for token in parse_requirements(row.get('Prerequisite', '')):
                token = normalize_code(token)
                if token in self.codes:
                    self.prereqs[code].add(token)

        self.successors: dict[str, set[str]] = defaultdict(set)
        for code, direct in self.prereqs.items():
            for p in direct:
                self.successors[p].add(code)

    @staticmethod
    def _walk(start: str, edges: dict[str, set[str]]) -> set[str]:
        visited: set[str] = set()
        stack = list(edges.get(start, ()))
        while stack:
            current = stack.pop()
            if current in visited:
                continue
            visited.add(current)
            stack.extend(edges.get(current, set()) - visited)
        return visited

    def descendants(self, code: str) -> set[str]:
        return self._walk(code, self.successors)

    def ancestors(self, code: str) -> set[str]:
        return self._walk(code, self.prereqs)

    def active_from_placements(self, placements: list[str]) -> set[str]:
        active: set[str] = set()
        for p in placements:
            active.add(p)
            active |= self.descendants(p)
        return active

    def placed_out(self, excluded: set[str]) -> set[str]:
        """Excluded intensive courses lying below an active course in its chain."""
        excluded_norm = {normalize_code(c) for c in excluded} & self.codes
        active = self.codes - excluded_norm
        result: set[str] = set()
        for code in active:
            result |= self.ancestors(code) & excluded_norm
        return result

    def lowest_active(self, excluded: set[str]) -> list[str]:
        """Active intensive courses with no active intensive prerequisite (the 'placed at' courses)."""
        excluded_norm = {normalize_code(c) for c in excluded} & self.codes
        active = self.codes - excluded_norm
        return sorted(c for c in active if not (self.prereqs.get(c, set()) & active))


def _major(session: Session, major_code: str) -> Major:
    major = session.scalar(select(Major).where(Major.code == major_code))
    if not major:
        raise ValueError(f'Major {major_code} not found.')
    return major


def _placement_record(session: Session, major_id: int, student_id: str) -> Optional[StudentPlacement]:
    return session.scalar(
        select(StudentPlacement).where(
            StudentPlacement.major_id == major_id,
            StudentPlacement.student_id == student_id,
        )
    )


def _replace_intensive_exclusions(
    session: Session,
    major_id: int,
    student_id: str,
    chains: IntensiveChains,
    excluded_intensive: set[str],
) -> list[str]:
    """Replace the student's intensive exclusions, keeping non-intensive ones."""
    existing = session.scalars(
        select(CourseExclusion).where(
            CourseExclusion.major_id == major_id,
            CourseExclusion.student_id == student_id,
        )
    ).all()
    for row in existing:
        if normalize_code(row.course_code) in chains.codes:
            session.delete(row)
    session.flush()
    kept = {row.course_code for row in existing if normalize_code(row.course_code) not in chains.codes}
    for code in sorted(excluded_intensive):
        canonical = chains.canonical[code]
        if canonical not in kept:
            session.add(CourseExclusion(major_id=major_id, student_id=student_id, course_code=canonical))
    return sorted(kept | {chains.canonical[c] for c in excluded_intensive})


def _upsert_placement_record(
    session: Session,
    major_id: int,
    student_id: str,
    source: str,
    placement_courses: list[str],
    user_id: Optional[int],
) -> None:
    record = _placement_record(session, major_id, student_id)
    if record is None:
        record = StudentPlacement(major_id=major_id, student_id=student_id)
        session.add(record)
    record.source = source
    record.placement_courses = placement_courses
    record.updated_by_user_id = user_id


def _known_student_ids(session: Session, major_code: str) -> set[str]:
    from app.services.dataset_service import dataset_dataframe  # noqa: PLC0415

    progress_df = dataset_dataframe(session, major_code, 'progress')
    if progress_df.empty or 'ID' not in progress_df.columns:
        return set()
    return {normalize_student_id(v) for v in progress_df['ID'].tolist()} - {''}


def bulk_placement_from_file(
    session: Session,
    major_code: str,
    content: bytes,
    overwrite_manual: bool = False,
    user_id: Optional[int] = None,
) -> dict[str, object]:
    """Parse an intensive placement report and apply exclusions per student.

    For each student, courses that should remain ACTIVE are:
      - the placement course itself
      - all descendants of the placement course (courses it unlocks)

    All other intensive courses are set as Excluded.
    Multiple placement rows per student are supported.

    Students whose placement was set manually in the Workspace are skipped
    unless ``overwrite_manual`` is True.

    Returns ``{processed, errors, skipped_manual}``.
    Students not in the file are untouched.
    """
    from app.services.dataset_service import dataset_dataframe  # noqa: PLC0415

    df = _parse_placement_file(content)

    courses_df = dataset_dataframe(session, major_code, 'courses')
    if courses_df.empty:
        raise ValueError('No courses dataset uploaded for this major.')

    chains = IntensiveChains(courses_df)
    if not chains.codes:
        raise ValueError('The courses dataset has no courses with Type "Intensive".')

    major = _major(session, major_code)
    known_ids = _known_student_ids(session, major_code)

    # Group placements by student (preserving multiple placements per student)
    by_student: dict[str, list[str]] = defaultdict(list)
    for _, row in df.iterrows():
        by_student[str(row['student_id'])].append(str(row['placement_course']))

    processed = 0
    errors: list[str] = []
    skipped_manual: list[str] = []

    for student_id, placements in by_student.items():
        if known_ids and student_id not in known_ids:
            errors.append(f'Student {student_id}: not found in the progress report — skipped.')
            continue

        invalid = [p for p in placements if p not in chains.codes]
        if invalid:
            errors.append(
                f'Student {student_id}: "{", ".join(invalid)}" is not an intensive course — skipped.'
            )
            continue

        record = _placement_record(session, major.id, student_id)
        if record is not None and record.source == 'manual' and not overwrite_manual:
            skipped_manual.append(student_id)
            continue

        active = chains.active_from_placements(placements)
        _replace_intensive_exclusions(session, major.id, student_id, chains, chains.codes - active)
        _upsert_placement_record(
            session, major.id, student_id, 'upload',
            sorted(chains.canonical[p] for p in set(placements)), user_id,
        )
        processed += 1

    session.commit()
    return {'processed': processed, 'errors': errors, 'skipped_manual': skipped_manual}


def save_manual_placement(
    session: Session,
    major_code: str,
    student_id: str,
    excluded_courses: list[str],
    user_id: Optional[int] = None,
) -> dict[str, object]:
    """Save a student's intensive placement as edited in the Workspace.

    ``excluded_courses`` lists the intensive courses to exclude; non-intensive
    exclusions already on the student are preserved.  The placement is marked
    'manual' so later bulk uploads do not overwrite it.
    """
    from app.services.dataset_service import dataset_dataframe  # noqa: PLC0415

    courses_df = dataset_dataframe(session, major_code, 'courses')
    chains = IntensiveChains(courses_df)
    major = _major(session, major_code)
    student_id = normalize_student_id(student_id)

    requested = {normalize_code(c) for c in excluded_courses} - {''}
    unknown = sorted(requested - chains.codes)
    if unknown:
        raise ValueError(f'Not intensive courses: {", ".join(unknown)}.')

    all_excluded = _replace_intensive_exclusions(session, major.id, student_id, chains, requested)
    _upsert_placement_record(
        session, major.id, student_id, 'manual',
        [chains.canonical[c] for c in chains.lowest_active(requested)], user_id,
    )
    session.commit()
    return {'student_id': student_id, 'excluded_courses': all_excluded}

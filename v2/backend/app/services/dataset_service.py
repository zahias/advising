from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from typing import Any, Optional

import pandas as pd
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models import CourseRule, DatasetVersion, EmailRosterEntry, Major, UploadBatch
from app.services.storage import StorageService

ROOT_DIR = Path(__file__).resolve().parents[4]
import sys
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

DATASET_TYPES = {'courses', 'progress', 'advising_selections', 'email_roster'}


def _json_safe_records(df: pd.DataFrame) -> list[dict[str, Any]]:
    safe_df = df.where(pd.notnull(df), None)
    return json.loads(safe_df.to_json(orient='records', date_format='iso'))


def load_progress_excel(content: bytes | BytesIO | str) -> pd.DataFrame:
    io_obj = BytesIO(content) if isinstance(content, (bytes, bytearray)) else content
    sheets = pd.read_excel(io_obj, sheet_name=None)
    req_key = next((key for key in sheets.keys() if 'required' in key.lower()), None)
    int_key = next((key for key in sheets.keys() if 'intensive' in key.lower()), None)
    if req_key is None:
        req_key = list(sheets.keys())[0]
    req_df = sheets[req_key].copy()
    if int_key is None:
        return req_df

    int_df = sheets[int_key].copy()
    base_columns = ['ID', 'NAME']
    numeric_columns = ['# of Credits Completed', '# Registered', '# Remaining', 'Total Credits']
    for column in base_columns:
        if column not in req_df.columns:
            req_df[column] = None
        if column not in int_df.columns:
            int_df[column] = None

    def course_columns(df: pd.DataFrame) -> list[str]:
        return [column for column in df.columns if column not in base_columns + numeric_columns]

    req_courses = course_columns(req_df)
    int_courses = course_columns(int_df)
    merged = pd.merge(
        req_df[base_columns + req_courses + [column for column in numeric_columns if column in req_df.columns]],
        int_df[base_columns + int_courses + [column for column in numeric_columns if column in int_df.columns]],
        on=base_columns,
        how='outer',
        suffixes=('_req', '_int'),
    )
    for column in numeric_columns:
        req_col = f'{column}_req'
        int_col = f'{column}_int'
        if req_col in merged.columns and int_col in merged.columns:
            merged[column] = merged[req_col].combine_first(merged[int_col])
            merged.drop(columns=[req_col, int_col], inplace=True)
        elif req_col in merged.columns:
            merged[column] = merged.pop(req_col)
        elif int_col in merged.columns:
            merged[column] = merged.pop(int_col)
    return merged


def _detect_raw_progress(file_bytes: bytes, filename: str) -> bool:
    """Return True if this looks like a raw wide-format progress report (not a processed two-sheet Excel)."""
    if not filename.lower().endswith(('.xlsx', '.xls')):
        return True  # CSV is always raw
    try:
        sheets = pd.read_excel(BytesIO(file_bytes), sheet_name=None)
        sheet_names_lower = [s.lower() for s in sheets.keys()]
        if any('required' in s for s in sheet_names_lower) and any('intensive' in s for s in sheet_names_lower):
            return False  # already processed
        # Check if first sheet has COURSE_* columns
        first_df = next(iter(sheets.values()))
        has_course_cols = any(c.upper().startswith('COURSE') for c in first_df.columns)
        has_major_col = 'MAJOR' in [c.upper() for c in first_df.columns]
        return has_course_cols or has_major_col
    except Exception:
        return True


def _upsert_course_rules(session: Session, major_id: int, df: pd.DataFrame) -> bool:
    """
    Parse optional PassingGrades / RuleFromSemester / RuleToSemester columns
    and upsert CourseRule rows. Returns True if any rules were written.
    """
    col_map = {c.lower().replace(' ', '').replace('_', ''): c for c in df.columns}
    passing_col = col_map.get('passinggrades') or col_map.get('passing')
    from_col = col_map.get('rulefromsemester') or col_map.get('fromsemester')
    to_col = col_map.get('ruletosemester') or col_map.get('tosemester')
    credits_col = next((c for c in df.columns if 'credit' in c.lower()), None)
    type_col = next((c for c in df.columns if 'type' in c.lower()), None)

    # Normalise code column
    code_col = next(
        (c for c in df.columns if 'course' in c.lower() and 'code' in c.lower()),
        df.columns[0],
    )

    # Delete existing rules for this major before re-inserting
    session.query(CourseRule).filter(CourseRule.major_id == major_id).delete()

    any_written = False
    for _, row in df.iterrows():
        code = str(row.get(code_col, '')).strip().upper()
        if not code or code == 'NAN':
            continue
        passing = str(row.get(passing_col, '')).strip() if passing_col else None
        from_sem = str(row.get(from_col, '')).strip() if from_col else None
        to_sem = str(row.get(to_col, '')).strip() if to_col else None
        credits = 0
        if credits_col:
            try:
                credits = int(float(row.get(credits_col, 0) or 0))
            except (ValueError, TypeError):
                credits = 0
        course_type = str(row.get(type_col, '')).strip().lower() if type_col else None

        session.add(CourseRule(
            major_id=major_id,
            course_code=code,
            credits=credits,
            passing_grades=passing,
            course_type=course_type or None,
            from_semester=from_sem or None,
            to_semester=to_sem or None,
        ))
        any_written = True

    return any_written


def _parse_dataset(
    dataset_type: str,
    file_bytes: bytes,
    filename: str,
    session: Optional[Session] = None,
    major_id: Optional[int] = None,
    major_mapping: Optional[dict[str, str]] = None,
) -> tuple[list[dict[str, Any]], dict[str, Any], bytes]:
    """
    Returns (parsed_records, metadata, stored_bytes).
    stored_bytes may differ from file_bytes when raw progress is processed.
    """
    if dataset_type == 'courses':
        df = pd.read_excel(BytesIO(file_bytes))
        if session and major_id:
            wrote = _upsert_course_rules(session, major_id, df)
            if wrote:
                session.flush()
        return _json_safe_records(df), {'rows': len(df), 'columns': list(map(str, df.columns))}, file_bytes

    if dataset_type == 'progress':
        is_raw = _detect_raw_progress(file_bytes, filename)
        if is_raw:
            if session is None or major_id is None:
                raise ValueError('session and major_id are required to process a raw progress report')
            # Enforce upload order: courses must exist first
            courses_v = session.scalar(
                select(DatasetVersion).where(
                    DatasetVersion.major_id == major_id,
                    DatasetVersion.dataset_type == 'courses',
                    DatasetVersion.is_active.is_(True),
                )
            )
            if courses_v is None:
                raise ValueError(
                    'Upload a courses file first before uploading a progress report. '
                    'The courses file is needed to map course codes and rules.'
                )
            # Load courses DataFrame from stored data
            courses_records = courses_v.parsed_payload.get('records', [])
            courses_df = pd.DataFrame(courses_records)

            # Read raw file
            if filename.lower().endswith('.csv'):
                raw_df = pd.read_csv(BytesIO(file_bytes))
            else:
                raw_df = pd.read_excel(BytesIO(file_bytes))

            # Apply major_mapping: filter and rename MAJOR column
            if major_mapping and 'MAJOR' in [c.upper() for c in raw_df.columns]:
                major_col = next(c for c in raw_df.columns if c.upper() == 'MAJOR')
                # Keep only rows whose MAJOR is in the mapping
                raw_df = raw_df[raw_df[major_col].astype(str).isin(major_mapping.keys())].copy()
                if raw_df.empty:
                    raise ValueError(
                        f'No students matched the provided major mapping. '
                        f'File contains: {raw_df[major_col].unique().tolist()}'
                    )

            from app.services.progress_service import process_transcript
            stored_bytes = process_transcript(raw_df, major_id, session, courses_df)
            df = load_progress_excel(stored_bytes)
            return _json_safe_records(df), {'rows': len(df), 'columns': list(map(str, df.columns))}, stored_bytes
        else:
            df = load_progress_excel(file_bytes)
            return _json_safe_records(df), {'rows': len(df), 'columns': list(map(str, df.columns))}, file_bytes

    if dataset_type == 'advising_selections':
        df = pd.read_csv(BytesIO(file_bytes)) if filename.lower().endswith('.csv') else pd.read_excel(BytesIO(file_bytes))
        return _json_safe_records(df), {'rows': len(df), 'columns': list(map(str, df.columns))}, file_bytes

    if dataset_type == 'email_roster':
        if filename.lower().endswith('.json'):
            payload = json.loads(file_bytes.decode('utf-8'))
            rows = [
                {'Student ID': str(student_id), 'Email': str(email).strip().lower()}
                for student_id, email in payload.items()
                if student_id and email
            ]
            return rows, {'rows': len(rows), 'columns': ['Student ID', 'Email']}, file_bytes
        if filename.lower().endswith('.csv'):
            df = pd.read_csv(BytesIO(file_bytes))
        else:
            df = pd.read_excel(BytesIO(file_bytes))
        return _json_safe_records(df), {'rows': len(df), 'columns': list(map(str, df.columns))}, file_bytes

    raise ValueError(f'Unsupported dataset type: {dataset_type}')


def _major_or_404(session: Session, major_code: str) -> Major:
    major = session.scalar(select(Major).where(Major.code == major_code))
    if not major:
        raise ValueError(f'Unknown major: {major_code}')
    return major


def upload_dataset(
    session: Session,
    *,
    major_code: str,
    dataset_type: str,
    filename: str,
    content: bytes,
    user_id: Optional[int],
    major_mapping: Optional[dict[str, str]] = None,
) -> DatasetVersion:
    if dataset_type not in DATASET_TYPES:
        raise ValueError(f'Unsupported dataset type: {dataset_type}')

    major = _major_or_404(session, major_code)
    storage = StorageService()
    parsed_payload, metadata, stored_bytes = _parse_dataset(
        dataset_type, content, filename,
        session=session, major_id=major.id, major_mapping=major_mapping,
    )

    # If courses were uploaded and had rules, update rules_updated_at
    if dataset_type == 'courses':
        session.execute(
            update(Major).where(Major.id == major.id).values(rules_updated_at=datetime.now(timezone.utc))
        )

    checksum = hashlib.sha256(content).hexdigest()
    key = f'datasets/{major.code}/{dataset_type}/{checksum}-{filename}'
    storage.put_bytes(key, stored_bytes)

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

    if dataset_type == 'email_roster':
        _refresh_email_roster(session, major.id, parsed_payload)

    session.commit()
    session.refresh(version)
    return version


def _refresh_email_roster(session: Session, major_id: int, rows: list[dict[str, Any]]) -> None:
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

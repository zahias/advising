"""
Progress report routes: serve the processed progress grid and staleness info.
"""
from __future__ import annotations

from datetime import timezone
from typing import Any, Optional

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import ensure_major_access, get_db, require_staff
from app.models import DatasetVersion, Major, User
from app.services.dataset_service import get_active_dataset, load_progress_excel
from app.services.progress_service import (
    collapse_pass_fail_value,
    extract_primary_grade_from_full_value,
)

router = APIRouter(prefix='/progress', tags=['progress'])


def _get_major_or_404(db: Session, major_code: str) -> Major:
    from fastapi import HTTPException
    major = db.scalar(select(Major).where(Major.code == major_code))
    if not major:
        raise HTTPException(status_code=404, detail=f'Major not found: {major_code}')
    return major


@router.get('/{major_code}/staleness')
def get_staleness(major_code: str, user: User = Depends(require_staff), db: Session = Depends(get_db)) -> dict[str, Any]:
    """
    Returns whether the progress data is stale (rules updated after last progress upload).
    """
    ensure_major_access(major_code, db, user)
    major = _get_major_or_404(db, major_code)

    progress_v = get_active_dataset(db, major_code, 'progress')

    rules_updated_at = major.rules_updated_at
    progress_uploaded_at = progress_v.created_at if progress_v else None

    stale = False
    if rules_updated_at and progress_uploaded_at:
        # Normalise to UTC-aware for comparison
        rup = rules_updated_at.replace(tzinfo=timezone.utc) if rules_updated_at.tzinfo is None else rules_updated_at
        pup = progress_uploaded_at.replace(tzinfo=timezone.utc) if progress_uploaded_at.tzinfo is None else progress_uploaded_at
        stale = rup > pup

    return {
        'stale': stale,
        'rules_updated_at': rules_updated_at.isoformat() if rules_updated_at else None,
        'progress_uploaded_at': progress_uploaded_at.isoformat() if progress_uploaded_at else None,
    }


@router.get('/{major_code}/report')
def get_progress_report(major_code: str, user: User = Depends(require_staff), db: Session = Depends(get_db)) -> dict[str, Any]:
    """
    Return the processed progress grid for the Progress Report page.
    """
    from fastapi import HTTPException
    import pandas as pd

    ensure_major_access(major_code, db, user)
    major = _get_major_or_404(db, major_code)
    progress_v = get_active_dataset(db, major_code, 'progress')
    if not progress_v:
        raise HTTPException(status_code=404, detail='No active progress dataset for this major.')

    from app.services.storage import StorageService
    storage = StorageService()
    file_bytes = storage.get_bytes(progress_v.storage_key)
    df = load_progress_excel(file_bytes)

    base_cols = {'ID', 'NAME', '# of Credits Completed', '# Registered', '# Remaining', 'Total Credits'}
    all_cols = list(df.columns)
    course_cols = [c for c in all_cols if c not in base_cols]

    # Determine which are required vs intensive by looking at which sheet they came from.
    # load_progress_excel merges both sheets; we re-read to find required/intensive columns.
    from io import BytesIO
    sheets = pd.read_excel(BytesIO(file_bytes), sheet_name=None)
    req_key = next((k for k in sheets if 'required' in k.lower()), None)
    int_key = next((k for k in sheets if 'intensive' in k.lower()), None)
    extra_key = next((k for k in sheets if 'extra' in k.lower()), None)
    id_cols = ['ID', 'NAME']
    required_courses = [c for c in (sheets[req_key].columns if req_key else []) if c not in id_cols and c not in base_cols]
    intensive_courses = [c for c in (sheets[int_key].columns if int_key else []) if c not in id_cols and c not in base_cols]

    # Extra courses (flat rows)
    extra_courses_rows: list[dict[str, Any]] = []
    if extra_key:
        exc_df = sheets[extra_key].fillna('')
        for _, er in exc_df.iterrows():
            extra_courses_rows.append({
                'student_id': str(er.get('ID', '')),
                'student_name': str(er.get('NAME', '')),
                'course': str(er.get('Course', '')),
                'grade': str(er.get('Grade', '')),
                'year': str(er.get('Year', '')),
                'semester': str(er.get('Semester', '')),
            })

    # Build student rows
    students = []
    credit_cols = ['# of Credits Completed', '# Registered', '# Remaining', 'Total Credits']
    for _, row in df.iterrows():
        def _cell(col: str) -> dict[str, Any]:
            raw = str(row.get(col, 'NR') or 'NR')
            primary_entry = extract_primary_grade_from_full_value(raw) if raw != 'NR' else 'NR'
            raw_status = collapse_pass_fail_value(primary_entry)
            # Map to frontend enum: 'c' → 'pass', 'cr' → 'cr', 'nc' → 'nc'
            status = 'pass' if raw_status == 'c' else raw_status if raw_status in ('cr', 'nc') else 'nc'
            return {'raw': raw, 'primary': primary_entry, 'status': status}

        required_cells = {c: _cell(c) for c in required_courses}
        intensive_cells = {c: _cell(c) for c in intensive_courses}

        students.append({
            'student_id': str(row.get('ID', '')),
            'student_name': str(row.get('NAME', '')),
            'credits_completed': row.get('# of Credits Completed'),
            'credits_registered': row.get('# Registered'),
            'credits_remaining': row.get('# Remaining'),
            'total_credits': row.get('Total Credits'),
            'required': required_cells,
            'intensive': intensive_cells,
        })

    return {
        'required_courses': required_courses,
        'intensive_courses': intensive_courses,
        'students': students,
        'extra_courses': extra_courses_rows,
        'assignment_types': major.assignment_types or [],
    }

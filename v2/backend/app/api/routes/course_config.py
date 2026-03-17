"""
Course configuration routes: equivalents, assignments, assignment types.
"""
from __future__ import annotations

import csv
import io
from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import ensure_major_access, get_db, require_staff
from app.models import CourseAssignment, CourseEquivalent, Major, User

router = APIRouter(prefix='/course-config', tags=['course-config'])


def _get_major_or_404(db: Session, major_code: str) -> Major:
    major = db.scalar(select(Major).where(Major.code == major_code))
    if not major:
        raise HTTPException(status_code=404, detail=f'Major not found: {major_code}')
    return major


# ---------------------------------------------------------------------------
# Equivalents
# ---------------------------------------------------------------------------

class EquivalentIn(BaseModel):
    alias_code: str
    canonical_code: str


class EquivalentOut(BaseModel):
    id: int
    alias_code: str
    canonical_code: str

    model_config = {'from_attributes': True}


@router.get('/{major_code}/equivalents', response_model=list[EquivalentOut])
def list_equivalents(major_code: str, user: User = Depends(require_staff), db: Session = Depends(get_db)):
    ensure_major_access(major_code, db, user)
    major = _get_major_or_404(db, major_code)
    return db.scalars(select(CourseEquivalent).where(CourseEquivalent.major_id == major.id)).all()


@router.post('/{major_code}/equivalents', response_model=EquivalentOut, status_code=201)
def add_equivalent(major_code: str, body: EquivalentIn, user: User = Depends(require_staff), db: Session = Depends(get_db)):
    ensure_major_access(major_code, db, user)
    major = _get_major_or_404(db, major_code)
    existing = db.scalar(
        select(CourseEquivalent).where(
            CourseEquivalent.major_id == major.id,
            CourseEquivalent.alias_code == body.alias_code.strip().upper(),
        )
    )
    if existing:
        raise HTTPException(status_code=409, detail=f'Equivalent already exists for alias {body.alias_code}')
    eq = CourseEquivalent(
        major_id=major.id,
        alias_code=body.alias_code.strip().upper(),
        canonical_code=body.canonical_code.strip().upper(),
    )
    db.add(eq)
    db.commit()
    db.refresh(eq)
    return eq


@router.delete('/{major_code}/equivalents/{eq_id}', status_code=204)
def delete_equivalent(major_code: str, eq_id: int, user: User = Depends(require_staff), db: Session = Depends(get_db)):
    ensure_major_access(major_code, db, user)
    eq = db.get(CourseEquivalent, eq_id)
    if not eq:
        raise HTTPException(status_code=404, detail='Equivalent not found')
    db.delete(eq)
    db.commit()


# ---------------------------------------------------------------------------
# Assignments (SCE / FEC / etc.)
# ---------------------------------------------------------------------------

class AssignmentIn(BaseModel):
    student_id: str
    assignment_type: str
    course_code: str


class AssignmentOut(BaseModel):
    id: int
    student_id: str
    assignment_type: str
    course_code: str

    model_config = {'from_attributes': True}


@router.get('/{major_code}/assignments', response_model=list[AssignmentOut])
def list_assignments(major_code: str, user: User = Depends(require_staff), db: Session = Depends(get_db)):
    ensure_major_access(major_code, db, user)
    major = _get_major_or_404(db, major_code)
    return db.scalars(select(CourseAssignment).where(CourseAssignment.major_id == major.id)).all()


@router.post('/{major_code}/assignments', response_model=AssignmentOut, status_code=201)
def add_assignment(major_code: str, body: AssignmentIn, user: User = Depends(require_staff), db: Session = Depends(get_db)):
    ensure_major_access(major_code, db, user)
    major = _get_major_or_404(db, major_code)
    existing = db.scalar(
        select(CourseAssignment).where(
            CourseAssignment.major_id == major.id,
            CourseAssignment.student_id == body.student_id.strip(),
            CourseAssignment.assignment_type == body.assignment_type.strip(),
        )
    )
    if existing:
        existing.course_code = body.course_code.strip().upper()
        db.commit()
        db.refresh(existing)
        return existing
    asgn = CourseAssignment(
        major_id=major.id,
        student_id=body.student_id.strip(),
        assignment_type=body.assignment_type.strip(),
        course_code=body.course_code.strip().upper(),
    )
    db.add(asgn)
    db.commit()
    db.refresh(asgn)
    return asgn


@router.delete('/{major_code}/assignments/{asgn_id}', status_code=204)
def delete_assignment(major_code: str, asgn_id: int, user: User = Depends(require_staff), db: Session = Depends(get_db)):
    ensure_major_access(major_code, db, user)
    asgn = db.get(CourseAssignment, asgn_id)
    if not asgn:
        raise HTTPException(status_code=404, detail='Assignment not found')
    db.delete(asgn)
    db.commit()


@router.post('/{major_code}/assignments/bulk-import', status_code=200)
async def bulk_import_assignments(
    major_code: str,
    file: UploadFile = File(...),
    user: User = Depends(require_staff),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """
    Accept a CSV with columns: student_id, assignment_type, course
    Upsert all rows for this major.
    """
    ensure_major_access(major_code, db, user)
    major = _get_major_or_404(db, major_code)
    content = await file.read()
    reader = csv.DictReader(io.StringIO(content.decode('utf-8-sig')))
    inserted = 0
    for row in reader:
        sid = str(row.get('student_id', '')).strip()
        atype = str(row.get('assignment_type', '')).strip()
        course = str(row.get('course', '')).strip().upper()
        if not sid or not atype or not course:
            continue
        existing = db.scalar(
            select(CourseAssignment).where(
                CourseAssignment.major_id == major.id,
                CourseAssignment.student_id == sid,
                CourseAssignment.assignment_type == atype,
            )
        )
        if existing:
            existing.course_code = course
        else:
            db.add(CourseAssignment(major_id=major.id, student_id=sid, assignment_type=atype, course_code=course))
        inserted += 1
    db.commit()
    return {'imported': inserted}


# ---------------------------------------------------------------------------
# Assignment types
# ---------------------------------------------------------------------------

class AssignmentTypesIn(BaseModel):
    types: list[str]


@router.get('/{major_code}/assignment-types')
def get_assignment_types(major_code: str, user: User = Depends(require_staff), db: Session = Depends(get_db)) -> dict:
    ensure_major_access(major_code, db, user)
    major = _get_major_or_404(db, major_code)
    return {'types': major.assignment_types or ['S.C.E', 'F.E.C']}


@router.put('/{major_code}/assignment-types')
def update_assignment_types(
    major_code: str,
    body: AssignmentTypesIn,
    user: User = Depends(require_staff),
    db: Session = Depends(get_db),
) -> dict:
    ensure_major_access(major_code, db, user)
    major = _get_major_or_404(db, major_code)
    types = [t.strip() for t in body.types if t.strip()]
    major.assignment_types = types
    db.commit()
    return {'types': types}

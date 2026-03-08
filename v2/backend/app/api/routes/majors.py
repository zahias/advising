from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_admin, require_staff
from app.models import Major, User
from app.schemas.admin import MajorCreateRequest, MajorResponse
from app.services.audit import log_event

router = APIRouter(prefix='/majors', tags=['majors'])


@router.get('', response_model=list[MajorResponse])
def list_majors(_: User = Depends(require_staff), db: Session = Depends(get_db)) -> list[Major]:
    return list(db.scalars(select(Major).order_by(Major.code.asc())))


@router.post('', response_model=MajorResponse)
def create_major(payload: MajorCreateRequest, admin: User = Depends(require_admin), db: Session = Depends(get_db)) -> Major:
    existing = db.scalar(select(Major).where(Major.code == payload.code))
    if existing:
        raise HTTPException(status_code=400, detail='Major already exists')
    major = Major(code=payload.code, name=payload.name)
    db.add(major)
    db.flush()
    log_event(db, admin.id, 'major.created', 'major', str(major.id), {'code': major.code})
    db.commit()
    db.refresh(major)
    return major

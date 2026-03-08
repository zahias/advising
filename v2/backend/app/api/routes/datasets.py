from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import ensure_major_access, get_db, require_admin, require_staff
from app.models import DatasetVersion, User
from app.schemas.admin import DatasetVersionResponse
from app.services.audit import log_event
from app.services.dataset_service import upload_dataset

router = APIRouter(prefix='/datasets', tags=['datasets'])


@router.get('/{major_code}', response_model=list[DatasetVersionResponse])
def list_dataset_versions(major_code: str, user: User = Depends(require_staff), db: Session = Depends(get_db)) -> list[DatasetVersion]:
    ensure_major_access(major_code, db, user)
    return list(
        db.scalars(
            select(DatasetVersion).where(DatasetVersion.major.has(code=major_code)).order_by(DatasetVersion.created_at.desc())
        )
    )


@router.post('/upload', response_model=DatasetVersionResponse)
async def upload_dataset_route(
    major_code: str = Form(...),
    dataset_type: str = Form(...),
    file: UploadFile = File(...),
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> DatasetVersion:
    try:
        version = upload_dataset(
            db,
            major_code=major_code,
            dataset_type=dataset_type,
            filename=file.filename,
            content=await file.read(),
            user_id=user.id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    log_event(db, user.id, 'dataset.uploaded', 'dataset_version', str(version.id), {'major_code': major_code, 'dataset_type': dataset_type})
    db.commit()
    db.refresh(version)
    return version

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_admin
from app.models import BackupRun, User
from app.schemas.admin import BackupRunResponse
from app.schemas.common import MessageResponse

router = APIRouter(prefix='/backups', tags=['backups'])


@router.get('', response_model=list[BackupRunResponse])
def list_backups(_: User = Depends(require_admin), db: Session = Depends(get_db)):
    return list(db.scalars(select(BackupRun).order_by(BackupRun.created_at.desc())))


@router.post('/trigger', response_model=MessageResponse)
def trigger_backup(_: User = Depends(require_admin)):
    return MessageResponse(message='Use the Render cron job or `python -m app.services.backup_job` to create a backup run.')

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_admin
from app.core.config import get_settings
from app.models import User
from app.schemas.common import MessageResponse
from app.services.import_service import import_legacy_snapshot

router = APIRouter(prefix='/imports', tags=['imports'])


@router.post('/legacy/{major_code}')
def import_legacy_route(major_code: str, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    settings = get_settings()
    try:
        return import_legacy_snapshot(db, major_code=major_code, import_root=settings.legacy_imports_path, user_id=admin.id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

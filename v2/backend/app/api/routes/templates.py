from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_admin, require_staff
from app.models import User
from app.schemas.admin import TemplateResponse, TemplateUpdateRequest
from app.services.template_service import list_templates, upsert_template

router = APIRouter(prefix='/templates', tags=['templates'])


@router.get('', response_model=list[TemplateResponse])
def list_templates_route(major_code: Optional[str] = None, user: User = Depends(require_staff), db: Session = Depends(get_db)):
    return list_templates(db, major_code)


@router.post('', response_model=TemplateResponse)
def upsert_template_route(payload: TemplateUpdateRequest, _: User = Depends(require_admin), db: Session = Depends(get_db)):
    try:
        return upsert_template(
            db,
            major_code=payload.major_code,
            template_key=payload.template_key,
            display_name=payload.display_name,
            description=payload.description,
            subject_template=payload.subject_template,
            body_template=payload.body_template,
            include_summary=payload.include_summary,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

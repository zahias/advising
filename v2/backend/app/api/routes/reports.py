from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.api.deps import ensure_major_access, get_db, require_staff
from app.models import User
from app.services.student_service import export_student_report

router = APIRouter(prefix='/reports', tags=['reports'])


@router.get('/{major_code}/student/{student_id}')
def student_report_route(major_code: str, student_id: str, user: User = Depends(require_staff), db: Session = Depends(get_db)):
    ensure_major_access(major_code, db, user)
    filename, payload = export_student_report(db, major_code, student_id)
    headers = {'Content-Disposition': f'attachment; filename={filename}'}
    return Response(content=payload, media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', headers=headers)

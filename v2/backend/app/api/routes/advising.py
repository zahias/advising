from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import ensure_major_access, get_db, require_staff
from app.models import User
from app.schemas.advising import BypassRequest, ExclusionRequest, HiddenCoursesRequest, SaveSelectionRequest, SelectionPayload, SessionSummary
from app.schemas.common import MessageResponse
from app.services.student_service import (
    list_sessions,
    remove_bypass,
    replace_exclusions,
    replace_hidden_courses,
    restore_latest_session,
    save_selection,
    set_bypass,
)

router = APIRouter(prefix='/advising', tags=['advising'])


@router.post('/selection', response_model=MessageResponse)
def save_selection_route(payload: SaveSelectionRequest, user: User = Depends(require_staff), db: Session = Depends(get_db)):
    ensure_major_access(payload.major_code, db, user)
    try:
        save_selection(db, major_code=payload.major_code, period_code=payload.period_code, student_id=payload.student_id, student_name=payload.student_name, payload=payload.selection, user_id=user.id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return MessageResponse(message='Selection saved.')


@router.get('/sessions/{major_code}', response_model=list[SessionSummary])
def list_sessions_route(major_code: str, period_code: Optional[str] = None, student_id: Optional[str] = None, user: User = Depends(require_staff), db: Session = Depends(get_db)):
    ensure_major_access(major_code, db, user)
    sessions = list_sessions(db, major_code, period_code=period_code, student_id=student_id)
    return [SessionSummary(id=item.id, title=item.title, student_id=item.student_id, student_name=item.payload.get('student_name', item.student_id), created_at=item.created_at, summary=item.summary) for item in sessions]


@router.post('/sessions/{major_code}/{period_code}/{student_id}/restore', response_model=MessageResponse)
def restore_session_route(major_code: str, period_code: str, student_id: str, user: User = Depends(require_staff), db: Session = Depends(get_db)):
    ensure_major_access(major_code, db, user)
    try:
        restore_latest_session(db, major_code, period_code, student_id, user.id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return MessageResponse(message='Latest session restored.')


@router.post('/bypasses', response_model=MessageResponse)
def set_bypass_route(payload: BypassRequest, user: User = Depends(require_staff), db: Session = Depends(get_db)):
    ensure_major_access(payload.major_code, db, user)
    set_bypass(db, major_code=payload.major_code, student_id=payload.student_id, course_code=payload.course_code, note=payload.note, advisor_name=payload.advisor_name or user.full_name)
    return MessageResponse(message='Bypass saved.')


@router.delete('/bypasses/{major_code}/{student_id}/{course_code}', response_model=MessageResponse)
def remove_bypass_route(major_code: str, student_id: str, course_code: str, user: User = Depends(require_staff), db: Session = Depends(get_db)):
    ensure_major_access(major_code, db, user)
    remove_bypass(db, major_code, student_id, course_code)
    return MessageResponse(message='Bypass removed.')


@router.post('/hidden-courses', response_model=list[str])
def hidden_courses_route(payload: HiddenCoursesRequest, user: User = Depends(require_staff), db: Session = Depends(get_db)):
    ensure_major_access(payload.major_code, db, user)
    return replace_hidden_courses(db, payload.major_code, payload.student_id, payload.course_codes)


@router.post('/exclusions', response_model=dict[str, list[str]])
def exclusions_route(payload: ExclusionRequest, user: User = Depends(require_staff), db: Session = Depends(get_db)):
    ensure_major_access(payload.major_code, db, user)
    return replace_exclusions(db, payload.major_code, payload.student_ids, payload.course_codes)

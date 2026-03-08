from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import Any, Optional

import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    AdvisingPeriod,
    Bypass,
    CourseExclusion,
    EmailRosterEntry,
    HiddenCourse,
    Major,
    SessionSnapshot,
    StudentSelection,
)
from app.schemas.advising import EligibilityCourse, SelectionPayload, StudentEligibilityResponse
from app.services.dataset_service import dataset_dataframe
from app.services.period_service import current_period

ROOT_DIR = Path(__file__).resolve().parents[4]
import sys
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from eligibility_utils import (  # noqa: E402
    build_requisites_str,
    check_course_completed,
    check_course_registered,
    check_eligibility,
    get_mutual_concurrent_pairs,
    get_student_standing,
)
from reporting import apply_excel_formatting  # noqa: E402


def _major(session: Session, major_code: str) -> Major:
    major = session.scalar(select(Major).where(Major.code == major_code))
    if not major:
        raise ValueError(f'Unknown major: {major_code}')
    return major


def _courses_df(session: Session, major_code: str) -> pd.DataFrame:
    return dataset_dataframe(session, major_code, 'courses')


def _progress_df(session: Session, major_code: str) -> pd.DataFrame:
    return dataset_dataframe(session, major_code, 'progress')


def search_students(session: Session, major_code: str, query: Optional[str] = None) -> list[dict[str, Any]]:
    progress_df = _progress_df(session, major_code)
    if progress_df.empty:
        return []
    working = progress_df.copy()
    working['Total Credits'] = pd.to_numeric(working.get('# of Credits Completed', 0), errors='coerce').fillna(0) + pd.to_numeric(working.get('# Registered', 0), errors='coerce').fillna(0)
    working['Standing'] = working['Total Credits'].apply(get_student_standing)
    working['Remaining Credits'] = pd.to_numeric(working.get('# Remaining', 0), errors='coerce').fillna(0)
    if query:
        q = query.lower().strip()
        working = working[
            working['NAME'].astype(str).str.lower().str.contains(q, na=False)
            | working['ID'].astype(str).str.lower().str.contains(q, na=False)
        ]
    results: list[dict[str, Any]] = []
    for _, row in working.iterrows():
        results.append({
            'student_id': str(row.get('ID', '')),
            'student_name': str(row.get('NAME', '')),
            'standing': str(row.get('Standing', '')),
            'total_credits': float(row.get('Total Credits', 0) or 0),
            'remaining_credits': float(row.get('Remaining Credits', 0) or 0),
        })
    return results


def _student_row(progress_df: pd.DataFrame, student_id: str) -> pd.Series:
    match = progress_df.loc[progress_df['ID'].astype(str) == str(student_id)]
    if match.empty:
        raise ValueError(f'Student not found: {student_id}')
    return match.iloc[0]


def _selection_for_student(session: Session, major_id: int, period_id: int, student_id: str, student_name: str) -> StudentSelection:
    selection = session.scalar(
        select(StudentSelection).where(
            StudentSelection.major_id == major_id,
            StudentSelection.period_id == period_id,
            StudentSelection.student_id == str(student_id),
        )
    )
    if selection:
        return selection
    selection = StudentSelection(
        major_id=major_id,
        period_id=period_id,
        student_id=str(student_id),
        student_name=student_name,
        advised=[],
        optional=[],
        repeat=[],
        note='',
    )
    session.add(selection)
    session.flush()
    return selection


def _bypass_map(session: Session, major_id: int, student_id: str) -> dict[str, dict[str, Any]]:
    items = session.scalars(select(Bypass).where(Bypass.major_id == major_id, Bypass.student_id == str(student_id))).all()
    return {item.course_code: {'note': item.note, 'advisor': item.advisor_name, 'timestamp': item.updated_at.isoformat()} for item in items}


def _hidden_courses(session: Session, major_id: int, student_id: str) -> set[str]:
    return {item.course_code for item in session.scalars(select(HiddenCourse).where(HiddenCourse.major_id == major_id, HiddenCourse.student_id == str(student_id))).all()}


def _excluded_courses(session: Session, major_id: int, student_id: str) -> set[str]:
    return {item.course_code for item in session.scalars(select(CourseExclusion).where(CourseExclusion.major_id == major_id, CourseExclusion.student_id == str(student_id))).all()}


def student_eligibility(session: Session, major_code: str, student_id: str) -> StudentEligibilityResponse:
    major = _major(session, major_code)
    period = current_period(session, major_code)
    if not period:
        raise ValueError(f'No active period for {major_code}')

    courses_df = _courses_df(session, major_code)
    progress_df = _progress_df(session, major_code)
    if courses_df.empty or progress_df.empty:
        raise ValueError('Courses and progress datasets must be uploaded first')

    student_row = _student_row(progress_df, student_id)
    selection = _selection_for_student(session, major.id, period.id, str(student_id), str(student_row.get('NAME', '')))
    selection_payload = SelectionPayload(
        advised=[str(x) for x in selection.advised],
        optional=[str(x) for x in selection.optional],
        repeat=[str(x) for x in selection.repeat],
        note=selection.note or '',
    )
    hidden_courses = _hidden_courses(session, major.id, student_id) | _excluded_courses(session, major.id, student_id)
    bypass_map = _bypass_map(session, major.id, student_id)
    mutual_pairs = get_mutual_concurrent_pairs(courses_df)

    eligibility_rows: list[EligibilityCourse] = []
    advised_credits = 0.0
    optional_credits = 0.0
    repeat_credits = 0.0

    for _, info in courses_df.iterrows():
        code = str(info.get('Course Code', ''))
        if not code or code in hidden_courses:
            continue
        status, justification = check_eligibility(
            student_row,
            code,
            list(selection_payload.advised) + list(selection_payload.optional),
            courses_df,
            registered_courses=[],
            ignore_offered=False,
            mutual_pairs=mutual_pairs,
            bypass_map=bypass_map,
        )
        action = ''
        if code in selection_payload.repeat:
            action = 'Advised-Repeat'
        elif code in selection_payload.advised:
            action = 'Advised'
        elif code in selection_payload.optional:
            action = 'Optional'
        credits = float(info.get('Credits', 0) or 0)
        if code in selection_payload.advised:
            advised_credits += credits
        if code in selection_payload.optional:
            optional_credits += credits
        if code in selection_payload.repeat:
            repeat_credits += credits
        eligibility_rows.append(
            EligibilityCourse(
                course_code=code,
                title=str(info.get('Title', '') or info.get('Course Title', '') or code),
                course_type=str(info.get('Type', '')),
                requisites=build_requisites_str(info),
                eligibility_status=status,
                justification=justification,
                offered=str(info.get('Offered', '')).strip().lower() == 'yes',
                action=action,
            )
        )

    credits_completed = float(student_row.get('# of Credits Completed', 0) or 0)
    credits_registered = float(student_row.get('# Registered', 0) or 0)
    credits_remaining = float(student_row.get('# Remaining', student_row.get('Remaining Credits', 0)) or 0)
    standing = get_student_standing(credits_completed + credits_registered)
    session.commit()
    return StudentEligibilityResponse(
        student_id=str(student_row.get('ID')),
        student_name=str(student_row.get('NAME', '')),
        standing=standing,
        credits_completed=credits_completed,
        credits_registered=credits_registered,
        credits_remaining=credits_remaining,
        advised_credits=advised_credits,
        optional_credits=optional_credits,
        repeat_credits=repeat_credits,
        eligibility=eligibility_rows,
        selection=selection_payload,
        bypasses=bypass_map,
        hidden_courses=sorted(hidden_courses),
    )


def save_selection(session: Session, *, major_code: str, period_code: str, student_id: str, student_name: str, payload: SelectionPayload, user_id: Optional[int]) -> StudentSelection:
    major = _major(session, major_code)
    period = session.scalar(select(AdvisingPeriod).where(AdvisingPeriod.period_code == period_code, AdvisingPeriod.major_id == major.id))
    if not period:
        raise ValueError(f'Unknown period: {period_code}')
    selection = _selection_for_student(session, major.id, period.id, student_id, student_name)
    selection.advised = [str(x) for x in payload.advised]
    selection.optional = [str(x) for x in payload.optional if str(x) not in selection.advised]
    selection.repeat = [str(x) for x in payload.repeat]
    selection.note = payload.note
    selection.last_saved_by_user_id = user_id
    snapshot = SessionSnapshot(
        major_id=major.id,
        period_id=period.id,
        student_id=student_id,
        title=f'{student_name} ({student_id}) - {period.semester} {period.year}',
        payload={
            'selection': payload.model_dump(),
            'student_id': student_id,
            'student_name': student_name,
            'period_code': period.period_code,
        },
        summary={
            'advised': payload.advised,
            'optional': payload.optional,
            'repeat': payload.repeat,
        },
        created_by_user_id=user_id,
    )
    session.add(snapshot)
    session.commit()
    session.refresh(selection)
    return selection


def list_sessions(session: Session, major_code: str, period_code: Optional[str] = None, student_id: Optional[str] = None) -> list[SessionSnapshot]:
    major = _major(session, major_code)
    stmt = select(SessionSnapshot).where(SessionSnapshot.major_id == major.id)
    if period_code:
        period = session.scalar(select(AdvisingPeriod).where(AdvisingPeriod.period_code == period_code, AdvisingPeriod.major_id == major.id))
        if period:
            stmt = stmt.where(SessionSnapshot.period_id == period.id)
    if student_id:
        stmt = stmt.where(SessionSnapshot.student_id == str(student_id))
    return list(session.scalars(stmt.order_by(SessionSnapshot.created_at.desc())))


def restore_latest_session(session: Session, major_code: str, period_code: str, student_id: str, user_id: Optional[int]) -> StudentSelection:
    sessions = list_sessions(session, major_code, period_code=period_code, student_id=student_id)
    if not sessions:
        raise ValueError('No saved session found for student')
    latest = sessions[0]
    payload = SelectionPayload(**latest.payload.get('selection', {}))
    return save_selection(
        session,
        major_code=major_code,
        period_code=period_code,
        student_id=student_id,
        student_name=latest.payload.get('student_name', student_id),
        payload=payload,
        user_id=user_id,
    )


def set_bypass(session: Session, *, major_code: str, student_id: str, course_code: str, note: str, advisor_name: str) -> Bypass:
    major = _major(session, major_code)
    existing = session.scalar(select(Bypass).where(Bypass.major_id == major.id, Bypass.student_id == str(student_id), Bypass.course_code == course_code))
    if existing:
        existing.note = note
        existing.advisor_name = advisor_name
        session.commit()
        session.refresh(existing)
        return existing
    bypass = Bypass(major_id=major.id, student_id=str(student_id), course_code=course_code, note=note, advisor_name=advisor_name)
    session.add(bypass)
    session.commit()
    session.refresh(bypass)
    return bypass


def remove_bypass(session: Session, major_code: str, student_id: str, course_code: str) -> None:
    major = _major(session, major_code)
    session.query(Bypass).filter(Bypass.major_id == major.id, Bypass.student_id == str(student_id), Bypass.course_code == course_code).delete()
    session.commit()


def replace_hidden_courses(session: Session, major_code: str, student_id: str, course_codes: list[str]) -> list[str]:
    major = _major(session, major_code)
    session.query(HiddenCourse).filter(HiddenCourse.major_id == major.id, HiddenCourse.student_id == str(student_id)).delete()
    for code in sorted(set(map(str, course_codes))):
        session.add(HiddenCourse(major_id=major.id, student_id=str(student_id), course_code=code))
    session.commit()
    return sorted(set(map(str, course_codes)))


def replace_exclusions(session: Session, major_code: str, student_ids: list[str], course_codes: list[str]) -> dict[str, list[str]]:
    major = _major(session, major_code)
    result: dict[str, list[str]] = {}
    for student_id in student_ids:
        session.query(CourseExclusion).filter(CourseExclusion.major_id == major.id, CourseExclusion.student_id == str(student_id)).delete()
        result[str(student_id)] = []
        for code in sorted(set(map(str, course_codes))):
            session.add(CourseExclusion(major_id=major.id, student_id=str(student_id), course_code=code))
            result[str(student_id)].append(code)
    session.commit()
    return result


def export_student_report(session: Session, major_code: str, student_id: str) -> tuple[str, bytes]:
    payload = student_eligibility(session, major_code, student_id)
    rows = [item.model_dump() for item in payload.eligibility]
    export_df = pd.DataFrame(rows)
    for drop_col in ('course_type', 'requisites'):
        if drop_col in export_df.columns:
            export_df = export_df.drop(columns=[drop_col])
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        export_df.to_excel(writer, index=False, sheet_name='Advising')
    apply_excel_formatting(
        output=output,
        student_name=payload.student_name,
        student_id=int(float(payload.student_id)),
        credits_completed=int(payload.credits_completed),
        standing=payload.standing,
        note=payload.selection.note,
        advised_credits=int(payload.advised_credits + payload.repeat_credits),
        optional_credits=int(payload.optional_credits),
        period_info=f'{major_code} Advising',
    )
    return f'Advising_{student_id}.xlsx', output.getvalue()


def get_student_email(session: Session, major_code: str, student_id: str) -> Optional[str]:
    major = _major(session, major_code)
    roster = session.scalar(select(EmailRosterEntry).where(EmailRosterEntry.major_id == major.id, EmailRosterEntry.student_id == str(student_id)))
    return roster.email if roster else None

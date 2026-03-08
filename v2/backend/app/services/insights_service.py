from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Bypass, Major, SessionSnapshot, StudentSelection
from app.schemas.insights import CourseOfferingRecommendation, DashboardMetrics, ScheduleConflictGroup
from app.services.dataset_service import dataset_dataframe
from app.services.period_service import current_period

ROOT_DIR = Path(__file__).resolve().parents[4]
import sys
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from eligibility_utils import check_course_completed, check_course_registered, check_eligibility, get_mutual_concurrent_pairs, get_student_standing, parse_requirements  # noqa: E402


def dashboard_metrics(session: Session, major_code: str) -> DashboardMetrics:
    major = session.scalar(select(Major).where(Major.code == major_code))
    if not major:
        raise ValueError(f'Unknown major: {major_code}')
    progress_df = dataset_dataframe(session, major_code, 'progress')
    if progress_df.empty:
        return DashboardMetrics(total_students=0, advised_students=0, not_advised_students=0, progress_percent=0, graduating_soon_unadvised=[], recent_activity=[])
    period = current_period(session, major_code)
    advised_ids = set()
    recent_activity: list[dict[str, Any]] = []
    if period:
        latest_sessions = list(session.scalars(select(SessionSnapshot).where(SessionSnapshot.major_id == major.id, SessionSnapshot.period_id == period.id).order_by(SessionSnapshot.created_at.desc())))
        for snap in latest_sessions:
            advised_ids.add(str(snap.student_id))
        for snap in latest_sessions[:5]:
            recent_activity.append({'student_name': snap.payload.get('student_name', snap.student_id), 'created_at': snap.created_at.isoformat()})
    total_students = len(progress_df)
    advised_count = 0
    graduating_soon_unadvised: list[str] = []
    for _, row in progress_df.iterrows():
        student_id = str(row.get('ID'))
        remaining = float(row.get('# Remaining', row.get('Remaining Credits', 999)) or 999)
        if student_id in advised_ids:
            advised_count += 1
        elif remaining <= 36:
            graduating_soon_unadvised.append(str(row.get('NAME', student_id)))
    percent = int((advised_count / total_students) * 100) if total_students else 0
    return DashboardMetrics(
        total_students=total_students,
        advised_students=advised_count,
        not_advised_students=total_students - advised_count,
        progress_percent=percent,
        graduating_soon_unadvised=graduating_soon_unadvised[:5],
        recent_activity=recent_activity,
    )


def _build_prerequisite_map(courses_df: pd.DataFrame) -> dict[str, list[str]]:
    prereq_map: dict[str, list[str]] = {}
    for _, row in courses_df.iterrows():
        course_code = str(row.get('Course Code', ''))
        prereqs = parse_requirements(row.get('Prerequisite'))
        for prereq in prereqs:
            prereq_map.setdefault(prereq, []).append(course_code)
    return prereq_map


def _calculate_cascading_eligibility(courses_df: pd.DataFrame, progress_df: pd.DataFrame, offered_course: str, mutual_pairs: dict[str, list[str]]) -> int:
    unlocked_students = 0
    for _, student in progress_df.iterrows():
        if check_course_completed(student, offered_course) or check_course_registered(student, offered_course):
            continue
        simulated = [offered_course]
        for _, course_row in courses_df.iterrows():
            target_course = str(course_row.get('Course Code', ''))
            if target_course == offered_course:
                continue
            status, _ = check_eligibility(student, target_course, [], courses_df, registered_courses=simulated, ignore_offered=True, mutual_pairs=mutual_pairs)
            if status == 'Eligible':
                unlocked_students += 1
                break
    return unlocked_students


def course_offering_recommendations(session: Session, major_code: str, graduation_threshold: int = 30, min_eligible_students: int = 3) -> list[CourseOfferingRecommendation]:
    courses_df = dataset_dataframe(session, major_code, 'courses')
    progress_df = dataset_dataframe(session, major_code, 'progress')
    if courses_df.empty or progress_df.empty:
        return []
    progress_df = progress_df.copy()
    progress_df['Remaining Credits'] = pd.to_numeric(progress_df.get('# Remaining', 0), errors='coerce').fillna(0)
    mutual_pairs = get_mutual_concurrent_pairs(courses_df)
    prereq_map = _build_prerequisite_map(courses_df)
    recommendations: list[CourseOfferingRecommendation] = []
    for _, course_row in courses_df.iterrows():
        course = str(course_row.get('Course Code', ''))
        if not course:
            continue
        eligible = 0
        graduating = 0
        for _, student in progress_df.iterrows():
            if check_course_completed(student, course) or check_course_registered(student, course):
                continue
            status, _ = check_eligibility(student, course, [], courses_df, registered_courses=[], ignore_offered=True, mutual_pairs=mutual_pairs)
            if status == 'Eligible':
                eligible += 1
                if float(student.get('Remaining Credits', 999) or 999) <= graduation_threshold:
                    graduating += 1
        if eligible < min_eligible_students:
            continue
        bottleneck = len(prereq_map.get(course, []))
        cascading = _calculate_cascading_eligibility(courses_df, progress_df, course, mutual_pairs)
        score = eligible + (graduating * 2) + bottleneck + cascading
        recommendations.append(
            CourseOfferingRecommendation(
                course=course,
                priority_score=float(score),
                currently_eligible=eligible,
                graduating_students=graduating,
                bottleneck_score=bottleneck,
                cascading_eligible=cascading,
                reason='Ranked by eligible demand, graduating pressure, bottleneck unlocks, and cascading impact.',
            )
        )
    return sorted(recommendations, key=lambda item: item.priority_score, reverse=True)


def all_students_view(session: Session, major_code: str) -> list[dict[str, Any]]:
    courses_df = dataset_dataframe(session, major_code, 'courses')
    progress_df = dataset_dataframe(session, major_code, 'progress')
    major = session.scalar(select(Major).where(Major.code == major_code))
    if courses_df.empty or progress_df.empty or not major:
        return []
    period = current_period(session, major_code)
    period_id = period.id if period else None
    bypasses = session.scalars(select(Bypass).where(Bypass.major_id == major.id)).all()
    bypass_map: dict[tuple[str, str], dict[str, Any]] = {(item.student_id, item.course_code): {'note': item.note, 'advisor': item.advisor_name} for item in bypasses}
    selections_by_student: dict[str, StudentSelection] = {}
    if period_id:
        for selection in session.scalars(select(StudentSelection).where(StudentSelection.major_id == major.id, StudentSelection.period_id == period_id)).all():
            selections_by_student[selection.student_id] = selection
    mutual_pairs = get_mutual_concurrent_pairs(courses_df)
    all_courses = [str(code) for code in courses_df['Course Code'].dropna().tolist()]
    rows: list[dict[str, Any]] = []
    for _, student in progress_df.iterrows():
        sid = str(student.get('ID'))
        total = float(student.get('# of Credits Completed', 0) or 0) + float(student.get('# Registered', 0) or 0)
        selection = selections_by_student.get(sid)
        row = {
            'student_id': sid,
            'student_name': str(student.get('NAME', sid)),
            'standing': get_student_standing(total),
            'total_credits': total,
            'remaining_credits': float(student.get('# Remaining', student.get('Remaining Credits', 0)) or 0),
            'advising_status': 'Advised' if selection and (selection.advised or selection.optional or selection.repeat or selection.note) else 'Not Advised',
            'courses': {},
        }
        advised = set(selection.advised if selection else [])
        optional = set(selection.optional if selection else [])
        repeat = set(selection.repeat if selection else [])
        for course in all_courses:
            if course in repeat:
                code = 'ar'
            elif check_course_completed(student, course):
                code = 'c'
            elif check_course_registered(student, course):
                code = 'r'
            elif course in optional:
                code = 'o'
            elif course in advised:
                code = 'a'
            else:
                status, _ = check_eligibility(student, course, list(advised), courses_df, registered_courses=[], ignore_offered=True, mutual_pairs=mutual_pairs, bypass_map={(course): bypass_map.get((sid, course), {})} if (sid, course) in bypass_map else {})
                code = 'b' if status == 'Eligible (Bypass)' else 'na' if status == 'Eligible' else 'ne'
            row['courses'][course] = code
        rows.append(row)
    return rows


def qaa_sheet(session: Session, major_code: str) -> list[dict[str, Any]]:
    rows = all_students_view(session, major_code)
    return [
        {
            'student_id': row['student_id'],
            'student_name': row['student_name'],
            'standing': row['standing'],
            'remaining_credits': row['remaining_credits'],
            'advising_status': row['advising_status'],
        }
        for row in rows
    ]


def schedule_conflicts(session: Session, major_code: str) -> list[ScheduleConflictGroup]:
    major = session.scalar(select(Major).where(Major.code == major_code))
    if not major:
        raise ValueError(f'Unknown major: {major_code}')
    period = current_period(session, major_code)
    if not period:
        return []

    progress_records = dataset_dataframe(session, major_code, 'progress').to_dict(orient='records')
    names_by_id = {str(row.get('ID')): str(row.get('NAME', row.get('ID'))) for row in progress_records}
    grouped: dict[tuple[str, ...], list[str]] = {}
    selections = session.scalars(
        select(StudentSelection).where(
            StudentSelection.major_id == major.id,
            StudentSelection.period_id == period.id,
        )
    ).all()
    for selection in selections:
        key = tuple(sorted(set([*selection.advised, *selection.repeat])))
        if not key:
            continue
        grouped.setdefault(key, []).append(selection.student_id)

    results: list[ScheduleConflictGroup] = []
    for courses, student_ids in grouped.items():
        if len(student_ids) < 2:
            continue
        results.append(
            ScheduleConflictGroup(
                group_name=' / '.join(courses),
                student_count=len(student_ids),
                courses=list(courses),
                student_ids=[f"{sid} - {names_by_id.get(sid, sid)}" for sid in student_ids],
            )
        )
    return sorted(results, key=lambda item: item.student_count, reverse=True)

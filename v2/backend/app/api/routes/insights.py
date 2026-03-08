from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import ensure_major_access, get_db, require_staff
from app.models import User
from app.schemas.insights import CourseOfferingRecommendation, DashboardMetrics, ScheduleConflictGroup
from app.services.insights_service import all_students_view, course_offering_recommendations, dashboard_metrics, qaa_sheet, schedule_conflicts

router = APIRouter(prefix='/insights', tags=['insights'])


@router.get('/{major_code}/dashboard', response_model=DashboardMetrics)
def dashboard_route(major_code: str, user: User = Depends(require_staff), db: Session = Depends(get_db)):
    ensure_major_access(major_code, db, user)
    return dashboard_metrics(db, major_code)


@router.get('/{major_code}/all-students')
def all_students_route(major_code: str, user: User = Depends(require_staff), db: Session = Depends(get_db)):
    ensure_major_access(major_code, db, user)
    return all_students_view(db, major_code)


@router.get('/{major_code}/course-planner', response_model=list[CourseOfferingRecommendation])
def planner_route(
    major_code: str,
    graduation_threshold: int = Query(default=30),
    min_eligible_students: int = Query(default=3),
    user: User = Depends(require_staff),
    db: Session = Depends(get_db),
):
    ensure_major_access(major_code, db, user)
    return course_offering_recommendations(db, major_code, graduation_threshold, min_eligible_students)


@router.get('/{major_code}/qaa')
def qaa_route(major_code: str, user: User = Depends(require_staff), db: Session = Depends(get_db)):
    ensure_major_access(major_code, db, user)
    return qaa_sheet(db, major_code)


@router.get('/{major_code}/schedule-conflicts', response_model=list[ScheduleConflictGroup])
def schedule_conflicts_route(major_code: str, user: User = Depends(require_staff), db: Session = Depends(get_db)):
    ensure_major_access(major_code, db, user)
    return schedule_conflicts(db, major_code)

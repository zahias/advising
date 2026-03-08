from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class DashboardMetrics(BaseModel):
    total_students: int
    advised_students: int
    not_advised_students: int
    progress_percent: int
    graduating_soon_unadvised: list[str]
    recent_activity: list[dict[str, Any]]


class CourseOfferingRecommendation(BaseModel):
    course: str
    priority_score: float
    currently_eligible: int
    graduating_students: int
    bottleneck_score: int
    cascading_eligible: int
    reason: str


class ScheduleConflictGroup(BaseModel):
    group_name: str
    student_count: int
    courses: list[str]
    student_ids: list[str]

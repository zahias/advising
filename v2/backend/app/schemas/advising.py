from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class StudentSearchItem(BaseModel):
    student_id: str
    student_name: str
    standing: str
    total_credits: float
    remaining_credits: float


class SelectionPayload(BaseModel):
    advised: list[str] = []
    optional: list[str] = []
    repeat: list[str] = []
    note: str = ''


class EligibilityCourse(BaseModel):
    course_code: str
    title: str
    course_type: str
    requisites: str
    eligibility_status: str
    justification: str
    offered: bool
    action: str


class StudentEligibilityResponse(BaseModel):
    student_id: str
    student_name: str
    standing: str
    credits_completed: float
    credits_registered: float
    credits_remaining: float
    advised_credits: float
    optional_credits: float
    repeat_credits: float
    eligibility: list[EligibilityCourse]
    selection: SelectionPayload
    bypasses: dict[str, dict[str, Any]]
    hidden_courses: list[str]


class SaveSelectionRequest(BaseModel):
    major_code: str
    period_code: str
    student_id: str
    student_name: str
    selection: SelectionPayload


class SessionSummary(BaseModel):
    id: int
    title: str
    student_id: str
    student_name: str
    created_at: datetime
    summary: dict[str, Any]


class BypassRequest(BaseModel):
    major_code: str
    student_id: str
    course_code: str
    note: str = ''
    advisor_name: str = ''


class HiddenCoursesRequest(BaseModel):
    major_code: str
    student_id: str
    course_codes: list[str]


class ExclusionRequest(BaseModel):
    major_code: str
    student_ids: list[str]
    course_codes: list[str]

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel


class StudentSearchItem(BaseModel):
    student_id: str
    student_name: str
    standing: str
    total_credits: float
    remaining_credits: float
    major: Optional[str] = None


class CourseCatalogItem(BaseModel):
    course_code: str
    title: str
    course_type: str
    credits: float
    offered: bool


class SelectionPayload(BaseModel):
    advised: list[str] = []
    optional: list[str] = []
    repeat: list[str] = []
    note: str = ''


class EligibilityCourse(BaseModel):
    course_code: str
    title: str
    course_type: str
    credits: float = 3
    suggested_semester: str = ''
    requisites: str
    eligibility_status: str
    justification: str
    offered: bool
    completed: bool
    registered: bool
    action: str


class IntensivePlacementCourse(BaseModel):
    course_code: str
    title: str
    excluded: bool
    # Excluded, but below an active course in its chain: counts as satisfied
    placed_out: bool = False


class PlacementInfo(BaseModel):
    source: str  # 'upload' | 'manual'
    placement_courses: list[str] = []
    updated_at: Optional[datetime] = None


class StudentEligibilityResponse(BaseModel):
    student_id: str
    student_name: str
    standing: str
    major: Optional[str] = None
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
    excluded_courses: list[str]
    intensive_placement: list[IntensivePlacementCourse] = []
    placement: Optional[PlacementInfo] = None


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
    period_code: Optional[str]
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


class BulkRestoreRequest(BaseModel):
    major_code: str
    period_code: str
    student_ids: list[str] = []


class RecommendationResponse(BaseModel):
    courses: list[str]


class ExclusionSummary(BaseModel):
    student_id: str
    student_name: str
    course_codes: list[str]


class TemplatePreviewResponse(BaseModel):
    template_key: str
    subject: str
    preview_body: str
    variables: dict[str, Optional[str]]


class ManualPlacementRequest(BaseModel):
    excluded_courses: list[str]

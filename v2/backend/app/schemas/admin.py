from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, EmailStr, computed_field, model_validator

from app.schemas.common import ORMModel


class UserCreateRequest(BaseModel):
    email: EmailStr
    full_name: str
    password: str
    role: str
    major_codes: list[str] = []


class UserResponse(ORMModel):
    id: int
    email: EmailStr
    full_name: str
    role: str
    is_active: bool
    created_at: datetime


class MajorCreateRequest(BaseModel):
    code: str
    name: str


class MajorResponse(ORMModel):
    id: int
    code: str
    name: str
    is_active: bool


class PeriodCreateRequest(BaseModel):
    major_code: str
    semester: str
    year: int
    advisor_name: str


class PeriodResponse(ORMModel):
    id: int
    major_id: int
    period_code: str
    semester: str
    year: int
    advisor_name: str
    is_active: bool
    archived_at: Optional[datetime]


class DatasetVersionResponse(ORMModel):
    id: int
    major_id: int
    dataset_type: str
    version_label: str
    original_filename: Optional[str]
    is_active: bool
    metadata_json: dict[str, Any]
    created_at: datetime

    @computed_field
    @property
    def uploaded_by(self) -> Optional[str]:
        return self.metadata_json.get('uploaded_by')


class TemplateUpdateRequest(BaseModel):
    major_code: Optional[str] = None
    template_key: str
    display_name: str
    description: str = ''
    subject_template: str
    body_template: str
    include_summary: bool = True


class TemplateResponse(ORMModel):
    id: int
    major_id: Optional[int]
    template_key: str
    display_name: str
    description: str
    subject_template: str
    body_template: str
    include_summary: bool


class BackupRunResponse(ORMModel):
    id: int
    status: str
    storage_key: Optional[str]
    manifest: dict[str, Any]
    notes: Optional[str]
    created_at: datetime


class AuditEventResponse(ORMModel):
    id: int
    actor_user_id: Optional[int]
    actor_name: Optional[str] = None
    event_type: str
    entity_type: str
    entity_id: str
    payload: dict[str, Any]
    created_at: datetime

    @model_validator(mode='before')
    @classmethod
    def populate_actor(cls, v: Any) -> Any:
        if hasattr(v, 'actor'):
            actor = getattr(v, 'actor', None)
            if actor is not None and hasattr(actor, 'full_name'):
                v.__dict__['actor_name'] = actor.full_name
        return v

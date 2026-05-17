import uuid
from datetime import datetime
from typing import Any

from pydantic import Field

from app.schemas.common import BaseResponse, BaseSchema


class ReportCreateRequest(BaseSchema):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    dashboard_id: uuid.UUID | None = None
    schedule_config: dict[str, Any] = Field(default_factory=dict)
    email_recipients: list[str] = Field(default_factory=list)


class ReportResponse(BaseResponse):
    organization_id: uuid.UUID
    dashboard_id: uuid.UUID | None
    name: str
    status: str
    schedule_config: dict[str, Any]
    email_recipients: list[str]
    last_run_at: datetime | None
    next_run_at: datetime | None

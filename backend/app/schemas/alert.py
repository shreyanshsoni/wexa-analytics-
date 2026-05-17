import uuid
from datetime import datetime
from typing import Any

from pydantic import Field

from app.schemas.common import BaseResponse, BaseSchema


class AlertCreateRequest(BaseSchema):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    saved_query_id: uuid.UUID | None = None
    condition: dict[str, Any]
    notification_channels: list[dict[str, Any]] = Field(default_factory=list)


class AlertUpdateRequest(BaseSchema):
    name: str | None = None
    condition: dict[str, Any] | None = None
    notification_channels: list[dict[str, Any]] | None = None
    status: str | None = None


class AlertResponse(BaseResponse):
    organization_id: uuid.UUID
    name: str
    description: str | None
    status: str
    condition: dict[str, Any]
    notification_channels: list[dict[str, Any]]
    muted_until: datetime | None

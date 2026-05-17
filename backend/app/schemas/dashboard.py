import uuid
from typing import Any

from pydantic import Field

from app.schemas.common import BaseResponse, BaseSchema


class DashboardCreateRequest(BaseSchema):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    refresh_interval: int | None = None
    template_type: str | None = None


class DashboardUpdateRequest(BaseSchema):
    name: str | None = None
    description: str | None = None
    refresh_interval: int | None = None
    is_public: bool | None = None


class DashboardResponse(BaseResponse):
    organization_id: uuid.UUID
    name: str
    description: str | None
    is_public: bool
    share_token: str | None
    refresh_interval: int | None
    template_type: str | None


class SavedQueryCreateRequest(BaseSchema):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    query_config: dict[str, Any] = Field(default_factory=dict)


class SavedQueryResponse(BaseResponse):
    organization_id: uuid.UUID
    name: str
    description: str | None
    query_config: dict[str, Any]

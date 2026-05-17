import uuid
from datetime import datetime
from typing import Any

from pydantic import Field, field_validator

from app.schemas.common import BaseResponse, BaseSchema


class EventIngestionRequest(BaseSchema):
    event_name: str = Field(min_length=1, max_length=255)
    properties: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime | None = None


class BatchEventIngestionRequest(BaseSchema):
    events: list[EventIngestionRequest] = Field(min_length=1, max_length=1000)

    @field_validator("events")
    @classmethod
    def validate_batch_size(cls, v: list[EventIngestionRequest]) -> list[EventIngestionRequest]:
        if len(v) > 1000:
            raise ValueError("Batch size cannot exceed 1000 events")
        return v


class EventResponse(BaseResponse):
    organization_id: uuid.UUID
    event_name: str
    properties: dict[str, Any]
    timestamp: datetime
    source: str


class IngestionResponse(BaseSchema):
    accepted: int
    message: str

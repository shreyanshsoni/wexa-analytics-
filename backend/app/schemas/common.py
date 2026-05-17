import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class BaseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class BaseResponse(BaseSchema):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime


class MessageResponse(BaseModel):
    message: str


class PaginatedResponse(BaseSchema):
    total: int
    page: int
    page_size: int
    items: list  # type: ignore[type-arg]

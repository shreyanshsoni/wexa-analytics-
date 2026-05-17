import uuid
from datetime import datetime
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict

T = TypeVar("T")


class BaseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class BaseResponse(BaseSchema):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime


class Meta(BaseModel):
    request_id: str
    timestamp: datetime


class ApiResponse(BaseModel, Generic[T]):
    data: T
    meta: Meta | None = None


class MessageResponse(BaseModel):
    message: str


class PaginatedMeta(BaseModel):
    total: int
    page: int
    per_page: int
    total_pages: int


class PaginatedResponse(BaseModel, Generic[T]):
    data: list[T]
    pagination: PaginatedMeta
    meta: Meta | None = None

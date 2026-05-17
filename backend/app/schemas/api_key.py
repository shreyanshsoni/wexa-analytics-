import uuid
from datetime import datetime

from pydantic import Field

from app.schemas.common import BaseSchema


class CreateApiKeyRequest(BaseSchema):
    name: str = Field(min_length=1, max_length=255)


class ApiKeyOut(BaseSchema):
    id: uuid.UUID
    name: str
    key_prefix: str
    is_active: bool
    last_used_at: datetime | None
    created_at: datetime


class ApiKeyCreatedOut(BaseSchema):
    id: uuid.UUID
    name: str
    key: str
    key_prefix: str
    created_at: datetime
    warning: str = "Save this key now — it will not be shown again"

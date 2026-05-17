import uuid

from app.schemas.common import BaseResponse, BaseSchema


class OrganizationResponse(BaseResponse):
    name: str
    slug: str


class MembershipResponse(BaseSchema):
    id: uuid.UUID
    user_id: uuid.UUID
    organization_id: uuid.UUID
    role: str
    user_email: str | None = None
    user_full_name: str | None = None

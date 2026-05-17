import uuid
from datetime import datetime

from pydantic import Field

from app.schemas.common import BaseResponse, BaseSchema


class OrganizationResponse(BaseResponse):
    name: str
    slug: str


class UpdateOrgRequest(BaseSchema):
    name: str = Field(min_length=1, max_length=255)


class MemberUserOut(BaseSchema):
    id: uuid.UUID
    email: str
    full_name: str


class MemberOut(BaseSchema):
    id: uuid.UUID
    user: MemberUserOut
    role: str
    joined_at: datetime


class OrgMeResponse(BaseSchema):
    org: OrganizationResponse
    members: list[MemberOut]


class UpdateMemberRoleRequest(BaseSchema):
    role: str = Field(pattern="^(admin|analyst|viewer)$")

import uuid
from datetime import datetime

from pydantic import EmailStr, Field, field_validator

from app.schemas.common import BaseResponse, BaseSchema


class SignupRequest(BaseSchema):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=1, max_length=255)
    org_name: str = Field(min_length=1, max_length=255)

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v


class LoginRequest(BaseSchema):
    email: EmailStr
    password: str


class UserOut(BaseResponse):
    email: str
    full_name: str
    is_active: bool


class OrgOut(BaseSchema):
    id: uuid.UUID
    name: str
    slug: str


class AuthData(BaseSchema):
    access_token: str
    token_type: str = "bearer"
    user: UserOut
    org: OrgOut
    role: str


class TokenData(BaseSchema):
    access_token: str
    token_type: str = "bearer"


class InviteRequest(BaseSchema):
    email: EmailStr
    role: str = Field(default="viewer", pattern="^(admin|analyst|viewer)$")


class InviteAcceptRequest(BaseSchema):
    # full_name only required for new users; ignored for existing accounts
    full_name: str | None = Field(default=None, max_length=255)
    password: str = Field(min_length=8, max_length=128)

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v


class InviteInfoResponse(BaseSchema):
    email: str
    org_name: str
    role: str
    inviter_name: str
    is_existing_user: bool
    expires_at: datetime


class InviteOut(BaseSchema):
    invite_id: uuid.UUID
    message: str
    expires_at: datetime

import uuid

from pydantic import EmailStr, Field, field_validator

from app.schemas.common import BaseResponse, BaseSchema


class SignupRequest(BaseSchema):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=1, max_length=255)
    organization_name: str = Field(min_length=1, max_length=255)

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


class TokenResponse(BaseSchema):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseResponse):
    email: str
    full_name: str
    is_active: bool
    is_verified: bool


class InviteRequest(BaseSchema):
    email: EmailStr
    role: str = "viewer"


class InviteAcceptRequest(BaseSchema):
    full_name: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=8, max_length=128)


class InviteResponse(BaseSchema):
    id: uuid.UUID
    email: str
    role: str
    organization_name: str

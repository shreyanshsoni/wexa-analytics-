from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class User(BaseModel):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    memberships: Mapped[list["Membership"]] = relationship(back_populates="user")  # type: ignore[name-defined]
    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(back_populates="user")  # type: ignore[name-defined]
    invites_sent: Mapped[list["Invite"]] = relationship(back_populates="invited_by")  # type: ignore[name-defined]
    api_keys: Mapped[list["ApiKey"]] = relationship(back_populates="created_by")  # type: ignore[name-defined]

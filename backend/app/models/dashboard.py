from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.organization import Organization
    from app.models.report import Report
    from app.models.widget import Widget


class Dashboard(BaseModel):
    __tablename__ = "dashboards"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_by_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)
    is_public: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    share_token: Mapped[str | None] = mapped_column(
        String(255), unique=True, nullable=True, default=None, index=True
    )
    refresh_interval: Mapped[int | None] = mapped_column(nullable=True, default=None)
    template_type: Mapped[str | None] = mapped_column(String(50), nullable=True, default=None)

    organization: Mapped[Organization] = relationship(back_populates="dashboards")
    widgets: Mapped[list[Widget]] = relationship(
        back_populates="dashboard", cascade="all, delete-orphan"
    )
    reports: Mapped[list[Report]] = relationship(back_populates="dashboard")

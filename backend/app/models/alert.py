from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.alert_history import AlertHistory
    from app.models.organization import Organization
    from app.models.saved_query import SavedQuery


class AlertStatus(enum.StrEnum):
    ACTIVE = "active"
    TRIGGERED = "triggered"
    RESOLVED = "resolved"
    MUTED = "muted"


class Alert(BaseModel):
    __tablename__ = "alerts"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    saved_query_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("saved_queries.id", ondelete="SET NULL"),
        nullable=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)
    condition: Mapped[dict] = mapped_column(JSONB, nullable=False)  # type: ignore[type-arg]
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default=AlertStatus.ACTIVE, index=True
    )
    muted_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None
    )
    notification_channels: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)  # type: ignore[type-arg]

    organization: Mapped[Organization] = relationship(back_populates="alerts")
    saved_query: Mapped[SavedQuery] = relationship(back_populates="alerts")
    history: Mapped[list[AlertHistory]] = relationship(
        back_populates="alert", cascade="all, delete-orphan"
    )

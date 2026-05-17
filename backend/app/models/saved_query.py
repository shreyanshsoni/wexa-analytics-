from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.alert import Alert
    from app.models.organization import Organization
    from app.models.widget import Widget


class SavedQuery(BaseModel):
    __tablename__ = "saved_queries"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)
    query_config: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)  # type: ignore[type-arg]

    organization: Mapped[Organization] = relationship(back_populates="saved_queries")
    widgets: Mapped[list[Widget]] = relationship(back_populates="saved_query")
    alerts: Mapped[list[Alert]] = relationship(back_populates="saved_query")

import uuid

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


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

    organization: Mapped["Organization"] = relationship(back_populates="saved_queries")  # type: ignore[name-defined]
    widgets: Mapped[list["Widget"]] = relationship(back_populates="saved_query")  # type: ignore[name-defined]
    alerts: Mapped[list["Alert"]] = relationship(back_populates="saved_query")  # type: ignore[name-defined]

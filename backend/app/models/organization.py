from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class Organization(BaseModel):
    __tablename__ = "organizations"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)

    memberships: Mapped[list["Membership"]] = relationship(back_populates="organization")  # type: ignore[name-defined]
    api_keys: Mapped[list["ApiKey"]] = relationship(back_populates="organization")  # type: ignore[name-defined]
    events: Mapped[list["Event"]] = relationship(back_populates="organization")  # type: ignore[name-defined]
    dashboards: Mapped[list["Dashboard"]] = relationship(back_populates="organization")  # type: ignore[name-defined]
    alerts: Mapped[list["Alert"]] = relationship(back_populates="organization")  # type: ignore[name-defined]
    saved_queries: Mapped[list["SavedQuery"]] = relationship(back_populates="organization")  # type: ignore[name-defined]
    reports: Mapped[list["Report"]] = relationship(back_populates="organization")  # type: ignore[name-defined]
    invites: Mapped[list["Invite"]] = relationship(back_populates="organization")  # type: ignore[name-defined]

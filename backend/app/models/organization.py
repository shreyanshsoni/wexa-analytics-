from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.alert import Alert
    from app.models.api_key import ApiKey
    from app.models.dashboard import Dashboard
    from app.models.event import Event
    from app.models.invite import Invite
    from app.models.membership import Membership
    from app.models.report import Report
    from app.models.saved_query import SavedQuery


class Organization(BaseModel):
    __tablename__ = "organizations"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)

    memberships: Mapped[list[Membership]] = relationship(back_populates="organization")
    api_keys: Mapped[list[ApiKey]] = relationship(back_populates="organization")
    events: Mapped[list[Event]] = relationship(back_populates="organization")
    dashboards: Mapped[list[Dashboard]] = relationship(back_populates="organization")
    alerts: Mapped[list[Alert]] = relationship(back_populates="organization")
    saved_queries: Mapped[list[SavedQuery]] = relationship(back_populates="organization")
    reports: Mapped[list[Report]] = relationship(back_populates="organization")
    invites: Mapped[list[Invite]] = relationship(back_populates="organization")

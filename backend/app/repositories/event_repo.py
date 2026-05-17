import uuid
from datetime import datetime

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.event import Event
from app.repositories.base import BaseRepository


class EventRepository(BaseRepository[Event]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Event, session)

    async def get_by_org(
        self,
        org_id: uuid.UUID,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Event]:
        result = await self.session.execute(
            select(Event)
            .where(Event.organization_id == org_id)
            .order_by(Event.timestamp.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def count_by_org_in_range(
        self,
        org_id: uuid.UUID,
        start: datetime,
        end: datetime,
    ) -> int:
        result = await self.session.execute(
            select(func.count(Event.id)).where(
                and_(
                    Event.organization_id == org_id,
                    Event.timestamp >= start,
                    Event.timestamp <= end,
                )
            )
        )
        return result.scalar_one()

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.widget import Widget
from app.repositories.base import BaseRepository


class WidgetRepository(BaseRepository[Widget]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Widget, session)

    async def get_by_dashboard(self, dashboard_id: uuid.UUID) -> list[Widget]:
        result = await self.session.execute(
            select(Widget)
            .where(Widget.dashboard_id == dashboard_id, Widget.deleted_at.is_(None))
            .order_by(Widget.position_y, Widget.position_x)
        )
        return list(result.scalars().all())

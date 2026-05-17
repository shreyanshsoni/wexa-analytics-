import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.dashboard import Dashboard
from app.repositories.base import BaseRepository


class DashboardRepository(BaseRepository[Dashboard]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Dashboard, session)

    async def get_by_org(self, org_id: uuid.UUID) -> list[Dashboard]:
        result = await self.session.execute(
            select(Dashboard)
            .where(Dashboard.organization_id == org_id, Dashboard.deleted_at.is_(None))
            .order_by(Dashboard.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_by_share_token(self, token: str) -> Dashboard | None:
        result = await self.session.execute(
            select(Dashboard).where(
                Dashboard.share_token == token,
                Dashboard.is_public.is_(True),
                Dashboard.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

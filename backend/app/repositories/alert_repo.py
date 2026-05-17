import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.alert import Alert
from app.repositories.base import BaseRepository


class AlertRepository(BaseRepository[Alert]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Alert, session)

    async def get_by_org(self, org_id: uuid.UUID) -> list[Alert]:
        result = await self.session.execute(
            select(Alert)
            .where(Alert.organization_id == org_id, Alert.deleted_at.is_(None))
            .order_by(Alert.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_active_alerts(self) -> list[Alert]:
        result = await self.session.execute(
            select(Alert).where(
                Alert.status.in_(["active", "triggered"]),
                Alert.deleted_at.is_(None),
            )
        )
        return list(result.scalars().all())

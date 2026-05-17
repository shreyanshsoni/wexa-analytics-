import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.report import Report
from app.repositories.base import BaseRepository


class ReportRepository(BaseRepository[Report]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Report, session)

    async def get_by_org(self, org_id: uuid.UUID) -> list[Report]:
        result = await self.session.execute(
            select(Report)
            .where(Report.organization_id == org_id, Report.deleted_at.is_(None))
            .order_by(Report.created_at.desc())
        )
        return list(result.scalars().all())

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.membership import Membership, MemberRole
from app.models.organization import Organization
from app.repositories.base import BaseRepository


class OrganizationRepository(BaseRepository[Organization]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Organization, session)

    async def get_by_slug(self, slug: str) -> Organization | None:
        result = await self.session.execute(
            select(Organization).where(
                Organization.slug == slug, Organization.deleted_at.is_(None)
            )
        )
        return result.scalar_one_or_none()

    async def slug_exists(self, slug: str) -> bool:
        return await self.get_by_slug(slug) is not None

    async def get_membership(
        self, user_id: uuid.UUID, org_id: uuid.UUID
    ) -> Membership | None:
        result = await self.session.execute(
            select(Membership).where(
                Membership.user_id == user_id,
                Membership.organization_id == org_id,
                Membership.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def get_org_members(self, org_id: uuid.UUID) -> list[Membership]:
        result = await self.session.execute(
            select(Membership).where(
                Membership.organization_id == org_id,
                Membership.deleted_at.is_(None),
            )
        )
        return list(result.scalars().all())

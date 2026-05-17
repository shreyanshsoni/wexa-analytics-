import secrets
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthorizationError, ConflictError, NotFoundError, ValidationError
from app.models.invite import Invite
from app.models.membership import MemberRole, Membership
from app.models.organization import Organization
from app.models.user import User
from app.repositories.organization_repo import OrganizationRepository


@dataclass
class MemberDetail:
    id: uuid.UUID
    user: User
    role: str
    joined_at: datetime


async def get_org_with_members(
    session: AsyncSession,
    org_id: uuid.UUID,
) -> tuple[Organization, list[MemberDetail]]:
    org = await session.get(Organization, org_id)
    if not org or org.deleted_at:
        raise NotFoundError("Organization", str(org_id))

    result = await session.execute(
        select(Membership, User)
        .join(User, Membership.user_id == User.id)
        .where(
            Membership.organization_id == org_id,
            Membership.deleted_at.is_(None),
            User.deleted_at.is_(None),
        )
        .order_by(Membership.created_at)
    )
    members = [
        MemberDetail(
            id=m.id,
            user=u,
            role=m.role,
            joined_at=m.created_at,
        )
        for m, u in result.all()
    ]
    return org, members


async def update_org(
    session: AsyncSession,
    org_id: uuid.UUID,
    name: str,
) -> Organization:
    org = await session.get(Organization, org_id)
    if not org or org.deleted_at:
        raise NotFoundError("Organization", str(org_id))
    org.name = name
    await session.commit()
    await session.refresh(org)
    return org


async def invite_member(
    session: AsyncSession,
    org_id: uuid.UUID,
    invited_by_id: uuid.UUID,
    email: str,
    role: str,
    inviter_name: str = "",
    org_name: str = "",
) -> Invite:
    existing = await session.execute(
        select(Invite).where(
            Invite.organization_id == org_id,
            Invite.email == email,
            Invite.accepted_at.is_(None),
            Invite.deleted_at.is_(None),
        )
    )
    if existing.scalar_one_or_none():
        raise ConflictError("A pending invite already exists for this email")

    result = await session.execute(
        select(User).where(User.email == email, User.deleted_at.is_(None))
    )
    existing_user = result.scalar_one_or_none()
    if existing_user:
        already_member = await session.execute(
            select(Membership).where(
                Membership.user_id == existing_user.id,
                Membership.organization_id == org_id,
                Membership.deleted_at.is_(None),
            )
        )
        if already_member.scalar_one_or_none():
            raise ConflictError("This user is already a member of the organization")

    invite = Invite(
        organization_id=org_id,
        invited_by_id=invited_by_id,
        email=email,
        token=secrets.token_urlsafe(32),
        role=role,
        expires_at=datetime.now(UTC) + timedelta(days=7),
    )
    session.add(invite)
    await session.commit()
    await session.refresh(invite)

    try:
        from app.core.email import send_invite_email
        await send_invite_email(
            to_email=email,
            inviter_name=inviter_name,
            org_name=org_name,
            invite_token=invite.token,
            role=role,
        )
    except Exception:
        import structlog as _log
        _log.get_logger().warning("invite_email_failed", to=email)

    return invite


async def remove_member(
    session: AsyncSession,
    org_id: uuid.UUID,
    membership_id: uuid.UUID,
    acting_user_id: uuid.UUID,
    acting_role: str,
) -> None:
    result = await session.execute(
        select(Membership).where(
            Membership.id == membership_id,
            Membership.organization_id == org_id,
            Membership.deleted_at.is_(None),
        )
    )
    target = result.scalar_one_or_none()
    if not target:
        raise NotFoundError("Membership", str(membership_id))

    if target.user_id == acting_user_id:
        raise ValidationError("Cannot remove yourself from the organization")

    if target.role == MemberRole.OWNER:
        raise AuthorizationError("Cannot remove the organization owner")

    if acting_role == MemberRole.ADMIN and target.role == MemberRole.ADMIN:
        raise AuthorizationError("Admins cannot remove other admins")

    target.deleted_at = datetime.now(UTC)
    await session.commit()


async def update_member_role(
    session: AsyncSession,
    org_id: uuid.UUID,
    membership_id: uuid.UUID,
    new_role: str,
    acting_role: str,
) -> Membership:
    result = await session.execute(
        select(Membership).where(
            Membership.id == membership_id,
            Membership.organization_id == org_id,
            Membership.deleted_at.is_(None),
        )
    )
    target = result.scalar_one_or_none()
    if not target:
        raise NotFoundError("Membership", str(membership_id))

    if target.role == MemberRole.OWNER:
        raise AuthorizationError("Cannot change the owner's role")

    if acting_role == MemberRole.ADMIN and target.role == MemberRole.ADMIN:
        raise AuthorizationError("Admins cannot change other admins' roles")

    target.role = new_role
    await session.commit()
    await session.refresh(target)
    return target


async def get_org_for_api_key(
    session: AsyncSession,
    org_id: uuid.UUID,
) -> Organization:
    repo = OrganizationRepository(session)
    org = await repo.get_by_id(org_id)
    if not org:
        raise NotFoundError("Organization", str(org_id))
    return org

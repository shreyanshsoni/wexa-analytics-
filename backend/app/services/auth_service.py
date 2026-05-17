import hashlib
import secrets
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import AuthenticationError, ConflictError, NotFoundError, ValidationError
from app.core.security import (
    create_access_token,
    hash_password,
    verify_password,
)
from app.models.invite import Invite
from app.models.membership import MemberRole, Membership
from app.models.organization import Organization
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.repositories.organization_repo import OrganizationRepository
from app.repositories.user_repo import UserRepository


@dataclass
class AuthResult:
    access_token: str
    refresh_token_raw: str
    user: User
    org: Organization
    role: str


def _slugify(name: str) -> str:
    import re
    slug = name.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_-]+", "-", slug)
    return slug.strip("-")[:100]


def _hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


async def signup(
    session: AsyncSession,
    email: str,
    password: str,
    full_name: str,
    org_name: str,
) -> AuthResult:
    user_repo = UserRepository(session)
    org_repo = OrganizationRepository(session)

    if await user_repo.email_exists(email):
        raise ConflictError("An account with this email already exists")

    user = User(
        email=email,
        hashed_password=hash_password(password),
        full_name=full_name,
        is_active=True,
        is_verified=False,
    )
    session.add(user)
    await session.flush()

    base_slug = _slugify(org_name)
    slug = base_slug
    counter = 1
    while await org_repo.slug_exists(slug):
        slug = f"{base_slug}-{counter}"
        counter += 1

    org = Organization(name=org_name, slug=slug)
    session.add(org)
    await session.flush()

    membership = Membership(
        user_id=user.id,
        organization_id=org.id,
        role=MemberRole.OWNER,
    )
    session.add(membership)
    await session.flush()

    access_token = create_access_token(
        subject=str(user.id),
        extra_claims={
            "org_id": str(org.id),
            "role": MemberRole.OWNER,
            "jti": str(uuid.uuid4()),
        },
    )

    raw_refresh = secrets.token_urlsafe(32)
    refresh_token = RefreshToken(
        user_id=user.id,
        token_hash=_hash_token(raw_refresh),
        expires_at=datetime.now(UTC) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )
    session.add(refresh_token)
    await session.commit()
    await session.refresh(user)
    await session.refresh(org)

    return AuthResult(
        access_token=access_token,
        refresh_token_raw=raw_refresh,
        user=user,
        org=org,
        role=MemberRole.OWNER,
    )


async def login(
    session: AsyncSession,
    email: str,
    password: str,
) -> AuthResult:
    user_repo = UserRepository(session)

    user = await user_repo.get_by_email(email)
    if not user or not verify_password(password, user.hashed_password):
        raise AuthenticationError("Invalid email or password")

    if not user.is_active:
        raise AuthenticationError("Account is disabled")

    from sqlalchemy import select
    result = await session.execute(
        select(Membership, Organization)
        .join(Organization, Membership.organization_id == Organization.id)
        .where(
            Membership.user_id == user.id,
            Membership.deleted_at.is_(None),
            Organization.deleted_at.is_(None),
        )
        .order_by(Membership.created_at)
        .limit(1)
    )
    row = result.first()
    if not row:
        raise AuthenticationError(
            "Your account is not part of any organization. "
            "Please use an invitation link sent to your email to join one."
        )

    membership, org = row

    access_token = create_access_token(
        subject=str(user.id),
        extra_claims={
            "org_id": str(org.id),
            "role": membership.role,
            "jti": str(uuid.uuid4()),
        },
    )

    raw_refresh = secrets.token_urlsafe(32)
    refresh_token = RefreshToken(
        user_id=user.id,
        token_hash=_hash_token(raw_refresh),
        expires_at=datetime.now(UTC) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )
    session.add(refresh_token)
    await session.commit()

    return AuthResult(
        access_token=access_token,
        refresh_token_raw=raw_refresh,
        user=user,
        org=org,
        role=membership.role,
    )


async def refresh_access_token(
    session: AsyncSession,
    raw_refresh_token: str,
) -> str:
    from sqlalchemy import select
    token_hash = _hash_token(raw_refresh_token)
    result = await session.execute(
        select(RefreshToken).where(
            RefreshToken.token_hash == token_hash,
            RefreshToken.revoked_at.is_(None),
            RefreshToken.deleted_at.is_(None),
        )
    )
    token = result.scalar_one_or_none()
    if not token:
        raise AuthenticationError("Invalid or expired refresh token")

    if token.expires_at.replace(tzinfo=UTC) < datetime.now(UTC):
        raise AuthenticationError("Refresh token expired")

    token.revoked_at = datetime.now(UTC)
    await session.flush()

    result2 = await session.execute(
        select(Membership, Organization)
        .join(Organization, Membership.organization_id == Organization.id)
        .where(
            Membership.user_id == token.user_id,
            Membership.deleted_at.is_(None),
        )
        .order_by(Membership.created_at)
        .limit(1)
    )
    row = result2.first()
    if not row:
        raise AuthenticationError("No organization found")

    membership, _ = row
    access_token = create_access_token(
        subject=str(token.user_id),
        extra_claims={
            "org_id": str(membership.organization_id),
            "role": membership.role,
            "jti": str(uuid.uuid4()),
        },
    )

    new_raw = secrets.token_urlsafe(32)
    new_token = RefreshToken(
        user_id=token.user_id,
        token_hash=_hash_token(new_raw),
        expires_at=datetime.now(UTC) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )
    session.add(new_token)
    await session.commit()

    return access_token


async def logout(session: AsyncSession, raw_refresh_token: str) -> None:
    from sqlalchemy import select
    token_hash = _hash_token(raw_refresh_token)
    result = await session.execute(
        select(RefreshToken).where(
            RefreshToken.token_hash == token_hash,
            RefreshToken.revoked_at.is_(None),
        )
    )
    token = result.scalar_one_or_none()
    if token:
        token.revoked_at = datetime.now(UTC)
        await session.commit()


async def get_invite_info(
    session: AsyncSession,
    invite_token: str,
) -> dict[str, object]:
    from sqlalchemy import select
    result = await session.execute(
        select(Invite).where(
            Invite.token == invite_token,
            Invite.accepted_at.is_(None),
            Invite.deleted_at.is_(None),
        )
    )
    invite = result.scalar_one_or_none()
    if not invite:
        raise NotFoundError("Invite", invite_token)

    if invite.expires_at.replace(tzinfo=UTC) < datetime.now(UTC):
        raise ValidationError("Invite has expired")

    org = await session.get(Organization, invite.organization_id)
    inviter = await session.get(User, invite.invited_by_id)

    user_repo = UserRepository(session)
    existing = await user_repo.get_by_email(invite.email)

    return {
        "email": invite.email,
        "org_name": org.name if org else "",
        "role": invite.role,
        "inviter_name": inviter.full_name if inviter else "",
        "is_existing_user": existing is not None,
        "expires_at": invite.expires_at,
    }


async def accept_invite(
    session: AsyncSession,
    invite_token: str,
    full_name: str | None,
    password: str,
) -> AuthResult:
    from sqlalchemy import select
    result = await session.execute(
        select(Invite).where(
            Invite.token == invite_token,
            Invite.accepted_at.is_(None),
            Invite.deleted_at.is_(None),
        )
    )
    invite = result.scalar_one_or_none()
    if not invite:
        raise NotFoundError("Invite", invite_token)

    if invite.expires_at.replace(tzinfo=UTC) < datetime.now(UTC):
        raise ValidationError("Invite has expired")

    user_repo = UserRepository(session)
    existing_user = await user_repo.get_by_email(invite.email)

    if existing_user:
        # Verify their existing password — proves identity without a login session
        if not verify_password(password, existing_user.hashed_password):
            raise AuthenticationError("Incorrect password for existing account")
        user = existing_user
    else:
        if not full_name or not full_name.strip():
            raise ValidationError("Full name is required for new accounts")
        user = User(
            email=invite.email,
            hashed_password=hash_password(password),
            full_name=full_name.strip(),
            is_active=True,
            is_verified=True,
        )
        session.add(user)
        await session.flush()

    existing_membership = await session.execute(
        select(Membership).where(
            Membership.user_id == user.id,
            Membership.organization_id == invite.organization_id,
            Membership.deleted_at.is_(None),
        )
    )
    if existing_membership.scalar_one_or_none():
        raise ConflictError("User is already a member of this organization")

    membership = Membership(
        user_id=user.id,
        organization_id=invite.organization_id,
        role=invite.role,
    )
    session.add(membership)
    invite.accepted_at = datetime.now(UTC)
    await session.flush()

    org_result = await session.get(Organization, invite.organization_id)
    if not org_result:
        raise NotFoundError("Organization", str(invite.organization_id))

    access_token = create_access_token(
        subject=str(user.id),
        extra_claims={
            "org_id": str(org_result.id),
            "role": invite.role,
            "jti": str(uuid.uuid4()),
        },
    )

    raw_refresh = secrets.token_urlsafe(32)
    refresh_token = RefreshToken(
        user_id=user.id,
        token_hash=_hash_token(raw_refresh),
        expires_at=datetime.now(UTC) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )
    session.add(refresh_token)
    await session.commit()
    await session.refresh(user)

    return AuthResult(
        access_token=access_token,
        refresh_token_raw=raw_refresh,
        user=user,
        org=org_result,
        role=invite.role,
    )

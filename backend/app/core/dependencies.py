import uuid
from typing import Annotated

from fastapi import Depends, Header
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db as _get_db
from app.core.exceptions import AuthenticationError, AuthorizationError
from app.core.redis import get_redis as _get_redis
from app.core.security import decode_token
from app.models.membership import MemberRole, Membership
from app.models.organization import Organization
from app.models.user import User
from app.repositories.organization_repo import OrganizationRepository
from app.repositories.user_repo import UserRepository

DbDep = Annotated[AsyncSession, Depends(_get_db)]
RedisDep = Annotated[Redis, Depends(_get_redis)]

_http_bearer = HTTPBearer(auto_error=False)


async def _extract_token(
    bearer: Annotated[HTTPAuthorizationCredentials | None, Depends(_http_bearer)],
) -> str | None:
    return bearer.credentials if bearer else None


async def get_current_user(
    token: Annotated[str | None, Depends(_extract_token)],
    db: DbDep,
) -> User:
    if not token:
        raise AuthenticationError("Not authenticated")
    try:
        payload = decode_token(token)
    except JWTError:
        raise AuthenticationError("Invalid or expired token")

    if payload.get("type") != "access":
        raise AuthenticationError("Invalid token type")

    user_id_str: str | None = payload.get("sub")
    if not user_id_str:
        raise AuthenticationError("Invalid token payload")

    repo = UserRepository(db)
    user = await repo.get_by_id(uuid.UUID(user_id_str))
    if not user:
        raise AuthenticationError("User not found")
    if not user.is_active:
        raise AuthenticationError("Account is disabled")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


async def _get_current_org_context(
    current_user: CurrentUser,
    token: Annotated[str | None, Depends(_extract_token)],
    db: DbDep,
) -> tuple[User, Organization, Membership]:
    if not token:
        raise AuthenticationError("Not authenticated")
    try:
        payload = decode_token(token)
    except JWTError:
        raise AuthenticationError("Invalid token")

    org_id_str: str | None = payload.get("org_id")
    if not org_id_str:
        raise AuthenticationError("No organization context in token")

    org_id = uuid.UUID(org_id_str)
    org_repo = OrganizationRepository(db)
    membership = await org_repo.get_membership(current_user.id, org_id)
    if not membership:
        raise AuthorizationError("Not a member of this organization")

    org = await db.get(Organization, org_id)
    if not org or org.deleted_at:
        raise AuthorizationError("Organization not found")

    return current_user, org, membership


OrgContext = Annotated[tuple[User, Organization, Membership], Depends(_get_current_org_context)]


def require_role(*roles: str):  # type: ignore[no-untyped-def]
    async def checker(ctx: OrgContext) -> tuple[User, Organization, Membership]:
        _, _, membership = ctx
        if membership.role not in roles:
            raise AuthorizationError(
                f"This action requires one of these roles: {', '.join(roles)}"
            )
        return ctx
    return checker


RequireOwner = Annotated[
    tuple[User, Organization, Membership],
    Depends(require_role(MemberRole.OWNER)),
]
RequireAdmin = Annotated[
    tuple[User, Organization, Membership],
    Depends(require_role(MemberRole.OWNER, MemberRole.ADMIN)),
]
RequireAnalyst = Annotated[
    tuple[User, Organization, Membership],
    Depends(require_role(MemberRole.OWNER, MemberRole.ADMIN, MemberRole.ANALYST)),
]
RequireMember = Annotated[
    tuple[User, Organization, Membership],
    Depends(require_role(MemberRole.OWNER, MemberRole.ADMIN, MemberRole.ANALYST, MemberRole.VIEWER)),
]


async def get_org_by_api_key(
    x_api_key: Annotated[str | None, Header(alias="X-API-Key")] = None,
    db: DbDep = Depends(_get_db),
) -> tuple[uuid.UUID, uuid.UUID]:
    if not x_api_key:
        raise AuthenticationError("X-API-Key header required")
    from app.services.api_key_service import get_org_by_api_key as _get_org
    api_key, org_id = await _get_org(db, x_api_key)
    return api_key.id, org_id


ApiKeyDep = Annotated[tuple[uuid.UUID, uuid.UUID], Depends(get_org_by_api_key)]

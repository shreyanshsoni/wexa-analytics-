import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthorizationError, NotFoundError
from app.core.security import generate_api_key
from app.models.api_key import ApiKey
from app.repositories.api_key_repo import ApiKeyRepository


@dataclass
class ApiKeyCreated:
    api_key: ApiKey
    raw_key: str


async def list_api_keys(session: AsyncSession, org_id: uuid.UUID) -> list[ApiKey]:
    repo = ApiKeyRepository(session)
    return await repo.get_by_org(org_id)


async def create_api_key(
    session: AsyncSession,
    org_id: uuid.UUID,
    name: str,
    created_by_id: uuid.UUID,
) -> ApiKeyCreated:
    raw_key, key_hash = generate_api_key()
    key_prefix = raw_key[:12]

    api_key = ApiKey(
        organization_id=org_id,
        created_by_id=created_by_id,
        name=name,
        key_hash=key_hash,
        key_prefix=key_prefix,
        is_active=True,
    )
    session.add(api_key)
    await session.commit()
    await session.refresh(api_key)
    return ApiKeyCreated(api_key=api_key, raw_key=raw_key)


async def revoke_api_key(
    session: AsyncSession,
    api_key_id: uuid.UUID,
    org_id: uuid.UUID,
) -> None:
    repo = ApiKeyRepository(session)
    key = await repo.get_by_id(api_key_id)
    if not key:
        raise NotFoundError("ApiKey", str(api_key_id))
    if key.organization_id != org_id:
        raise AuthorizationError("API key does not belong to this organization")
    key.is_active = False
    key.deleted_at = datetime.now(UTC)
    await session.commit()


async def rotate_api_key(
    session: AsyncSession,
    api_key_id: uuid.UUID,
    org_id: uuid.UUID,
    created_by_id: uuid.UUID,
) -> ApiKeyCreated:
    repo = ApiKeyRepository(session)
    old_key = await repo.get_by_id(api_key_id)
    if not old_key:
        raise NotFoundError("ApiKey", str(api_key_id))
    if old_key.organization_id != org_id:
        raise AuthorizationError("API key does not belong to this organization")

    old_key.is_active = False
    old_key.deleted_at = datetime.now(UTC)
    await session.flush()

    return await create_api_key(session, org_id, old_key.name, created_by_id)


async def get_org_by_api_key(
    session: AsyncSession,
    raw_key: str,
) -> tuple[ApiKey, uuid.UUID]:
    from app.core.security import hash_api_key
    repo = ApiKeyRepository(session)
    key = await repo.get_by_hash(hash_api_key(raw_key))
    if not key:
        raise AuthorizationError("Invalid API key")
    await repo.update_last_used(key.id)
    await session.flush()
    return key, key.organization_id

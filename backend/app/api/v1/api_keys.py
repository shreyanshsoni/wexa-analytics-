import uuid

from fastapi import APIRouter

from app.core.dependencies import DbDep, RequireAdmin
from app.schemas.api_key import ApiKeyCreatedOut, ApiKeyOut, CreateApiKeyRequest
from app.schemas.common import ApiResponse, MessageResponse
from app.services import api_key_service

router = APIRouter(prefix="/api-keys", tags=["api-keys"])


@router.get("")
async def list_api_keys(
    ctx: RequireAdmin,
    db: DbDep,
) -> ApiResponse[list[ApiKeyOut]]:
    _, org, _ = ctx
    keys = await api_key_service.list_api_keys(db, org.id)
    return ApiResponse(
        data=[
            ApiKeyOut(
                id=k.id,
                name=k.name,
                key_prefix=k.key_prefix,
                is_active=k.is_active,
                last_used_at=k.last_used_at,
                created_at=k.created_at,
            )
            for k in keys
        ]
    )


@router.post("", status_code=201)
async def create_api_key(
    body: CreateApiKeyRequest,
    ctx: RequireAdmin,
    db: DbDep,
) -> ApiResponse[ApiKeyCreatedOut]:
    user, org, _ = ctx
    result = await api_key_service.create_api_key(db, org.id, body.name, user.id)
    return ApiResponse(
        data=ApiKeyCreatedOut(
            id=result.api_key.id,
            name=result.api_key.name,
            key=result.raw_key,
            key_prefix=result.api_key.key_prefix,
            created_at=result.api_key.created_at,
        )
    )


@router.post("/{api_key_id}/revoke")
async def revoke_api_key(
    api_key_id: uuid.UUID,
    ctx: RequireAdmin,
    db: DbDep,
) -> ApiResponse[MessageResponse]:
    _, org, _ = ctx
    await api_key_service.revoke_api_key(db, api_key_id, org.id)
    return ApiResponse(data=MessageResponse(message="API key revoked"))


@router.post("/{api_key_id}/rotate", status_code=201)
async def rotate_api_key(
    api_key_id: uuid.UUID,
    ctx: RequireAdmin,
    db: DbDep,
) -> ApiResponse[ApiKeyCreatedOut]:
    user, org, _ = ctx
    result = await api_key_service.rotate_api_key(db, api_key_id, org.id, user.id)
    return ApiResponse(
        data=ApiKeyCreatedOut(
            id=result.api_key.id,
            name=result.api_key.name,
            key=result.raw_key,
            key_prefix=result.api_key.key_prefix,
            created_at=result.api_key.created_at,
        )
    )

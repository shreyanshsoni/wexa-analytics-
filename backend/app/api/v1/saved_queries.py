import uuid
from typing import Any

from fastapi import APIRouter

from app.core.dependencies import DbDep, RequireAnalyst, RequireMember
from app.schemas.common import ApiResponse
from app.schemas.dashboard import (
    SavedQueryCreateRequest,
    SavedQueryResponse,
    SavedQueryUpdateRequest,
)
from app.services import dashboard_service

router = APIRouter(prefix="/saved-queries", tags=["saved-queries"])


def _to_response(sq: Any) -> SavedQueryResponse:
    return SavedQueryResponse(
        id=sq.id,
        created_at=sq.created_at,
        updated_at=sq.updated_at,
        organization_id=sq.organization_id,
        name=sq.name,
        description=sq.description,
        query_config=sq.query_config,
    )


@router.get("", response_model=ApiResponse[list[SavedQueryResponse]])
async def list_saved_queries(ctx: RequireMember, db: DbDep) -> Any:
    _, org, _ = ctx
    queries = await dashboard_service.list_saved_queries(db, org.id)
    return ApiResponse(data=[_to_response(q) for q in queries])


@router.post("", response_model=ApiResponse[SavedQueryResponse], status_code=201)
async def create_saved_query(
    body: SavedQueryCreateRequest,
    ctx: RequireAnalyst,
    db: DbDep,
) -> Any:
    _, org, _ = ctx
    sq = await dashboard_service.create_saved_query(db, org.id, body)
    return ApiResponse(data=_to_response(sq))


@router.get("/{query_id}", response_model=ApiResponse[SavedQueryResponse])
async def get_saved_query(
    query_id: uuid.UUID,
    ctx: RequireMember,
    db: DbDep,
) -> Any:
    _, org, _ = ctx
    sq = await dashboard_service.get_saved_query(db, org.id, query_id)
    return ApiResponse(data=_to_response(sq))


@router.put("/{query_id}", response_model=ApiResponse[SavedQueryResponse])
async def update_saved_query(
    query_id: uuid.UUID,
    body: SavedQueryUpdateRequest,
    ctx: RequireAnalyst,
    db: DbDep,
) -> Any:
    _, org, _ = ctx
    sq = await dashboard_service.update_saved_query(db, org.id, query_id, body)
    return ApiResponse(data=_to_response(sq))


@router.delete("/{query_id}", status_code=204)
async def delete_saved_query(
    query_id: uuid.UUID,
    ctx: RequireAnalyst,
    db: DbDep,
) -> None:
    _, org, _ = ctx
    await dashboard_service.delete_saved_query(db, org.id, query_id)

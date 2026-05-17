import uuid
from typing import Any

from fastapi import APIRouter
from sqlalchemy import select

from app.core.dependencies import CurrentUser, DbDep
from app.models.membership import Membership
from app.schemas.common import ApiResponse
from app.schemas.dashboard import (
    SavedQueryCreateRequest,
    SavedQueryResponse,
    SavedQueryUpdateRequest,
)
from app.services import dashboard_service

router = APIRouter(prefix="/saved-queries", tags=["saved-queries"])


async def _get_org_id(user: Any, db: Any) -> uuid.UUID:
    result = await db.execute(
        select(Membership).where(
            Membership.user_id == user.id,
            Membership.deleted_at.is_(None),
        )
    )
    membership = result.scalar_one_or_none()
    if not membership:
        from app.core.exceptions import AuthorizationError
        raise AuthorizationError("No organization membership found")
    return uuid.UUID(str(membership.organization_id))


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
async def list_saved_queries(user: CurrentUser, db: DbDep) -> Any:
    org_id = await _get_org_id(user, db)
    queries = await dashboard_service.list_saved_queries(db, org_id)
    return ApiResponse(data=[_to_response(q) for q in queries])


@router.post("", response_model=ApiResponse[SavedQueryResponse], status_code=201)
async def create_saved_query(
    body: SavedQueryCreateRequest,
    user: CurrentUser,
    db: DbDep,
) -> Any:
    org_id = await _get_org_id(user, db)
    sq = await dashboard_service.create_saved_query(db, org_id, body)
    return ApiResponse(data=_to_response(sq))


@router.get("/{query_id}", response_model=ApiResponse[SavedQueryResponse])
async def get_saved_query(
    query_id: uuid.UUID,
    user: CurrentUser,
    db: DbDep,
) -> Any:
    org_id = await _get_org_id(user, db)
    sq = await dashboard_service.get_saved_query(db, org_id, query_id)
    return ApiResponse(data=_to_response(sq))


@router.put("/{query_id}", response_model=ApiResponse[SavedQueryResponse])
async def update_saved_query(
    query_id: uuid.UUID,
    body: SavedQueryUpdateRequest,
    user: CurrentUser,
    db: DbDep,
) -> Any:
    org_id = await _get_org_id(user, db)
    sq = await dashboard_service.update_saved_query(db, org_id, query_id, body)
    return ApiResponse(data=_to_response(sq))


@router.delete("/{query_id}", status_code=204)
async def delete_saved_query(
    query_id: uuid.UUID,
    user: CurrentUser,
    db: DbDep,
) -> None:
    org_id = await _get_org_id(user, db)
    await dashboard_service.delete_saved_query(db, org_id, query_id)

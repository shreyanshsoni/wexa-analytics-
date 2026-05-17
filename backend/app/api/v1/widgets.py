import uuid
from typing import Any

from fastapi import APIRouter
from sqlalchemy import select

from app.core.dependencies import CurrentUser, DbDep, RedisDep
from app.models.membership import Membership
from app.schemas.common import ApiResponse
from app.schemas.dashboard import (
    QueryResult,
    WidgetCreateRequest,
    WidgetResponse,
    WidgetUpdateRequest,
)
from app.services import dashboard_service
from app.services.dashboard_service import execute_query

router = APIRouter(prefix="/widgets", tags=["widgets"])


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


async def _widget_to_response(widget: Any, org_id: uuid.UUID, db: Any, redis: Any) -> WidgetResponse:
    time_range: str = widget.config.get("time_range", "24h") if widget.config else "24h"
    query_result: QueryResult | None = None

    if widget.saved_query_id:
        from app.models.saved_query import SavedQuery
        sq = await db.get(SavedQuery, widget.saved_query_id)
        if sq and not sq.deleted_at:
            points, cached = await execute_query(db, org_id, sq.query_config, time_range, redis)
            query_result = QueryResult(data=points, cached=cached)

    return WidgetResponse(
        id=widget.id,
        created_at=widget.created_at,
        updated_at=widget.updated_at,
        dashboard_id=widget.dashboard_id,
        saved_query_id=widget.saved_query_id,
        title=widget.title,
        widget_type=widget.widget_type,
        time_range=time_range,
        position_x=widget.position_x,
        position_y=widget.position_y,
        width=widget.width,
        height=widget.height,
        query_result=query_result,
    )


@router.post("", response_model=ApiResponse[WidgetResponse], status_code=201)
async def create_widget(
    body: WidgetCreateRequest,
    user: CurrentUser,
    db: DbDep,
    redis: RedisDep,
) -> Any:
    org_id = await _get_org_id(user, db)
    widget = await dashboard_service.create_widget(db, org_id, body)
    data = await _widget_to_response(widget, org_id, db, redis)
    return ApiResponse(data=data)


@router.get("/{widget_id}", response_model=ApiResponse[WidgetResponse])
async def get_widget(
    widget_id: uuid.UUID,
    user: CurrentUser,
    db: DbDep,
    redis: RedisDep,
) -> Any:
    org_id = await _get_org_id(user, db)
    widget = await dashboard_service.get_widget(db, org_id, widget_id)
    data = await _widget_to_response(widget, org_id, db, redis)
    return ApiResponse(data=data)


@router.put("/{widget_id}", response_model=ApiResponse[WidgetResponse])
async def update_widget(
    widget_id: uuid.UUID,
    body: WidgetUpdateRequest,
    user: CurrentUser,
    db: DbDep,
    redis: RedisDep,
) -> Any:
    org_id = await _get_org_id(user, db)
    widget = await dashboard_service.update_widget(db, org_id, widget_id, body)
    data = await _widget_to_response(widget, org_id, db, redis)
    return ApiResponse(data=data)


@router.delete("/{widget_id}", status_code=204)
async def delete_widget(
    widget_id: uuid.UUID,
    user: CurrentUser,
    db: DbDep,
) -> None:
    org_id = await _get_org_id(user, db)
    await dashboard_service.delete_widget(db, org_id, widget_id)

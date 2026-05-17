import uuid
from typing import Any

from fastapi import APIRouter

from app.core.dependencies import DbDep, RedisDep, RequireAnalyst, RequireMember
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
    ctx: RequireAnalyst,
    db: DbDep,
    redis: RedisDep,
) -> Any:
    _, org, _ = ctx
    widget = await dashboard_service.create_widget(db, org.id, body)
    data = await _widget_to_response(widget, org.id, db, redis)
    return ApiResponse(data=data)


@router.get("/{widget_id}", response_model=ApiResponse[WidgetResponse])
async def get_widget(
    widget_id: uuid.UUID,
    ctx: RequireMember,
    db: DbDep,
    redis: RedisDep,
) -> Any:
    _, org, _ = ctx
    widget = await dashboard_service.get_widget(db, org.id, widget_id)
    data = await _widget_to_response(widget, org.id, db, redis)
    return ApiResponse(data=data)


@router.put("/{widget_id}", response_model=ApiResponse[WidgetResponse])
async def update_widget(
    widget_id: uuid.UUID,
    body: WidgetUpdateRequest,
    ctx: RequireAnalyst,
    db: DbDep,
    redis: RedisDep,
) -> Any:
    _, org, _ = ctx
    widget = await dashboard_service.update_widget(db, org.id, widget_id, body)
    data = await _widget_to_response(widget, org.id, db, redis)
    return ApiResponse(data=data)


@router.delete("/{widget_id}", status_code=204)
async def delete_widget(
    widget_id: uuid.UUID,
    ctx: RequireAnalyst,
    db: DbDep,
) -> None:
    _, org, _ = ctx
    await dashboard_service.delete_widget(db, org.id, widget_id)

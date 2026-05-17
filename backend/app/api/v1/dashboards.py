import uuid
from typing import Any

from fastapi import APIRouter

from app.core.config import settings
from app.core.dependencies import DbDep, RedisDep, RequireAdmin, RequireAnalyst, RequireMember
from app.models.widget import Widget
from app.schemas.common import ApiResponse
from app.schemas.dashboard import (
    DashboardCreateRequest,
    DashboardListItem,
    DashboardResponse,
    DashboardShareRequest,
    DashboardUpdateRequest,
    QueryResult,
    ShareResponse,
    WidgetResponse,
)
from app.services import dashboard_service
from app.services.dashboard_service import execute_query

router = APIRouter(prefix="/dashboards", tags=["dashboards"])


def _refresh_label(seconds: int | None) -> str | None:
    if seconds is None:
        return None
    mapping = {30: "30s", 60: "1m", 300: "5m"}
    return mapping.get(seconds)


async def _build_widget_response(
    widget: Widget,
    org_id: uuid.UUID,
    db: Any,
    redis: Any,
) -> WidgetResponse:
    time_range: str = widget.config.get("time_range", "24h") if widget.config else "24h"
    query_result: QueryResult | None = None

    if widget.saved_query_id and not widget.deleted_at:
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


async def _build_dashboard_response(
    dashboard: Any,
    org_id: uuid.UUID,
    db: Any,
    redis: Any,
) -> DashboardResponse:
    active_widgets = [w for w in dashboard.widgets if not w.deleted_at]
    widget_responses = []
    for w in sorted(active_widgets, key=lambda x: (x.position_y, x.position_x)):
        wr = await _build_widget_response(w, org_id, db, redis)
        widget_responses.append(wr)

    return DashboardResponse(
        id=dashboard.id,
        created_at=dashboard.created_at,
        updated_at=dashboard.updated_at,
        organization_id=dashboard.organization_id,
        name=dashboard.name,
        description=dashboard.description,
        is_public=dashboard.is_public,
        share_token=dashboard.share_token,
        auto_refresh_interval=_refresh_label(dashboard.refresh_interval),
        template_type=dashboard.template_type,
        widgets=widget_responses,
    )


# ── Routes ─────────────────────────────────────────────────────────────────────

@router.get("", response_model=ApiResponse[list[DashboardListItem]])
async def list_dashboards(ctx: RequireMember, db: DbDep) -> Any:
    _, org, _ = ctx
    pairs = await dashboard_service.list_dashboards(db, org.id)
    items = [
        DashboardListItem(
            id=d.id,
            created_at=d.created_at,
            updated_at=d.updated_at,
            name=d.name,
            description=d.description,
            is_public=d.is_public,
            widget_count=count,
            auto_refresh_interval=_refresh_label(d.refresh_interval),
        )
        for d, count in pairs
    ]
    return ApiResponse(data=items)


@router.post("", response_model=ApiResponse[DashboardResponse], status_code=201)
async def create_dashboard(
    body: DashboardCreateRequest,
    ctx: RequireAnalyst,
    db: DbDep,
    redis: RedisDep,
) -> Any:
    user, org, _ = ctx
    from sqlalchemy import select as sa_select
    from sqlalchemy.orm import selectinload as sli
    dashboard = await dashboard_service.create_dashboard(db, org.id, user.id, body)
    result = await db.execute(
        sa_select(type(dashboard)).where(type(dashboard).id == dashboard.id).options(sli(type(dashboard).widgets))
    )
    dashboard = result.scalar_one()
    data = await _build_dashboard_response(dashboard, org.id, db, redis)
    return ApiResponse(data=data)


@router.get("/shared/{share_token}", response_model=ApiResponse[DashboardResponse])
async def get_shared_dashboard(
    share_token: str,
    db: DbDep,
    redis: RedisDep,
) -> Any:
    dashboard = await dashboard_service.get_dashboard_by_share_token(db, share_token)
    data = await _build_dashboard_response(dashboard, dashboard.organization_id, db, redis)
    return ApiResponse(data=data)


@router.get("/{dashboard_id}", response_model=ApiResponse[DashboardResponse])
async def get_dashboard(
    dashboard_id: uuid.UUID,
    ctx: RequireMember,
    db: DbDep,
    redis: RedisDep,
) -> Any:
    _, org, _ = ctx
    dashboard = await dashboard_service.get_dashboard(db, org.id, dashboard_id, redis)
    data = await _build_dashboard_response(dashboard, org.id, db, redis)
    return ApiResponse(data=data)


@router.put("/{dashboard_id}", response_model=ApiResponse[DashboardResponse])
async def update_dashboard(
    dashboard_id: uuid.UUID,
    body: DashboardUpdateRequest,
    ctx: RequireAnalyst,
    db: DbDep,
    redis: RedisDep,
) -> Any:
    _, org, _ = ctx
    dashboard = await dashboard_service.update_dashboard(db, org.id, dashboard_id, body)
    data = await _build_dashboard_response(dashboard, org.id, db, redis)
    return ApiResponse(data=data)


@router.delete("/{dashboard_id}", status_code=204)
async def delete_dashboard(
    dashboard_id: uuid.UUID,
    ctx: RequireAdmin,
    db: DbDep,
) -> None:
    _, org, _ = ctx
    await dashboard_service.delete_dashboard(db, org.id, dashboard_id)


@router.post("/{dashboard_id}/share", response_model=ApiResponse[ShareResponse])
async def share_dashboard(
    dashboard_id: uuid.UUID,
    body: DashboardShareRequest,
    ctx: RequireAnalyst,
    db: DbDep,
) -> Any:
    _, org, _ = ctx
    share_url, token = await dashboard_service.share_dashboard(
        db, org.id, dashboard_id, body.is_public, settings.FRONTEND_URL
    )
    return ApiResponse(data=ShareResponse(is_public=body.is_public, share_token=token, share_url=share_url))

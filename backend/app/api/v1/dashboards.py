import uuid
from typing import Any

from fastapi import APIRouter

from app.core.config import settings
from app.core.dependencies import CurrentUser, DbDep, RedisDep
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
async def list_dashboards(user: CurrentUser, db: DbDep, redis: RedisDep) -> Any:
    from sqlalchemy import select as sa_select

    from app.models.membership import Membership
    result = await db.execute(
        sa_select(Membership).where(
            Membership.user_id == user.id,
            Membership.deleted_at.is_(None),
        )
    )
    membership = result.scalar_one_or_none()
    if not membership:
        return ApiResponse(data=[])
    org_id = membership.organization_id

    pairs = await dashboard_service.list_dashboards(db, org_id)
    items = [
        DashboardListItem(
            id=d.id,
            created_at=d.created_at,
            updated_at=d.updated_at,
            name=d.name,
            description=d.description,
            widget_count=count,
            is_public=d.is_public,
            auto_refresh_interval=_refresh_label(d.refresh_interval),
        )
        for d, count in pairs
    ]
    return ApiResponse(data=items)


@router.post("", response_model=ApiResponse[DashboardResponse], status_code=201)
async def create_dashboard(
    body: DashboardCreateRequest,
    user: CurrentUser,
    db: DbDep,
    redis: RedisDep,
) -> Any:
    from sqlalchemy import select as sa_select

    from app.models.membership import Membership
    result = await db.execute(
        sa_select(Membership).where(
            Membership.user_id == user.id,
            Membership.deleted_at.is_(None),
        )
    )
    membership = result.scalar_one_or_none()
    if not membership:
        from app.core.exceptions import AuthorizationError
        raise AuthorizationError("No organization membership found")
    org_id = membership.organization_id

    from sqlalchemy.orm import selectinload as sli
    dashboard = await dashboard_service.create_dashboard(db, org_id, user.id, body)
    # Reload with widgets
    from sqlalchemy import select as sa_select2
    result2 = await db.execute(
        sa_select2(type(dashboard)).where(type(dashboard).id == dashboard.id).options(sli(type(dashboard).widgets))
    )
    dashboard = result2.scalar_one()
    data = await _build_dashboard_response(dashboard, org_id, db, redis)
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
    user: CurrentUser,
    db: DbDep,
    redis: RedisDep,
) -> Any:
    from sqlalchemy import select as sa_select

    from app.models.membership import Membership
    result = await db.execute(
        sa_select(Membership).where(
            Membership.user_id == user.id,
            Membership.deleted_at.is_(None),
        )
    )
    membership = result.scalar_one_or_none()
    if not membership:
        from app.core.exceptions import AuthorizationError
        raise AuthorizationError("No organization membership found")
    org_id = membership.organization_id

    dashboard = await dashboard_service.get_dashboard(db, org_id, dashboard_id, redis)
    data = await _build_dashboard_response(dashboard, org_id, db, redis)
    return ApiResponse(data=data)


@router.put("/{dashboard_id}", response_model=ApiResponse[DashboardResponse])
async def update_dashboard(
    dashboard_id: uuid.UUID,
    body: DashboardUpdateRequest,
    user: CurrentUser,
    db: DbDep,
    redis: RedisDep,
) -> Any:
    from sqlalchemy import select as sa_select

    from app.models.membership import Membership
    result = await db.execute(
        sa_select(Membership).where(
            Membership.user_id == user.id,
            Membership.deleted_at.is_(None),
        )
    )
    membership = result.scalar_one_or_none()
    org_id = membership.organization_id if membership else None
    if not org_id:
        from app.core.exceptions import AuthorizationError
        raise AuthorizationError("No organization membership found")

    dashboard = await dashboard_service.update_dashboard(db, org_id, dashboard_id, body)
    data = await _build_dashboard_response(dashboard, org_id, db, redis)
    return ApiResponse(data=data)


@router.delete("/{dashboard_id}", status_code=204)
async def delete_dashboard(
    dashboard_id: uuid.UUID,
    user: CurrentUser,
    db: DbDep,
) -> None:
    from sqlalchemy import select as sa_select

    from app.models.membership import Membership
    result = await db.execute(
        sa_select(Membership).where(
            Membership.user_id == user.id,
            Membership.deleted_at.is_(None),
        )
    )
    membership = result.scalar_one_or_none()
    org_id = membership.organization_id if membership else None
    if not org_id:
        from app.core.exceptions import AuthorizationError
        raise AuthorizationError("No organization membership found")
    await dashboard_service.delete_dashboard(db, org_id, dashboard_id)


@router.post("/{dashboard_id}/share", response_model=ApiResponse[ShareResponse])
async def share_dashboard(
    dashboard_id: uuid.UUID,
    body: DashboardShareRequest,
    user: CurrentUser,
    db: DbDep,
) -> Any:
    from sqlalchemy import select as sa_select

    from app.models.membership import Membership
    result = await db.execute(
        sa_select(Membership).where(
            Membership.user_id == user.id,
            Membership.deleted_at.is_(None),
        )
    )
    membership = result.scalar_one_or_none()
    org_id = membership.organization_id if membership else None
    if not org_id:
        from app.core.exceptions import AuthorizationError
        raise AuthorizationError("No organization membership found")

    share_url, share_token = await dashboard_service.share_dashboard(
        db, org_id, dashboard_id, body.enabled, settings.FRONTEND_URL
    )
    return ApiResponse(data=ShareResponse(share_url=share_url or "", share_token=share_token))

import json
import secrets
import uuid
from datetime import UTC, datetime
from typing import Any

import structlog
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import AuthorizationError, NotFoundError
from app.models.dashboard import Dashboard
from app.models.event import Event
from app.models.saved_query import SavedQuery
from app.models.widget import Widget
from app.schemas.dashboard import (
    REFRESH_INTERVAL_SECONDS,
    DashboardCreateRequest,
    DashboardUpdateRequest,
    QueryResultPoint,
    SavedQueryCreateRequest,
    SavedQueryUpdateRequest,
    WidgetCreateRequest,
    WidgetUpdateRequest,
)

logger = structlog.get_logger()

_CACHE_TTL = 300  # 5 minutes

# ── Helpers ────────────────────────────────────────────────────────────────────

def _time_range_to_interval(time_range: str) -> str:
    mapping = {"1h": "1 hour", "6h": "6 hours", "24h": "24 hours", "7d": "7 days", "30d": "30 days"}
    return mapping.get(time_range, "24 hours")


def _group_by_to_trunc(group_by: str) -> str:
    mapping = {"minute": "minute", "hour": "hour", "day": "day", "week": "week", "month": "month"}
    return mapping.get(group_by, "hour")


# ── Query Execution Engine ─────────────────────────────────────────────────────

async def execute_query(
    session: AsyncSession,
    org_id: uuid.UUID,
    query_config: dict[str, Any],
    time_range: str,
    redis: Any | None = None,
) -> tuple[list[QueryResultPoint], bool]:
    """Execute a saved query and return (data_points, was_cached)."""
    cache_key = f"query:{org_id}:{json.dumps(query_config, sort_keys=True)}:{time_range}"

    # Try cache first
    if redis:
        try:
            cached = await redis.get(cache_key)
            if cached:
                raw = json.loads(cached)
                points = [QueryResultPoint(bucket=p["bucket"], value=p["value"]) for p in raw]
                return points, True
        except Exception:
            pass

    event_name: str = query_config.get("event_name", "")
    aggregation: str = query_config.get("aggregation", "count")
    group_by: str = query_config.get("group_by", "hour")
    filters: list[dict[str, Any]] = query_config.get("filters", [])

    trunc = _group_by_to_trunc(group_by)
    interval = _time_range_to_interval(time_range)

    # Build aggregation expression
    if aggregation == "count":
        agg_expr = func.count().label("value")
    elif aggregation == "sum":
        agg_expr = func.sum(text("1")).label("value")
    elif aggregation == "avg":
        agg_expr = func.avg(text("1")).label("value")
    else:
        agg_expr = func.count().label("value")

    bucket_expr = func.date_trunc(trunc, Event.timestamp).label("bucket")

    stmt = (
        select(bucket_expr, agg_expr)
        .where(
            Event.organization_id == org_id,
            Event.event_name == event_name,
            Event.timestamp >= text(f"NOW() - INTERVAL '{interval}'"),
            Event.deleted_at.is_(None),
        )
        .group_by(bucket_expr)
        .order_by(bucket_expr)
    )

    # Apply property filters
    for f in filters:
        key = f.get("key", "")
        op = f.get("operator", "eq")
        val = f.get("value", "")
        prop_col = text(f"properties->>'{key}'")
        if op == "eq":
            stmt = stmt.where(prop_col == val)
        elif op == "neq":
            stmt = stmt.where(prop_col != val)
        elif op == "contains":
            stmt = stmt.where(text(f"properties->>'{key}' ILIKE '%{val}%'"))

    result = await session.execute(stmt)
    rows = result.all()

    points = [
        QueryResultPoint(bucket=str(row.bucket), value=float(row.value or 0))
        for row in rows
    ]

    # Cache result (including empty results to avoid repeated DB hits)
    if redis:
        try:
            payload = [{"bucket": p.bucket, "value": p.value} for p in points]
            await redis.setex(cache_key, _CACHE_TTL, json.dumps(payload))
        except Exception:
            pass

    return points, False


# ── Saved Query CRUD ───────────────────────────────────────────────────────────

async def create_saved_query(
    session: AsyncSession,
    org_id: uuid.UUID,
    data: SavedQueryCreateRequest,
) -> SavedQuery:
    config = {
        "event_name": data.event_name,
        "aggregation": data.aggregation,
        "group_by": data.group_by,
        "filters": [f.model_dump() for f in data.filters],
        "time_range": data.time_range,
    }
    sq = SavedQuery(
        organization_id=org_id,
        name=data.name,
        description=data.description,
        query_config=config,
    )
    session.add(sq)
    await session.commit()
    await session.refresh(sq)
    return sq


async def list_saved_queries(
    session: AsyncSession,
    org_id: uuid.UUID,
) -> list[SavedQuery]:
    result = await session.execute(
        select(SavedQuery).where(
            SavedQuery.organization_id == org_id,
            SavedQuery.deleted_at.is_(None),
        ).order_by(SavedQuery.created_at.desc())
    )
    return list(result.scalars().all())


async def get_saved_query(
    session: AsyncSession,
    org_id: uuid.UUID,
    query_id: uuid.UUID,
) -> SavedQuery:
    sq = await session.get(SavedQuery, query_id)
    if not sq or sq.deleted_at or sq.organization_id != org_id:
        raise NotFoundError("SavedQuery", str(query_id))
    return sq


async def update_saved_query(
    session: AsyncSession,
    org_id: uuid.UUID,
    query_id: uuid.UUID,
    data: SavedQueryUpdateRequest,
) -> SavedQuery:
    sq = await get_saved_query(session, org_id, query_id)
    if data.name is not None:
        sq.name = data.name
    if data.description is not None:
        sq.description = data.description
    config = dict(sq.query_config)
    if data.event_name is not None:
        config["event_name"] = data.event_name
    if data.aggregation is not None:
        config["aggregation"] = data.aggregation
    if data.group_by is not None:
        config["group_by"] = data.group_by
    if data.filters is not None:
        config["filters"] = [f.model_dump() for f in data.filters]
    if data.time_range is not None:
        config["time_range"] = data.time_range
    sq.query_config = config
    await session.commit()
    await session.refresh(sq)
    return sq


async def delete_saved_query(
    session: AsyncSession,
    org_id: uuid.UUID,
    query_id: uuid.UUID,
) -> None:
    sq = await get_saved_query(session, org_id, query_id)
    sq.deleted_at = datetime.now(UTC)
    await session.commit()


# ── Dashboard CRUD ─────────────────────────────────────────────────────────────

async def list_dashboards(
    session: AsyncSession,
    org_id: uuid.UUID,
) -> list[tuple[Dashboard, int]]:
    result = await session.execute(
        select(Dashboard)
        .where(Dashboard.organization_id == org_id, Dashboard.deleted_at.is_(None))
        .order_by(Dashboard.created_at.desc())
        .options(selectinload(Dashboard.widgets))
    )
    dashboards = list(result.scalars().all())
    return [(d, len([w for w in d.widgets if not w.deleted_at])) for d in dashboards]


async def get_dashboard(
    session: AsyncSession,
    org_id: uuid.UUID,
    dashboard_id: uuid.UUID,
    redis: Any | None = None,
) -> Dashboard:
    result = await session.execute(
        select(Dashboard)
        .where(Dashboard.id == dashboard_id, Dashboard.deleted_at.is_(None))
        .options(selectinload(Dashboard.widgets))
    )
    dashboard = result.scalar_one_or_none()
    if not dashboard:
        raise NotFoundError("Dashboard", str(dashboard_id))
    if dashboard.organization_id != org_id:
        raise AuthorizationError("Access denied")
    return dashboard


async def get_dashboard_by_share_token(
    session: AsyncSession,
    share_token: str,
) -> Dashboard:
    result = await session.execute(
        select(Dashboard)
        .where(
            Dashboard.share_token == share_token,
            Dashboard.is_public.is_(True),
            Dashboard.deleted_at.is_(None),
        )
        .options(selectinload(Dashboard.widgets))
    )
    dashboard = result.scalar_one_or_none()
    if not dashboard:
        raise NotFoundError("Dashboard", share_token)
    return dashboard


async def create_dashboard(
    session: AsyncSession,
    org_id: uuid.UUID,
    user_id: uuid.UUID,
    data: DashboardCreateRequest,
) -> Dashboard:
    refresh_seconds: int | None = None
    if data.auto_refresh_interval:
        refresh_seconds = REFRESH_INTERVAL_SECONDS.get(data.auto_refresh_interval)

    dashboard = Dashboard(
        organization_id=org_id,
        created_by_id=user_id,
        name=data.name,
        description=data.description,
        refresh_interval=refresh_seconds,
        template_type=data.template_type,
    )
    session.add(dashboard)
    await session.flush()  # get dashboard.id before template widgets

    if data.template_type:
        await _apply_template(session, org_id, dashboard.id, data.template_type)

    await session.commit()
    await session.refresh(dashboard)
    return dashboard


async def update_dashboard(
    session: AsyncSession,
    org_id: uuid.UUID,
    dashboard_id: uuid.UUID,
    data: DashboardUpdateRequest,
) -> Dashboard:
    dashboard = await get_dashboard(session, org_id, dashboard_id)
    if data.name is not None:
        dashboard.name = data.name
    if data.description is not None:
        dashboard.description = data.description
    if data.auto_refresh_interval is not None:
        dashboard.refresh_interval = REFRESH_INTERVAL_SECONDS.get(data.auto_refresh_interval)
    await session.commit()
    await session.refresh(dashboard)
    return dashboard


async def delete_dashboard(
    session: AsyncSession,
    org_id: uuid.UUID,
    dashboard_id: uuid.UUID,
) -> None:
    dashboard = await get_dashboard(session, org_id, dashboard_id)
    dashboard.deleted_at = datetime.now(UTC)
    await session.commit()


async def share_dashboard(
    session: AsyncSession,
    org_id: uuid.UUID,
    dashboard_id: uuid.UUID,
    enabled: bool,
    frontend_url: str,
) -> tuple[str | None, str | None]:
    dashboard = await get_dashboard(session, org_id, dashboard_id)
    if enabled:
        if not dashboard.share_token:
            dashboard.share_token = secrets.token_urlsafe(32)
        dashboard.is_public = True
        await session.commit()
        share_url = f"{frontend_url}/shared/{dashboard.share_token}"
        return share_url, dashboard.share_token
    else:
        dashboard.is_public = False
        dashboard.share_token = None
        await session.commit()
        return None, None


# ── Widget CRUD ────────────────────────────────────────────────────────────────

async def create_widget(
    session: AsyncSession,
    org_id: uuid.UUID,
    data: WidgetCreateRequest,
) -> Widget:
    # Verify dashboard belongs to org
    dashboard = await get_dashboard(session, org_id, data.dashboard_id)

    # Verify saved query belongs to org if provided
    if data.saved_query_id:
        sq = await session.get(SavedQuery, data.saved_query_id)
        if not sq or sq.organization_id != org_id or sq.deleted_at:
            raise NotFoundError("SavedQuery", str(data.saved_query_id))

    widget = Widget(
        dashboard_id=dashboard.id,
        saved_query_id=data.saved_query_id,
        title=data.title,
        widget_type=data.widget_type,
        config={"time_range": data.time_range},
        position_x=data.position.x,
        position_y=data.position.y,
        width=data.position.w,
        height=data.position.h,
    )
    session.add(widget)
    await session.commit()
    await session.refresh(widget)
    return widget


async def get_widget(
    session: AsyncSession,
    org_id: uuid.UUID,
    widget_id: uuid.UUID,
) -> Widget:
    result = await session.execute(
        select(Widget)
        .where(Widget.id == widget_id, Widget.deleted_at.is_(None))
        .options(selectinload(Widget.dashboard))
    )
    widget = result.scalar_one_or_none()
    if not widget:
        raise NotFoundError("Widget", str(widget_id))
    if widget.dashboard.organization_id != org_id:
        raise AuthorizationError("Access denied")
    return widget


async def update_widget(
    session: AsyncSession,
    org_id: uuid.UUID,
    widget_id: uuid.UUID,
    data: WidgetUpdateRequest,
) -> Widget:
    widget = await get_widget(session, org_id, widget_id)
    if data.title is not None:
        widget.title = data.title
    if data.widget_type is not None:
        widget.widget_type = data.widget_type
    if data.saved_query_id is not None:
        sq = await session.get(SavedQuery, data.saved_query_id)
        if not sq or sq.organization_id != org_id or sq.deleted_at:
            raise NotFoundError("SavedQuery", str(data.saved_query_id))
        widget.saved_query_id = data.saved_query_id
    if data.time_range is not None:
        config = dict(widget.config)
        config["time_range"] = data.time_range
        widget.config = config
    if data.position is not None:
        widget.position_x = data.position.x
        widget.position_y = data.position.y
        widget.width = data.position.w
        widget.height = data.position.h
    await session.commit()
    await session.refresh(widget)
    return widget


async def delete_widget(
    session: AsyncSession,
    org_id: uuid.UUID,
    widget_id: uuid.UUID,
) -> None:
    widget = await get_widget(session, org_id, widget_id)
    widget.deleted_at = datetime.now(UTC)
    await session.commit()


# ── Templates ──────────────────────────────────────────────────────────────────

_TEMPLATES: dict[str, list[dict[str, Any]]] = {
    "web_analytics": [
        {"title": "Page Views Over Time", "widget_type": "line_chart", "event_name": "page_view", "aggregation": "count", "group_by": "hour", "time_range": "24h", "x": 0, "y": 0, "w": 8, "h": 4},
        {"title": "Total Visitors", "widget_type": "kpi_card", "event_name": "page_view", "aggregation": "count", "group_by": "day", "time_range": "7d", "x": 8, "y": 0, "w": 4, "h": 2},
        {"title": "Sign Ups", "widget_type": "kpi_card", "event_name": "sign_up", "aggregation": "count", "group_by": "day", "time_range": "7d", "x": 8, "y": 2, "w": 4, "h": 2},
        {"title": "Button Clicks by Day", "widget_type": "bar_chart", "event_name": "button_click", "aggregation": "count", "group_by": "day", "time_range": "7d", "x": 0, "y": 4, "w": 6, "h": 4},
        {"title": "Event Breakdown", "widget_type": "pie_chart", "event_name": "page_view", "aggregation": "count", "group_by": "day", "time_range": "7d", "x": 6, "y": 4, "w": 6, "h": 4},
    ],
    "sales": [
        {"title": "Purchases Over Time", "widget_type": "line_chart", "event_name": "purchase", "aggregation": "count", "group_by": "day", "time_range": "30d", "x": 0, "y": 0, "w": 8, "h": 4},
        {"title": "Total Purchases", "widget_type": "kpi_card", "event_name": "purchase", "aggregation": "count", "group_by": "day", "time_range": "30d", "x": 8, "y": 0, "w": 4, "h": 2},
        {"title": "Checkouts", "widget_type": "kpi_card", "event_name": "checkout", "aggregation": "count", "group_by": "day", "time_range": "7d", "x": 8, "y": 2, "w": 4, "h": 2},
        {"title": "Daily Sales", "widget_type": "bar_chart", "event_name": "purchase", "aggregation": "count", "group_by": "day", "time_range": "30d", "x": 0, "y": 4, "w": 12, "h": 4},
    ],
    "devops": [
        {"title": "Error Rate Over Time", "widget_type": "line_chart", "event_name": "error", "aggregation": "count", "group_by": "hour", "time_range": "24h", "x": 0, "y": 0, "w": 8, "h": 4},
        {"title": "Total Errors", "widget_type": "kpi_card", "event_name": "error", "aggregation": "count", "group_by": "hour", "time_range": "24h", "x": 8, "y": 0, "w": 4, "h": 2},
        {"title": "Requests", "widget_type": "kpi_card", "event_name": "request", "aggregation": "count", "group_by": "hour", "time_range": "24h", "x": 8, "y": 2, "w": 4, "h": 2},
        {"title": "Request Volume", "widget_type": "bar_chart", "event_name": "request", "aggregation": "count", "group_by": "hour", "time_range": "24h", "x": 0, "y": 4, "w": 6, "h": 4},
        {"title": "Error Breakdown", "widget_type": "pie_chart", "event_name": "error", "aggregation": "count", "group_by": "day", "time_range": "7d", "x": 6, "y": 4, "w": 6, "h": 4},
    ],
}


async def _apply_template(
    session: AsyncSession,
    org_id: uuid.UUID,
    dashboard_id: uuid.UUID,
    template_type: str,
) -> None:
    widgets_config = _TEMPLATES.get(template_type, [])
    for wc in widgets_config:
        config = {
            "event_name": wc["event_name"],
            "aggregation": wc["aggregation"],
            "group_by": wc["group_by"],
            "filters": [],
            "time_range": wc["time_range"],
        }
        sq = SavedQuery(
            organization_id=org_id,
            name=f"{wc['title']} Query",
            query_config=config,
        )
        session.add(sq)
        await session.flush()

        widget = Widget(
            dashboard_id=dashboard_id,
            saved_query_id=sq.id,
            title=wc["title"],
            widget_type=wc["widget_type"],
            config={"time_range": wc["time_range"]},
            position_x=wc["x"],
            position_y=wc["y"],
            width=wc["w"],
            height=wc["h"],
        )
        session.add(widget)

    logger.info("template_applied", template=template_type, dashboard_id=str(dashboard_id))

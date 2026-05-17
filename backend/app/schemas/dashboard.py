import uuid
from typing import Any, Literal

from pydantic import Field, field_validator

from app.schemas.common import BaseResponse, BaseSchema

# ── Saved Query ────────────────────────────────────────────────────────────────

AggregationType = Literal["count", "sum", "avg", "min", "max"]
GroupByType = Literal["minute", "hour", "day", "week", "month"]
TimeRange = Literal["1h", "6h", "24h", "7d", "30d"]


class QueryFilter(BaseSchema):
    key: str
    operator: Literal["eq", "neq", "gt", "gte", "lt", "lte", "contains"]
    value: str


class SavedQueryCreateRequest(BaseSchema):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    event_name: str = Field(min_length=1, max_length=255)
    aggregation: AggregationType = "count"
    group_by: GroupByType = "hour"
    filters: list[QueryFilter] = Field(default_factory=list)
    time_range: TimeRange = "24h"


class SavedQueryUpdateRequest(BaseSchema):
    name: str | None = None
    description: str | None = None
    event_name: str | None = None
    aggregation: AggregationType | None = None
    group_by: GroupByType | None = None
    filters: list[QueryFilter] | None = None
    time_range: TimeRange | None = None


class SavedQueryResponse(BaseResponse):
    organization_id: uuid.UUID
    name: str
    description: str | None
    query_config: dict[str, Any]

    @property
    def event_name(self) -> str:
        return str(self.query_config.get("event_name", ""))


# ── Widget ─────────────────────────────────────────────────────────────────────

WidgetType = Literal["line_chart", "bar_chart", "pie_chart", "kpi_card", "table"]

WIDGET_TYPES = {"line_chart", "bar_chart", "pie_chart", "kpi_card", "table"}


class WidgetPosition(BaseSchema):
    x: int = Field(ge=0)
    y: int = Field(ge=0)
    w: int = Field(ge=1, le=12)
    h: int = Field(ge=1)


class WidgetCreateRequest(BaseSchema):
    dashboard_id: uuid.UUID
    title: str = Field(min_length=1, max_length=255)
    widget_type: WidgetType
    saved_query_id: uuid.UUID | None = None
    time_range: TimeRange = "24h"
    position: WidgetPosition = Field(default_factory=lambda: WidgetPosition(x=0, y=0, w=6, h=4))

    @field_validator("widget_type")
    @classmethod
    def validate_widget_type(cls, v: str) -> str:
        if v not in WIDGET_TYPES:
            raise ValueError(f"widget_type must be one of {WIDGET_TYPES}")
        return v


class WidgetUpdateRequest(BaseSchema):
    title: str | None = None
    widget_type: WidgetType | None = None
    saved_query_id: uuid.UUID | None = None
    time_range: TimeRange | None = None
    position: WidgetPosition | None = None


class QueryResultPoint(BaseSchema):
    bucket: str
    value: float


class QueryResult(BaseSchema):
    data: list[QueryResultPoint]
    cached: bool = False
    cached_at: str | None = None


class WidgetResponse(BaseResponse):
    dashboard_id: uuid.UUID
    saved_query_id: uuid.UUID | None
    title: str
    widget_type: str
    time_range: str
    position_x: int
    position_y: int
    width: int
    height: int
    query_result: QueryResult | None = None


# ── Dashboard ──────────────────────────────────────────────────────────────────

RefreshInterval = Literal["30s", "1m", "5m"]
TemplateType = Literal["web_analytics", "sales", "devops"]

REFRESH_INTERVAL_SECONDS = {"30s": 30, "1m": 60, "5m": 300}


class DashboardCreateRequest(BaseSchema):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    auto_refresh_interval: RefreshInterval | None = None
    template_type: TemplateType | None = None


class DashboardUpdateRequest(BaseSchema):
    name: str | None = None
    description: str | None = None
    auto_refresh_interval: RefreshInterval | None = None


class DashboardShareRequest(BaseSchema):
    enabled: bool


class DashboardListItem(BaseResponse):
    name: str
    description: str | None
    widget_count: int
    is_public: bool
    auto_refresh_interval: str | None
    created_at: Any
    updated_at: Any


class DashboardResponse(BaseResponse):
    organization_id: uuid.UUID
    name: str
    description: str | None
    is_public: bool
    share_token: str | None
    auto_refresh_interval: str | None
    template_type: str | None
    widgets: list[WidgetResponse] = Field(default_factory=list)


class ShareResponse(BaseSchema):
    share_url: str
    share_token: str | None

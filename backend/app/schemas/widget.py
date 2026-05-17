import uuid
from typing import Any

from pydantic import Field

from app.schemas.common import BaseResponse, BaseSchema

WIDGET_TYPES = {"line_chart", "bar_chart", "pie_chart", "kpi_card", "table"}


class WidgetCreateRequest(BaseSchema):
    title: str = Field(min_length=1, max_length=255)
    widget_type: str
    saved_query_id: uuid.UUID | None = None
    config: dict[str, Any] = Field(default_factory=dict)
    position_x: int = 0
    position_y: int = 0
    width: int = 4
    height: int = 3


class WidgetUpdateRequest(BaseSchema):
    title: str | None = None
    config: dict[str, Any] | None = None
    position_x: int | None = None
    position_y: int | None = None
    width: int | None = None
    height: int | None = None


class WidgetResponse(BaseResponse):
    dashboard_id: uuid.UUID
    saved_query_id: uuid.UUID | None
    title: str
    widget_type: str
    config: dict[str, Any]
    position_x: int
    position_y: int
    width: int
    height: int

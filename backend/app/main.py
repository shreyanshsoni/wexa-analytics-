from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator

from app.api.router import api_router
from app.core.config import settings
from app.core.middleware import setup_middleware
from app.core.redis import close_redis

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    logger.info("startup", environment=settings.ENVIRONMENT)
    yield
    await close_redis()
    logger.info("shutdown")


app = FastAPI(
    title="Wexa Analytics API",
    description="Real-Time Analytics & Reporting Platform",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

setup_middleware(app)
app.include_router(api_router, prefix="/api/v1")

# Expose Prometheus metrics at GET /metrics
# Tracks: request count, latency histograms, in-progress requests — per route + status code
Instrumentator(
    should_group_status_codes=False,
    excluded_handlers=["/metrics"],  # don't track scrapes of /metrics itself
).instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)

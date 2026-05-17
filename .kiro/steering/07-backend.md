# 07-backend.md — Backend Implementation Details

---

## FastAPI App Setup

### main.py Structure
```python
# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import structlog

from app.core.middleware import add_middlewares
from app.core.exceptions import add_exception_handlers
from app.api.router import api_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    structlog.configure(...)
    yield
    # Shutdown
    await engine.dispose()

app = FastAPI(
    title="Wexa Analytics API",
    version="1.0.0",
    lifespan=lifespan,
)

add_middlewares(app)
add_exception_handlers(app)
app.include_router(api_router, prefix="/api/v1")
```

---

## Error Handling

### Custom Exception Hierarchy
```python
# app/core/exceptions.py

class AppException(Exception):
    """Base exception for all app errors"""
    status_code: int = 500
    error_code: str = "INTERNAL_ERROR"
    message: str = "An unexpected error occurred"

class NotFoundError(AppException):
    status_code = 404
    error_code = "NOT_FOUND"

class UnauthorizedError(AppException):
    status_code = 401
    error_code = "UNAUTHORIZED"

class ForbiddenError(AppException):
    status_code = 403
    error_code = "FORBIDDEN"

class ValidationError(AppException):
    status_code = 422
    error_code = "VALIDATION_ERROR"

class ConflictError(AppException):
    status_code = 409
    error_code = "CONFLICT"

class RateLimitError(AppException):
    status_code = 429
    error_code = "RATE_LIMIT_EXCEEDED"

class InternalError(AppException):
    status_code = 500
    error_code = "INTERNAL_ERROR"
```

### Centralized Exception Handler
```python
# All exceptions return same format
def add_exception_handlers(app: FastAPI):
    @app.exception_handler(AppException)
    async def app_exception_handler(request, exc: AppException):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": exc.error_code,
                    "message": exc.message,
                    "request_id": request.state.request_id,
                }
            }
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request, exc):
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Request validation failed",
                    "details": exc.errors(),
                    "request_id": request.state.request_id,
                }
            }
        )
```

---

## Middleware Stack

### Correlation ID Middleware
```python
# app/core/middleware.py
import uuid
import structlog

class CorrelationIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request.state.request_id = request_id

        # Bind to structlog context
        structlog.contextvars.bind_contextvars(request_id=request_id)

        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id

        structlog.contextvars.clear_contextvars()
        return response
```

---

## Celery Configuration

### Celery App Setup
```python
# app/workers/celery_app.py
from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "wexa",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    broker_use_ssl={"ssl_cert_reqs": "required"},  # Upstash requires SSL
    redis_backend_use_ssl={"ssl_cert_reqs": "required"},
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,                # acknowledge after completion not before
    worker_prefetch_multiplier=1,       # one task at a time per worker
    task_routes={
        "app.workers.tasks.ingestion_tasks.*": {"queue": "ingestion"},
        "app.workers.tasks.alert_tasks.*": {"queue": "alerts"},
        "app.workers.tasks.report_tasks.*": {"queue": "reports"},
    },
    # Dead letter queue for failed tasks
    task_reject_on_worker_lost=True,
    task_default_retry_delay=60,        # retry after 60 seconds
)
```

### Celery Beat Schedule
```python
# app/workers/beat_schedule.py
from celery.schedules import crontab

BEAT_SCHEDULE = {
    "evaluate-alerts-every-minute": {
        "task": "app.workers.tasks.alert_tasks.evaluate_all_alerts",
        "schedule": 60.0,               # every 60 seconds
        "options": {"queue": "alerts"},
    },
    "process-scheduled-reports": {
        "task": "app.workers.tasks.report_tasks.process_scheduled_reports",
        "schedule": crontab(minute=0),  # every hour
        "options": {"queue": "reports"},
    },
    "cleanup-expired-tokens": {
        "task": "app.workers.tasks.auth_tasks.cleanup_expired_tokens",
        "schedule": crontab(hour=2, minute=0),  # daily at 2am
    },
}
```

### Celery Task Patterns
```python
# app/workers/tasks/ingestion_tasks.py
from celery import shared_task
from celery.utils.log import get_task_logger
import asyncio

logger = get_task_logger(__name__)

@celery_app.task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    autoretry_for=(Exception,),
    retry_backoff=True,             # exponential backoff
    retry_backoff_max=600,          # max 10 minutes between retries
    retry_jitter=True,              # add randomness to backoff
    name="ingestion.process_event",
    queue="ingestion",
)
def process_event(self, event_data: dict, org_id: str):
    """Process and store a single event"""
    try:
        # Run async code in Celery (sync context)
        asyncio.run(_process_event_async(event_data, org_id))
    except Exception as exc:
        logger.error(f"Failed to process event: {exc}")
        raise self.retry(exc=exc)

async def _process_event_async(event_data: dict, org_id: str):
    async with AsyncSessionLocal() as db:
        # normalize and store event
        ...
```

---

## Observability

### Structlog Configuration
```python
# app/core/config.py
import structlog

def configure_logging():
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.dev.ConsoleRenderer() if DEV else structlog.processors.JSONRenderer(),
        ],
        logger_factory=structlog.PrintLoggerFactory(),
    )

# Usage throughout app:
logger = structlog.get_logger()
logger.info("user_login", user_id=str(user.id), org_id=str(org.id))
logger.error("ingestion_failed", event_name=event_data.get("event"), error=str(e))
```

### Health Check Endpoint
```python
# app/api/v1/health.py
@router.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)):
    checks = {}

    # DB check
    try:
        await db.execute(text("SELECT 1"))
        checks["database"] = "healthy"
    except Exception:
        checks["database"] = "unhealthy"

    # Redis check
    try:
        await redis.ping()
        checks["redis"] = "healthy"
    except Exception:
        checks["redis"] = "unhealthy"

    status = "healthy" if all(v == "healthy" for v in checks.values()) else "unhealthy"
    return {"status": status, "checks": checks, "version": "1.0.0"}
```

---

## Upstash Redis Connection
```python
# app/core/redis.py
import redis.asyncio as aioredis
from app.core.config import settings

# IMPORTANT: Upstash requires SSL — use rediss:// not redis://
redis_client = aioredis.from_url(
    settings.REDIS_URL,             # must start with rediss://
    encoding="utf-8",
    decode_responses=True,
    ssl_cert_reqs=None,             # Upstash self-signed cert
)

async def get_redis():
    return redis_client
```

---

## Running Services Locally
```bash
# Terminal 1: FastAPI
cd backend
uvicorn app.main:app --reload --port 8000

# Terminal 2: Celery Worker
cd backend
celery -A app.workers.celery_app worker --loglevel=info -Q ingestion,alerts,reports

# Terminal 3: Celery Beat
cd backend
celery -A app.workers.celery_app beat --loglevel=info

# Terminal 4: Frontend
cd frontend
npm run dev
```

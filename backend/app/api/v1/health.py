import structlog
from fastapi import APIRouter
from sqlalchemy import text

from app.core.dependencies import DbDep, RedisDep

logger = structlog.get_logger()
router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check(db: DbDep, redis: RedisDep) -> dict:  # type: ignore[type-arg]
    db_status = "unhealthy"
    redis_status = "unhealthy"

    try:
        await db.execute(text("SELECT 1"))
        db_status = "healthy"
    except Exception as e:
        logger.error("db_health_check_failed", error=str(e))

    try:
        await redis.ping()
        redis_status = "healthy"
    except Exception as e:
        logger.error("redis_health_check_failed", error=str(e))

    overall = "healthy" if db_status == "healthy" and redis_status == "healthy" else "unhealthy"

    return {
        "status": overall,
        "checks": {
            "database": db_status,
            "redis": redis_status,
        },
    }

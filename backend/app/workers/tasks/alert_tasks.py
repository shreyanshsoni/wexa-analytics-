from typing import Any

import structlog

from app.workers.celery_app import celery_app

logger = structlog.get_logger()


@celery_app.task  # type: ignore
def evaluate_alerts() -> dict[str, Any]:
    logger.info("evaluating_alerts")
    return {"status": "evaluated"}


@celery_app.task  # type: ignore
def cleanup_expired_tokens() -> dict[str, Any]:
    logger.info("cleaning_up_expired_tokens")
    return {"status": "cleaned"}

import structlog

from app.workers.celery_app import celery_app

logger = structlog.get_logger()


@celery_app.task  # type: ignore[misc]
def evaluate_alerts() -> dict:  # type: ignore[type-arg]
    logger.info("evaluating_alerts")
    return {"status": "evaluated"}


@celery_app.task  # type: ignore[misc]
def cleanup_expired_tokens() -> dict:  # type: ignore[type-arg]
    logger.info("cleaning_up_expired_tokens")
    return {"status": "cleaned"}

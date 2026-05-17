import structlog

from app.workers.celery_app import celery_app

logger = structlog.get_logger()


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)  # type: ignore[misc]
def process_event(self: object, event_data: dict, org_id: str) -> dict:  # type: ignore[type-arg]
    logger.info("processing_event", org_id=org_id, event_name=event_data.get("event_name"))
    return {"status": "processed", "org_id": org_id}


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)  # type: ignore[misc]
def process_batch_events(self: object, events: list, org_id: str) -> dict:  # type: ignore[type-arg]
    logger.info("processing_batch", org_id=org_id, count=len(events))
    return {"status": "processed", "count": len(events)}


@celery_app.task(bind=True, max_retries=3, default_retry_delay=120)  # type: ignore[misc]
def process_csv_upload(self: object, file_path: str, org_id: str) -> dict:  # type: ignore[type-arg]
    logger.info("processing_csv", org_id=org_id, file=file_path)
    return {"status": "processed", "file": file_path}

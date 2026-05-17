from typing import Any

import structlog

from app.workers.celery_app import celery_app

logger = structlog.get_logger()


@celery_app.task(bind=True, max_retries=3, default_retry_delay=300)  # type: ignore
def generate_report(self: object, report_id: str, org_id: str) -> dict[str, Any]:
    logger.info("generating_report", report_id=report_id, org_id=org_id)
    return {"status": "generated", "report_id": report_id}

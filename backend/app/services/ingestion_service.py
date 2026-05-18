"""Ingestion service: rate limiting and Celery dispatch."""
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import structlog
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import RateLimitError
from app.repositories.event_repo import EventRepository

logger = structlog.get_logger()

_ORG_RATE_LIMIT = 1000   # events per minute per org
_KEY_RATE_LIMIT = 100    # events per minute per API key


async def _check_rate_limit(redis: Redis, key: str, limit: int) -> None:
    count = await redis.incr(key)
    if count == 1:
        await redis.expire(key, 60)
    if count > limit:
        raise RateLimitError(f"Rate limit exceeded ({limit}/min). Retry after 60 seconds.")


async def ingest_event(
    redis: Redis,
    event_data: dict[str, Any],
    api_key_id: uuid.UUID,
    org_id: uuid.UUID,
) -> str:
    await _check_rate_limit(redis, f"rl:org:{org_id}:events", _ORG_RATE_LIMIT)
    await _check_rate_limit(redis, f"rl:key:{api_key_id}:events", _KEY_RATE_LIMIT)

    from app.workers.tasks.ingestion_tasks import process_event
    batch_id = str(uuid.uuid4())
    process_event.delay(event_data, str(org_id), batch_id)

    logger.info("event_queued", org_id=str(org_id), event_name=event_data.get("event_name"))
    return batch_id


async def ingest_batch(
    redis: Redis,
    events: list[dict[str, Any]],
    api_key_id: uuid.UUID,
    org_id: uuid.UUID,
) -> str:
    count = len(events)
    await _check_rate_limit(redis, f"rl:org:{org_id}:events", _ORG_RATE_LIMIT)
    await _check_rate_limit(redis, f"rl:key:{api_key_id}:events", _KEY_RATE_LIMIT)

    from app.workers.tasks.ingestion_tasks import process_batch_events
    batch_id = str(uuid.uuid4())
    process_batch_events.delay(events, str(org_id), batch_id)

    logger.info("batch_queued", org_id=str(org_id), count=count)
    return batch_id


async def ingest_webhook(
    redis: Redis,
    event_name: str,
    properties: dict[str, Any],
    timestamp: Any,
    api_key_id: uuid.UUID,
    org_id: uuid.UUID,
) -> str:
    await _check_rate_limit(redis, f"rl:org:{org_id}:events", _ORG_RATE_LIMIT)
    await _check_rate_limit(redis, f"rl:key:{api_key_id}:events", _KEY_RATE_LIMIT)

    from app.workers.tasks.ingestion_tasks import process_event
    batch_id = str(uuid.uuid4())
    event_data = {
        "event_name": event_name,
        "properties": properties,
        "timestamp": timestamp.isoformat() if hasattr(timestamp, "isoformat") else None,
    }
    process_event.delay(event_data, str(org_id), batch_id)
    logger.info("webhook_event_queued", org_id=str(org_id), event_name=event_name)
    return batch_id


async def queue_csv_upload(
    org_id: uuid.UUID,
    file_path: str,
) -> str:
    from app.workers.tasks.ingestion_tasks import process_csv_upload
    upload_id = str(uuid.uuid4())
    process_csv_upload.delay(file_path, str(org_id), upload_id)

    logger.info("csv_queued", org_id=str(org_id), file=file_path)
    return upload_id


async def get_ingestion_stats(
    db: AsyncSession,
    org_id: uuid.UUID,
) -> dict[str, int]:
    repo = EventRepository(db)
    now = datetime.now(UTC)

    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    tomorrow_start = today_start + timedelta(days=1)
    week_start = now - timedelta(days=7)
    month_start = now - timedelta(days=30)
    epoch = datetime(2000, 1, 1, tzinfo=UTC)

    # Use timestamp (business event time) so seed data spans correctly across buckets.
    # today uses full-day range (not <= NOW()) to include future-timestamped seed events.
    total_today = await repo.count_by_org_in_range(org_id, today_start, tomorrow_start)
    total_week = await repo.count_by_org_in_range(org_id, week_start, tomorrow_start)
    total_month = await repo.count_by_org_in_range(org_id, month_start, tomorrow_start)
    total_all_time = await repo.count_by_org_in_range(org_id, epoch, tomorrow_start)

    return {
        "total_today": total_today,
        "total_week": total_week,
        "total_month": total_month,
        "total_all_time": total_all_time,
    }

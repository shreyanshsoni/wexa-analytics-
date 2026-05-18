"""Celery tasks: normalize and persist events to the database."""
import asyncio
import csv
import os
import uuid
from datetime import UTC, datetime
from typing import Any

import structlog
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.models.event import Event
from app.workers.celery_app import celery_app

logger = structlog.get_logger()


# ── helpers ──────────────────────────────────────────────────────────────────

def _parse_timestamp(raw: Any) -> datetime:
    if isinstance(raw, datetime):
        return raw if raw.tzinfo else raw.replace(tzinfo=UTC)
    if isinstance(raw, str):
        try:
            dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
            return dt if dt.tzinfo else dt.replace(tzinfo=UTC)
        except ValueError:
            pass
    return datetime.now(UTC)


def _build_event(data: dict[str, Any], org_id: uuid.UUID, source: str = "api") -> Event:
    return Event(
        organization_id=org_id,
        event_name=data["event_name"],
        properties=data.get("properties", {}),
        timestamp=_parse_timestamp(data.get("timestamp")),
        source=source,
    )


async def _store_events(events: list[Event]) -> None:
    # NullPool: no connection reuse — required because asyncio.run() closes the
    # event loop after each task, making pooled asyncpg connections invalid.
    engine = create_async_engine(settings.async_database_url, poolclass=NullPool)
    session_factory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    try:
        async with session_factory() as db:
            db.add_all(events)
            await db.commit()
    finally:
        await engine.dispose()


# ── tasks ─────────────────────────────────────────────────────────────────────

@celery_app.task(  # type: ignore[untyped-decorator]
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=300,
    retry_jitter=True,
    name="ingestion.process_event",
    queue="ingestion",
    ignore_result=True,
)
def process_event(
    self: Any,
    event_data: dict[str, Any],
    org_id: str,
    batch_id: str,
) -> dict[str, Any]:
    logger.info("task_process_event", org_id=org_id, batch_id=batch_id)
    try:
        event = _build_event(event_data, uuid.UUID(org_id))
        asyncio.run(_store_events([event]))
        logger.info("event_stored", org_id=org_id, batch_id=batch_id)
        return {"status": "stored", "batch_id": batch_id}
    except Exception as exc:
        logger.error("event_store_failed", org_id=org_id, error=str(exc))
        raise


@celery_app.task(  # type: ignore[untyped-decorator]
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=300,
    retry_jitter=True,
    name="ingestion.process_batch_events",
    queue="ingestion",
    ignore_result=True,
)
def process_batch_events(
    self: Any,
    events: list[dict[str, Any]],
    org_id: str,
    batch_id: str,
) -> dict[str, Any]:
    logger.info("task_process_batch", org_id=org_id, count=len(events), batch_id=batch_id)
    try:
        org_uuid = uuid.UUID(org_id)
        event_objects = [_build_event(e, org_uuid) for e in events]
        asyncio.run(_store_events(event_objects))
        logger.info("batch_stored", org_id=org_id, count=len(events), batch_id=batch_id)
        return {"status": "stored", "count": len(events), "batch_id": batch_id}
    except Exception as exc:
        logger.error("batch_store_failed", org_id=org_id, error=str(exc))
        raise


@celery_app.task(  # type: ignore[untyped-decorator]
    bind=True,
    max_retries=3,
    default_retry_delay=120,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
    name="ingestion.process_csv_upload",
    queue="ingestion",
    ignore_result=True,
)
def process_csv_upload(
    self: Any,
    file_path: str,
    org_id: str,
    upload_id: str,
) -> dict[str, Any]:
    logger.info("task_process_csv", org_id=org_id, file=file_path, upload_id=upload_id)
    try:
        org_uuid = uuid.UUID(org_id)
        event_objects: list[Event] = []
        errors: list[str] = []

        with open(file_path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row_num, row in enumerate(reader, start=2):  # 1-indexed, row 1 = header
                event_name = row.get("event_name") or row.get("event", "").strip()
                if not event_name:
                    errors.append(f"Row {row_num}: missing event_name")
                    continue

                # All non-reserved columns go into properties
                reserved = {"event_name", "event", "timestamp"}
                properties = {k: v for k, v in row.items() if k not in reserved and v != ""}

                event_objects.append(_build_event(
                    {
                        "event_name": event_name,
                        "properties": properties,
                        "timestamp": row.get("timestamp"),
                    },
                    org_uuid,
                    source="csv",
                ))

        if event_objects:
            asyncio.run(_store_events(event_objects))

        # Clean up temp file
        try:
            os.remove(file_path)
        except OSError:
            pass

        logger.info(
            "csv_stored",
            org_id=org_id,
            stored=len(event_objects),
            errors=len(errors),
            upload_id=upload_id,
        )
        return {"status": "stored", "stored": len(event_objects), "errors": errors}
    except Exception as exc:
        logger.error("csv_store_failed", org_id=org_id, error=str(exc))
        raise

"""Data ingestion endpoints: single event, batch, CSV upload, stats."""
import os
import tempfile

import aiofiles
import structlog
from fastapi import APIRouter, File, UploadFile
from fastapi import status as http_status

from app.core.dependencies import (
    ApiKeyDep,
    DbDep,
    RedisDep,
    RequireAnalyst,
    RequireMember,
    WebhookDep,
)
from app.core.exceptions import ValidationError
from app.schemas.common import ApiResponse
from app.schemas.event import (
    BatchEventIngestionRequest,
    CsvUploadResponse,
    EventIngestionRequest,
    IngestionResponse,
    IngestionStatsResponse,
    WebhookPayload,
    WebhookResponse,
)
from app.services import ingestion_service

router = APIRouter(prefix="/ingest", tags=["ingestion"])
logger = structlog.get_logger()

_MAX_CSV_BYTES = 10 * 1024 * 1024  # 10 MB


@router.post(
    "/events",
    status_code=http_status.HTTP_202_ACCEPTED,
    response_model=ApiResponse[IngestionResponse],
    summary="Ingest a single event",
)
async def ingest_event(
    body: EventIngestionRequest,
    api_key_ctx: ApiKeyDep,
    redis: RedisDep,
) -> ApiResponse[IngestionResponse]:
    api_key_id, org_id = api_key_ctx
    event_data = {
        "event_name": body.event_name,
        "properties": body.properties,
        "timestamp": body.timestamp.isoformat() if body.timestamp else None,
    }
    batch_id = await ingestion_service.ingest_event(redis, event_data, api_key_id, org_id)
    return ApiResponse(data=IngestionResponse(
        accepted=1,
        batch_id=batch_id,
        message="Event accepted for processing",
    ))


@router.post(
    "/events/batch",
    status_code=http_status.HTTP_202_ACCEPTED,
    response_model=ApiResponse[IngestionResponse],
    summary="Ingest a batch of events (max 1000)",
)
async def ingest_batch(
    body: BatchEventIngestionRequest,
    api_key_ctx: ApiKeyDep,
    redis: RedisDep,
) -> ApiResponse[IngestionResponse]:
    api_key_id, org_id = api_key_ctx
    events_data = [
        {
            "event_name": e.event_name,
            "properties": e.properties,
            "timestamp": e.timestamp.isoformat() if e.timestamp else None,
        }
        for e in body.events
    ]
    batch_id = await ingestion_service.ingest_batch(redis, events_data, api_key_id, org_id)
    return ApiResponse(data=IngestionResponse(
        accepted=len(body.events),
        batch_id=batch_id,
        message=f"{len(body.events)} events accepted for processing",
    ))


@router.post(
    "/csv",
    status_code=http_status.HTTP_202_ACCEPTED,
    response_model=ApiResponse[CsvUploadResponse],
    summary="Upload a CSV file for bulk ingestion (Analyst+ only)",
)
async def upload_csv(
    ctx: RequireAnalyst,
    db: DbDep,
    file: UploadFile = File(...),
) -> ApiResponse[CsvUploadResponse]:
    _, org, _ = ctx

    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise ValidationError("File must be a .csv file")

    content = await file.read()
    if len(content) > _MAX_CSV_BYTES:
        raise ValidationError("CSV file exceeds 10 MB limit")

    # Write to temp file for Celery task to consume
    fd, tmp_path = tempfile.mkstemp(suffix=".csv", prefix="wexa_csv_")
    try:
        async with aiofiles.open(tmp_path, "wb") as f:
            await f.write(content)
        os.close(fd)
    except Exception:
        os.close(fd)
        os.unlink(tmp_path)
        raise

    upload_id = await ingestion_service.queue_csv_upload(org.id, tmp_path)
    logger.info("csv_upload_accepted", org_id=str(org.id), upload_id=upload_id, size=len(content))

    return ApiResponse(data=CsvUploadResponse(
        upload_id=upload_id,
        message=f"CSV accepted ({len(content):,} bytes). Processing in background.",
    ))


@router.post(
    "/webhook",
    status_code=200,
    response_model=ApiResponse[WebhookResponse],
    summary="Receive a webhook event from an external service",
)
async def receive_webhook(
    body: WebhookPayload,
    webhook_ctx: WebhookDep,
    redis: RedisDep,
) -> ApiResponse[WebhookResponse]:
    api_key_id, org_id = webhook_ctx
    event_name = body.resolved_event_name()
    properties = body.resolved_properties()
    batch_id = await ingestion_service.ingest_webhook(
        redis, event_name, properties, body.timestamp, api_key_id, org_id
    )
    logger.info("webhook_received", org_id=str(org_id), event_name=event_name)
    return ApiResponse(data=WebhookResponse(
        received=1,
        batch_id=batch_id,
        message=f"Webhook event '{event_name}' accepted for processing",
    ))


@router.get(
    "/stats",
    response_model=ApiResponse[IngestionStatsResponse],
    summary="Get ingestion statistics for the organization",
)
async def get_stats(
    ctx: RequireMember,
    db: DbDep,
) -> ApiResponse[IngestionStatsResponse]:
    _, org, _ = ctx
    stats = await ingestion_service.get_ingestion_stats(db, org.id)
    return ApiResponse(data=IngestionStatsResponse(**stats))

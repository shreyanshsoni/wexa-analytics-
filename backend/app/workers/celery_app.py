import ssl

import certifi
from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "wexa",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=[
        "app.workers.tasks.ingestion_tasks",
        "app.workers.tasks.alert_tasks",
        "app.workers.tasks.report_tasks",
    ],
)

_ssl_options: dict | None = (
    {
        "ssl_cert_reqs": ssl.CERT_REQUIRED,
        "ssl_ca_certs": certifi.where(),
    }
    if settings.REDIS_URL.startswith("rediss://")
    else None
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    broker_connection_retry_on_startup=True,
    broker_transport_options={"visibility_timeout": 3600},
    broker_use_ssl=_ssl_options,
    redis_backend_use_ssl=_ssl_options,
)

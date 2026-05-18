import ssl
from typing import Any

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

_ssl_options: dict[str, Any] | None = (
    {
        "ssl_cert_reqs": ssl.CERT_REQUIRED,
        "ssl_ca_certs": certifi.where(),
    }
    if settings.REDIS_URL.startswith("rediss://")
    else None
)

_redis_transport_opts: dict[str, Any] = {
    "visibility_timeout": 3600,
    "socket_timeout": 10,
    "socket_connect_timeout": 5,
    "socket_keepalive": True,
    "retry_on_timeout": True,
    "health_check_interval": 25,
}

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    broker_connection_retry_on_startup=True,
    broker_transport_options=_redis_transport_opts,
    redis_backend_transport_options=_redis_transport_opts,
    broker_use_ssl=_ssl_options,
    redis_backend_use_ssl=_ssl_options,
)

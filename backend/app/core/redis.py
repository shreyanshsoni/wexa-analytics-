from typing import Any

import certifi
from redis.asyncio import Redis
from redis.asyncio import from_url as redis_from_url

from app.core.config import settings

_redis_client: Redis | None = None


async def get_redis() -> Redis:
    global _redis_client
    if _redis_client is None:
        kwargs: dict[str, Any] = {
            "encoding": "utf-8",
            "decode_responses": True,
        }
        if settings.REDIS_URL.startswith("rediss://"):
            kwargs["ssl_ca_certs"] = certifi.where()
        _redis_client = redis_from_url(settings.REDIS_URL, **kwargs)  # type: ignore[no-untyped-call]
    return _redis_client


async def close_redis() -> None:
    global _redis_client
    if _redis_client is not None:
        await _redis_client.aclose()
        _redis_client = None

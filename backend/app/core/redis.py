from redis.asyncio import Redis
from redis.asyncio import from_url as redis_from_url

from app.core.config import settings

_redis_client: Redis | None = None  # type: ignore[type-arg]


async def get_redis() -> Redis:  # type: ignore[type-arg]
    global _redis_client
    if _redis_client is None:
        _redis_client = redis_from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
            ssl_cert_reqs=None,  # Upstash uses self-signed cert on some envs
        )
    return _redis_client


async def close_redis() -> None:
    global _redis_client
    if _redis_client is not None:
        await _redis_client.aclose()
        _redis_client = None

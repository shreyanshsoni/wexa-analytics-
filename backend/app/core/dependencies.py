from typing import Annotated

from fastapi import Depends
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db as _get_db
from app.core.redis import get_redis as _get_redis

DbDep = Annotated[AsyncSession, Depends(_get_db)]
RedisDep = Annotated[Redis, Depends(_get_redis)]

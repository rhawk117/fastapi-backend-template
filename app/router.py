from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING
from redis.asyncio import ConnectionPool, Redis

from app.core.settings import SecretSettings

if TYPE_CHECKING:
    from asyncpg import Pool




@dataclass
class RedisConnection:
    client: Redis
    pool: ConnectionPool


def _create_redis_connection(secrets: SecretSettings) -> RedisConnection:
    pool = ConnectionPool(
        
    )
    client = Redis(connection_pool=pool)
    return RedisConnection(client=client, pool=pool)


@dataclass
class LifespanState:
    pg_pool: Pool
    redis_connection: RedisConnection

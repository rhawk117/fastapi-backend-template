import dataclasses as dc
import logging

from redis.asyncio import Redis
from redis.asyncio import from_url as redis_from_url

from backend.config import get_app_config
from backend.settings.configs import RedisConfig

logger = logging.getLogger(__name__)


@dc.dataclass(kw_only=True, slots=True)
class RedisDatabase:
    url: str
    client: Redis

    async def ping(self) -> bool:
        try:
            pong = await self.client.ping()  # type: ignore
        except Exception as e:
            logger.error(f'Redis ping failed: {e}')
            return False

        return pong

    async def aclose(self) -> None:
        logger.info('Disposing Redis client...')
        await self.client.aclose()

def create_redis_database(
    *,
    redis_config: RedisConfig | None = None
) -> RedisDatabase:

    redis_config = redis_config or get_app_config().redis

    redis_url = redis_config.get_url()

    redis_client = redis_from_url(
        redis_url,
        **redis_config.client_kwargs()
    )
    return RedisDatabase(
        url=redis_url,
        client=redis_client
    )

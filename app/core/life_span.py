from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

from app.core.databases import PostgresDatabase, RedisDatabase

if TYPE_CHECKING:
    from app.core.settings import AppSettings
    from app.router import SecretSettings


logger = logging.getLogger(__name__)


@dataclass(slots=True)
class LifespanState:
    """
    Holds the state for the application lifespan, including database
    connections and settings.
    """
    redis_db: RedisDatabase
    postgres_db: PostgresDatabase
    settings: AppSettings
    secrets: SecretSettings

    async def initialize(self) -> None:
        logger.info('Testing if redis is reachable...')
        await self.redis_db.test_connection()
        logger.info('Testing if Postgres is reachable...')
        # await self.postgres_db.test_connection()
        logger.info('All databases are reachable.')

    async def dispose(self) -> None:
        logger.info('Disposing database connections...')
        await self.redis_db.aclose()
        await self.postgres_db.aclose()
        logger.info('All database connections disposed.')


def create_lifespan_state(
    settings: AppSettings,
    secrets: SecretSettings,
) -> LifespanState:

    postgres_db = PostgresDatabase.create(secrets=secrets)
    redis_db = RedisDatabase.create(
        connection_config=settings.redis,
        url=secrets.REDIS_URL
    )

    return LifespanState(
        redis_db=redis_db,
        postgres_db=postgres_db,
        settings=settings,
        secrets=secrets,
    )

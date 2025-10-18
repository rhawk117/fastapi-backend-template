from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Self

from app.databases import PostgresDatabase, RedisDatabase

if TYPE_CHECKING:
    from app.core.configs import AppSettings
    from app.core.secrets import JWKSecrets, SecretTomlSettings

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class LifespanState:
    '''
    Holds the state for the application lifespan, including database
    connections and settings.
    '''
    redis_db: RedisDatabase
    postgres_db: PostgresDatabase
    settings: AppSettings
    secrets: SecretTomlSettings
    jwks: JWKSecrets

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

    @classmethod
    def create(
        cls,
        secrets: SecretTomlSettings,
        settings: AppSettings,
        jwks: JWKSecrets,
    ) -> Self:

        postgres_db = PostgresDatabase.create(pg_secrets=secrets.postgres)
        redis_db = RedisDatabase.create(
            connection_config=settings.redis_connection,
            url=secrets.redis.get_url(),
        )
        return cls(
            redis_db=redis_db,
            postgres_db=postgres_db,
            settings=settings,
            secrets=secrets,
            jwks=jwks,
        )


async def get_lifespan_state() -> LifespanState:
    from app.settings import get_app_settings, get_secret_jwks, get_secret_settings

    secrets = get_secret_settings()
    settings = get_app_settings()
    jwks = get_secret_jwks()
    try:
        state = LifespanState.create(
            secrets,
            settings,
            jwks,
        )
        await state.initialize()
    except Exception as e:
        logger.critical(
            f"{type(e).__name__}: Failed to initialize lifespan state",
            exc_info=e
        )
        raise

    return state

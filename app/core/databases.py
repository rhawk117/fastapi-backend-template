from __future__ import annotations

from typing import TYPE_CHECKING, Self

if TYPE_CHECKING:

    from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

    from app.core.settings import RedisConfig
    from app.router import SecretSettings

import contextlib
import logging
from dataclasses import dataclass

from redis.asyncio import ConnectionPool, Redis
from sqlalchemy import URL
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.settings import get_app_settings, get_secret_settings

logger = logging.getLogger(__name__)


@contextlib.asynccontextmanager
async def _log_connection_failure(db_name: str):  # noqa: ANN202, RUF029
    logger.info(f"Connecting to {db_name}...")
    try:
        yield
    except Exception as e:
        exc_name = type(e).__name__
        logger.error(f"{exc_name} Failed to connect to {db_name}: {e}", exc_info=True)
        raise
    else:
        logger.info(f"Successfully connected to {db_name}.")


@dataclass(slots=True)
class RedisDatabase:
    pool: ConnectionPool
    client: Redis
    url: str

    async def test_connection(self) -> None:
        async with _log_connection_failure('Redis'):
            await self.client.ping()

    async def aclose(self) -> None:
        logger.info("Closing Redis connection...")
        await self.client.aclose()
        await self.pool.disconnect()

    @classmethod
    def create(cls, connection_config: RedisConfig, url: str | None = None) -> Self:
        """
        Create a new RedisDatabase instance

        Parameters
        ----------
        connection_config : RedisConfig
            The Redis connection configuration, by default None / app settings
        url : str | None, optional
            The Redis connection URL. If None, the URL will be constructed
            from the secret settings, by default None

        Returns
        -------
        Self
        """
        if url is None:
            secrets = get_secret_settings()
            url = secrets.REDIS_URL
        pool = ConnectionPool.from_url(url, **connection_config.model_dump())
        client = Redis(connection_pool=pool)
        return cls(pool=pool, client=client, url=url)


# @dataclass(slots=True)
# class PostgresDatabase:
#     url: str
#     async_engine: AsyncEngine
#     sessionlocal: async_sessionmaker[AsyncSession]

def create_postgres_url(
    drivername: str,
    *,
    secrets: SecretSettings | None = None,
) -> URL:
    if secrets is None:
        secrets = get_secret_settings()

    return URL.create(
        drivername=drivername,
        username=secrets.PG_USER,
        host=secrets.PG_HOSTNAME,
        port=secrets.PG_PORT,
        database=secrets.PG_DATABASE_NAME,
    )


@dataclass(slots=True)
class PostgresDatabase:
    async_engine: AsyncEngine
    sessionmaker: async_sessionmaker[AsyncSession]
    url: str

    @classmethod
    def create(cls, *, secrets: SecretSettings | None = None) -> Self:
        """
        Create a new PostgresDatabase instance

        Parameters
        ----------
        secrets : SecretSettings | None, optional
            The secret settings to use for the database connection.
            If None, the default secret settings will be used.
            by default None

        Returns
        -------
        Self
            The created PostgresDatabase instance
        """
        secrets = secrets or get_secret_settings()
        sa_config = get_app_settings().sql_alchemy

        url = create_postgres_url(
            'postgresql+asyncpg',
            secrets=secrets
        )

        engine = create_async_engine(
            url,
            echo=sa_config.echo,
            pool_size=sa_config.pool_size,
            max_overflow=sa_config.max_overflow,
            pool_timeout=sa_config.pool_timeout,
            pool_recycle=sa_config.pool_recycle,
            future=True,
            pool_pre_ping=True,
        )

        sessionlocal = async_sessionmaker(
            bind=engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
            autocommit=False,
        )

        return cls(
            async_engine=engine,
            sessionmaker=sessionlocal,
            url=str(url),
        )

    @contextlib.asynccontextmanager
    async def get_session(self):  # noqa: ANN201
        """
        Context manager to get a new database session with rollbacks on
        exception

        Returns
        -------
        AsyncGenerator[AsyncSession]

        Yields
        ------
        Iterator[AsyncGenerator[AsyncSession]]
        """
        async with self.sessionmaker() as session:
            try:
                yield session
            except Exception as exc:
                exc_name = type(exc).__name__
                logger.error(
                    f"{exc_name}: Session rollback because of exception: {exc}",
                    exc_info=True
                )
                raise

    async def aclose(self) -> None:
        logger.info("Closing Postgres connection...")
        await self.async_engine.dispose()

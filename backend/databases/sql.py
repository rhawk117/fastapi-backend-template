from __future__ import annotations

import contextlib
import dataclasses as dc
import logging
from sqlite3 import OperationalError
from typing import TYPE_CHECKING

import anyio.to_thread
import sqlalchemy as sa
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from backend.config import get_app_config
from backend.exceptions.base import InfrastructureError

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from sqlalchemy.ext.asyncio import AsyncEngine

    from backend.settings.configs import DatabaseConfig


logger = logging.getLogger(__name__)


async def upgrade_alembic_head(*, sql: bool = False, timeout: int = 60) -> None:
    """Upgrades the database schema to the latest Alembic head revision.

    Raises
    ------
    TimeoutError
        If the upgrade operation exceeds the specified timeout.
    """
    from alembic import command
    from alembic.config import Config

    alembic_conf = Config('alembic.ini')
    with anyio.move_on_after(timeout) as scope:
        await anyio.to_thread.run_sync(command.upgrade, alembic_conf, 'head', sql)

    if scope.cancel_called:
        raise TimeoutError(f'alembic upgrade exceeded {timeout} seconds')



@dc.dataclass(slots=True, kw_only=True)
class SQLDatabase:
    url: sa.URL
    async_engine: AsyncEngine
    SessionLocal: async_sessionmaker[AsyncSession]

    async def aclose(self) -> None:
        logger.info('Closing SQL Database')
        await self.async_engine.dispose()

    @contextlib.asynccontextmanager
    async def session(self) -> AsyncGenerator[AsyncSession]:
        """
        Context manager for providing a database session.
        """
        async with self.SessionLocal() as session:
            try:
                yield session
            except (DBAPIError, OperationalError) as e:
                raise InfrastructureError(
                    'database',
                    meta={
                        'exception_type': type(e).__name__,
                        'exception_args': e.args,
                        'is_disconnect': getattr(e, 'is_disconnect', None),
                        'traceback': repr(e.__traceback__),
                    },
                )

    @contextlib.asynccontextmanager
    async def begin_session(self) -> AsyncGenerator[AsyncSession]:
        async with self.session() as session:
            async with session.begin():
                yield session

    async def ping(self) -> bool:
        try:
            async with self.async_engine.connect() as conn:
                await conn.execute(sa.text('SELECT 1'))
        except Exception as exc:
            logger.error(f'Database ping failed: {exc}')
            return False

        return True


def get_sql_database(
    db_config: DatabaseConfig | None = None,
    *,
    expire_on_commit: bool = False,
    autoflush: bool = True,
    autobegin: bool = True,
    autocommit: bool = False,
) -> SQLDatabase:
    """Creates a new DatabaseConnection instance.

    Parameters
    ----------
    db_config : DatabaseConfig, optional
        Defaults to the application config

    expire_on_commit : bool, optional
        Whether to expire objects on commit

    autoflush : bool, optional
        Whether to autoflush changes

    autobegin : bool, optional
        Whether to automatically begin transactions

    autocommit : bool, optional
        Whether to autocommit changes

    Returns
    -------
    DatabaseConnection
        The created DatabaseConnection instance.
    """

    db_config = db_config or get_app_config().database

    database_url = db_config.get_url(sync=False)
    async_engine = create_async_engine(
        database_url,
        **db_config.engine_kwargs()
    )
    sessionmaker = async_sessionmaker(
        bind=async_engine,
        expire_on_commit=expire_on_commit,
        autoflush=autoflush,
        autobegin=autobegin,
        autocommit=autocommit,
        class_=AsyncSession,
    )

    return SQLDatabase(
        url=database_url,
        async_engine=async_engine,
        SessionLocal=sessionmaker,
    )

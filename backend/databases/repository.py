from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

import sqlalchemy as sa

from backend.schemas.paginate import (
    APICollection,
    PaginateParams,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

    from sqlalchemy.ext.asyncio import AsyncSession
    from sqlalchemy.orm.interfaces import ORMOption


logger = logging.getLogger(__name__)


async def count_query_total(
    session: AsyncSession,
    query: sa.Select[Any],
) -> int:
    """Count total rows for a query, ignoring limit/offset."""
    count_query = sa.select(sa.func.count()).select_from(
        query.order_by(None).limit(None).offset(None).subquery()
    )
    result = await session.scalar(count_query)
    return result or 0


def _row_asdict(row: sa.Row) -> dict[str, Any]:
    return dict(row._mapping)


class SQLRepositoryMixin:
    """Repository Mixin class for common database operations using SQLAlchemy
    reccomended to use in repository subclasses
    """

    def __init__(self, database: AsyncSession) -> None:
        self.database = database

    async def insert[T: Any](self, target: type[T], values: dict[str, Any]) -> T:
        stmt = sa.insert(target).values(**values).returning(target)
        result = await self.database.execute(stmt)
        await self.database.flush()
        return result.scalar_one()

    async def add_orm(self, instance: Any) -> None:
        logger.debug('Adding %r', instance)
        self.database.add(instance)
        await self.database.flush()

    async def patch_orm(self, model: Any, values: dict[str, Any]) -> None:
        logger.debug('Patching %r with %r', model, values)
        for key, value in values.items():
            setattr(model, key, value)

        await self.add_orm(model)

    async def get_orm[M: Any](
        self,
        model: type[M],
        pk: Any,
        *,
        with_for_update: bool = False,
        options: Sequence[ORMOption] | None = None,
    ) -> M | None:
        return await self.database.get(
            model,
            pk,
            with_for_update=with_for_update,
            options=options,
        )

    async def first_orm[M: Any](self, query: sa.Select[tuple[M]]) -> M | None:
        result = await self.database.execute(query)
        return result.scalars().first()

    async def list_orms[M: Any](self, query: sa.Select[tuple[M]]) -> list[M]:
        result = await self.database.execute(query)
        return list(result.unique().scalars().all())

    async def first_columns(self, query: sa.Select[Any]) -> dict[str, Any] | None:
        result = await self.database.execute(query)
        if row := result.first():
            return dict(row._mapping)
        return None

    async def list_columns(self, query: sa.Select[Any]) -> list[dict[str, Any]]:
        result = await self.database.execute(query)
        return list(map(_row_asdict, result.all()))

    async def paginate_orms[T: Any](
        self,
        query: sa.Select[tuple[T]],
        page_params: PaginateParams,
    ) -> APICollection[T]:
        total = await count_query_total(self.database, query)
        if total == 0:
            return APICollection()

        query = page_params.apply(query)
        result = await self.database.execute(query)
        items = list(result.unique().scalars().all())
        return APICollection(items)

    async def paginate_columns(
        self,
        query: sa.Select,
        page_params: PaginateParams,
    ) -> APICollection[dict[str, Any]]:
        total = await count_query_total(self.database, query)
        if total == 0:
            return APICollection()

        query = page_params.apply(query)
        result = await self.database.execute(query)
        return APICollection(list(map(_row_asdict, result.all())))

    async def delete_by(
        self,
        model: type[Any],
        *where: sa.ColumnExpressionArgument[Any],
    ) -> int:
        stmt = sa.delete(model).where(*where)
        result = await self.database.execute(stmt)
        await self.database.flush()
        return getattr(result, 'rowcount', 0)

    async def delete_orm(self, instance: Any) -> None:
        logger.debug('Deleting %r', instance)
        await self.database.delete(instance)
        await self.database.flush()

    async def exists(
        self,
        model: type[Any],
        *where: sa.ColumnExpressionArgument[Any],
    ) -> bool:
        stmt = sa.select(sa.exists().where(*where).select_from(model))
        result = await self.database.execute(stmt)
        return bool(result.scalar())

    async def update_by(
        self,
        *where: sa.ColumnExpressionArgument[Any],
        model: type[Any],
        values: dict[str, Any],
    ) -> int:
        stmt = sa.update(model).where(*where).values(**values)
        result = await self.database.execute(stmt)
        await self.database.flush()
        return getattr(result, 'rowcount', 0)

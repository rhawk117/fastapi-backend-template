from __future__ import annotations

import dataclasses as dc
from typing import TYPE_CHECKING, Annotated, Any, Self
from urllib.parse import urlencode

from annotated_types import Ge, Le
from fastapi import Query, Request
from pydantic import Field, HttpUrl, NonNegativeInt, computed_field

from backend.schemas.base import RequestSchema, ResponseSchema

if TYPE_CHECKING:
    from collections.abc import Callable

    from sqlalchemy import Select


PageParam = Annotated[int, Ge(0), Le(1000)]

PageSize = Annotated[
    PageParam,
    Query(title='Page Size', description='Number of items per page.'),
]
PageNumber = Annotated[
    PageParam,
    Query(title='Page Number', description='Current page number.'),
]
NextUrl = Annotated[HttpUrl, Field(description='URL for the next page.')]
PreviousUrl = Annotated[HttpUrl, Field(description='URL for the previous page.')]
FirstUrl = Annotated[HttpUrl, Field(description='URL for the first page.')]
LastUrl = Annotated[HttpUrl, Field(description='URL for the last page.')]


class PaginateParams(RequestSchema):
    page: PageParam
    size: PageParam

    @property
    def offset(self) -> int:
        return max(self.page - 1, 0) * self.size

    @property
    def limit(self) -> int:
        return max(self.size, 0)

    def apply[T: Any](self, query: Select[tuple[T]]) -> Select[tuple[T]]:
        return query.offset(self.offset).limit(self.limit)

    @classmethod
    async def depends(cls, page: PageNumber = 1, size: PageSize = 1) -> Self:
        return cls(page=page, size=size)


class PageInfo(ResponseSchema):
    page_number: NonNegativeInt
    page_size: NonNegativeInt
    total_items: NonNegativeInt

    @computed_field
    @property
    def total_pages(self) -> NonNegativeInt:
        if self.total_items == 0:
            return 0
        return (self.total_items + self.page_size - 1) // self.page_size

    @computed_field
    @property
    def has_next(self) -> bool:
        return self.page_number < self.total_pages

    @computed_field
    @property
    def has_previous(self) -> bool:
        return self.page_number > 1

    @classmethod
    def create(cls, total: int, page_options: PaginateParams) -> Self:
        return cls(
            page_number=page_options.page,
            page_size=page_options.size,
            total_items=total,
        )


class PageLinks(ResponseSchema):
    next_url: NextUrl | None = None
    previous_url: PreviousUrl | None = None
    first_url: FirstUrl | None = None
    last_url: LastUrl | None = None

    @classmethod
    def from_request(cls, request: Request, total_pages: int) -> Self:
        base_url = str(request.url.replace(query=None))
        query_params = dict(request.query_params)

        def build_url(page_num: int) -> str:
            params = {**query_params, 'page': page_num}
            return f'{base_url}?{urlencode(params)}'

        page: str | int = query_params.get('page', 1)
        try:
            page = int(page)
        except (TypeError, ValueError):
            page = 1

        return cls.model_validate({
            'next': build_url(page + 1) if page < total_pages else None,
            'previous': build_url(page - 1) if page > 1 else None,
            'first': build_url(1) if total_pages > 0 else None,
            'last': build_url(total_pages) if total_pages > 0 else None,
        })


class PaginatedSchema[T: Any](ResponseSchema):
    data: list[T]
    page: PageInfo
    links: PageLinks


@dc.dataclass(slots=True)
class APICollection[T: Any]:
    data: list[T] = dc.field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.data)

    def map_with[M: Any](self, func: Callable[[T], M]) -> APICollection[M]:
        mapped_data = list(map(func, self.data))
        return APICollection[M](data=mapped_data)

    def filter_with(self, func: Callable[[T], bool]) -> list[T]:
        return list(filter(func, self.data))

    def to_response_schema(
        self,
        request: Request,
        page_options: PaginateParams,
    ) -> PaginatedSchema[T]:
        page_info = PageInfo.create(total=self.total, page_options=page_options)
        page_links = PageLinks.from_request(request, total_pages=page_info.total_pages)
        return PaginatedSchema(data=self.data, page=page_info, links=page_links)

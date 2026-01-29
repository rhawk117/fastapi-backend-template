from datetime import UTC, date, datetime
from enum import StrEnum
from typing import Any

import sqlalchemy as sa


def _escape_like(value: str, *, escape_char: str | None = None) -> tuple[str, str]:
    esc = escape_char or '\\'
    return (
        value.replace(esc, esc + esc).replace('%', esc + '%').replace('_', esc + '_'),
        esc,
    )


class LikeExpression(StrEnum):
    STARTS_WITH = '{value}%'
    ENDS_WITH = '%{value}'
    CONTAINS = '%{value}%'

    def __call__(
        self,
        column: sa.ColumnElement[str] | Any,
        value: str,
        *,
        case_sensitive: bool = True,
        escape_char: str | None = None,
    ) -> sa.ColumnElement[bool]:
        escaped_value, esc = _escape_like(value, escape_char=escape_char)
        pattern = self.value.format(value=escaped_value)

        if case_sensitive:
            return column.like(pattern, escape=esc)

        return column.ilike(pattern, escape=esc)


def on_date_expression(
    column: sa.ColumnElement[sa.DateTime] | Any, date: date
) -> sa.ColumnElement[bool]:
    start = datetime(date.year, date.month, date.day, tzinfo=UTC)
    end = datetime(date.year, date.month, date.day, 23, 59, 59, 999999, tzinfo=UTC)
    return sa.and_(column >= start, column <= end)

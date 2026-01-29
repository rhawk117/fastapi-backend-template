from __future__ import annotations

import dataclasses as dc
from typing import TYPE_CHECKING, Any, Self

from pydantic import ConfigDict, ValidationError

from backend.utils.correlation import get_correlation_id
from backend.schemas.base import PydanticSchema, camel_case_alias_generator

if TYPE_CHECKING:
    from fastapi.exceptions import RequestValidationError
    from pydantic_core import ErrorDetails

    from backend.exceptions import ServerError


@dc.dataclass(slots=True)
class PydanticError:
    """
    Normalized standard format for Pydantic validation errors
    """
    field: str
    detail: str
    type: str

    @classmethod
    def create(cls, details: ErrorDetails | Any) -> Self:
        loc = details.get('loc', ())
        field = '' if not loc else '.'.join(str(x) for x in loc)

        return cls(
            field=field,
            detail=details.get('msg', 'Unknown error'),
            type=details.get('type', 'unknown_error'),
        )

    def to_message(self) -> str:
        return (
            f'Validation Error on Field({self.field}, type=`{self.type}`):'
            f'\nDetail: {self.detail} '
        )

    @classmethod
    def from_exception(
        cls,
        error: ValidationError | RequestValidationError,
    ) -> dict[str, Self]:
        errors = {}
        for details in error.errors():
            error_spec = PydanticError.create(details)
            errors[error_spec.field] = error_spec

        return errors


class ErrorContent(PydanticSchema):
    model_config = ConfigDict(
        alias_generator=camel_case_alias_generator,
        extra='forbid',
    )

    error_type: str
    status: int
    code: str
    message: str
    correlation_id: str
    context: dict[str, Any] | None = None

    @classmethod
    def from_domain_error(cls, error: ServerError) -> Self:
        return cls(
            error_type=error.__class__.__name__,
            status=error.status_code,
            code=error.code,
            message=error.public,
            correlation_id=get_correlation_id(default='N/A'),
        )



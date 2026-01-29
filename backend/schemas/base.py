import dataclasses as dc
from typing import Any, Self

from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, ConfigDict, ValidationError
from pydantic_core import ErrorDetails


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


def camel_case_alias_generator(string: str) -> str:
    """
    Pydantic alias generator to convert snake_case to camelCase
    when `model_dump()` is called which automatically makes snake
    case to camel case conversions for keys in dicts.
    """
    words = string.split('_')
    new_name = []
    for i, word in enumerate(words):
        if i:
            new_name.append(word.capitalize())
        else:
            new_name.append(word.lower())

    return ''.join(new_name)


class PydanticSchema(BaseModel):
    """
    Base class for schemas that you don't want expose
    directly as request/response schemas.
    """
    model_config = ConfigDict(
        use_enum_values=True,
        populate_by_name=True,
        validate_assignment=True,
        validate_default=True,
        from_attributes=True,
        str_strip_whitespace=True,
        ser_json_timedelta='iso8601',
    )


class RequestSchema(PydanticSchema):
    """
    Base class for all request/response schemas exposed
    via the API.
    """

    model_config = ConfigDict(
        alias_generator=camel_case_alias_generator,
        str_max_length=2048,
        extra='forbid',
    )


class ResponseSchema(PydanticSchema):
    """
    Base class for all response schemas exposed
    via the API.
    """

    model_config = ConfigDict(
        alias_generator=camel_case_alias_generator,
        extra='ignore',
    )

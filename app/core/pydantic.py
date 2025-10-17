"""
range_monitor.core.schema

Common pydantic models and utilities for use throughout the application
so that common behaviors such as serialization, validation,
and methods are standardized from a centralized base class for easy
propagation of changes.
"""

import dataclasses as dc
import hashlib
from typing import Any, Literal, Self

import msgspec
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, ConfigDict, ValidationError
from pydantic_core import ErrorDetails


class AliasGenerator:
    @staticmethod
    def to_camel_case(string: str) -> str:
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

    @staticmethod
    def kebab_case(string: str) -> str:
        return string.replace('_', '-').lower()


def parse_pydantic_error(details: ErrorDetails | Any) -> 'PydanticError':
    """
    Parses a single `ErrorDetails` from a validation error PydanticError
    into a human readable format
    Parameters
    ----------
    details : ErrorDetails | Any
        The error details to parse

    Returns
    -------
    PydanticError
    """
    loc = details.get('loc', ())
    field = '' if not loc else '.'.join(str(x) for x in loc)

    return PydanticError(
        field=field,
        detail=details.get('msg', 'Unknown error'),
        type=details.get('type', 'unknown_error'),
    )


@dc.dataclass(slots=True)
class PydanticError(BaseModel):
    """
    Normalized standard format for Pydantic validation errors
    """

    field: str
    detail: str
    type: str

    def message(self) -> str:
        return f'Error on field "{self.field}": {self.detail} (type={self.type})'


def normalize_validation_error(
    err: ValidationError | RequestValidationError
) -> list[PydanticError]:

    errors = []
    for details in err.errors():
        loc = details.get('loc', ())
        field = '' if not loc else '.'.join(str(x) for x in loc)

        errors.append(PydanticError(
            field=field,
            detail=details.get('msg', 'Unknown error'),
            type=details.get('type', 'unknown_error'),
        ))

    return errors


class PydanticModel(BaseModel):
    """
    The base pydantic schema for use in all pydantic models
    with common utility methods to standardize behavior.
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

    @classmethod
    def convert(cls, obj_in: Any) -> Self:
        return cls.model_validate(obj=obj_in, from_attributes=True)

    def dump(
        self,
        *,
        exclude_none: bool = True,
        exclude_unset: bool = False,
        mode: Literal['json', 'python'] = 'python',
        by_alias: bool = False,
    ) -> dict:
        """
        utility `.model_dump()` method to generalize behaviors across
        all models.
        Sets `exclude_unset=True` and `exclude_none=True`

        Returns
        -------
        dict
        """
        return self.model_dump(
            exclude_none=exclude_none,
            exclude_unset=exclude_unset,
            mode=mode,
            by_alias=by_alias,
        )

    def jsonify(
        self,
        *,
        by_alias: bool = True,
        exclude_none: bool = True,
        order: Literal['deterministic', 'sorted'] | None = None,
    ) -> str:
        """
        utility `.model_dump_json()` method to generalize behaviors across
        all models.
        Sets `exclude_none=True` and `by_alias=True` by default.

        Returns
        -------
        str
        """
        schema = self.dump(
            by_alias=by_alias,
            exclude_none=exclude_none,
        )
        return msgspec.json.encode(schema, order=order).decode('utf-8')

    def to_hash(self) -> str:
        """
        Stable schema hash (good for cache keys / idempotency keys)
        using sha256 over the jsonable dict representation. The keys
        are sorted to ensure stability.
        """
        json_str = msgspec.json.encode(
            self.dump(exclude_none=True, by_alias=True),
            order='sorted'
        )
        return hashlib.sha256(json_str).hexdigest()

    def equals(self, other: 'PydanticModel') -> bool:
        """
        Compares two pydantic schemas for equality by comparing their
        hash values from `to_hash()`.

        Parameters
        ----------
        other : 'PydanticSchema'
            The other PydanticSchema instance to compare against.

        Returns
        -------
        bool
        """
        return self.to_hash() == other.to_hash()

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}<{self.jsonify()}>'

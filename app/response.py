from typing import Annotated, Any

import msgspec
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from pydantic_settings import SettingsConfigDict

from app.core.pydantic import PydanticModel, to_camel_case

ErrorType = Annotated[
    str,
    Field(description='A string representing the type of error that occurred'),
]


class ErrorResponseModel(PydanticModel):
    error_type: ErrorType = 'about:blank'
    detail: str = Field(
        ...,
        description='A human-readable explanation specific to this occurrence of the problem.',
    )
    correlation_id: str | None = None
    error_code: str | None = Field(
        None,
        description='short code representing the error (if applicable)',
    )
    status_code: int
    extras: dict[str, Any] | None = None

    model_config = SettingsConfigDict(
        alias_generator=to_camel_case
    )


class ApiJsonResponse(JSONResponse):
    """
    A faster JSON response class using msgspec for serialization
    msgspec is up to 3-10x faster than the standard json library
    which is used by FastAPI's default JSONResponse class and
    makes a significant difference for large payloads.
    """
    media_type = 'application/json'

    def render(self, content: Any) -> bytes:
        if isinstance(content, bytes):
            return content

        if isinstance(content, BaseModel):
            content = content.model_dump()

        return msgspec.json.encode(content)


class ApiRequestModel(PydanticModel):
    model_config = SettingsConfigDict(
        alias_generator=to_camel_case,
        extra='forbid',
        str_strip_whitespace=True,
    )


class ApiResponseModel(PydanticModel):
    model_config = SettingsConfigDict(
        alias_generator=to_camel_case,
        extra='ignore',
    )

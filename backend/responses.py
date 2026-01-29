from __future__ import annotations

from typing import TYPE_CHECKING, Any, Self

from fastapi.responses import JSONResponse
from pydantic import ConfigDict

from backend.utils.correlation import get_correlation_id
from backend.utils.encoders import EncodableResponses, JSONEncoder
from backend.schemas.base import PydanticSchema, camel_case_alias_generator

if TYPE_CHECKING:
    from fastapi import BackgroundTasks

    from backend.exceptions import DomainError, ServerError


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


class APIResponse(JSONResponse):
    """Specialized JSONResponse using Msgspec for encoding
    for better performance.
    """

    media_type = 'application/json'

    def render(self, content: Any) -> bytes:
        return JSONEncoder.encode(content)

    @classmethod
    def success(
        cls,
        body: EncodableResponses,
        *,
        status: int = 200,
        headers: dict[str, str] | None = None,
        bg_tasks: BackgroundTasks | None = None,
    ) -> Self:
        return cls(
            content=body,
            status_code=status,
            headers=headers,
            background=bg_tasks,
        )

    @classmethod
    def created(
        cls,
        body: EncodableResponses,
        location: str,
        headers: dict[str, str] | None = None,
        tasks: BackgroundTasks | None = None,
    ) -> Self:
        headers = headers or {}
        headers.update({'Location': location})
        return cls(content=body, status_code=201, headers=headers, background=tasks)

    @classmethod
    def problem(
        cls,
        error_type: str,
        *,
        detail: str | None = None,
        status: int = 400,
        code: str | None = None,
        headers: dict[str, str] | None = None,
        context: dict[str, Any] | None = None,
    ) -> Self:
        if not detail:
            detail = 'An error occurred processing your request.'

        code = code or 'about:blank'
        response_content = ErrorContent(
            error_type=error_type,
            status=status,
            code=code,
            message=detail,
            correlation_id=get_correlation_id(default='N/A'),
            context=context,
        )

        return cls(
            content=response_content,
            status_code=status,
            headers=headers,
        )

    @classmethod
    def domain_problem(
        cls,
        domain_error: DomainError,
        *,
        headers: dict[str, str] | None = None,
    ) -> Self:
        return cls(
            content=ErrorContent.from_domain_error(domain_error),
            status_code=domain_error.status_code,
            headers=headers,
        )

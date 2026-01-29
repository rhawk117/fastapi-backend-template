"""
Implementation of exception handlers for the API, ensures all exceptions
are handled, logged and returned in to the client in a consistent manner.
"""
import logging

from fastapi import Request, status
from fastapi.exceptions import RequestValidationError

from backend.exceptions.base import ServerError
from backend.responses import APIResponse
from backend.schemas.errors import PydanticError

# NOTE: Do NOT return metadata of an exception a client, its for logging only

logger = logging.getLogger(__name__)


def get_status_severity(status_code: int) -> int:
    if 500 <= status_code <= 599:
        return logging.ERROR

    return logging.WARNING


def log_http_error_message(
    request: Request,
    status_code: int,
    exception: Exception,
    metadata: dict | None = None,
) -> None:
    message = (
        f'HTTP error occurred during request {request.method}->{request.url} '
        f'with status code {status_code} of type {exception.__class__.__name__} '
        f'with the following details: {exception}'
    )
    severity = get_status_severity(status_code)
    metadata = metadata or {}
    logger.log(
        severity,
        message,
        exc_info=exception,
        extra={
            'error_cls': exception.__class__.__name__,
            'status_code': status_code,
            'request_method': request.method,
            'request_url': str(request.url),
            **metadata,
        },
    )


async def handle_server_error(request: Request, exception: ServerError) -> APIResponse:
    log_http_error_message(
        request=request,
        status_code=exception.status_code,
        exception=exception,
        metadata=exception.meta,
    )

    return APIResponse.from_exception(
        domain_error=exception,
        headers=dict(exception.headers or {}),
    )


async def handle_validation_error(
    request: Request,
    exception: RequestValidationError,
) -> APIResponse:
    log_http_error_message(
        request=request,
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        exception=exception,
    )

    parsed_errors = PydanticError.from_exception(exception)
    return APIResponse.problem(
        error_type='RequestValidationError',
        detail='One or more validation errors occurred',
        status=status.HTTP_422_UNPROCESSABLE_CONTENT,
        context=parsed_errors,
    )


async def handle_generic_exception(
    request: Request, exception: Exception
) -> APIResponse:
    log_http_error_message(
        request=request,
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        exception=exception,
    )
    return APIResponse.problem(
        error_type='InternalServerError',
        detail='Oops, something went wrong on our end please try again later.',
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )



registered_exception_handlers = {
    ServerError: handle_server_error,
    RequestValidationError: handle_validation_error,
    Exception: handle_generic_exception,
}

__all__ = ('registered_exception_handlers',)

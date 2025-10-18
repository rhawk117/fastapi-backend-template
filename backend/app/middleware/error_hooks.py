from typing import cast

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarleteHTTPException
from starlette.requests import Request

from app.core.pydantic import normalize_validation_error
from app.exceptions import HTTPError
from app.middleware.exc_hook_abc import APIErrorHandler, ErrorHook
from app.response import ErrorResponseModel


def register_error_hook(hook_cls: type[ErrorHook], app: FastAPI) -> None:
    '''
    Add an error hook to the FastAPI application

    Parameters
    ----------
    hook_cls : type[ErrorHook]
        The error hook class to add
    app : FastAPI
        The FastAPI application instance
    '''
    hook = hook_cls()
    app.add_exception_handler(hook.handles, handler=APIErrorHandler(hook))


class HTTPErrorHandler(ErrorHook[HTTPError]):
    handles = HTTPError

    async def get_logger_details(
        self,
        request: Request,
        exception: HTTPError
    ) -> tuple[str, dict]:
        message = (
            f'[{exception.status_code}, {exception.code}] An HTTP Error failed during a '
            f'{request.method} request to {request.url} from client {request.client} '
            f'detail: {exception.detail}'
        )
        details = {
            'status_code': exception.status_code,
            'error_code': exception.code,
            'headers': exception.headers,
            'correlation_id': request.headers.get('X-Request-ID', 'N/A'),
            'method': request.method,
            'detail': exception.detail,
            'url': str(request.url),
            'service_name': getattr(exception, 'service_name', 'N/A'),
            'reason': getattr(exception, 'reason', 'N/A'),
        }
        return message, details

    def get_response_model(self, exception: HTTPError) -> ErrorResponseModel:
        return ErrorResponseModel(
            status_code=exception.status_code,
            error_code=exception.code,
            detail=exception.detail,
        )


class ValidationErrorHandler(ErrorHook[RequestValidationError]):
    handles = RequestValidationError

    async def get_logger_details(
        self,
        request: Request,
        exception: RequestValidationError,
    ) -> tuple[str, dict]:
        message = (
            f'A Pydantic Validation Error of type {type(exception)} occurred during a '
            f'{request.method} request to {request.url} from client {request.client}.'
        )
        details = {
            'correlation_id': request.headers.get('X-Request-ID', 'N/A'),
            'method': request.method,
            'url': str(request.url),
            'errors': exception.errors(),
        }
        return message, details

    def get_response_model(
        self,
        exception: RequestValidationError,
    ) -> ErrorResponseModel:
        norm_errors = normalize_validation_error(exception)

        return ErrorResponseModel(
            status_code=400,
            error_code='validation_error',
            detail='There was an error validating the request data.',
            extras=cast('dict', norm_errors)
        )


class StarletteErrorHandler(ErrorHook[StarleteHTTPException]):
    '''
    catches both lower level starlette HTTP exceptions
    and fastapi HTTP exceptions as they both inherit from `StarletteHTTPException`
    '''
    handles = StarleteHTTPException

    async def get_logger_details(
        self,
        request: Request,
        exception: StarleteHTTPException
    ) -> tuple[str, dict]:
        message = (
            f'[{exception.status_code}] A Starlette HTTP Exception of type '
            f'{type(exception)} {request.method} request to {request.url} from client '
            f'{request.client} detail: {exception.detail}'
        )
        details = {
            'status_code': exception.status_code,
            'correlation_id': request.headers.get('X-Request-ID', 'N/A'),
            'method': request.method,
            'detail': exception.detail,
            'url': str(request.url),
        }
        return message, details

    def get_response_model(self, exception: StarleteHTTPException) -> ErrorResponseModel:
        return ErrorResponseModel(
            status_code=exception.status_code,
            error_code='starlette_http_exception',
            detail=exception.detail,
        )


class GenericExceptionHandler(ErrorHook[Exception]):
    handles = Exception

    async def get_logger_details(
        self,
        request: Request,
        exception: Exception
    ) -> tuple[str, dict]:
        message = (
            f'An unhandled exception of type {type(exception)} occurred during a '
            f'{request.method} request to {request.url} from client {request.client}. '
            f'Exception message: {exception!s}'
        )
        details = {
            'correlation_id': request.headers.get('X-Request-ID', 'N/A'),
            'method': request.method,
            'url': str(request.url),
            'exception_type': str(type(exception)),
            'exception_message': str(exception),
            'traceback': repr(exception.__traceback__),
        }
        return message, details

    def get_response_model(self, exception: Exception) -> ErrorResponseModel:
        return ErrorResponseModel(
            status_code=500,
            error_code=type(exception).__name__,
            detail='Oops, something messed on our end. Please try again later.',
        )

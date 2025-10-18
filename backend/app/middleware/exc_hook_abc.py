import abc
from typing import TypeVar, cast

from fastapi import BackgroundTasks
from starlette.requests import Request
from starlette.responses import Response

from app import log
from app.exceptions import get_logger_severity
from app.response import ApiJsonResponse, ErrorResponseModel

E = TypeVar('E', bound=Exception)


async def log_http_exception(  # noqa: RUF029
    message: str,
    error_info: dict,
    status_code: int,
) -> None:
    log_severity = get_logger_severity(status_code)
    logger = log.get_logger()
    logger.log(
        log_severity,
        message,
        **error_info,
    )


class ErrorHook[E: Exception](abc.ABC):
    handles: type[E] | int

    @abc.abstractmethod
    def get_logger_details(self, request: Request, exception: E) -> tuple[str, dict]: ...

    @abc.abstractmethod
    def get_response_model(self, exception: E) -> ErrorResponseModel: ...


class APIErrorHandler[E: Exception]:
    def __init__(self, hook: ErrorHook[E]) -> None:
        self.hook = hook

    async def __call__(self, request: Request, exc: Exception) -> Response:
        exception = cast('E', exc)
        message, error_info = self.hook.get_logger_details(request, exception)
        response = self.hook.get_response_model(exception)
        bg_tasks = BackgroundTasks()
        bg_tasks.add_task(
            log_http_exception,
            message,
            error_info,
            response.status_code,
        )

        return ApiJsonResponse(
            status_code=response.status_code,
            content=response.dump(),
            headers=getattr(exc, 'headers', None),
            background=bg_tasks,
        )

import logging

from fastapi import status


def get_logger_severity(status_code: int) -> int:
    if status_code >= 500:
        return logging.ERROR

    if status_code == 401 or status_code == 403:
        return logging.INFO + 5  # NOTICE level

    return logging.WARNING


class HTTPError(Exception):
    status_code: int = status.HTTP_400_BAD_REQUEST
    code: str = 'bad_request_content'

    def __init__(
        self,
        error_code: str | None = None,
        *,
        detail: str,
        headers: dict[str, str] | None = None,
    ) -> None:
        self.detail = detail
        self.code = error_code or self.code
        self.headers = headers


class ServiceUnavailableError(HTTPError):
    status_code: int = status.HTTP_503_SERVICE_UNAVAILABLE
    code: str = 'service_unavailable'

    def __init__(
        self,
        service_name: str,
        *,
        reason: str | None = None,
        error_code: str | None = None,
    ) -> None:
        self.reason = reason or 'Not provided.'
        self.service_name = service_name
        super().__init__(
            error_code,
            detail='This service is currently unavailable, try again later.',
            headers={'Retry-After': '30'},
        )


class InternalServerError(HTTPError):
    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    code: str = 'internal_server_error'

    def __init__(
        self,
        error_code: str | None = None,
        *,
        reason: str | None = None
    ) -> None:
        self.reason = reason or 'Not provided.'
        super().__init__(
            error_code,
            detail='An error occured on our end, please try again later.',
        )

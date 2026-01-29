from traceback import TracebackException

from fastapi import status


class ServerError(Exception):
    """
    Base exception for all errors that occur at runtime
    which are handled explicitly / intentionally by the server
    during a request lifecycle.
    """

    code: str = 'internal_error'
    public: str = 'Oops, something went wrong on our end. Please try again later.'
    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR

    def __init__(
        self,
        msg: str | None = None,
        *,
        meta: dict | None = None,
        headers: dict | None = None,
    ) -> None:
        self.public = msg or self.public
        self.meta = meta or {}
        self.headers = headers or {}
        super().__init__(self.public)

    @property
    def error_name(self) -> str:
        return type(self).__name__

    def as_traceback(
        self,
        *,
        capture_locals: bool = True
    ) -> TracebackException:
        return TracebackException.from_exception(
            self,
            capture_locals=capture_locals
        )

class DomainError(ServerError):
    """
    An error related to domain logic in services, such as invalid operations
    or business rule violations.
    """
    code: str = 'about:blank'


class InfrastructureError(ServerError):
    public = 'The requested service is currently unavailable. Please try again later.'
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    def __init__(
        self,
        adapter: str,
        *,
        detail: str | None = None,
        retry_after: int | None = None,
        meta: dict | None = None,
    ) -> None:
        self.detail = detail or self.public
        self.adapter = adapter
        self.retry_after = retry_after
        self.meta = meta or {}
        headers = {}
        if retry_after is not None:
            headers['Retry-After'] = str(retry_after)
        super().__init__(self.detail, meta=self.meta, headers=headers)




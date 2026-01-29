from __future__ import annotations

from typing import TYPE_CHECKING, Any

from backend.core.correlation import correlation_id, generate_id
from backend.middleware.abstract import ASGIMiddleware

if TYPE_CHECKING:
    from starlette.types import ASGIApp, Message, Receive, Scope, Send


def _get_from_headers(header_name: bytes, headers: list[tuple[Any, Any]]) -> str | None:
    existing_value = next(
        (value for name, value in headers if name.lower() == header_name.lower()),
        None,
    )
    if not existing_value:
        return None

    return existing_value.decode('ascii', 'ignore')


class CorrelationMiddleware(ASGIMiddleware):
    """
    Middleware that ensures each request has a correlation ID
    that is accessible throughout the request lifecycle.
    """

    __slot__ = ('app', '_header_name')

    def __init__(self, app: ASGIApp, header_name: bytes | None = None) -> None:
        self.app = app

        header_name = header_name or b'x-correlation-id'
        self._header_name: bytes = header_name.lower()

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """
        Attach a correlation ID to each incoming request
        and reset it after the request is complete.
        """
        if scope['type'] != 'http':
            return await self.app(scope, receive, send)

        asgi_headers = scope.get('headers', [])

        existing = _get_from_headers(self._header_name, asgi_headers)
        correlation = existing or generate_id()
        ctx_token = correlation_id.set(correlation)

        async def send_wrapper(message: Message) -> None:
            if message['type'] == 'http.response.start':
                headers = message.setdefault('headers', [])
                headers.append((self._header_name, correlation.encode('ascii')))
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            correlation_id.reset(ctx_token)

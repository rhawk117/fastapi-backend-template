from __future__ import annotations

import uuid
from contextvars import ContextVar, Token
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable

    from starlette.types import ASGIApp, Message, Receive, Scope, Send


_correlation_id: ContextVar[str] = ContextVar(
    'correlation_id', default='not-set')


def generate() -> str:
    return uuid.uuid4().hex


def set_correlation_id(val: str | None) -> Token[str]:
    cid = val or generate()
    return _correlation_id.set(cid)


def get_correlation_id() -> str:
    return _correlation_id.get()


def reset_correlation_id(token: Token[str]) -> None:
    _correlation_id.reset(token)


def _defaultfactory() -> str:
    return uuid.uuid4().hex


def _get_from_headers(header_name: bytes, headers: list[tuple[Any, Any]]) -> str | None:
    existing_value = next(
        (
            value
            for name, value in headers
            if name.lower() == header_name.lower()
        ),
        None,
    )
    if not existing_value:
        return None

    return existing_value.decode('ascii', 'ignore')


class CorrelationMiddleware:

    __slot__ = ('app', '_factory', '_header_name')

    def __init__(
        self,
        app: ASGIApp,
        id_factory: Callable[[], str] | None = None,
        header_name: bytes | None = None
    ) -> None:
        self.app = app

        header_name = header_name or b'x-correlation-id'
        self._header_name: bytes = header_name.lower()
        self._factory: Callable[[], str] = id_factory or _defaultfactory

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope['type'] != 'http':
            return await self.app(scope, receive, send)

        asgi_headers = scope.get('headers', [])

        existing = _get_from_headers(self._header_name, asgi_headers)
        correlation = existing or self._factory()
        ctx_token = set_correlation_id(correlation)

        async def send_wrapper(message: Message) -> None:
            if message['type'] == 'http.response.start':
                headers = message.setdefault('headers', [])
                headers.append((self._header_name, correlation.encode('ascii')))
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            reset_correlation_id(ctx_token)

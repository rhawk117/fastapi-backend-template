from __future__ import annotations

import time
from typing import TYPE_CHECKING

from backend.common.logging import get_loguru_logger
from backend.middleware.abstract import ASGIMiddleware

if TYPE_CHECKING:
    from starlette.types import ASGIApp, Message, Receive, Scope, Send


class LoggingMiddleware(ASGIMiddleware):
    """
    ASGI middleware for logging HTTP requests and recording telemetry data.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app
        self.logger = get_loguru_logger()

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope['type'] != 'http':
            return await self.app(scope, receive, send)

        method = scope.get('method', 'N/A')
        path = scope.get('path', 'N/A')
        status_holder = {'code': 500}
        headers = dict(scope.get('headers', []))

        user_agent = headers.get(b'user-agent', b'N/A').decode('utf-8', 'ignore')
        message = f'Incoming {method} Request to {path} from User-Agent: {user_agent}'
        self.logger.bind(path=path, method=method).info(message)
        start_time = time.perf_counter()

        async def send_wrapper(event: Message) -> None:
            if event['type'] == 'http.response.start':
                status_holder['code'] = event.get('status', 500)
            await send(event)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            elapsed = time.perf_counter() - start_time
            message = (
                f'{method} Request to {path} completed in {elapsed:.4f} seconds with '
                f'status {status_holder["code"]}'
            )

            self.logger.info(
                message,
                path=path,
                method=method,
                status_code=status_holder['code'],
                latency=elapsed,
            )

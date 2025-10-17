from __future__ import annotations

import time
from http import HTTPStatus
from typing import TYPE_CHECKING

from starlette.middleware.base import BaseHTTPMiddleware

from app import log

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from fastapi import Request, Response
    from starlette.types import ASGIApp


class AccessMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)
        self.logger = log.get_logger()

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        start_time = time.perf_counter()

        ip_address = request.client.host if request.client else 'N/A'
        user_agent = request.headers.get('User-Agent', 'N/A')

        message = (
            f'[{request.method}] -> {request.url} IP={ip_address!s}, '
            f', User-Agent={user_agent!s}'
        )

        cor_id = request.headers.get('X-Request-ID', 'N/A')
        self.logger.log(
            'SECURITY',
            message,
            correlation_id=cor_id,
            method=request.method,
            url=str(request.url),
            path=request.url.path,
            ip_address=ip_address,
            user_agent=str(user_agent),
        )

        response = await call_next(request)

        duration = time.perf_counter() - start_time
        phrase = HTTPStatus(response.status_code).phrase
        message = (
            f'Responded to {cor_id} in {duration:.3f}s with a '
            f'{response.status_code}, {phrase}.'
        )

        self.logger.log(
            'SECURITY',
            message,
            status_code=response.status_code,
            phrase=phrase,
            elapsed=duration,
            correlation_id=response.headers.get('X-Request-ID', 'N/A'),
        )

        return response

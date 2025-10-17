from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi.middleware.cors import CORSMiddleware

if TYPE_CHECKING:
    from fastapi import FastAPI

    from app.core.settings import CORSPolicyConfig


def register_middleware(app: FastAPI, cors: CORSPolicyConfig) -> None:
    """
    Register middleware for the FastAPI application

    Parameters
    ----------
    app : FastAPI
        The FastAPI application instance
    cors : CORSPolicyConfig
        The CORS policy configuration
    """
    from app.core.correlation_id import CorrelationMiddleware
    from app.middleware.access import AccessMiddleware

    app.add_middleware(
        CorrelationMiddleware,
        header_name=b'X-Correlation-ID'
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors.allow_origins,
        allow_credentials=cors.allow_credentials,
        allow_methods=cors.allow_methods,
        allow_headers=cors.allow_headers,
    )
    app.add_middleware(AccessMiddleware)

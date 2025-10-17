from __future__ import annotations

import contextlib
import logging
from typing import TYPE_CHECKING

from fastapi import FastAPI

from app.life_span import get_lifespan_state
from app.log import initialize_logger
from app.response import ApiJsonResponse
from app.settings import get_app_settings

if TYPE_CHECKING:
    from app.core.configs import AppSettings

logger = logging.getLogger(__name__)


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):  # noqa: ANN201
    logger.info("===== ASGI Lifespan Startup =====")
    state = await get_lifespan_state()
    try:
        yield {
            'redis_db': state.redis_db,
            'postgres_db': state.postgres_db,
            'settings': state.settings,
            'secrets': state.secrets,
            'jwks': state.jwks,
        }
    finally:
        logger.info("===== ASGI Lifespan Shutdown =====")
        await state.dispose()


def configure_app(app: FastAPI, *, settings: AppSettings) -> None:
    from app.middleware.core import register_exception_handlers, register_middleware
    from app.router import api_router

    if not settings.app.allow_doc_routes:
        app.docs_url = None
        app.redoc_url = None
        app.openapi_url = None
    else:
        logger.warning(
            'Notice: Documentation routes are enabled, disable in production.')

    if settings.app.debug:
        logger.warning('Notice: Debug mode is enabled, disable in production.')

    logger.info('Registering middleware...')
    register_middleware(app, settings.cors)

    logger.info('Registering exception handlers...')
    register_exception_handlers(app)

    logger.info('Registering routes...')
    app.include_router(api_router)


def create_app() -> FastAPI:
    '''
    Create and configure the FastAPI application instance

    Returns
    -------
    FastAPI
        
    '''
    settings = get_app_settings()

    initialize_logger(settings.logger)

    app = FastAPI(
        title=settings.app.name,
        version=settings.version,
        debug=settings.app.debug,
        description=settings.app.description,
        openapi_url=settings.app.openapi_url,
        docs_url=settings.app.docs_url,
        redoc_url=settings.app.redoc_url,
        lifespan=lifespan,
        default_response_class=ApiJsonResponse,
    )

    configure_app(app, settings=settings)

    return app

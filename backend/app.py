import logging
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.config import get_app_config
from backend.logging import configure_logging
from backend.settings.configs import CorsConfig

logger = logging.getLogger(__name__)


def is_ci_mode() -> bool:
    flag = os.getenv('CI_MODE', 'false').lower()
    return flag in ('1', 'true', 'yes')


def register_exception_handlers(app: FastAPI) -> None:
    from backend.exceptions.handlers import registered_exception_handlers

    logger.info('Adding exception handlers...')
    for exception_cls, handler in registered_exception_handlers.items():
        app.add_exception_handler(exception_cls, handler)


def register_middleware(app: FastAPI, cors: CorsConfig) -> None:
    from backend.middleware.correlation_id import CorrelationMiddleware
    from backend.middleware.logging import LoggingMiddleware

    logger.info('Adding middleware...')
    app.add_middleware(CorrelationMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors.ALLOW_ORIGINS,
        allow_credentials=cors.ALLOW_CREDENTIALS,
        allow_methods=cors.ALLOW_METHODS,
        allow_headers=cors.ALLOW_HEADERS,
    )
    app.add_middleware(LoggingMiddleware)

# TODO
def get_fastapi_kwargs() -> dict: ...


def create_app() -> FastAPI:
    config = get_app_config()
    configure_logging(
        json_stdout=config.server.LOGGING_JSON_STDOUT,
        levelname=config.server.LOGGING_LEVEL,
    )
    logger.info('Creating FastAPI application')

    app = FastAPI(
        title='FastAPI Backend Template',
        version='0.1.0',
    )

    register_exception_handlers(app)
    register_middleware(app, config.cors)

    return app

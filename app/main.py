import contextlib
import logging

from fastapi import FastAPI

from app.life_span import LifespanState
from app.log import initialize_logger
from app.core.settings import get_app_settings, get_secret_settings

logger = logging.getLogger(__name__)


async def get_lifespan_state() -> LifespanState:
    secrets = get_secret_settings()
    settings = get_app_settings()
    try:
        state = LifespanState.create(
            secrets,
            settings
        )
        await state.initialize()
    except Exception as e:
        logger.critical(
            f"{type(e).__name__}: Failed to initialize lifespan state",
            exc_info=e
        )
        raise

    return state


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
        }
    finally:
        logger.info("===== ASGI Lifespan Shutdown =====")
        await state.dispose()


def create_app() -> FastAPI:
    from app.middleware.core import register_middleware
    from app.router import api_router

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
    )
    if not settings.app.allow_doc_routes:
        app.docs_url = None
        app.redoc_url = None
        app.openapi_url = None
    else:
        logger.warning('Notice: Documentation routes are enabled, disable in production.')

    if settings.app.debug:
        logger.warning('Notice: Debug mode is enabled, disable in production.')

    logger.info('Registering middleware...')
    register_middleware(app, settings.cors)
    logger.info('Registering routes...')
    app.include_router(api_router)

    return app

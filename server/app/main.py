import contextlib
import logging

from fastapi import FastAPI

logger = logging.getLogger(__name__)


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("===== ASGI Lifespan Startup =====")

    try:
        yield
    finally:
        logger.info("===== ASGI Lifespan Shutdown =====")


def create_app() -> FastAPI:
    app = FastAPI(
        title="FastAPI Backend Template",
        lifespan=lifespan,
    )

    @app.get("/health", tags=["Health"])
    async def health_check():
        return {"status": "ok"}

    return app

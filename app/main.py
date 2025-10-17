import contextlib
import functools
import logging
import os
from pathlib import Path

import asyncpg
from fastapi import FastAPI

from app.core.config_class import EnvConfig, TomlConfig, TomlSection

logger = logging.getLogger(__name__)


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("===== ASGI Lifespan Startup =====")

    await asyncpg.create_pool(

    )

    try:
        yield
    finally:
        logger.info("===== ASGI Lifespan Shutdown =====")


def register_routes(app: FastAPI) -> None:




def create_app() -> FastAPI:
    app = FastAPI(
        title="FastAPI Backend Template",
        lifespan=lifespan,
    )

    @app.get("/")
    async def health_check():
        return {"status": "ok"}

    return app

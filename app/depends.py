from typing import Annotated

from fastapi import Depends, Request
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.life_span import LifespanState
from app.core.settings import AppSettings, SecretSettings


async def get_lifespan_context(request: Request) -> LifespanState:
    return request.state.lifespan


ServerContext = Annotated[LifespanState, Depends(get_lifespan_context)]


async def get_redis_client(context: ServerContext) -> Redis:
    return context.redis_db.client


async def get_postgres_session(context: ServerContext):
    async with context.postgres_db.local_session() as session:
        yield session


async def get_app_settings(context: ServerContext) -> AppSettings:
    return context.settings


async def get_secret_settings(context: ServerContext) -> SecretSettings:
    return context.secrets


PostgresDep = Annotated[AsyncSession, Depends(get_postgres_session)]
RedisDep = Annotated[Redis, Depends(get_redis_client)]
SettingsDep = Annotated[AppSettings, Depends(get_app_settings)]
SecretsDep = Annotated[SecretSettings, Depends(get_secret_settings)]

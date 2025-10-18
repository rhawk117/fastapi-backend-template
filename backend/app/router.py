import os

import sqlalchemy as sa
from fastapi import APIRouter

from app.depends import PostgresDep, RedisDep, SettingsDep

api_router = APIRouter()


@api_router.get('/', tags=['Root'])
async def root() -> dict[str, bool]:
    return {'ok': True}


@api_router.get('/health', tags=['Health'])
async def health_check(redis: RedisDep, pg_session: PostgresDep) -> dict[str, str]:

    result = await pg_session.execute(sa.text('SELECT 1'))
    pg_status = result.scalar_one_or_none()
    redis_status = await redis.ping()
    return {
        'status': 'ok' if pg_status == 1 and redis_status else 'error',
        'redis': 'ok' if redis_status else 'error',
        'postgres': 'ok' if pg_status == 1 else 'error',
    }


@api_router.get('/version', tags=['Version'])
async def get_deployment_config(settings: SettingsDep) -> dict:
    return {
        'environment': os.getenv('ENVIRONMENT', 'development'),
        'config': settings,
    }

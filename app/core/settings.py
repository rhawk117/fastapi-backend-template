import functools
import logging
import os
from pathlib import Path

from app.core.config_sources import EnvConfig, TomlConfig, TomlSection

logger = logging.getLogger(__name__)


class SecretSettings(EnvConfig):

    # model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")
    PG_USER: str = 'appuser'
    PG_PASSWORD: str = 'changeme'
    PG_DATABASE_NAME: str = 'appdb'
    PG_HOSTNAME: str = 'postgres'
    PG_PORT: int = 5432
    AUTH_JWT_PRIVATE_KEY: str
    AUTH_JWT_PUBLIC_KEY: str
    AUTH_CSRF_SECRET: str
    REDIS_URL: str = 'redis://redis:6379/0'


class ServerConfig(TomlSection):
    host: str = '0.0.0.0'
    port: int = 8000


class AppConfig(TomlSection):
    name: str = "FastAPI Backend Template"
    description: str = "A template for building FastAPI applications."
    debug: bool = True
    openapi_url: str = "/openapi.json"
    docs_url: str = "/docs"
    redoc_url: str = "/redoc"
    allow_doc_routes: bool = True


class LoggerConfig(TomlSection):
    format: str = (
        '<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | '
        '<level>{level: <8}</level> | '
        'cid=<cyan>{extra[correlation_id]}</cyan> | '
        '<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - '
        '<level>{message}</level>'
    )
    level: str = 'DEBUG'
    retention_days: int = 7
    rotation_mb: int = 5
    compression: str = 'zip'
    security_level_no: int = 25
    structured_logs: bool = True


class CORSPolicyConfig(TomlSection):
    allow_origins: list[str] = ['*']
    allow_credentials: bool = True
    allow_methods: list[str] = ['*']
    allow_headers: list[str] = ['*']


class RedisConfig(TomlSection):
    socket_connect_timeout: int = 5
    retry_on_timeout: bool = True
    max_connections: int = 10
    socket_keepalive: bool = True
    decode_responses: bool = True
    health_check_interval: int = 30
    socket_timeout: int = 5


class SqlalchemyConfig(TomlSection):
    pool_size: int = 10
    max_overflow: int = 20
    pool_timeout: int = 30
    pool_recycle: int = 1800
    echo: bool = False
    future: bool = True


# class PostgresConfig(TomlSection):
#     _DRIVERNAME: str = 'asyncpg'

#     statement_timeout_sec: int = 30
#     statement_cache_size: int = 100
#     timezone: str = 'UTC'
#     jit: bool = True
#     command_timeout_sec: int = 60


class AppSettings(TomlConfig):
    version: str = "0.1.0"
    server: ServerConfig = ServerConfig()
    app: AppConfig = AppConfig()
    logger: LoggerConfig = LoggerConfig()
    redis: RedisConfig = RedisConfig()
    cors: CORSPolicyConfig = CORSPolicyConfig()
    sql_alchemy: SqlalchemyConfig = SqlalchemyConfig()


def know_app_settings() -> list[str]:
    config_dir = Path('configs')
    return [str(f) for f in config_dir.glob('app.*.toml') if f.is_file()]


@functools.lru_cache
def get_app_settings(*, environment: str | None = None) -> AppSettings:
    if not environment:
        environment = os.getenv('ENVIRONMENT', 'development')

    toml_file_path = os.path.join('configs', f'{environment}.toml')
    if not os.path.exists(toml_file_path):
        known_files = know_app_settings()
        raise FileNotFoundError(
            f"Configuration file {toml_file_path} not found, "
            f"known files: {', '.join(known_files)}"
        )

    return AppSettings(_toml_file=f'configs/app.{environment}.toml')


@functools.lru_cache
def get_secret_settings() -> SecretSettings:
    return SecretSettings()  # type: ignore

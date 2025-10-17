import functools
import logging
import os
from pathlib import Path

from app.core.config_class import EnvConfig, TomlConfig, TomlSection

logger = logging.getLogger(__name__)


class SecretSettings(EnvConfig):

    # model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    DATABASE_URL: str
    JWT_PRIVATE_KEY: str
    JWT_PUBLIC_KEY: str
    CSRF_SECRET: str


class ServerConfig(TomlSection):
    host: str = '0.0.0.0'
    port: int = 8000


class AppConfig(TomlSection):
    environment: str = "development"
    name: str = "FastAPI Backend Template"
    version: str = "0.1.0"
    description: str = "A template for building FastAPI applications."
    debug: bool = True
    openapi_url: str = "/openapi.json"
    docs_url: str = "/docs"
    redoc_url: str = "/redoc"


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


class AppSettings(TomlConfig):
    server: ServerConfig = ServerConfig()
    app: AppConfig = AppConfig()
    logger: LoggerConfig = LoggerConfig()


def know_app_settings() -> list[str]:
    config_dir = Path('configs')
    return [str(f) for f in config_dir.glob('app.*.toml') if f.is_file()]


@functools.lru_cache
def get_app_settings(*, environment: str = 'development') -> AppSettings:
    toml_file_path = os.path.join('configs', f'app.{environment}.toml')
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

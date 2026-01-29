import base64
import dataclasses as dc
import functools
import os
import secrets
import urllib.parse as urlib_parse
from typing import Any, Literal

from cryptography.fernet import Fernet
from pydantic import SecretBytes, SecretStr, ValidationError
from pydantic_settings import SettingsConfigDict
from sqlalchemy import URL as SqlURL  # noqa: N811

from backend.settings.jwks import JsonWebKey
from backend.settings.sources import SettingsModel

LogLevelnames = Literal[
    'CRITICAL',
    'ERROR',
    'WARNING',
    'INFO',
    'DEBUG',
    'NOTSET',
]


def get_postgres_driver(*, sync: bool = False) -> str:
    return 'postgresql+psycopg2' if sync else 'postgresql+asyncpg'


def generate_secret_bytes(nbytes: int = 16) -> bytes:
    return base64.urlsafe_b64encode(secrets.token_bytes(nbytes))


def generate_secret_str(*, length: int = 32) -> str:
    return secrets.token_urlsafe(length)

def create_redis_url(
    host: str,
    *,
    user: str,
    password: str,
    port: int = 6379,
    scheme: str = 'redis://',
) -> str:
    auth_part = ''
    if user and password:
        encoded_user = urlib_parse.quote_plus(user)
        encoded_password = urlib_parse.quote_plus(password)
        auth_part = f'{encoded_user}:{encoded_password}@'

    elif password:
        encoded_password = urlib_parse.quote_plus(password)
        auth_part = f':{encoded_password}@'

    return f'{scheme}{auth_part}{host}:{port}/'

class AuthConfig(SettingsModel):
    PBKDF2_SALT: SecretBytes
    FERNET_KEY: SecretBytes
    PUBLIC_KEY_PEM: SecretStr
    PRIVATE_KEY_PEM: SecretStr
    JWK_KID: str
    _json_web_key: JsonWebKey | None = None

    @classmethod
    def generate_required_fields(cls) -> dict[str, Any]:
        json_web_keys = JsonWebKey.generate()
        return {
            'FERNET_KEY': Fernet.generate_key(),
            'PBKDF2_SALT': generate_secret_str(),
            'PUBLIC_KEY_PEM': json_web_keys.public_key,
            'PRIVATE_KEY_PEM': json_web_keys.private_key,
            'JWK_KID': json_web_keys.kid,
        }

    @property
    def json_web_key(self) -> JsonWebKey:
        if self._json_web_key is None:
            self._json_web_key = JsonWebKey(
                kid=self.JWK_KID,
                private_key=self.PRIVATE_KEY_PEM.get_secret_value(),
                public_key=self.PUBLIC_KEY_PEM.get_secret_value(),
            )
        return self._json_web_key

    model_config = SettingsConfigDict(
        env_prefix='AUTH_',
    )

class RedisConfig(SettingsModel):
    """
    Redis related environment configuration with env prefix `REDIS_`
    """
    model_config = SettingsConfigDict(env_prefix='REDIS_')

    HOST: str = 'redis'
    USER: str = ''
    PASSWORD: SecretStr
    PORT: int = 6379
    SCHEME: Literal['redis://', 'rediss://'] = 'redis://'
    APP_DB: int = 0
    SOCKET_CONNECT_TIMEOUT: int = 5
    MAX_CONNECTIONS: int = 10
    HEALTH_CHECK_INTERVAL: int = 30
    SOCKET_TIMEOUT: int = 5

    def get_url(self) -> str:
        return create_redis_url(
            self.HOST,
            user=self.USER,
            password=self.PASSWORD.get_secret_value(),
            port=self.PORT,
            scheme=self.SCHEME
        )

    def client_kwargs(self) -> dict:
        return {
            'retry_on_timeout': True,
            'decode_responses': True,
            'socket_keepalive': True,
            'max_connections': self.MAX_CONNECTIONS,
            'socket_timeout': self.SOCKET_TIMEOUT,
            'socket_connect_timeout': self.SOCKET_CONNECT_TIMEOUT,
            'health_check_interval': self.HEALTH_CHECK_INTERVAL,
        }

    @classmethod
    def generate_required_fields(cls) -> dict[str, Any]:
        return {
            'PASSWORD': generate_secret_str()
        }


class DatabaseConfig(SettingsModel):
    PASSWORD: SecretStr
    USER: str = 'scheduler'
    NAME: str = 'schedulerdb'
    HOST: str = 'db'
    PORT: int = 5432
    ECHO: bool = False
    MAX_OVERFLOW: int = 5
    POOL_RECYCLE: int = 3600
    POOL_SIZE: int = 10
    TIMEOUT: int = 30

    def get_url(self, *, sync: bool = False) -> SqlURL:
        return SqlURL.create(
            drivername=get_postgres_driver(sync=sync),
            username=self.USER,
            password=self.PASSWORD.get_secret_value(),
            host=self.HOST,
            port=self.PORT,
            database=self.NAME,
        )

    def connect_args(self) -> dict:
        return {'timeout': self.TIMEOUT}

    def engine_kwargs(self) -> dict:
        return {
            'echo': self.ECHO,
            'future': True,
            'pool_pre_ping': True,
            'max_overflow': self.MAX_OVERFLOW,
            'pool_size': self.POOL_SIZE,
            'pool_recycle': self.POOL_RECYCLE,
            'connect_args': self.connect_args(),
        }

    model_config = SettingsConfigDict(
        env_prefix='DATABASE_',
    )


class ServerConfig(SettingsModel):
    DEBUG: bool = False
    HOST: str = '0.0.0.0'
    PORT: int = 8000
    LOGGING_LEVEL: LogLevelnames = 'INFO'
    LOGGING_JSON_STDOUT: bool = False
    ALLOW_DOCUMENTATION: bool = True
    WORKERS: int = 1
    TIMEOUT_KEEP_ALIVE: int = 5
    TIMEOUT_WORKER_HEALTHCHECK: int = 30
    SERVER_HEADER: bool = True
    DATE_HEADER: bool = True
    PROXY_HEADER: bool = False
    RELOAD: bool = False

    model_config = SettingsConfigDict(
        env_prefix='SERVER_',
    )


@dc.dataclass(slots=True, frozen=True)
class AppConfig:
    auth: AuthConfig = dc.field(default_factory=AuthConfig)  # type: ignore
    server: ServerConfig = dc.field(default_factory=ServerConfig)  # type: ignore
    database: DatabaseConfig = dc.field(default_factory=DatabaseConfig)  # type: ignore




def generate_app_config(
    *,
    secret_key: str | None = None,
    fernet_key: str | None = None,
    pbkdf2_salt: bytes | None = None,
    database_password: str | None = None,
) -> AppConfig:
    """Generate an AppConfig with all required secrets.

    If secrets are not provided, they will be generated automatically.
    This is useful for initial setup or testing environments.
    """
    auth = AuthConfig(
        SECRET_KEY=SecretStr(secret_key or secrets.token_urlsafe(32)),
        FERNET_KEY=SecretStr(fernet_key or generate_fernet_key()),
        PBKDF2_SALT=SecretBytes(pbkdf2_salt or os.urandom(16)),
    )

    server = ServerConfig()

    database = DatabaseConfig(
        PASSWORD=SecretStr(database_password or secrets.token_urlsafe(24)),
    )

    return AppConfig(auth=auth, server=server, database=database)


def export_app_config(config: AppConfig) -> dict[str, str]:
    env_vars: dict[str, str] = {}

    config_mapping: list[tuple[str, SettingsModel]] = [
        ('AUTH_', config.auth),
        ('SERVER_', config.server),
        ('DATABASE_', config.database),
    ]

    for prefix, settings in config_mapping:
        dumped = settings.model_dump()
        for key, value in dumped.items():
            env_key = f'{prefix}{key}'
            env_vars[env_key] = _serialize_env_value(value)

    return env_vars


def _serialize_env_value(value: object) -> str:
    match value:
        case bool():
            return str(value).lower()
        case bytes():
            return base64.urlsafe_b64encode(value).decode('ascii')
        case _:
            return str(value)

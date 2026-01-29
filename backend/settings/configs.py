import base64
import secrets
import urllib.parse as urlib_parse
from typing import Any, Literal, Self

from cryptography.fernet import Fernet
from pydantic import SecretBytes, SecretStr
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
            scheme=self.SCHEME,
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
        return {'PASSWORD': generate_secret_str()}


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


class Argon2Config(SettingsModel):
    model_config = SettingsConfigDict(env_prefix='ARGON2_')

    TIME_COST: int = 2
    MEMORY_COST: int = 19456
    PARALLELISM: int = 1
    HASH_LEN: int = 32
    SALT_LEN: int = 16

    @classmethod
    def fast(cls) -> Self:
        return cls(
            TIME_COST=1,
            MEMORY_COST=8192,
            PARALLELISM=1,
            HASH_LEN=16,
            SALT_LEN=16,
        )

    @classmethod
    def secure(cls) -> Self:
        return cls(
            TIME_COST=4,
            MEMORY_COST=65536,
            PARALLELISM=2,
            HASH_LEN=64,
            SALT_LEN=16,
        )

    def hasher_kwargs(self) -> dict:
        return {
            'time_cost': self.TIME_COST,
            'memory_cost': self.MEMORY_COST,
            'parallelism': self.PARALLELISM,
            'hash_len': self.HASH_LEN,
            'salt_len': self.SALT_LEN,
        }


class CorsConfig(SettingsModel):
    model_config = SettingsConfigDict(env_prefix='CORS_')

    ALLOW_ORIGINS: list[str] = ['*']
    ALLOW_CREDENTIALS: bool = True
    ALLOW_METHODS: list[str] = ['*']
    ALLOW_HEADERS: list[str] = ['*']

import functools

from app.core.configs import AppSettings
from app.core.secrets import JWKSecrets, SecretTomlSettings

# we use lru cache to load settings once per process
# read: https://fastapi.tiangolo.com/advanced/settings/#creating-the-settings-only-once-with-lru-cache


@functools.lru_cache
def get_secret_settings() -> SecretTomlSettings:
    return SecretTomlSettings()  # type: ignore[return-value]


@functools.lru_cache
def get_secret_jwks() -> JWKSecrets:
    return JWKSecrets()  # type: ignore[return-value]


@functools.lru_cache
def get_app_settings() -> AppSettings:
    return AppSettings()  # type: ignore[return-value]

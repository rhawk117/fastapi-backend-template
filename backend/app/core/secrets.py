
import urllib.parse
from functools import cached_property
from typing import Annotated, Literal

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from pydantic import AfterValidator, Field, SecretStr
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    TomlConfigSettingsSource,
)
from sqlalchemy import URL

from app.core.config_sources import (
    Settings,
    TomlSection,
    get_app_environment,
    verify_toml_path,
)


def _verify_pem_headers(value: SecretStr) -> SecretStr:
    pem = value.get_secret_value()
    if not (pem.startswith('-----BEGIN') and pem.strip().endswith('-----END')):
        raise ValueError(
            "PEM key must start with '-----BEGIN' and end with '-----END'."
        )
    return value


PortNumber = Annotated[int, Field(
    description='A valid port number between 1 and 65535.',
    ge=1,
    le=65535,
)]
SecretPemFile = Annotated[SecretStr, AfterValidator(_verify_pem_headers)]


def create_redis_url(
    db: int = 0,
    *,
    username: str | None = None,
    password: str | None = None,
    hostname: str,
    port: int = 6379,
    ssl: bool = False,
) -> str:
    if db < 0 or db > 15:
        raise ValueError("Redis database number must be between 0 and 15.")

    scheme = 'rediss' if ssl else 'redis'
    auth_part = ''
    if username and password:
        username = urllib.parse.quote_plus(username)
        password = urllib.parse.quote_plus(password)
        auth_part = f"{username}:{password}@"
    elif password:
        password = urllib.parse.quote_plus(password)
        auth_part = f":{password}@"
    return f"{scheme}://{auth_part}{hostname}:{port}/{db}"


class PostgresSecrets(TomlSection):
    '''
    stored in `.secrets/secrets.<environment>.toml`
    '''
    user: str
    password: str
    database_name: str
    hostname: str
    port: PortNumber = 5432

    def get_url(self) -> URL:
        return URL.create(
            drivername='postgresql+asyncpg',
            username=self.user,
            password=self.password,
            host=self.hostname,
            port=self.port,
            database=self.database_name,
        )


class RedisSecrets(TomlSection):
    '''
    Redis connection secrets; stored in `.secrets/secrets.<env>.toml`
    '''
    username: str | None = None
    password: str | None = None
    port: PortNumber = 6379
    hostname: str
    ssl: bool = False

    def get_url(self, db: int = 0) -> str:
        if db < 0 or db > 15:
            raise ValueError("Redis database number must be between 0 and 15.")
        return create_redis_url(
            db,
            username=self.username,
            password=self.password,
            hostname=self.hostname,
            port=self.port,
            ssl=self.ssl,
        )


class JWKSecrets(Settings):
    '''
    JSON Web Key (JWK) Secrets loaded from .secrets/jwk/ directory.
    '''
    jwt_alg: Literal['RS256'] = 'RS256'
    private_key: SecretPemFile
    public_key: SecretPemFile

    @cached_property
    def _rsa_private_key(self) -> rsa.RSAPrivateKey:
        raw = self.private_key.get_secret_value().encode()
        return serialization.load_pem_private_key(
            raw,
            password=None,
            backend=default_backend()
        )  # type: ignore[return-value]

    @cached_property
    def _rsa_public_key(self) -> rsa.RSAPublicKey:
        raw = self.public_key.get_secret_value().encode()
        return serialization.load_pem_public_key(
            raw,
            backend=default_backend()
        )  # type: ignore[return-value]

    @cached_property
    def private_key_signer(self) -> bytes:
        return self._rsa_private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )

    @cached_property
    def public_key_verifier(self) -> bytes:
        return self._rsa_public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )

    model_config = SettingsConfigDict(
        secrets_dir='./.secrets/jwk/'
    )


class JwtSecrets(TomlSection):
    '''
    JWT related secrets stored in `.secrets/secrets.<environment>.toml`
    '''
    issuer: str = "fastapi-backend-template"
    audience: str = "fastapi-backend-template-users"
    jwk_id: str = 'default'


class SecretTomlSettings(Settings):
    '''
    The secret settings loaded from TOML files, stored in `.secrets/` directory
    in the file `secrets.<environment>.toml`.
    '''
    postgres: PostgresSecrets
    redis: RedisSecrets
    jwt: JwtSecrets

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        app_environment = get_app_environment()
        toml_file_path = verify_toml_path(
            '.secrets',
            f'secrets.{app_environment}.toml'
        )

        toml_source = TomlConfigSettingsSource(
            settings_cls,
            toml_file=str(toml_file_path),
        )
        return (
            toml_source,
            init_settings,
            env_settings,
            dotenv_settings,
            file_secret_settings,
        )

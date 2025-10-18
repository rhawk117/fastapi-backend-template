from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    TomlConfigSettingsSource,
)

from app.core.config_sources import (
    Settings,
    TomlSection,
    get_app_environment,
    verify_toml_path,
)


class AppConfig(TomlSection):
    name: str = 'FastAPI Backend Template'
    description: str = 'A template for building FastAPI applications.'
    debug: bool = True
    openapi_url: str = '/openapi.json'
    docs_url: str = '/docs'
    redoc_url: str = '/redoc'
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


class AppSettings(Settings):
    environment: str
    version: str = '0.1.0'

    app: AppConfig = AppConfig()
    logger: LoggerConfig = LoggerConfig()
    cors: CORSPolicyConfig = CORSPolicyConfig()
    sql_alchemy: SqlalchemyConfig = SqlalchemyConfig()
    redis_connection: RedisConfig = RedisConfig()

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        environment = get_app_environment()
        toml_file_path = verify_toml_path('configs', f'config.{environment}.toml')
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

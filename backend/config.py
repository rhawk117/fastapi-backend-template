import base64
import dataclasses as dc
import functools
from collections.abc import Iterator
from typing import cast

from pydantic import ValidationError
from pydantic.fields import FieldInfo
from pydantic_settings import BaseSettings

from backend.schemas.errors import PydanticError
from backend.settings.configs import (
    AuthConfig,
    DatabaseConfig,
    RedisConfig,
    ServerConfig,
)


@dc.dataclass(slots=True)
class AppConfig:
    auth: AuthConfig = dc.field(default_factory=AuthConfig)  # type: ignore
    server: ServerConfig = dc.field(default_factory=ServerConfig)  # type: ignore
    database: DatabaseConfig = dc.field(default_factory=DatabaseConfig)  # type: ignore
    redis: RedisConfig = dc.field(default_factory=RedisConfig)  # type: ignore

    @classmethod
    def config_classes(cls) -> Iterator[type[BaseSettings]]:
        for field in dc.fields(cls):
            yield cast('type[BaseSettings]', field.type)


@functools.lru_cache(maxsize=1)
def get_app_config() -> AppConfig:
    """Loads and returns the application settings, caching the result for future calls
    this ensures that settings are only loaded once during the application's lifetime
    per worker process. Learn more about this pattern here:

    https://fastapi.tiangolo.com/advanced/settings/#read-settings-from-env

    Raises
    ------
    RuntimeValidationError
        Descriptive error wrapping Pydantic's ValidationError if settings
        fail to validate.
    """
    try:
        app_settings = AppConfig()
    except ValidationError as exc:
        errors = [PydanticError.create(detail).to_message() for detail in exc.errors()]
        raise RuntimeError('Invalid application settings:\n' + '\n'.join(errors))

    return app_settings


def _serialize_env_value(value: object) -> str:
    match value:
        case bool():
            return str(value).lower()
        case bytes():
            return base64.urlsafe_b64encode(value).decode('ascii')
        case _:
            return str(value)


def collect_model_field(
    field_name: str,
    field_info: FieldInfo,
    provided_required_values: dict[str, str],
) -> str:
    if field_info.is_required():
        provided_value = provided_required_values.pop(field_name, '')
        if not provided_value:
            raise ValueError(
                f'A required value for was not provided in '
                f'generate_required_fields() for field {field_name}'
            )
        value = provided_value
    else:
        value = field_info.get_default()

    return _serialize_env_value(value)


def generate_config_env_variables(
    settings_cls: type[BaseSettings],
) -> dict[str, str]:
    if not issubclass(settings_cls, BaseSettings):
        raise TypeError(f'Is `{settings_cls}` not a pydantic BaseSettings subclass')

    generated_required_fields = {}
    if hasattr(settings_cls, 'generate_required_fields()'):
        generated_required_fields = settings_cls.generate_required_fields()  # type: ignore

    settings_env_prefix = settings_cls.model_config.get('env_prefix', '')
    dotenv_mapping = {}
    for field_name, field_info in settings_cls.model_fields.items():
        enviornment_variable = f'{settings_env_prefix}{field_name}'
        dotenv_mapping[enviornment_variable] = collect_model_field(
            field_name,
            field_info,
            generated_required_fields,
        )

    return dotenv_mapping

def generate_dotenv_config() -> dict[str, str]:
    dotenv_vars = {}
    for settings_cls in AppConfig.config_classes():
        setting_env_vars = generate_config_env_variables(settings_cls)
        dotenv_vars.update(setting_env_vars)

    return dotenv_vars

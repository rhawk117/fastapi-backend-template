from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any, get_origin

from pydantic_settings import (
    BaseSettings,
    DotEnvSettingsSource,
    EnvSettingsSource,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)

if TYPE_CHECKING:
    from pydantic.fields import FieldInfo


def get_app_env(override: str | None = None) -> str:
    return override or os.getenv('APP_ENV', 'dev')


def _prepare_sequence_env_field(
    field: FieldInfo,
    value: Any,
) -> Any:
    """
    Allows parsing of list/set fields from environment variables or dotenv files
    """
    origin = get_origin(field.annotation)
    delimiter = ','
    if field.json_schema_extra and (
        custom_delimiter := field.json_schema_extra.get('delimiter')
    ):
        delimiter = custom_delimiter

    parsed = [item.strip() for item in value.split(delimiter) if item.strip()]
    return set(parsed) if origin is set else parsed


class CustomEnvSource(EnvSettingsSource):
    """
    Allows for sequence types (list, set) to be parsed from
    environment variables.
    """

    def prepare_field_value(
        self,
        field_name: str,
        field: FieldInfo,
        value: Any,
        value_is_complex: bool,  # noqa: FBT001
    ) -> Any:
        if isinstance(value, str):
            origin = get_origin(field.annotation)
            if origin in (list, set):
                return _prepare_sequence_env_field(field, value)
        return super().prepare_field_value(field_name, field, value, value_is_complex)


class CustomDotenvSource(DotEnvSettingsSource):
    def __init__(self, settings_cls: type[BaseSettings]) -> None:
        app_env_file = f'.{get_app_env()}.env'
        load_order = ('.env.example', '.env', app_env_file)
        super().__init__(
            settings_cls,
            case_sensitive=False,
            env_file=load_order,
            env_file_encoding='utf-8',
        )

    def prepare_field_value(
        self,
        field_name: str,
        field: FieldInfo,
        value: Any,
        value_is_complex: bool,  # noqa: FBT001
    ) -> Any:
        if isinstance(value, str):
            origin = get_origin(field.annotation)
            if origin in (list, set):
                return _prepare_sequence_env_field(field, value)
        return super().prepare_field_value(field_name, field, value, value_is_complex)


class SettingsModel(BaseSettings):
    model_config = SettingsConfigDict(
        env_file_encoding='utf-8',
        env_nested_delimiter='_',
        validate_assignment=True,
        case_sensitive=False,
        extra='ignore',
    )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        return (
            init_settings,
            CustomEnvSource(settings_cls),
            CustomDotenvSource(settings_cls),
            file_secret_settings,
        )

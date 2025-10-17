from typing import Any, get_origin

from pydantic import BaseModel
from pydantic.fields import FieldInfo
from pydantic_settings import (
    BaseSettings,
    EnvSettingsSource,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    TomlConfigSettingsSource,
)


def _parse_env_sequence(value: str, *, is_hashset: bool = False) -> set[str] | list[str]:
    """
    Parses a comma delimited string into a list or set from a comma delimited
    string.

    Parameters
    ----------
    value : str
        _description_
    is_hashset : bool, optional
        _description_, by default False

    Returns
    -------
    set[str] | list[str]
    """
    seq = [item.strip() for item in value.split(',') if item.strip()]
    if is_hashset:
        return set(seq)
    return seq


class _EnvSource(EnvSettingsSource):
    """
    Allows for sequence values to be parsed from environment
    variables
    """

    def prepare_field_value(
        self,
        field_name: str,
        field: FieldInfo,
        value: Any,
        value_is_complex: bool  # noqa: FBT001
    ) -> Any:
        field_origin = get_origin(field.annotation)

        is_hashset = field_origin is set
        if field_origin is list or is_hashset:
            return _parse_env_sequence(value, is_hashset=is_hashset)

        return super().prepare_field_value(field_name, field, value, value_is_complex)


class BaseConfig(BaseSettings):
    """
    The base configuration for settings classes
    with QOL settings.
    """

    model_config = SettingsConfigDict(
        env_nested_delimiter='__',
        extra='ignore',
        validate_assignment=True,
        case_sensitive=False,
    )


class EnvConfig(BaseConfig):
    """
    Represents a configuration that is loaded from environment variables.
    Order
    1. Init settings
    2. Environment variables
    3. .env file
    4. File secrets
    """

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
            _EnvSource(settings_cls),
            init_settings,
            dotenv_settings,
            file_secret_settings,
        )


class TomlSection(BaseModel):
    """
    A base model for TOML sections,
    easy to configure defaults if needed
    in future
    """


class TomlConfig(BaseSettings):
    """
    A pydantic settings class that is configured
    to load settings from a TOML file.

    Order
    -----
    1. TOML file
    2. Init settings
    3. Environment variables
    4. .env file
    5. File secrets
    """

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
            TomlConfigSettingsSource(settings_cls),
            init_settings,
            _EnvSource(settings_cls),
            dotenv_settings,
            file_secret_settings,
        )

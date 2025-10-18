import os
from pathlib import Path
from typing import Any

from pydantic import BaseModel, SecretStr
from pydantic_settings import (
    BaseSettings,
    SettingsConfigDict,
)


def parse_env_sequence(value: str, *, is_hashset: bool = False) -> set[str] | list[str]:
    '''
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
    '''
    seq = [item.strip() for item in value.split(',') if item.strip()]
    if is_hashset:
        return set(seq)
    return seq


def _env_serialize_field(attr_val: Any) -> str:
    if isinstance(attr_val, SecretStr):
        return attr_val.get_secret_value()

    if isinstance(attr_val, bool):
        return str(attr_val).lower()

    if isinstance(attr_val, (set, tuple, list)):
        return ','.join(str(v) for v in attr_val)

    return str(attr_val)


def env_model_dump_serializer(
    current: dict[str, Any], prefix: str = ''
) -> dict[str, str]:
    '''
    Serializes a dumped pydantic model into
    a dictionary suitable for environment variables.

    Parameters
    ----------
    current : dict[str, Any]
        The dumped pydantic model as a dictionary or
        nested dictionaries.
    prefix : str, optional
        The env prefix, by default ''

    Returns
    -------
    dict[str, str]
    '''
    env_dict = {}
    prefix = prefix.upper()
    for key, value in current.items():
        env_key = f"{prefix}{key.upper()}"
        if isinstance(value, dict):
            nested_dict = env_model_dump_serializer(
                value, prefix=f"{env_key}_"
            )
            env_dict.update(nested_dict)
        else:
            env_dict[env_key] = _env_serialize_field(value)
    return env_dict


def _get_directory_tomls(dir: str, *, pattern: str | None = None) -> list[str]:
    pattern = pattern or '*.toml'
    config_dir = Path(dir)
    return [str(f) for f in config_dir.glob(pattern) if f.is_file()]


def verify_toml_path(dirname: str, filename: str) -> Path:
    '''
    Verifies that a TOML file exists at the given path.

    Parameters
    ----------
    dirname : str
        Directory Name
    filename : str
        File Name

    Returns
    -------
    Path

    Raises
    ------
    FileNotFoundError
        If the TOML file does not exist.
    '''
    path = Path(dirname) / filename
    if not path.exists() or not path.is_file():
        known_files = _get_directory_tomls(dirname)
        raise FileNotFoundError(
            f'TOML file at {path} not found, known files of `{dirname}` are'
            f'{', '.join(known_files)}'
        )

    return path


def get_app_environment(override: str | None = None) -> str:
    return override or os.getenv('APP_ENVIRONMENT', 'development')


class TomlSection(BaseModel):
    '''
    A base model to denote a "section" in a TOML file.
    '''
    model_config = SettingsConfigDict(
        populate_by_name=True,
        extra='ignore',
        validate_assignment=True,
    )


class Settings(BaseSettings):
    '''
    The base settings class for the application with
    quality of life settings set for environment variable
    handling.
    '''
    model_config = SettingsConfigDict(
        env_nested_delimiter='__',
        extra='ignore',
        validate_assignment=True,
    )

    def model_dump_env(self, *, prefix: str = '') -> dict[str, str]:
        '''
        Serializes the settings into a dictionary
        suitable for environment variables.

        Parameters
        ----------
        prefix : str, optional
            A prefix to add to each environment variable key,
            by default ''

        Returns
        -------
        dict[str, str]
            A dictionary of environment variable keys and values.
        '''
        dumped = self.model_dump(
            by_alias=True,
            exclude_unset=True
        )
        return env_model_dump_serializer(dumped, prefix=prefix)

from pathlib import Path
import toml


def get_secret_fields() -> dict:
    from app.settings import get_secret_settings





def toml_to_env(toml_path: Path) -> dict[str, str]:
    toml_dict = toml.load(toml_path)

    for s


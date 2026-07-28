from pathlib import Path
from typing import Any

import yaml


CONFIG_DIR = Path(__file__).resolve().parent.parent / "configs"


def load_yaml(filename: str) -> dict[str, Any]:
    path = CONFIG_DIR / filename

    if not path.exists():
        raise FileNotFoundError(f"Configuration file not found: {path}")

    with path.open("r", encoding="utf-8-sig") as file:
        data = yaml.safe_load(file)

    return data or {}


def load_settings() -> dict[str, Any]:
    return load_yaml("settings.yaml")


def load_job_preferences() -> dict[str, Any]:
    return load_yaml("job_preferences.yaml")

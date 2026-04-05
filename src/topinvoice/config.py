from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from dotenv import dotenv_values

from topinvoice.errors import ConfigurationError


@dataclass(frozen=True)
class Config:
    login: str
    password: str


def _read_env_file(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}

    loaded_values = dotenv_values(path)
    return {
        key: value
        for key, value in loaded_values.items()
        if value is not None
    }


def _merge_environment(file_values: Mapping[str, str], environment: Mapping[str, str] | None = None) -> dict[str, str]:
    merged = dict(file_values)
    source_environment = dict(os.environ) if environment is None else dict(environment)
    merged.update(source_environment)

    return merged


def load_config(env_file: Path, environment: Mapping[str, str] | None = None) -> Config:
    merged_environment = _merge_environment(_read_env_file(env_file), environment)
    login = (merged_environment.get("GUESTSAGE_LOGIN") or merged_environment.get("GUESTSAGE_EMAIL") or "").strip()
    password = merged_environment.get("GUESTSAGE_PASSWORD", "").strip()

    if not login:
        raise ConfigurationError("Missing required environment variable: GUESTSAGE_LOGIN")
    if not password:
        raise ConfigurationError("Missing required environment variable: GUESTSAGE_PASSWORD")

    return Config(login=login, password=password)

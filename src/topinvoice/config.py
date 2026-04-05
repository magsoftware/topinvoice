from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from dotenv import dotenv_values

from topinvoice.errors import ConfigurationError


@dataclass(frozen=True)
class Config:
    """Credentials required to access GuestSage."""

    login: str
    password: str


def _read_env_file(path: Path) -> dict[str, str]:
    """Read environment values from a dotenv file.

    Args:
        path: Path to the dotenv file.

    Returns:
        Mapping of variables loaded from the file. Missing files return an empty
        mapping, and keys with null values are ignored.
    """
    if not path.exists():
        return {}

    loaded_values = dotenv_values(path)
    return {
        key: value
        for key, value in loaded_values.items()
        if value is not None
    }


def _merge_environment(file_values: Mapping[str, str], environment: Mapping[str, str] | None = None) -> dict[str, str]:
    """Merge dotenv values with environment variables.

    Args:
        file_values: Values loaded from a dotenv file.
        environment: Optional environment mapping used instead of `os.environ`.

    Returns:
        Combined environment where explicit environment variables override file
        values.
    """
    merged = dict(file_values)
    source_environment = dict(os.environ) if environment is None else dict(environment)
    merged.update(source_environment)

    return merged


def load_config(env_file: Path, environment: Mapping[str, str] | None = None) -> Config:
    """Load validated application configuration.

    Args:
        env_file: Path to the dotenv file.
        environment: Optional environment mapping used instead of `os.environ`.

    Returns:
        Validated runtime configuration.

    Raises:
        ConfigurationError: If the required GuestSage credentials are missing.
    """
    merged_environment = _merge_environment(_read_env_file(env_file), environment)
    login = (merged_environment.get("GUESTSAGE_LOGIN") or merged_environment.get("GUESTSAGE_EMAIL") or "").strip()
    password = merged_environment.get("GUESTSAGE_PASSWORD", "").strip()

    if not login:
        raise ConfigurationError("Missing required environment variable: GUESTSAGE_LOGIN")
    if not password:
        raise ConfigurationError("Missing required environment variable: GUESTSAGE_PASSWORD")

    return Config(login=login, password=password)

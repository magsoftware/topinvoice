from __future__ import annotations

from pathlib import Path

import pytest

from topinvoice.config import _merge_environment, _read_env_file, load_config
from topinvoice.errors import ConfigurationError


def test_read_env_file_parses_supported_lines(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join(
            (
                "# comment",
                "GUESTSAGE_LOGIN='file-login@example.com'",
                'GUESTSAGE_PASSWORD="file-secret"',
                "BROKEN_LINE",
            ),
        ),
        encoding="utf-8",
    )

    assert _read_env_file(env_file) == {
        "GUESTSAGE_LOGIN": "file-login@example.com",
        "GUESTSAGE_PASSWORD": "file-secret",
    }


def test_read_env_file_preserves_empty_string_values(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("GUESTSAGE_LOGIN=\nGUESTSAGE_PASSWORD=file-secret\n", encoding="utf-8")

    assert _read_env_file(env_file) == {
        "GUESTSAGE_LOGIN": "",
        "GUESTSAGE_PASSWORD": "file-secret",
    }


def test_read_env_file_returns_empty_mapping_for_missing_file(tmp_path: Path) -> None:
    assert _read_env_file(tmp_path / "missing.env") == {}


def test_merge_environment_prefers_environment_values() -> None:
    merged = _merge_environment({"GUESTSAGE_LOGIN": "from-file"}, {"GUESTSAGE_LOGIN": "from-env"})

    assert merged["GUESTSAGE_LOGIN"] == "from-env"


def test_load_config_uses_file_values(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "GUESTSAGE_LOGIN=file-login@example.com\nGUESTSAGE_PASSWORD=file-secret\n",
        encoding="utf-8",
    )

    config = load_config(env_file, {})

    assert config.login == "file-login@example.com"
    assert config.password == "file-secret"


def test_load_config_falls_back_to_email_key(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("GUESTSAGE_EMAIL=file-login@example.com\nGUESTSAGE_PASSWORD=file-secret\n", encoding="utf-8")

    config = load_config(env_file, {})

    assert config.login == "file-login@example.com"


def test_load_config_rejects_missing_login(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("GUESTSAGE_PASSWORD=file-secret\n", encoding="utf-8")

    with pytest.raises(ConfigurationError, match="GUESTSAGE_LOGIN"):
        load_config(env_file, {})


def test_load_config_rejects_missing_password(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("GUESTSAGE_LOGIN=file-login@example.com\n", encoding="utf-8")

    with pytest.raises(ConfigurationError, match="GUESTSAGE_PASSWORD"):
        load_config(env_file, {})

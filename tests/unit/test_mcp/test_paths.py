"""Tests for shared runtime path helpers."""

import os
from pathlib import Path

from benedict.paths import find_repo_root, get_data_dir, get_env_file, load_runtime_env


def test_get_data_dir_uses_env(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("BENEDICT_DATA_DIR", str(tmp_path))
    assert get_data_dir() == tmp_path.resolve()


def test_get_env_file_uses_env(tmp_path: Path, monkeypatch):
    env_file = tmp_path / "custom.env"
    monkeypatch.setenv("BENEDICT_ENV_FILE", str(env_file))
    assert get_env_file() == env_file.resolve()


def test_find_repo_root_finds_pyproject():
    root = find_repo_root()
    assert (root / "pyproject.toml").exists()


def test_load_runtime_env_fills_notion_key_when_slack_tokens_already_set(
    tmp_path: Path, monkeypatch
):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "NOTION_API_KEY=secret_from_file\nSLACK_BOT_TOKEN=from_file\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("BENEDICT_ENV_FILE", str(env_file))
    monkeypatch.setenv("SLACK_BOT_TOKEN", "from_process")
    monkeypatch.delenv("NOTION_API_KEY", raising=False)

    loaded = load_runtime_env()

    assert loaded == env_file.resolve()
    assert os.environ["NOTION_API_KEY"] == "secret_from_file"
    assert os.environ["SLACK_BOT_TOKEN"] == "from_process"


def test_load_runtime_env_missing_file_is_a_noop(tmp_path: Path, monkeypatch):
    missing = tmp_path / "does-not-exist.env"
    monkeypatch.setenv("BENEDICT_ENV_FILE", str(missing))
    monkeypatch.delenv("NOTION_API_KEY", raising=False)

    loaded = load_runtime_env()

    assert loaded == missing.resolve()
    assert "NOTION_API_KEY" not in os.environ

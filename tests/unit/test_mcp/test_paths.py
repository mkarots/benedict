"""Tests for shared runtime path helpers."""

import os
from pathlib import Path

from benedict.paths import (
    DEFAULT_DATA_DIR_NAME,
    default_data_dir,
    find_repo_root,
    get_data_dir,
    get_env_file,
    load_runtime_env,
)


def test_get_data_dir_uses_env(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("BENEDICT_DATA_DIR", str(tmp_path))
    assert get_data_dir() == tmp_path.resolve()
    assert tmp_path.is_dir()


def test_get_data_dir_defaults_to_home_benedict(tmp_path: Path, monkeypatch):
    monkeypatch.delenv("BENEDICT_DATA_DIR", raising=False)
    monkeypatch.setattr("benedict.paths.Path.home", lambda: tmp_path)
    expected = tmp_path / DEFAULT_DATA_DIR_NAME
    assert get_data_dir() == expected
    assert expected.is_dir()
    assert default_data_dir() == expected


def test_get_env_file_uses_env(tmp_path: Path, monkeypatch):
    env_file = tmp_path / "custom.env"
    monkeypatch.setenv("BENEDICT_ENV_FILE", str(env_file))
    assert get_env_file() == env_file.resolve()


def test_get_env_file_still_defaults_to_repo_root():
    assert get_env_file().name == ".env"
    assert (get_env_file().parent / "pyproject.toml").exists()


def test_find_repo_root_finds_pyproject():
    root = find_repo_root()
    assert (root / "pyproject.toml").exists()


def test_load_runtime_env_fills_missing_keys_when_slack_tokens_set(tmp_path: Path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text("NOTION_API_KEY=from-file\nSLACK_BOT_TOKEN=from-file\n", encoding="utf-8")
    monkeypatch.setenv("BENEDICT_ENV_FILE", str(env_file))
    monkeypatch.setenv("SLACK_BOT_TOKEN", "already-set")
    monkeypatch.delenv("NOTION_API_KEY", raising=False)

    path = load_runtime_env()
    assert path == env_file.resolve()
    assert os.environ["NOTION_API_KEY"] == "from-file"
    assert os.environ["SLACK_BOT_TOKEN"] == "already-set"


def test_load_runtime_env_does_not_override_process_env(tmp_path: Path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text("NOTION_API_KEY=from-file\n", encoding="utf-8")
    monkeypatch.setenv("BENEDICT_ENV_FILE", str(env_file))
    monkeypatch.setenv("NOTION_API_KEY", "from-process")

    load_runtime_env()
    assert os.environ["NOTION_API_KEY"] == "from-process"

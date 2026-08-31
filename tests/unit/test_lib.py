"""src/benedict/lib is tracked and its helpers behave as callers expect."""

import logging
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from benedict.lib.dateutil import normalize_to_utc
from benedict.lib.logging import get_logger, setup_logging

REPO_ROOT = Path(__file__).resolve().parents[2]
LIB_DIR = REPO_ROOT / "src" / "benedict" / "lib"
LIB_PY_FILES = ("__init__.py", "logging.py", "dateutil.py")


@pytest.fixture
def restore_root_logging():
    root = logging.getLogger()
    handlers = list(root.handlers)
    level = root.level
    yield
    root.handlers.clear()
    for handler in handlers:
        root.addHandler(handler)
    root.setLevel(level)


def test_gitignore_does_not_ignore_benedict_lib():
    gitignore = (REPO_ROOT / ".gitignore").read_text(encoding="utf-8")
    rules = [
        line.strip()
        for line in gitignore.splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    assert "/lib/" in rules
    assert "lib/" not in rules

    for name in LIB_PY_FILES:
        relative = f"src/benedict/lib/{name}"
        result = subprocess.run(
            ["git", "check-ignore", "-v", relative],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 1, (
            f"{relative} must not be ignored; check-ignore said: "
            f"{result.stdout.strip() or result.stderr.strip() or result.returncode}"
        )


def test_benedict_lib_python_files_are_tracked():
    listed = subprocess.run(
        ["git", "ls-files", "--", "src/benedict/lib"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.splitlines()
    tracked = {Path(path).name for path in listed}
    missing = [name for name in LIB_PY_FILES if name not in tracked]
    assert missing == [], f"src/benedict/lib files missing from git: {missing}"


def test_lib_package_files_exist_on_disk():
    missing = [name for name in LIB_PY_FILES if not (LIB_DIR / name).is_file()]
    assert missing == [], f"missing lib modules: {missing}"


def test_normalize_to_utc_treats_naive_datetime_as_utc():
    naive = datetime(2026, 8, 31, 12, 0, 0)
    result = normalize_to_utc(naive)
    assert result.tzinfo == timezone.utc
    assert result.replace(tzinfo=None) == naive


def test_normalize_to_utc_converts_aware_datetime():
    offset = timezone(timedelta(hours=5))
    aware = datetime(2026, 8, 31, 12, 0, 0, tzinfo=offset)
    result = normalize_to_utc(aware)
    assert result.tzinfo == timezone.utc
    assert result == datetime(2026, 8, 31, 7, 0, 0, tzinfo=timezone.utc)


def test_normalize_to_utc_leaves_utc_datetime_in_utc():
    utc = datetime(2026, 8, 31, 12, 0, 0, tzinfo=timezone.utc)
    result = normalize_to_utc(utc)
    assert result == utc
    assert result.tzinfo == timezone.utc


def test_get_logger_returns_named_logger(restore_root_logging):
    logger = get_logger("benedict.test.lib.logger")
    assert logger.name == "benedict.test.lib.logger"
    assert isinstance(logger, logging.Logger)


def test_setup_logging_defaults_to_info_without_debug_env(monkeypatch, restore_root_logging):
    monkeypatch.delenv("DEBUG", raising=False)
    setup_logging()
    assert logging.getLogger().level == logging.INFO
    assert logging.getLogger().handlers


def test_setup_logging_uses_debug_when_env_set(monkeypatch, restore_root_logging):
    monkeypatch.setenv("DEBUG", "1")
    setup_logging()
    assert logging.getLogger().level == logging.DEBUG


def test_setup_logging_falls_back_without_rich(monkeypatch, restore_root_logging):
    monkeypatch.setattr("benedict.lib.logging.RICH_AVAILABLE", False)
    monkeypatch.delenv("DEBUG", raising=False)
    setup_logging()
    handlers = logging.getLogger().handlers
    assert handlers
    assert all(type(handler).__name__ != "RichHandler" for handler in handlers)


def test_get_logger_configures_root_when_unconfigured(restore_root_logging):
    root = logging.getLogger()
    root.handlers.clear()
    get_logger("benedict.test.lib.unconfigured")
    assert root.handlers

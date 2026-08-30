"""Pre-commit hooks exist and match the pinned Black and Ruff in the `dev` extra."""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest
import yaml

if sys.version_info >= (3, 11):
    import tomllib
else:
    tomllib = pytest.importorskip("tomli")

REPO_ROOT = Path(__file__).resolve().parents[2]
CONFIG = REPO_ROOT / ".pre-commit-config.yaml"
PYPROJECT = REPO_ROOT / "pyproject.toml"

REQUIRED_HOOK_IDS = (
    "black",
    "ruff",
    "trailing-whitespace",
    "end-of-file-fixer",
)


def _config() -> dict:
    return yaml.safe_load(CONFIG.read_text(encoding="utf-8"))


def _dev_extra() -> list[str]:
    with PYPROJECT.open("rb") as handle:
        extras = tomllib.load(handle)["project"]["optional-dependencies"]["dev"]
    return extras


def _pinned_extra(name: str) -> str:
    prefix = f"{name}=="
    for spec in _dev_extra():
        if spec.startswith(prefix):
            return spec[len(prefix) :]
    raise AssertionError(f"{name}== is not pinned in the dev extra")


def _hook_ids_and_revs() -> dict[str, str]:
    found: dict[str, str] = {}
    for repo in _config().get("repos") or []:
        rev = repo.get("rev") or ""
        for hook in repo.get("hooks") or []:
            hook_id = hook.get("id")
            if hook_id:
                found[hook_id] = rev
    return found


def test_pre_commit_config_exists():
    assert CONFIG.is_file(), ".pre-commit-config.yaml is missing from the repository root"


def test_pre_commit_config_has_required_hooks():
    found = _hook_ids_and_revs()
    missing = [hook_id for hook_id in REQUIRED_HOOK_IDS if hook_id not in found]
    assert missing == [], f".pre-commit-config.yaml is missing hooks: {missing}"


def test_black_and_ruff_hook_versions_match_dev_extra():
    found = _hook_ids_and_revs()
    black_pin = _pinned_extra("black")
    ruff_pin = _pinned_extra("ruff")
    assert (
        found["black"] == black_pin
    ), f"black hook rev {found['black']!r} must match dev extra black=={black_pin}"
    assert found["ruff"] in {
        ruff_pin,
        f"v{ruff_pin}",
    }, f"ruff hook rev {found['ruff']!r} must match dev extra ruff=={ruff_pin}"


def test_dev_extra_includes_pre_commit():
    extras = _dev_extra()
    assert any(re.match(r"pre-commit([=<>]|$)", spec) for spec in extras), (
        "pre-commit must be in the pyproject.toml dev extra so `make sync-dev` "
        "then `pre-commit install` works"
    )

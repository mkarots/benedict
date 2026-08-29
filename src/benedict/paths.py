"""Runtime path helpers shared by the Slack bot and the MCP server."""

import os
from pathlib import Path

DEFAULT_DATA_DIR_NAME = ".benedict"


def find_repo_root() -> Path:
    """Find repository root by looking for common markers.

    Returns:
        Path to repository root, or current working directory if not found.
    """
    current = Path(__file__).parent
    for parent in [current] + list(current.parents):
        if any(
            (parent / marker).exists() for marker in [".git", "pyproject.toml", "setup.py", ".env"]
        ):
            return parent
    return Path.cwd()


def default_data_dir() -> Path:
    """Default data directory: ~/.benedict (not the git checkout)."""
    return Path.home() / DEFAULT_DATA_DIR_NAME


def get_data_dir() -> Path:
    """Get data directory from BENEDICT_DATA_DIR or ~/.benedict.

    Creates the directory if it does not exist. Slack and MCP must share this
    path. .env still comes from get_env_file() (repo root unless overridden).
    """
    data_dir = os.environ.get("BENEDICT_DATA_DIR")
    path = Path(data_dir).resolve() if data_dir else default_data_dir()
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_env_file() -> Path:
    """Get .env file path from BENEDICT_ENV_FILE or the repo root."""
    env_file = os.environ.get("BENEDICT_ENV_FILE")
    if env_file:
        return Path(env_file).resolve()
    return find_repo_root() / ".env"

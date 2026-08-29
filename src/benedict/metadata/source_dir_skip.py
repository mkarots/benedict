"""Skip rules for walking a source tree. Only inspect paths under the repo root."""

from pathlib import Path

SKIP_DIRECTORY_NAMES = frozenset(
    {
        "venv",
        ".venv",
        "env",
        ".env",
        "ENV",
        "virtualenv",
        "build-env",
        "env-build",
        "__pycache__",
        ".mypy_cache",
        ".pytest_cache",
        "node_modules",
        ".git",
        ".hg",
        ".svn",
        "build",
        "dist",
        ".tox",
        ".coverage",
        "htmlcov",
        ".eggs",
        ".idea",
        ".vscode",
        ".DS_Store",
        "site-packages",
    }
)


def should_skip_source_directory(directory: Path, repo_root: Path) -> bool:
    """True if directory is outside the repo or is a skipped child of it.

    Parents above ``repo_root`` are ignored. A data dir named ``.benedict``
    must not suppress overlay generation for every workspace under it.
    """
    directory = Path(directory).resolve()
    repo_root = Path(repo_root).resolve()
    try:
        rel = directory.relative_to(repo_root)
    except ValueError:
        return True
    parts = () if rel == Path(".") else rel.parts
    for part in parts:
        if part.startswith("."):
            return True
        if part in SKIP_DIRECTORY_NAMES:
            return True
        if part.endswith(".egg-info") or part.endswith(".dist-info"):
            return True
    return False

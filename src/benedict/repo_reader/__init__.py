"""Repository reader protocol and implementations."""

from .protocol import RepoReader
from .repo_reader_local import LocalRepoReader
from .repo_reader_mock import MockRepoReader

__all__ = ["RepoReader", "LocalRepoReader", "MockRepoReader", "create_repo_reader"]


def create_repo_reader(source: str = "local") -> RepoReader:
    """Factory function to create RepoReader instance.

    Args:
        source: Source type ("local" or "mock")

    Returns:
        RepoReader instance

    Raises:
        ValueError: If source is unknown
    """
    if source == "local":
        return LocalRepoReader()
    if source == "mock":
        return MockRepoReader()
    raise ValueError(f"Unknown source: {source}")

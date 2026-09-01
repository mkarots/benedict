"""RepoReader Protocol Definition

Defines the interface for repository file readers.
"""

from typing import Protocol, List


class RepoReader(Protocol):
    """Protocol for repository file readers."""

    def read_file(self, repo: str, path: str) -> str:
        """Read single file content from repository.

        Args:
            repo: Repository identifier/name
            path: File path relative to repository root

        Returns:
            File content as string

        Raises:
            FileNotFoundError: If file doesn't exist
        """
        ...

    def list_files(self, repo: str, path: str = "") -> List[str]:
        """List files in repository directory.

        Args:
            repo: Repository identifier/name
            path: Directory path relative to repository root (empty = root)

        Returns:
            List of file paths relative to the specified path
        """
        ...

    def file_exists(self, repo: str, path: str) -> bool:
        """Check if file exists in repository.

        Args:
            repo: Repository identifier/name
            path: File path relative to repository root

        Returns:
            True if file exists, False otherwise
        """
        ...

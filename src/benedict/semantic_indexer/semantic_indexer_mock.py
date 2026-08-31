"""Mock Semantic Indexer Implementation

Mock semantic indexer for testing purposes.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from benedict.protocols.repo_reader import RepoReader

logger = logging.getLogger(__name__)


class MockSemanticIndexer:
    """Mock semantic indexer that simulates semantic search."""

    def __init__(self) -> None:
        """Initialize mock semantic indexer."""
        self.indexed_repos: set[str] = set()
        self._relevant_files: List[Dict[str, Any]] = []
        logger.info("Initialized MockSemanticIndexer")

    def add_relevant_file(
        self, file_path: str, score: float = 0.9, content: Optional[str] = None
    ) -> None:
        """Pre-populate a search hit (test helper)."""
        self._relevant_files.append(
            {
                "file_path": file_path,
                "content": content if content is not None else f"[Mock content for {file_path}]",
                "score": score,
            }
        )

    def index_repository(
        self, repo: str, repo_reader: RepoReader, workspace_path: Any = None, force: bool = False
    ) -> None:
        """Mock repository indexing.

        Args:
            repo: Repository identifier
            repo_reader: RepoReader instance (ignored)
        """
        self.indexed_repos.add(repo)
        logger.debug(f"Mock indexed repository {repo}")

    def update_index(
        self,
        repo: str,
        repo_reader: RepoReader,
        workspace_path: Any = None,
        since: Optional[datetime] = None,
    ) -> None:
        """Mock incremental update."""
        self.index_repository(repo, repo_reader, workspace_path=workspace_path)

    def search(
        self,
        repo: str,
        query: str,
        top_k: int = 5,
        workspace_path: Any = None,
        metadata_reader: Any = None,
    ) -> List[Dict[str, Any]]:
        """Mock semantic search.

        Args:
            repo: Repository identifier
            query: Search query
            top_k: Number of results

        Returns:
            Mock results
        """
        if self._relevant_files:
            return self._relevant_files[:top_k]

        if repo not in self.indexed_repos:
            return []

        # Return mock results based on query keywords
        keywords = query.lower().split()
        mock_files = [f"file_{kw}.py" for kw in keywords[:top_k] if len(kw) > 3]

        results = []
        for i, file_path in enumerate(mock_files[:top_k]):
            results.append(
                {
                    "file_path": file_path,
                    "content": f"[Mock content for {file_path} related to: {query}]",
                    "score": 0.9 - (i * 0.1),
                }
            )

        return results

    def is_indexed(self, repo: str) -> bool:
        """Check if repository is indexed.

        Args:
            repo: Repository identifier

        Returns:
            True if mock-indexed
        """
        return repo in self.indexed_repos

"""Semantic Indexer Protocol

Defines interface for semantic code search and indexing.
"""

from datetime import datetime
from typing import Any, List, Optional, Protocol

from benedict.semantic_indexer.search_hit import SearchHit


class SemanticIndexer(Protocol):
    """Protocol for semantic code indexing and search."""

    def index_repository(
        self, repo: str, repo_reader: Any, workspace_path: Any = None, force: bool = False
    ) -> None:
        """Index a repository for semantic search.

        Args:
            repo: Repository identifier
            repo_reader: RepoReader instance to read files
            workspace_path: Optional workspace path for generating metadata overlays
            force: If True, reindex even if already indexed (default: False, incremental update)
        """
        ...

    def update_index(
        self,
        repo: str,
        repo_reader: Any,
        workspace_path: Any = None,
        since: Optional[datetime] = None,
    ) -> None:
        """Incrementally update index with new/changed content.

        Args:
            repo: Repository identifier
            repo_reader: RepoReader instance to read files
            workspace_path: Optional workspace path for generating metadata overlays
            since: Optional datetime to only index files modified since this time
        """
        ...

    def search(
        self,
        repo: str,
        query: str,
        top_k: int = 5,
        workspace_path: Any = None,
        metadata_reader: Any = None,
    ) -> List[SearchHit]:
        """Search repository using semantic similarity.

        Args:
            repo: Repository identifier
            query: Search query/question
            top_k: Number of results to return

        Returns:
            Ranked search hits
        """
        ...

    def is_indexed(self, repo: str) -> bool:
        """Check if repository is indexed.

        Args:
            repo: Repository identifier

        Returns:
            True if repository is indexed
        """
        ...

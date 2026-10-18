"""Semantic indexer protocol and implementations."""

from typing import Any, Optional

from .protocol import SemanticIndexer
from .search_hit import SearchHit
from .semantic_indexer_mock import MockSemanticIndexer

__all__ = [
    "SemanticIndexer",
    "SearchHit",
    "MockSemanticIndexer",
    "create_semantic_indexer",
]


def create_semantic_indexer(
    provider: str = "chromadb",
    persist_directory: Optional[str] = None,
    metadata_generator: Any = None,
    change_detector: Any = None,
    client: Any = None,
) -> SemanticIndexer:
    """Factory function to create SemanticIndexer instance.

    Args:
        provider: Provider name ("chromadb" or "mock")
        persist_directory: Optional directory path for ChromaDB persistence
        metadata_generator: Optional metadata generator for creating METADATA overlays
        change_detector: Optional change detector for git-based incremental updates
        client: Shared Chroma client. When omitted, one is created from persist_directory.

    Returns:
        SemanticIndexer instance

    Raises:
        ValueError: If provider is unknown
    """
    if provider == "chromadb":
        from .semantic_indexer_chromadb import ChromaDBSemanticIndexer

        kwargs: dict = {
            "metadata_generator": metadata_generator,
            "change_detector": change_detector,
            "client": client,
        }
        if persist_directory:
            kwargs["persist_directory"] = persist_directory
        return ChromaDBSemanticIndexer(**kwargs)
    if provider == "mock":
        return MockSemanticIndexer()
    raise ValueError(f"Unknown provider: {provider}")

"""Chroma access for Benedict.

One PersistentClient per process (one directory / one database). Code and
conversation history are separate collections inside that database.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Union

PathLike = Union[str, Path]


def code_collection_name(repo: str) -> str:
    """Collection name for one repository's code chunks."""
    return f"repo_{hashlib.md5(repo.encode()).hexdigest()[:16]}"


def conversation_collection_name(context_id: str) -> str:
    """Collection name for one conversation context."""
    return f"conversation_{hashlib.md5(context_id.encode()).hexdigest()[:16]}"


def create_chroma_client(persist_directory: PathLike) -> Any:
    """Open (or create) the single Chroma database at ``persist_directory``."""
    import chromadb
    from chromadb.config import Settings

    path = Path(persist_directory)
    path.mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(path=str(path), settings=Settings(anonymized_telemetry=False))

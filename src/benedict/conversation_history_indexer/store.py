"""Conversation-history collections on the shared Chroma client.

Slack (or any other surface) is only an ingest adapter. Code chunks use
``repo_*`` collections; this store uses ``conversation_*`` on the same client.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from benedict.lib.chroma import conversation_collection_name, create_chroma_client

logger = logging.getLogger(__name__)

DEFAULT_EMBEDDING_MODEL = "all-MiniLM-L6-v2"


def _embedding_as_list(query_embedding: Any) -> List[float]:
    """Accept numpy arrays from MiniLM and plain lists in tests."""
    values = query_embedding.tolist() if hasattr(query_embedding, "tolist") else query_embedding
    return [float(value) for value in values]


def _embeddings_as_matrix(embeddings: Any) -> List[List[float]]:
    if hasattr(embeddings, "tolist"):
        return embeddings.tolist()
    return [_embedding_as_list(row) for row in embeddings]


def format_conversation_hits(results: Dict[str, Any], context_id: str) -> List[Dict[str, Any]]:
    """Turn a Chroma query payload into conversation retrieval hits."""
    documents = (results.get("documents") or [[]])[0] or []
    metadatas = (results.get("metadatas") or [[]])[0] or []
    distances = (results.get("distances") or [[]])[0] or []
    formatted: List[Dict[str, Any]] = []
    for i, doc in enumerate(documents):
        metadata = metadatas[i] if i < len(metadatas) and metadatas[i] else {}
        distance = distances[i] if i < len(distances) else 0.0
        score = 1.0 / (1.0 + float(distance))
        message_ts = str(metadata.get("message_ts") or "")
        formatted.append(
            {
                "file_path": f"conversation:{context_id}:{message_ts}",
                "content": doc,
                "score": score,
                "channel_id": metadata.get("channel_id") or context_id,
                "context_id": metadata.get("context_id") or context_id,
                "message_ts": message_ts,
                "user": metadata.get("user"),
                "type": metadata.get("type") or "message",
                "thread_ts": metadata.get("thread_ts"),
            }
        )
    return formatted


class ConversationHistoryStore:
    """Chroma + local embeddings for conversation messages."""

    def __init__(
        self,
        persist_directory: Optional[str] = None,
        embedding_model: Any = None,
        client: Any = None,
    ) -> None:
        self.persist_directory = Path(persist_directory) if persist_directory else None
        self._embedding_model = embedding_model
        self._client = client
        if self.persist_directory is not None:
            self.persist_directory.mkdir(parents=True, exist_ok=True)

    @property
    def available(self) -> bool:
        return self._client is not None or self.persist_directory is not None

    def _client_or_none(self) -> Any:
        if self._client is not None:
            return self._client
        if self.persist_directory is None:
            return None
        self._client = create_chroma_client(self.persist_directory)
        return self._client

    def _model(self) -> Any:
        if self._embedding_model is None:
            from sentence_transformers import SentenceTransformer

            self._embedding_model = SentenceTransformer(DEFAULT_EMBEDDING_MODEL)
            logger.info("Loaded conversation embedding model: %s", DEFAULT_EMBEDDING_MODEL)
        return self._embedding_model

    def document_count(self, context_id: str) -> int:
        collection = self._get_collection(context_id, create=False)
        if collection is None:
            return 0
        try:
            return int(collection.count())
        except Exception:
            return 0

    def search(self, context_id: str, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        if not context_id or not str(query).strip():
            return []
        collection = self._get_collection(context_id, create=False)
        if collection is None:
            return []
        try:
            count = collection.count()
        except Exception:
            return []
        if count == 0:
            return []
        query_embedding = self._model().encode([str(query).strip()])[0]
        n_results = min(top_k, count)
        results = collection.query(
            query_embeddings=[_embedding_as_list(query_embedding)], n_results=n_results
        )
        return format_conversation_hits(results, context_id)

    def add_messages(
        self,
        context_id: str,
        messages: List[Dict[str, Any]],
        threads: Optional[Dict[str, List[Dict[str, Any]]]] = None,
    ) -> None:
        if not self.available or not context_id:
            return
        documents, metadatas, ids = _documents_from_messages(context_id, messages, threads or {})
        if not documents:
            logger.debug("No conversation documents to index for %s", context_id)
            return
        collection = self._get_collection(context_id, create=True)
        if collection is None:
            return
        logger.info(
            "Indexing %s conversation messages for context %s",
            len(documents),
            context_id,
        )
        embeddings = self._model().encode(documents, show_progress_bar=False)
        matrix = _embeddings_as_matrix(embeddings)
        batch_size = 5000
        total_batches = (len(documents) + batch_size - 1) // batch_size
        for batch_idx in range(total_batches):
            start_idx = batch_idx * batch_size
            end_idx = min(start_idx + batch_size, len(documents))
            collection.add(
                embeddings=matrix[start_idx:end_idx],
                documents=documents[start_idx:end_idx],
                metadatas=metadatas[start_idx:end_idx],
                ids=ids[start_idx:end_idx],
            )
        logger.info(
            "Indexed %s conversation messages for context %s",
            len(documents),
            context_id,
        )

    def _get_collection(self, context_id: str, *, create: bool) -> Any:
        client = self._client_or_none()
        if client is None:
            return None
        name = conversation_collection_name(context_id)
        try:
            return client.get_collection(name)
        except Exception:
            if not create:
                return None
            return client.create_collection(
                name=name,
                metadata={"context_id": context_id, "type": "conversation_history"},
            )


def _documents_from_messages(
    context_id: str,
    messages: List[Dict[str, Any]],
    threads: Dict[str, List[Dict[str, Any]]],
) -> tuple[List[str], List[Dict[str, Any]], List[str]]:
    documents: List[str] = []
    metadatas: List[Dict[str, Any]] = []
    ids: List[str] = []

    for msg in messages:
        text = msg.get("text", "")
        if not text:
            continue
        msg_ts = msg.get("ts", "")
        documents.append(text)
        metadata: Dict[str, Any] = {
            "context_id": context_id,
            "channel_id": context_id,
            "message_ts": msg_ts,
            "type": "message",
        }
        if msg.get("thread_ts"):
            metadata["thread_ts"] = msg.get("thread_ts")
        if msg.get("user"):
            metadata["user"] = msg.get("user")
        metadatas.append(metadata)
        ids.append(f"{context_id}:{msg_ts}")

    for thread_ts, thread_messages in threads.items():
        for msg in thread_messages:
            text = msg.get("text", "")
            if not text:
                continue
            msg_ts = msg.get("ts", "")
            documents.append(text)
            metadata = {
                "context_id": context_id,
                "channel_id": context_id,
                "message_ts": msg_ts,
                "thread_ts": thread_ts,
                "type": "thread_reply",
            }
            if msg.get("user"):
                metadata["user"] = msg.get("user")
            metadatas.append(metadata)
            ids.append(f"{context_id}:{msg_ts}:thread")

    return documents, metadatas, ids

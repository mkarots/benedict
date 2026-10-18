"""Conversation history indexer protocol and implementations."""

from typing import Any, Optional

from .protocol import ConversationHistoryIndexer, ConversationReader
from .slack_history_indexer import (
    MockConversationHistoryIndexer,
    SlackConversationHistoryIndexer,
)
from .store import (
    ConversationHistoryStore,
    conversation_collection_name,
    format_conversation_hits,
)

__all__ = [
    "ConversationHistoryIndexer",
    "ConversationHistoryStore",
    "ConversationReader",
    "SlackConversationHistoryIndexer",
    "MockConversationHistoryIndexer",
    "format_conversation_hits",
    "conversation_collection_name",
    "create_conversation_history_indexer",
]


def create_conversation_history_indexer(
    platform: str = "slack",
    slack_client: Any = None,
    persist_directory: Optional[str] = None,
    embedding_model: Any = None,
    store: Any = None,
    client: Any = None,
) -> ConversationHistoryIndexer:
    """Factory function to create ConversationHistoryIndexer instance.

    Args:
        platform: Platform name ("slack", "discord", "mock", etc.)
        slack_client: Optional Slack client for Slack platform
        persist_directory: Fallback Chroma path when ``client`` is omitted
        embedding_model: Optional embedder; production lazy-loads MiniLM
        store: Optional ConversationHistoryStore (tests)
        client: Shared Chroma client from the composition root

    Returns:
        ConversationHistoryIndexer instance

    Raises:
        ValueError: If platform is unknown
    """
    if platform == "slack":
        return SlackConversationHistoryIndexer(
            slack_client=slack_client,
            persist_directory=persist_directory,
            embedding_model=embedding_model,
            store=store,
            client=client,
        )
    if platform == "mock":
        return MockConversationHistoryIndexer()
    raise ValueError(f"Unknown platform: {platform}")

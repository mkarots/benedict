"""Conversation history indexer protocol and implementations."""

from typing import Any

from .protocol import ConversationHistoryIndexer, ConversationReader
from .slack_history_indexer import (
    MockConversationHistoryIndexer,
    SlackConversationHistoryIndexer,
    format_slack_channel_hits,
    search_indexed_slack_channel,
    slack_channel_collection_name,
)

__all__ = [
    "ConversationHistoryIndexer",
    "ConversationReader",
    "SlackConversationHistoryIndexer",
    "MockConversationHistoryIndexer",
    "format_slack_channel_hits",
    "search_indexed_slack_channel",
    "slack_channel_collection_name",
    "create_conversation_history_indexer",
]


def create_conversation_history_indexer(
    platform: str = "slack", slack_client: Any = None
) -> ConversationHistoryIndexer:
    """Factory function to create ConversationHistoryIndexer instance.

    Args:
        platform: Platform name ("slack", "discord", "mock", etc.)
        slack_client: Optional Slack client for Slack platform

    Returns:
        ConversationHistoryIndexer instance

    Raises:
        ValueError: If platform is unknown
    """
    if platform == "slack":
        return SlackConversationHistoryIndexer(slack_client=slack_client)
    if platform == "mock":
        return MockConversationHistoryIndexer()
    raise ValueError(f"Unknown platform: {platform}")

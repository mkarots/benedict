"""Conversation repository implementations."""

from ..protocols.conversation_repository import ConversationRepository
from .conversation_repository_json import JsonConversationRepository
from .conversation_repository_mock import MockConversationRepository

JSONConversationRepository = JsonConversationRepository

__all__ = [
    "ConversationRepository",
    "JsonConversationRepository",
    "JSONConversationRepository",
    "MockConversationRepository",
]

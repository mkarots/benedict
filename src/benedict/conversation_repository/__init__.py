"""Conversation repository protocol and implementations."""

from .conversation_repository_json import JsonConversationRepository
from .conversation_repository_mock import MockConversationRepository
from .protocol import ConversationRepository

JSONConversationRepository = JsonConversationRepository

__all__ = [
    "ConversationRepository",
    "JsonConversationRepository",
    "JSONConversationRepository",
    "MockConversationRepository",
    "create_conversation_repository",
]


def create_conversation_repository(
    provider: str = "json", state_file: str = "state.json"
) -> ConversationRepository:
    """Factory function to create ConversationRepository instance.

    Args:
        provider: Provider name ("json" or "mock")
        state_file: Path to state file (for JSON provider)

    Returns:
        ConversationRepository instance

    Raises:
        ValueError: If provider is unknown
    """
    if provider == "json":
        return JsonConversationRepository(state_file=state_file)
    if provider == "mock":
        return MockConversationRepository()
    raise ValueError(f"Unknown provider: {provider}")

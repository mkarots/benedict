"""Conversation Repository Protocol

Defines interface for conversation persistence.
"""

from typing import Protocol, Dict, Optional
from benedict.models.conversation import Conversation


class ConversationRepository(Protocol):
    """Protocol for conversation persistence."""

    def find_by_thread_ts(self, thread_ts: str) -> Optional[Conversation]:
        """Find conversation by thread timestamp.

        Args:
            thread_ts: Thread timestamp identifier

        Returns:
            Conversation if found, None otherwise
        """
        ...

    def find_all(self) -> Dict[str, Conversation]:
        """Find all conversations.

        Returns:
            Dict mapping thread_ts to Conversation
        """
        ...

    def save(self, conversation: Conversation) -> None:
        """Save or update conversation.

        Args:
            conversation: Conversation to save
        """
        ...

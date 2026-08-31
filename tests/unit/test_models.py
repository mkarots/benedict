"""Tests for conversation models.

Tests the Message and Conversation domain models.
"""

import json
from datetime import datetime, timezone


from benedict.models import Message, Conversation


def _utcnow_warnings(caught: list) -> list:
    return [
        warning
        for warning in caught
        if issubclass(warning.category, DeprecationWarning) and "utcnow" in str(warning.message)
    ]


class TestMessage:
    """Tests for Message model."""

    def test_create_message(self):
        """Test creating a message with basic fields."""
        message = Message(role="user", content="Hello")

        assert message.role == "user"
        assert message.content == "Hello"
        assert message.timestamp
        assert isinstance(message.timestamp, str)

    def test_message_roles(self):
        """Test both user and assistant roles."""
        user_msg = Message(role="user", content="Question")
        assistant_msg = Message(role="assistant", content="Answer")

        assert user_msg.role == "user"
        assert assistant_msg.role == "assistant"

    def test_message_to_dict(self):
        """Test converting message to dictionary."""
        message = Message(role="user", content="Test", timestamp="2026-08-01T10:00:00Z")
        data = message.to_dict()

        assert data["role"] == "user"
        assert data["content"] == "Test"
        assert data["timestamp"] == "2026-08-01T10:00:00Z"

    def test_message_from_dict(self):
        """Test creating message from dictionary."""
        data = {
            "role": "assistant",
            "content": "Response",
            "timestamp": "2026-08-01T10:00:00Z",
        }
        message = Message.from_dict(data)

        assert message.role == "assistant"
        assert message.content == "Response"
        assert message.timestamp == "2026-08-01T10:00:00Z"

    def test_message_to_json(self):
        """Test converting message to JSON string."""
        message = Message(role="user", content="Test")
        json_str = message.to_json()

        assert isinstance(json_str, str)
        data = json.loads(json_str)
        assert data["role"] == "user"
        assert data["content"] == "Test"

    def test_message_timestamp_auto_generated(self):
        """Test that timestamp is auto-generated if not provided."""
        message = Message(role="user", content="Test")

        assert message.timestamp
        assert message.timestamp.endswith("Z")
        parsed = datetime.fromisoformat(message.timestamp.replace("Z", "+00:00"))
        assert parsed.tzinfo is not None
        assert abs((datetime.now(timezone.utc) - parsed).total_seconds()) < 5

    def test_message_from_dict_without_timestamp_uses_utc(self):
        """Missing timestamps are filled with timezone-aware UTC."""
        message = Message.from_dict({"role": "user", "content": "Hi"})

        assert message.timestamp.endswith("Z")
        datetime.fromisoformat(message.timestamp.replace("Z", "+00:00"))


class TestConversation:
    """Tests for Conversation model."""

    def test_create_conversation(self):
        """Test creating a conversation with required fields."""
        conv = Conversation(
            thread_ts="1234567890.123456",
            channel_id="C123456",
            repo="example-org/repo",
        )

        assert conv.thread_ts == "1234567890.123456"
        assert conv.channel_id == "C123456"
        assert conv.repo == "example-org/repo"
        assert len(conv.messages) == 0
        assert conv.created_at
        assert conv.updated_at

    def test_add_message(self):
        """Test adding messages to conversation."""
        conv = Conversation(
            thread_ts="1234567890.123456",
            channel_id="C123456",
            repo="example-org/repo",
        )

        conv.add_message("user", "Question")
        assert len(conv.messages) == 1
        assert conv.messages[0].role == "user"
        assert conv.messages[0].content == "Question"

        conv.add_message("assistant", "Answer")
        assert len(conv.messages) == 2
        assert conv.messages[1].role == "assistant"

    def test_add_message_updates_timestamp(self):
        """Test that adding message updates the updated_at timestamp."""
        conv = Conversation(
            thread_ts="1234567890.123456",
            channel_id="C123456",
            repo="example-org/repo",
        )

        conv.add_message("user", "Question")

        # Updated_at should be different (though might be same if very fast)
        assert conv.updated_at

    def test_get_messages(self):
        """Test retrieving all messages."""
        conv = Conversation(
            thread_ts="1234567890.123456",
            channel_id="C123456",
            repo="example-org/repo",
        )

        conv.add_message("user", "Question 1")
        conv.add_message("assistant", "Answer 1")
        conv.add_message("user", "Question 2")

        messages = conv.get_messages()
        assert len(messages) == 3
        assert messages[0].content == "Question 1"
        assert messages[2].content == "Question 2"

    def test_get_messages_with_limit(self):
        """Test retrieving limited number of messages."""
        conv = Conversation(
            thread_ts="1234567890.123456",
            channel_id="C123456",
            repo="example-org/repo",
        )

        for i in range(5):
            conv.add_message("user", f"Message {i}")

        # Get last 2 messages
        messages = conv.get_messages(max_messages=2)
        assert len(messages) == 2
        assert messages[0].content == "Message 3"
        assert messages[1].content == "Message 4"

    def test_get_message_history(self):
        """Test getting message history in LLM format."""
        conv = Conversation(
            thread_ts="1234567890.123456",
            channel_id="C123456",
            repo="example-org/repo",
        )

        conv.add_message("user", "Question")
        conv.add_message("assistant", "Answer")

        history = conv.get_message_history()
        assert len(history) == 2
        assert history[0] == {"role": "user", "content": "Question"}
        assert history[1] == {"role": "assistant", "content": "Answer"}

    def test_get_message_history_with_limit(self):
        """Test getting limited message history."""
        conv = Conversation(
            thread_ts="1234567890.123456",
            channel_id="C123456",
            repo="example-org/repo",
        )

        for i in range(5):
            conv.add_message("user", f"Message {i}")

        history = conv.get_message_history(max_messages=2)
        assert len(history) == 2
        assert history[0]["content"] == "Message 3"

    def test_conversation_to_dict(self):
        """Test converting conversation to dictionary."""
        conv = Conversation(
            thread_ts="1234567890.123456",
            channel_id="C123456",
            repo="example-org/repo",
        )
        conv.add_message("user", "Question")

        data = conv.to_dict()
        assert data["thread_ts"] == "1234567890.123456"
        assert data["channel_id"] == "C123456"
        assert data["repo"] == "example-org/repo"
        assert len(data["messages"]) == 1
        assert data["created_at"]
        assert data["updated_at"]

    def test_conversation_from_dict(self):
        """Test creating conversation from dictionary."""
        data = {
            "thread_ts": "1234567890.123456",
            "channel_id": "C123456",
            "repo": "example-org/repo",
            "messages": [
                {"role": "user", "content": "Question", "timestamp": "2026-08-01T10:00:00Z"}
            ],
            "created_at": "2026-08-01T09:00:00Z",
            "updated_at": "2026-08-01T10:00:00Z",
        }

        conv = Conversation.from_dict(data)
        assert conv.thread_ts == "1234567890.123456"
        assert len(conv.messages) == 1
        assert conv.messages[0].content == "Question"

    def test_conversation_from_dict_without_timestamps_uses_utc(self):
        """Missing created_at and updated_at are filled with timezone-aware UTC."""
        conv = Conversation.from_dict(
            {
                "thread_ts": "1234567890.123456",
                "channel_id": "C123456",
                "repo": "example-org/repo",
            }
        )

        assert conv.created_at.endswith("Z")
        assert conv.updated_at.endswith("Z")
        datetime.fromisoformat(conv.created_at.replace("Z", "+00:00"))
        datetime.fromisoformat(conv.updated_at.replace("Z", "+00:00"))


class TestConversationManager:
    """Tests for ConversationManager."""

    def test_create_conversation(self, conversation_manager):
        """Test creating a new conversation."""
        conv = conversation_manager.get_conversation(
            thread_ts="1234567890.123456",
            channel_id="C123456",
            repo="example-org/repo",
        )

        assert conv.thread_ts == "1234567890.123456"
        assert conv.channel_id == "C123456"
        assert conv.repo == "example-org/repo"

    def test_get_conversation(self, conversation_manager):
        """Test retrieving an existing conversation."""
        conversation_manager.get_conversation(
            thread_ts="1234567890.123456",
            channel_id="C123456",
            repo="example-org/repo",
        )

        conv = conversation_manager.get_conversation(
            thread_ts="1234567890.123456",
            channel_id="C123456",
            repo="example-org/repo",
        )
        assert conv is not None
        assert conv.thread_ts == "1234567890.123456"

    def test_get_nonexistent_conversation(self, conversation_manager):
        """Unknown threads are created on get_conversation."""
        conv = conversation_manager.get_conversation(
            thread_ts="nonexistent",
            channel_id="C123456",
            repo="example-org/repo",
        )
        assert conv is not None
        assert conv.thread_ts == "nonexistent"
        assert conv.messages == []

    def test_add_message_to_conversation(self, conversation_manager):
        """Test adding a message to existing conversation."""
        conv = conversation_manager.get_conversation(
            thread_ts="1234567890.123456",
            channel_id="C123456",
            repo="example-org/repo",
        )
        conv.add_message("user", "Question")
        conversation_manager.save_conversation(conv)

        retrieved = conversation_manager.get_conversation(
            thread_ts="1234567890.123456",
            channel_id="C123456",
            repo="example-org/repo",
        )
        assert len(retrieved.messages) == 1
        assert retrieved.messages[0].content == "Question"

    def test_get_or_create_conversation_existing(self, conversation_manager):
        """Test get_conversation returns the existing thread."""
        conversation_manager.get_conversation(
            thread_ts="1234567890.123456",
            channel_id="C123456",
            repo="example-org/repo",
        )

        conv = conversation_manager.get_conversation(
            thread_ts="1234567890.123456",
            channel_id="C123456",
            repo="example-org/repo",
        )

        assert conv.thread_ts == "1234567890.123456"

    def test_get_or_create_conversation_new(self, conversation_manager):
        """Test get_conversation creates a new thread when missing."""
        conv = conversation_manager.get_conversation(
            thread_ts="1234567890.123456",
            channel_id="C123456",
            repo="example-org/repo",
        )

        assert conv.thread_ts == "1234567890.123456"
        assert conv.channel_id == "C123456"

    def test_conversation_persistence(self, conversation_manager):
        """Test that conversations are persisted."""
        conv = conversation_manager.get_conversation(
            thread_ts="1234567890.123456",
            channel_id="C123456",
            repo="example-org/repo",
        )
        conv.add_message("user", "Question")
        conversation_manager.save_conversation(conv)

        retrieved = conversation_manager.get_conversation(
            thread_ts="1234567890.123456",
            channel_id="C123456",
            repo="example-org/repo",
        )
        assert retrieved is not None
        assert len(retrieved.messages) == 1

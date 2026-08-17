"""Unit tests for conversation models and the in-memory repository."""

from benedict.conversation_repository.conversation_repository_json import (
    JsonConversationRepository,
)
from benedict.conversation_repository.conversation_repository_mock import (
    MockConversationRepository,
)
from benedict.models.conversation import Conversation, ConversationManager, Message


def test_message_and_conversation_roundtrip():
    conversation = Conversation(
        thread_ts="111.222",
        channel_id="C123",
        repo="example-org/example-repo",
    )
    conversation.add_message("user", "hello")
    conversation.add_message("assistant", "hi")

    restored = Conversation.from_dict(conversation.to_dict())
    assert restored.thread_ts == "111.222"
    assert restored.repo == "example-org/example-repo"
    assert [msg.content for msg in restored.messages] == ["hello", "hi"]
    assert restored.get_message_history() == [
        {"role": "user", "content": "hello"},
        {"role": "assistant", "content": "hi"},
    ]
    assert restored.get_messages(max_messages=1)[0].content == "hi"


def test_message_from_dict_defaults_timestamp():
    message = Message.from_dict({"role": "user", "content": "ping"})
    assert message.timestamp.endswith("Z")


def test_mock_repository_save_and_find():
    repo = MockConversationRepository()
    conversation = Conversation("111.222", "C123", "example-org/example-repo")
    repo.save(conversation)
    assert repo.find_by_thread_ts("111.222") is conversation
    assert repo.find_by_thread_ts("missing") is None
    assert "111.222" in repo.find_all()


def test_conversation_manager_creates_and_updates_repo():
    repository = MockConversationRepository()
    manager = ConversationManager(repository)
    first = manager.get_conversation("111.222", "C123", "example-org/example-repo")
    second = manager.get_conversation("111.222", "C123", "example-org/other-repo")
    assert first.thread_ts == second.thread_ts
    assert second.repo == "example-org/other-repo"


def test_json_repository_persists(tmp_path):
    path = tmp_path / "state.json"
    repository = JsonConversationRepository(str(path))
    conversation = Conversation("111.222", "C123", "example-org/example-repo")
    conversation.add_message("user", "hello")
    repository.save(conversation)

    loaded = JsonConversationRepository(str(path))
    found = loaded.find_by_thread_ts("111.222")
    assert found is not None
    assert found.messages[0].content == "hello"


def test_json_repository_handles_missing_and_corrupt(tmp_path):
    missing = JsonConversationRepository(str(tmp_path / "nope.json"))
    assert missing.find_all() == {}

    corrupt = tmp_path / "state.json"
    corrupt.write_text("{bad", encoding="utf-8")
    repository = JsonConversationRepository(str(corrupt))
    assert repository.find_all() == {}

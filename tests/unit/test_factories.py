"""Factories live on capability packages, not on protocol modules."""

import pytest

from benedict.conversation_history_indexer import (
    MockConversationHistoryIndexer,
    create_conversation_history_indexer,
)
from benedict.conversation_repository import (
    MockConversationRepository,
    create_conversation_repository,
)
from benedict.llm import MockLLM, create_llm
from benedict.repo_reader import MockRepoReader, create_repo_reader
from benedict.semantic_indexer import MockSemanticIndexer, create_semantic_indexer
from benedict.semantic_indexer.change_detector import (
    GitChangeDetector,
    create_repo_change_detector,
)


def test_create_llm_mock_and_unknown():
    llm = create_llm(provider="mock")
    assert isinstance(llm, MockLLM)
    with pytest.raises(ValueError, match="Unknown provider"):
        create_llm(provider="unknown")


def test_create_repo_reader_mock_and_unknown():
    reader = create_repo_reader(source="mock")
    assert isinstance(reader, MockRepoReader)
    with pytest.raises(ValueError, match="Unknown source"):
        create_repo_reader(source="unknown")


def test_create_semantic_indexer_mock_and_unknown():
    indexer = create_semantic_indexer(provider="mock")
    assert isinstance(indexer, MockSemanticIndexer)
    with pytest.raises(ValueError, match="Unknown provider"):
        create_semantic_indexer(provider="unknown")


def test_create_conversation_repository_mock_and_unknown():
    repo = create_conversation_repository(provider="mock")
    assert isinstance(repo, MockConversationRepository)
    with pytest.raises(ValueError, match="Unknown provider"):
        create_conversation_repository(provider="unknown")


def test_create_conversation_history_indexer_mock_and_unknown():
    indexer = create_conversation_history_indexer(platform="mock")
    assert isinstance(indexer, MockConversationHistoryIndexer)
    with pytest.raises(ValueError, match="Unknown platform"):
        create_conversation_history_indexer(platform="unknown")


def test_create_repo_change_detector_git_and_unknown():
    detector = create_repo_change_detector(detector_type="git")
    assert isinstance(detector, GitChangeDetector)
    with pytest.raises(ValueError, match="Unknown detector_type"):
        create_repo_change_detector(detector_type="unknown")


def test_protocol_modules_do_not_export_factories():
    import benedict.conversation_history_indexer.protocol as history_protocol
    import benedict.conversation_repository.protocol as conversation_protocol
    import benedict.llm.protocol as llm_protocol
    import benedict.repo_reader.protocol as reader_protocol
    import benedict.semantic_indexer.change_detector.protocol as change_protocol
    import benedict.semantic_indexer.protocol as indexer_protocol

    assert not hasattr(llm_protocol, "create_llm")
    assert not hasattr(reader_protocol, "create_repo_reader")
    assert not hasattr(indexer_protocol, "create_semantic_indexer")
    assert not hasattr(conversation_protocol, "create_conversation_repository")
    assert not hasattr(history_protocol, "create_conversation_history_indexer")
    assert not hasattr(change_protocol, "create_repo_change_detector")


def test_removed_top_level_packages_are_gone():
    for name in (
        "benedict.protocols",
        "benedict.commands",
        "benedict.utils",
        "benedict.metadata",
        "benedict.indexers",
        "benedict.repo_change_detector",
    ):
        with pytest.raises(ModuleNotFoundError):
            __import__(name)

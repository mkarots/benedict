"""Integration tests for RepoAgent.

Tests the agent with multiple components working together.
"""

from benedict.agent import RepoAgent
from benedict.repo_reader.repo_reader_mock import DEFAULT_TEST_REPO


def _get_conversation(agent, thread_ts, channel_id, repo):
    return agent.conversation_manager.get_conversation(
        thread_ts=thread_ts,
        channel_id=channel_id,
        repo=repo,
    )


def _add_message(agent, thread_ts, channel_id, repo, role, content):
    conv = _get_conversation(agent, thread_ts, channel_id, repo)
    conv.add_message(role, content)
    agent.conversation_manager.save_conversation(conv)
    return conv


class TestRepoAgentIntegration:
    """Integration tests for RepoAgent with dependencies."""

    def test_agent_with_llm_and_repo_reader(
        self,
        temp_state_file,
        mock_llm,
        populated_mock_repo_reader,
        mock_conversation_repository,
    ):
        """Test agent with LLM and repository reader."""
        agent = RepoAgent(
            state_file=str(temp_state_file),
            llm=mock_llm,
            repo_reader=populated_mock_repo_reader,
            conversation_repository=mock_conversation_repository,
        )

        assert agent.llm is not None
        assert agent.repo_reader is not None

    def test_full_conversation_flow(
        self,
        temp_state_file,
        mock_llm,
        populated_mock_repo_reader,
        mock_conversation_repository,
    ):
        """Test complete conversation flow from onboarding to question."""
        agent = RepoAgent(
            state_file=str(temp_state_file),
            llm=mock_llm,
            repo_reader=populated_mock_repo_reader,
            conversation_repository=mock_conversation_repository,
        )

        agent.set_channel_repo("C123456", DEFAULT_TEST_REPO, "U123456")

        repo = agent.get_channel_repo("C123456")
        assert repo == DEFAULT_TEST_REPO

        _get_conversation(agent, "1234567890.123456", "C123456", DEFAULT_TEST_REPO)
        _add_message(
            agent,
            "1234567890.123456",
            "C123456",
            DEFAULT_TEST_REPO,
            "user",
            "What is the architecture?",
        )

        retrieved = _get_conversation(agent, "1234567890.123456", "C123456", DEFAULT_TEST_REPO)
        assert retrieved is not None
        assert len(retrieved.messages) == 1

    def test_multiple_conversations_same_channel(
        self,
        temp_state_file,
        mock_llm,
        populated_mock_repo_reader,
        mock_conversation_repository,
    ):
        """Test multiple conversations in the same channel."""
        agent = RepoAgent(
            state_file=str(temp_state_file),
            llm=mock_llm,
            repo_reader=populated_mock_repo_reader,
            conversation_repository=mock_conversation_repository,
        )

        agent.set_channel_repo("C123456", DEFAULT_TEST_REPO, "U123456")

        _get_conversation(agent, "1111111111.111111", "C123456", DEFAULT_TEST_REPO)
        _get_conversation(agent, "2222222222.222222", "C123456", DEFAULT_TEST_REPO)

        _add_message(agent, "1111111111.111111", "C123456", DEFAULT_TEST_REPO, "user", "Question 1")
        _add_message(agent, "2222222222.222222", "C123456", DEFAULT_TEST_REPO, "user", "Question 2")

        retrieved1 = _get_conversation(agent, "1111111111.111111", "C123456", DEFAULT_TEST_REPO)
        retrieved2 = _get_conversation(agent, "2222222222.222222", "C123456", DEFAULT_TEST_REPO)

        assert retrieved1.messages[0].content == "Question 1"
        assert retrieved2.messages[0].content == "Question 2"

    def test_agent_with_semantic_indexer(
        self,
        temp_state_file,
        mock_llm,
        populated_mock_repo_reader,
        mock_semantic_indexer,
        mock_conversation_repository,
    ):
        """Test agent with semantic indexer for intelligent file selection."""
        agent = RepoAgent(
            state_file=str(temp_state_file),
            llm=mock_llm,
            repo_reader=populated_mock_repo_reader,
            semantic_indexer=mock_semantic_indexer,
            conversation_repository=mock_conversation_repository,
        )

        assert agent.semantic_indexer is not None

        relevant_files = mock_semantic_indexer.search(DEFAULT_TEST_REPO, "architecture", top_k=5)
        assert len(relevant_files) > 0

    def test_conversation_persistence(
        self,
        temp_state_file,
        mock_llm,
        populated_mock_repo_reader,
        mock_conversation_repository,
    ):
        """Test that conversations persist across agent restarts."""
        agent1 = RepoAgent(
            state_file=str(temp_state_file),
            llm=mock_llm,
            repo_reader=populated_mock_repo_reader,
            conversation_repository=mock_conversation_repository,
        )

        agent1.set_channel_repo("C123456", DEFAULT_TEST_REPO, "U123456")
        _add_message(
            agent1,
            "1234567890.123456",
            "C123456",
            DEFAULT_TEST_REPO,
            "user",
            "Question",
        )

        agent2 = RepoAgent(
            state_file=str(temp_state_file),
            llm=mock_llm,
            repo_reader=populated_mock_repo_reader,
            conversation_repository=mock_conversation_repository,
        )

        conv = _get_conversation(agent2, "1234567890.123456", "C123456", DEFAULT_TEST_REPO)
        assert conv is not None
        assert len(conv.messages) == 1
        assert conv.messages[0].content == "Question"

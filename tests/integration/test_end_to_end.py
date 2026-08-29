"""End-to-end integration tests.

Tests complete workflows from user interaction to response.
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


class TestEndToEnd:
    """End-to-end workflow tests."""

    def test_onboard_and_status_workflow(
        self,
        temp_state_file,
        mock_conversation_repository,
    ):
        """Test complete onboard and status check workflow."""
        agent = RepoAgent(
            state_file=str(temp_state_file),
            conversation_repository=mock_conversation_repository,
        )

        text = "onboard repo example-org/example-repo"

        assert agent.is_onboard_command(text)

        repo = agent.extract_repo_name(text)
        assert repo == "example-org/example-repo"

        agent.set_channel_repo(
            channel_id="C123456",
            repo=repo,
            user_id="U123456",
        )

        status_text = "status"
        assert agent.is_status_command(status_text)

        channel_repo = agent.get_channel_repo("C123456")
        assert channel_repo == "example-org/example-repo"

    def test_complete_conversation_workflow(
        self,
        temp_state_file,
        mock_llm,
        populated_mock_repo_reader,
        mock_conversation_repository,
    ):
        """Test complete conversation workflow."""
        agent = RepoAgent(
            state_file=str(temp_state_file),
            llm=mock_llm,
            repo_reader=populated_mock_repo_reader,
            conversation_repository=mock_conversation_repository,
        )

        agent.set_channel_repo("C123456", DEFAULT_TEST_REPO, "U123456")

        thread_ts = "1234567890.123456"
        channel_id = "C123456"
        user_message = "What files are in the repository?"

        _get_conversation(agent, thread_ts, channel_id, DEFAULT_TEST_REPO)
        _add_message(agent, thread_ts, channel_id, DEFAULT_TEST_REPO, "user", user_message)

        if agent.repo_reader:
            files = agent.repo_reader.list_files(DEFAULT_TEST_REPO)
            assert len(files) > 0

        _add_message(
            agent,
            thread_ts,
            channel_id,
            DEFAULT_TEST_REPO,
            "assistant",
            "The repository contains several files including README.md and source files.",
        )

        final_conv = _get_conversation(agent, thread_ts, channel_id, DEFAULT_TEST_REPO)
        assert len(final_conv.messages) == 2
        assert final_conv.messages[0].role == "user"
        assert final_conv.messages[1].role == "assistant"

    def test_multi_turn_conversation(
        self,
        temp_state_file,
        mock_llm,
        populated_mock_repo_reader,
        mock_conversation_repository,
    ):
        """Test multi-turn conversation with context."""
        agent = RepoAgent(
            state_file=str(temp_state_file),
            llm=mock_llm,
            repo_reader=populated_mock_repo_reader,
            conversation_repository=mock_conversation_repository,
        )

        thread_ts = "1234567890.123456"
        agent.set_channel_repo("C123456", DEFAULT_TEST_REPO, "U123456")

        conv = _get_conversation(agent, thread_ts, "C123456", DEFAULT_TEST_REPO)

        _add_message(agent, thread_ts, "C123456", DEFAULT_TEST_REPO, "user", "What is in README?")
        _add_message(
            agent,
            thread_ts,
            "C123456",
            DEFAULT_TEST_REPO,
            "assistant",
            "The README describes an example project.",
        )

        _add_message(
            agent,
            thread_ts,
            "C123456",
            DEFAULT_TEST_REPO,
            "user",
            "What about src/main.py?",
        )
        _add_message(
            agent,
            thread_ts,
            "C123456",
            DEFAULT_TEST_REPO,
            "assistant",
            "The main.py file contains the entry point.",
        )

        _add_message(
            agent, thread_ts, "C123456", DEFAULT_TEST_REPO, "user", "Can you explain more?"
        )

        conv = _get_conversation(agent, thread_ts, "C123456", DEFAULT_TEST_REPO)
        history = conv.get_message_history()
        assert len(history) == 5

        _add_message(
            agent,
            thread_ts,
            "C123456",
            DEFAULT_TEST_REPO,
            "assistant",
            "Sure, main.py is the entry point that prints 'Hello, World!'",
        )

        final_conv = _get_conversation(agent, thread_ts, "C123456", DEFAULT_TEST_REPO)
        assert len(final_conv.messages) == 6

    def test_multiple_channels_workflow(
        self,
        temp_state_file,
        mock_llm,
        populated_mock_repo_reader,
        mock_conversation_repository,
    ):
        """Test managing multiple channels simultaneously."""
        agent = RepoAgent(
            state_file=str(temp_state_file),
            llm=mock_llm,
            repo_reader=populated_mock_repo_reader,
            conversation_repository=mock_conversation_repository,
        )

        agent.set_channel_repo("C111111", "org1/repo1", "U123456")
        agent.set_channel_repo("C222222", "org2/repo2", "U123456")

        _add_message(
            agent,
            "1111111111.111111",
            "C111111",
            "org1/repo1",
            "user",
            "Question about repo1",
        )
        _add_message(
            agent,
            "2222222222.222222",
            "C222222",
            "org2/repo2",
            "user",
            "Question about repo2",
        )

        repo1 = agent.get_channel_repo("C111111")
        repo2 = agent.get_channel_repo("C222222")

        assert repo1 == "org1/repo1"
        assert repo2 == "org2/repo2"

        retrieved1 = _get_conversation(agent, "1111111111.111111", "C111111", "org1/repo1")
        retrieved2 = _get_conversation(agent, "2222222222.222222", "C222222", "org2/repo2")

        assert retrieved1.repo == "org1/repo1"
        assert retrieved2.repo == "org2/repo2"
        assert retrieved1.messages[0].content == "Question about repo1"
        assert retrieved2.messages[0].content == "Question about repo2"

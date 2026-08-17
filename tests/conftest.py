"""Shared pytest fixtures."""

from pathlib import Path

import pytest

from benedict.agent import RepoAgent
from benedict.conversation_repository.conversation_repository_mock import (
    MockConversationRepository,
)
from benedict.llm.llm_mock import MockLLM
from benedict.repo_reader.repo_reader_mock import MockRepoReader


@pytest.fixture
def state_file(tmp_path: Path) -> str:
    return str(tmp_path / "state.json")


@pytest.fixture
def mock_llm() -> MockLLM:
    return MockLLM()


@pytest.fixture
def mock_repo_reader() -> MockRepoReader:
    return MockRepoReader(
        repos={
            "example-org/example-repo": {
                "README.md": "# Example\nThis is a sample repository.",
                "src/auth.py": "def login():\n    return True\n",
                "src/app.py": "def main():\n    login()\n",
            }
        }
    )


@pytest.fixture
def mock_conversation_repository() -> MockConversationRepository:
    return MockConversationRepository()


@pytest.fixture
def agent(state_file: str, mock_conversation_repository) -> RepoAgent:
    return RepoAgent(
        state_file=state_file,
        conversation_repository=mock_conversation_repository,
    )

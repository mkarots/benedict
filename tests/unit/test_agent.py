"""Unit tests for RepoAgent command helpers and channel state."""

import json

from benedict.agent import RepoAgent
from benedict.llm.llm_mock import MockLLM
from benedict.repo_reader.repo_reader_mock import MockRepoReader


def test_extract_repo_name_from_common_formats():
    assert RepoAgent.extract_repo_name("onboard repo example-org/example-repo") == (
        "example-org/example-repo"
    )
    assert RepoAgent.extract_repo_name("github.com/example-org/example-repo") == (
        "example-org/example-repo"
    )
    assert RepoAgent.extract_repo_name("no repo here") is None


def test_command_detectors():
    assert RepoAgent.is_onboard_command("please onboard this channel")
    assert RepoAgent.is_onboard_command("this channel is for example-org/example-repo")
    assert not RepoAgent.is_onboard_command("what is the architecture?")

    assert RepoAgent.is_status_command("status")
    assert RepoAgent.is_offboard_command("offboard this channel")
    assert RepoAgent.is_update_index_command("update index")
    assert RepoAgent.is_update_index_command("please reindex")


def test_message_directed_at_bot():
    assert RepoAgent.is_message_directed_at_bot("hey benedict, what is auth?")
    assert RepoAgent.is_message_directed_at_bot("what is the architecture?")
    assert RepoAgent.is_message_directed_at_bot("can you explain the indexer?")
    assert not RepoAgent.is_message_directed_at_bot("ok")


def test_load_state_missing_and_corrupt(tmp_path):
    agent = RepoAgent(state_file=str(tmp_path / "missing.json"))
    assert agent.load_state() == {"channels": {}}

    corrupt = tmp_path / "state.json"
    corrupt.write_text("{not-json", encoding="utf-8")
    agent = RepoAgent(state_file=str(corrupt))
    assert agent.load_state() == {"channels": {}}


def test_set_and_get_channel_repo(agent):
    assert agent.get_channel_repo("C123") is None
    agent.set_channel_repo("C123", "example-org/example-repo", "Ualice")
    assert agent.get_channel_repo("C123") == "example-org/example-repo"

    state = json.loads(agent.state_file.read_text(encoding="utf-8"))
    assert state["channels"]["C123"]["onboarded_by"] == "Ualice"
    assert "onboarded_at" in state["channels"]["C123"]


def test_handle_status_not_onboarded(agent):
    success, message, config = agent.handle_status("C123")
    assert success is False
    assert config is None
    assert "Not Onboarded" in message


def test_handle_status_onboarded(agent):
    agent.set_channel_repo("C123", "example-org/example-repo", "Ualice")
    success, message, config = agent.handle_status("C123")
    assert success is True
    assert config["repo"] == "example-org/example-repo"
    assert "example-org/example-repo" in message
    assert "<@Ualice>" in message


def test_handle_onboard_missing_repo(agent):
    success, message = agent.handle_onboard("C123", "Ualice", "onboard please")
    assert success is False
    assert "Repository Not Found" in message


def test_handle_onboard_without_workspace(agent):
    success, message = agent.handle_onboard(
        "C123", "Ualice", "onboard repo example-org/example-repo"
    )
    assert success is True
    assert "example-org/example-repo" in message
    assert agent.get_channel_repo("C123") == "example-org/example-repo"


def test_handle_offboard(agent):
    success, message = agent.handle_offboard("C123", "Ualice")
    assert success is False
    assert "not currently onboarded" in message.lower()

    agent.set_channel_repo("C123", "example-org/example-repo", "Ualice")
    success, message = agent.handle_offboard("C123", "Ualice")
    assert success is True
    assert agent.get_channel_repo("C123") is None
    assert "example-org/example-repo" in message


def test_handle_conversation_without_onboarding(tmp_path):
    agent = RepoAgent(
        state_file=str(tmp_path / "state.json"),
        llm=MockLLM(),
        repo_reader=MockRepoReader(repos={}),
    )
    success, message = agent.handle_conversation("C123", "what is auth?", "111.222")
    assert success is False
    assert "onboard" in message.lower()

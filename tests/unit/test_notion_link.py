"""Tests for channel Notion link/unlink helpers."""

from unittest.mock import patch

from benedict.agent import RepoAgent
from benedict.conversation_repository.conversation_repository_mock import (
    MockConversationRepository,
)


def _agent(tmp_path):
    return RepoAgent(
        state_file=str(tmp_path / "state.json"),
        conversation_repository=MockConversationRepository(),
    )


def test_link_notion_requires_onboard(tmp_path):
    agent = _agent(tmp_path)
    success, message = agent.handle_link_notion(
        "C123", "link notion https://www.notion.so/aaaaaaaabbbbccccddddeeeeeeeeeeee"
    )
    assert success is False
    assert "onboard" in message.lower()


def test_link_and_unlink_notion(tmp_path):
    agent = _agent(tmp_path)
    agent.set_channel_repo("C123", "example-org/example-repo", "Ualice")
    notion_id = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"

    with patch(
        "benedict.agent.probe_notion_id",
        return_value=(True, "Roadmap", {"page_id": notion_id, "title": "Roadmap"}),
    ):
        success, message = agent.handle_link_notion(
            "C123", f"link notion https://www.notion.so/Roadmap-{notion_id.replace('-', '')}"
        )
    assert success is True
    assert "Roadmap" in message
    assert agent.get_channel_notion("C123")["page_id"] == notion_id

    success, status, config = agent.handle_status("C123")
    assert success is True
    assert "Roadmap" in status or notion_id in status
    assert config["notion"]["page_id"] == notion_id

    success, message = agent.handle_unlink_notion("C123")
    assert success is True
    assert agent.get_channel_notion("C123") == {}
    assert agent.get_channel_repo("C123") == "example-org/example-repo"


def test_reonboard_preserves_notion(tmp_path):
    agent = _agent(tmp_path)
    agent.set_channel_repo("C123", "example-org/example-repo", "Ualice")
    agent.set_channel_notion("C123", {"page_id": "page-1"})
    agent.set_channel_repo("C123", "example-org/example-repo", "Ubob")
    assert agent.get_channel_notion("C123")["page_id"] == "page-1"


def test_offboard_does_not_match_unlink_notion():
    assert RepoAgent.is_unlink_notion_command("unlink notion")
    assert RepoAgent.is_link_notion_command("link notion https://www.notion.so/abc")
    assert not RepoAgent.is_link_notion_command("unlink notion")
    assert not RepoAgent.is_offboard_command("unlink notion")
    assert RepoAgent.is_offboard_command("offboard this channel")
    assert RepoAgent.is_offboard_command("unlink this channel")


def test_link_notion_help_does_not_use_angle_brackets(tmp_path):
    agent = _agent(tmp_path)
    agent.set_channel_repo("C123", "example-org/example-repo", "Ualice")
    success, message = agent.handle_link_notion("C123", "link notion")
    assert success is False
    assert "link notion https://www.notion.so/" in message
    assert "<" not in message

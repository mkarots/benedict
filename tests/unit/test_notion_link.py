"""Tests for channel Notion link/unlink helpers."""

from unittest.mock import patch

from benedict.agent import RepoAgent
from benedict.conversation_repository.conversation_repository_mock import (
    MockConversationRepository,
)
from benedict.slack.payloads import StatusPayload


def _agent(tmp_path):
    return RepoAgent(
        state_file=str(tmp_path / "state.json"),
        conversation_repository=MockConversationRepository(),
    )


def test_link_notion_requires_onboard(tmp_path):
    agent = _agent(tmp_path)
    reply = agent.handle_link_notion(
        "C123", "link notion https://www.notion.so/aaaaaaaabbbbccccddddeeeeeeeeeeee"
    )
    assert reply.success is False
    assert "onboard" in reply.text().lower()


def test_link_and_unlink_notion(tmp_path):
    agent = _agent(tmp_path)
    agent.set_channel_repo("C123", "example-org/example-repo", "Ualice")
    notion_id = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"

    with patch(
        "benedict.agent.probe_notion_id",
        return_value=(True, "Roadmap", {"page_id": notion_id, "title": "Roadmap"}),
    ):
        reply = agent.handle_link_notion(
            "C123", f"link notion https://www.notion.so/Roadmap-{notion_id.replace('-', '')}"
        )
    assert reply.success is True
    assert "Roadmap" in reply.text()
    assert agent.get_channel_notion("C123")["page_id"] == notion_id

    status_reply = agent.handle_status("C123")
    assert isinstance(status_reply, StatusPayload)
    assert status_reply.success is True
    assert status_reply.fields["Notion"] == "`Roadmap`"
    assert agent.get_channel_notion("C123")["page_id"] == notion_id

    reply = agent.handle_unlink_notion("C123")
    assert reply.success is True
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
    reply = agent.handle_link_notion("C123", "link notion")
    assert reply.success is False
    assert "link notion https://www.notion.so/" in reply.text()
    assert "<" not in reply.text()


def test_handle_status_returns_fields_not_emoji_string(tmp_path):
    agent = _agent(tmp_path)
    agent.set_channel_repo("C123", "example-org/example-repo", "Ualice")
    reply = agent.handle_status("C123")
    assert isinstance(reply, StatusPayload)
    assert reply.title == "Channel Status"
    assert reply.fields["Repository"] == "`example-org/example-repo`"
    assert reply.fields["By"] == "<@Ualice>"
    assert "📊" not in reply.fields["Repository"]


def test_handle_status_not_onboarded_stays_markdown(tmp_path):
    from benedict.slack.payloads import MarkdownPayload

    agent = _agent(tmp_path)
    reply = agent.handle_status("C123")
    assert isinstance(reply, MarkdownPayload)
    assert reply.success is False
    assert "Not Onboarded" in reply.text()

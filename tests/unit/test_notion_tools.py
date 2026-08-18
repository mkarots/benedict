"""Tests for RunNotionTool."""

from unittest.mock import Mock, patch

from benedict.commands.notion_tools import (
    RunNotionTool,
    _redact_tokens,
    _sanitize_output,
    _truncate,
)


def test_truncate_redact_and_sanitize():
    assert _truncate("short") == "short"
    truncated = _truncate("a" * 40, limit=8)
    assert truncated.startswith("a" * 8)
    assert "omitted" in truncated
    assert "[redacted-token]" in _redact_tokens("token secret_abc123 rest")
    sanitized = _sanitize_output({"token": "secret_abc123", "items": ["ntn_987xyz"]})
    assert sanitized["token"] == "[redacted-token]"
    assert sanitized["items"][0] == "[redacted-token]"


def test_requires_api_key():
    tool = RunNotionTool()
    with patch.dict("os.environ", {}, clear=True):
        result = tool.execute({"action": "search", "query": "roadmap"})
    assert result.success is False
    assert "NOTION_API_KEY" in result.error


@patch("benedict.commands.notion_tools.Client")
def test_search_requires_query(mock_client):
    tool = RunNotionTool()
    with patch.dict("os.environ", {"NOTION_API_KEY": "secret_abc123"}, clear=True):
        result = tool.execute({"action": "search"})
    assert result.success is False
    assert "query is required" in result.error
    mock_client.assert_called_once_with(auth="secret_abc123")


@patch("benedict.commands.notion_tools.Client")
def test_search_calls_notion_with_capped_page_size(mock_client):
    client = Mock()
    client.search.return_value = {
        "results": [{"id": "page-1", "url": "https://www.notion.so/page-1"}],
        "next_cursor": "cursor-1",
    }
    mock_client.return_value = client

    tool = RunNotionTool()
    with patch.dict("os.environ", {"NOTION_API_KEY": "secret_abc123"}, clear=True):
        result = tool.execute(
            {
                "action": "search",
                "query": "roadmap",
                "page_size": 1000,
                "start_cursor": "cursor-0",
            }
        )

    assert result.success is True
    assert result.data["next_cursor"] == "cursor-1"
    client.search.assert_called_once_with(
        query="roadmap",
        page_size=100,
        start_cursor="cursor-0",
    )


@patch("benedict.commands.notion_tools.Client")
def test_retrieve_page_markdown_returns_sanitized_message(mock_client):
    client = Mock()
    client.pages.retrieve_markdown.return_value = "Top line\nsecret_abc123"
    mock_client.return_value = client

    tool = RunNotionTool()
    with patch.dict("os.environ", {"NOTION_API_KEY": "secret_abc123"}, clear=True):
        result = tool.execute({"action": "retrieve_page_markdown", "page_id": "page-1"})

    assert result.success is True
    assert "[redacted-token]" in result.message
    client.pages.retrieve_markdown.assert_called_once_with(page_id="page-1")


@patch("benedict.commands.notion_tools.Client")
def test_list_block_children_requires_block_id(mock_client):
    tool = RunNotionTool()
    with patch.dict("os.environ", {"NOTION_API_KEY": "secret_abc123"}, clear=True):
        result = tool.execute({"action": "list_block_children"})
    assert result.success is False
    assert "block_id is required" in result.error
    mock_client.assert_called_once_with(auth="secret_abc123")

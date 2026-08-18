"""Tests for RunNotionTool."""

from unittest.mock import Mock, patch

from benedict.commands.notion_tools import (
    RunNotionTool,
    parse_notion_id,
    probe_notion_id,
    _encode_property,
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


def test_parse_notion_id_from_url_and_uuid():
    assert parse_notion_id("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee") == (
        "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
    )
    url = "https://www.notion.so/workspace/Roadmap-aaaaaaaabbbbccccddddeeeeeeeeeeee"
    assert parse_notion_id(url) == "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
    assert parse_notion_id("not a notion id") is None


def test_requires_api_key():
    tool = RunNotionTool()
    with patch.dict("os.environ", {}, clear=True):
        result = tool.execute({"action": "search", "query": "roadmap"})
    assert result.success is False
    assert "NOTION_API_KEY" in result.error


def test_search_requires_query():
    client = Mock()
    tool = RunNotionTool(client=client)
    result = tool.execute({"action": "search"})
    assert result.success is False
    assert "query is required" in result.error
    client.search.assert_not_called()


def test_search_summarizes_results():
    client = Mock()
    client.search.return_value = {
        "results": [
            {
                "object": "page",
                "id": "page-1",
                "url": "https://www.notion.so/page-1",
                "properties": {"title": {"type": "title", "title": [{"plain_text": "Roadmap"}]}},
            }
        ],
        "next_cursor": "cursor-1",
        "has_more": False,
    }
    tool = RunNotionTool(client=client)
    result = tool.execute({"action": "search", "query": "roadmap", "page_size": 1000})
    assert result.success is True
    assert result.data["results"][0]["title"] == "Roadmap"
    client.search.assert_called_once()
    assert client.search.call_args.kwargs["page_size"] == 100


def test_get_page_uses_linked_id_and_flattens_blocks():
    client = Mock()
    client.pages.retrieve.return_value = {
        "id": "page-1",
        "url": "https://www.notion.so/page-1",
        "properties": {"title": {"type": "title", "title": [{"plain_text": "Spec"}]}},
    }
    client.blocks.children.list.return_value = {
        "results": [
            {
                "type": "paragraph",
                "paragraph": {"rich_text": [{"plain_text": "Hello"}]},
            }
        ],
        "has_more": False,
    }
    tool = RunNotionTool(client=client)
    result = tool.execute(
        {"action": "get_page"},
        {"notion": {"page_id": "page-1"}},
    )
    assert result.success is True
    assert result.data["content"] == "Hello"
    client.pages.retrieve.assert_called_once_with(page_id="page-1")


def test_query_database_requires_id_without_link():
    tool = RunNotionTool(client=Mock())
    result = tool.execute({"action": "query_database"})
    assert result.success is False
    assert "database_id is required" in result.error


def test_create_database_card_and_update_status():
    client = Mock()
    created = {
        "id": "card-1",
        "url": "https://www.notion.so/card-1",
        "properties": {
            "Name": {"type": "title", "title": [{"plain_text": "Fix login"}]},
            "Status": {"type": "status", "status": {"name": "In progress"}},
        },
    }
    client.pages.create.return_value = created
    client.pages.update.return_value = {
        **created,
        "properties": {
            "Name": {"type": "title", "title": [{"plain_text": "Fix login"}]},
            "Status": {"type": "status", "status": {"name": "Done"}},
        },
    }
    tool = RunNotionTool(client=client)
    context = {"notion": {"database_id": "db-1"}}

    created_result = tool.execute(
        {"action": "create_page", "title": "Fix login", "properties": {"Status": "In progress"}},
        context,
    )
    assert created_result.success is True
    payload = client.pages.create.call_args.kwargs
    assert payload["parent"] == {"database_id": "db-1"}
    assert payload["properties"]["Name"]["title"][0]["text"]["content"] == "Fix login"
    assert payload["properties"]["Status"] == {"status": {"name": "In progress"}}

    updated = tool.execute(
        {"action": "update_page", "page_id": "card-1", "properties": {"Status": "Done"}},
        context,
    )
    assert updated.success is True
    assert updated.data["properties"]["Status"] == "Done"
    client.pages.update.assert_called_once()


def test_append_content_and_create_child_page():
    client = Mock()
    client.pages.create.return_value = {
        "id": "child-1",
        "url": "https://www.notion.so/child-1",
        "properties": {"title": {"type": "title", "title": [{"plain_text": "Notes"}]}},
    }
    client.blocks.children.append.return_value = {}
    tool = RunNotionTool(client=client)
    context = {"notion": {"page_id": "page-1"}}

    created = tool.execute(
        {"action": "create_page", "title": "Notes", "content": "Hello\n\nWorld"},
        context,
    )
    assert created.success is True
    assert client.pages.create.call_args.kwargs["parent"] == {"page_id": "page-1"}
    assert len(client.pages.create.call_args.kwargs["children"]) == 2

    appended = tool.execute(
        {"action": "append_content", "content": "More notes"},
        context,
    )
    assert appended.success is True
    client.blocks.children.append.assert_called_once()


def test_encode_property_status_and_native_payload():
    assert _encode_property("Status", "Done") == {"status": {"name": "Done"}}
    native = {"select": {"name": "P1"}}
    assert _encode_property("Priority", native) == native


def test_probe_page_then_database():
    client = Mock()

    class NotFound(Exception):
        code = "object_not_found"

    client.pages.retrieve.side_effect = NotFound()
    client.databases.retrieve.return_value = {
        "id": "db-1",
        "url": "https://www.notion.so/db-1",
        "title": [{"plain_text": "Board"}],
    }
    with patch("benedict.commands.notion_tools.APIResponseError", NotFound):
        ok, message, state = probe_notion_id("db-1", client=client)
    assert ok is True
    assert message == "Board"
    assert state["database_id"] == "db-1"


def test_unsupported_action():
    result = RunNotionTool(client=Mock()).execute({"action": "delete_everything"})
    assert result.success is False
    assert "Unsupported" in result.error

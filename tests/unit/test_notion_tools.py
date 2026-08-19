"""Tests for RunNotionTool (ntn argv) and id parsing."""

import json
import subprocess
from unittest.mock import patch

from benedict.commands.notion_tools import (
    RunNotionTool,
    _normalize_argv,
    _redact_tokens,
    _truncate,
    parse_notion_id,
    probe_notion_id,
)
from benedict.commands.tool_framework import ToolResult


def _ok(stdout: str, exit_code: int = 0) -> ToolResult:
    return ToolResult(
        success=True,
        message=stdout,
        data={"exit_code": exit_code, "stdout": stdout, "stderr": ""},
    )


def test_normalize_argv_list_and_strip_ntn():
    assert _normalize_argv(["pages", "get", "abc"]) == ["pages", "get", "abc"]
    assert _normalize_argv(["ntn", "pages", "get", "abc"]) == ["pages", "get", "abc"]
    assert _normalize_argv("datasources query ds-1") == ["datasources", "query", "ds-1"]
    assert _normalize_argv(None) is None
    assert _normalize_argv({"bad": True}) is None


def test_truncate_and_redact():
    assert _truncate("short") == "short"
    truncated = _truncate("a" * 40, limit=8)
    assert truncated.startswith("a" * 8)
    assert "omitted" in truncated
    assert "[redacted-token]" in _redact_tokens("token ntn_abc123 rest")
    assert "[redacted-token]" in _redact_tokens("secret_abc123")


def test_parse_notion_id_from_url_uuid_and_collection():
    assert parse_notion_id("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee") == (
        "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
    )
    url = "https://www.notion.so/workspace/Roadmap-aaaaaaaabbbbccccddddeeeeeeeeeeee"
    assert parse_notion_id(url) == "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
    assert parse_notion_id("not a notion id") is None
    assert parse_notion_id(
        'collection://30e9ddda-a890-800d-8f3d-000ba2ec9a5c'
    ) == "30e9ddda-a890-800d-8f3d-000ba2ec9a5c"
    compact = "https://app.notion.com/p/2fc9dddaa890808ba7e0fb556ab271f6"
    assert parse_notion_id(compact) == "2fc9ddda-a890-808b-a7e0-fb556ab271f6"


def test_parse_notion_id_ignores_board_view_query():
    database_id = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
    view_id = "11111111222233334444555566667777"
    compact = database_id.replace("-", "")
    url = f"https://www.notion.so/workspace/Roadmap-{compact}?v={view_id}"
    assert parse_notion_id(url) == database_id
    assert parse_notion_id(f"link notion {url}") == database_id
    assert parse_notion_id(f"link notion <{url}>") == database_id
    assert parse_notion_id(f"<{url}|Roadmap>") == database_id


def test_rejects_empty_and_login():
    tool = RunNotionTool(execute=lambda argv: _ok("nope"))
    missing = tool.execute({"argv": []})
    assert missing.success is False
    assert "empty" in missing.error
    blocked = tool.execute({"argv": ["login"]})
    assert blocked.success is False
    assert "login" in blocked.error
    oauth = tool.execute({"argv": ["workers", "oauth", "token", "x"]})
    assert oauth.success is False


def test_runs_ntn_argv_and_follows_up_query():
    calls = []

    def fake(argv):
        calls.append(argv)
        if argv[:2] == ["pages", "get"]:
            return _ok("collection://30e9ddda-a890-800d-8f3d-000ba2ec9a5c\n")
        if argv[:2] == ["datasources", "query"]:
            return _ok("ID  Task name\ncard-1  Open source")
        return _ok("")

    tool = RunNotionTool(execute=fake)
    page = tool.execute({"argv": ["pages", "get", "page-1"]})
    nested = parse_notion_id(page.message)
    query = tool.execute({"argv": ["datasources", "query", nested]})
    assert page.success is True
    assert query.success is True
    assert "Open source" in query.message
    assert calls == [
        ["pages", "get", "page-1"],
        ["datasources", "query", "30e9ddda-a890-800d-8f3d-000ba2ec9a5c"],
    ]


@patch("benedict.commands.notion_tools.shutil.which", return_value=None)
def test_missing_ntn_binary(mock_which):
    result = RunNotionTool().execute({"argv": ["pages", "get", "x"]})
    assert result.success is False
    assert "ntn is not installed" in result.error
    mock_which.assert_called()


@patch("benedict.commands.notion_tools.shutil.which", return_value="/usr/bin/ntn")
@patch("benedict.commands.notion_tools.subprocess.run")
def test_passes_api_key_as_ntn_token(mock_run, mock_which):
    mock_run.return_value = subprocess.CompletedProcess(
        args=["ntn", "pages", "get", "x"], returncode=0, stdout="ok", stderr=""
    )
    with patch.dict("os.environ", {"NOTION_API_KEY": "ntn_testtoken"}, clear=True):
        result = RunNotionTool().execute({"argv": ["pages", "get", "x"]})
    assert result.success is True
    env = mock_run.call_args.kwargs["env"]
    assert env["NOTION_API_TOKEN"] == "ntn_testtoken"
    assert mock_run.call_args[0][0] == ["ntn", "pages", "get", "x"]
    assert mock_run.call_args.kwargs.get("shell") in (None, False)


@patch("benedict.commands.notion_tools.shutil.which", return_value="/usr/bin/ntn")
@patch("benedict.commands.notion_tools.subprocess.run")
def test_timeout(mock_run, mock_which):
    mock_run.side_effect = subprocess.TimeoutExpired(cmd="ntn", timeout=45)
    result = RunNotionTool(timeout_s=45).execute({"argv": ["pages", "get", "x"]})
    assert result.success is False
    assert "timed out" in result.error


def test_probe_database_via_ntn_api():
    def fake(argv):
        if argv[0] == "api" and argv[1].startswith("v1/pages/"):
            return _ok("not json", exit_code=1)
        if argv[0] == "api" and argv[1].startswith("v1/databases/"):
            return _ok(
                json.dumps(
                    {
                        "object": "database",
                        "id": "db-1",
                        "url": "https://www.notion.so/db-1",
                        "title": [{"plain_text": "Projects"}],
                        "data_sources": [{"id": "ds-1", "name": "Projects"}],
                    }
                )
            )
        raise AssertionError(argv)

    ok, message, state = probe_notion_id("db-1", execute=fake)
    assert ok is True
    assert message == "Projects"
    assert state["database_id"] == "db-1"
    assert state["data_source_id"] == "ds-1"


def test_probe_page_via_ntn_api():
    def fake(argv):
        if argv[0] == "api" and argv[1].startswith("v1/pages/"):
            return _ok(
                json.dumps(
                    {
                        "object": "page",
                        "id": "page-1",
                        "url": "https://www.notion.so/page-1",
                        "properties": {
                            "Name": {"type": "title", "title": [{"plain_text": "Benedict"}]}
                        },
                    }
                )
            )
        raise AssertionError(argv)

    ok, message, state = probe_notion_id("page-1", execute=fake)
    assert ok is True
    assert message == "Benedict"
    assert state["page_id"] == "page-1"


def test_probe_failure_message():
    def fake(argv):
        return _ok("not found", exit_code=1)

    ok, message, state = probe_notion_id("missing", execute=fake)
    assert ok is False
    assert state == {}
    assert "missing" in message
    assert "ntn login" in message

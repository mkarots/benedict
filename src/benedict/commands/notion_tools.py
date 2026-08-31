"""Notion CLI tool.

One tool that runs `ntn` with caller-supplied argv. The prompt owns Notion
navigation (pages get → nested data-source query → more pages get). This
module only locks the binary, timeout, output size, and a few credential
commands.
"""

from __future__ import annotations

import json
import logging
import os
import re
import shlex
import shutil
import subprocess
from typing import Any, Callable, Dict, List, Optional, Tuple, Union
from urllib.parse import unquote, urlparse

from .tool_framework import Tool, ToolResult

logger = logging.getLogger(__name__)

NOTION_BINARY = "ntn"
NOTION_API_KEY_ENV_VAR = "NOTION_API_KEY"
NOTION_API_TOKEN_ENV_VAR = "NOTION_API_TOKEN"
LINK_NOTION_EXAMPLE = "@benedict link notion https://www.notion.so/your-page-or-database"
DEFAULT_TIMEOUT_S = 45
MAX_OUTPUT_CHARS = 32000
_TOKEN_RE = re.compile(r"(secret_[A-Za-z0-9]+|ntn_[A-Za-z0-9]+)")
_NOTION_HEX_RE = re.compile(r"[0-9a-fA-F]{32}")
_UUID_RE = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)
_COLLECTION_RE = re.compile(
    r"collection://([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})"
)
ExecuteFn = Callable[[List[str]], ToolResult]


def _truncate(text: str, limit: int = MAX_OUTPUT_CHARS) -> str:
    if not text:
        return ""
    if len(text) <= limit:
        return text
    return text[:limit] + f"\n...[truncated, {len(text) - limit} chars omitted]"


def _redact_tokens(text: str) -> str:
    if not text:
        return text
    return _TOKEN_RE.sub("[redacted-token]", text)


def _format_notion_id(hex32: str) -> str:
    hex32 = hex32.lower()
    return f"{hex32[0:8]}-{hex32[8:12]}-{hex32[12:16]}-{hex32[16:20]}-{hex32[20:32]}"


def _id_from_path(path: str) -> Optional[str]:
    matches = _NOTION_HEX_RE.findall(unquote(path).replace("-", ""))
    if not matches:
        return None
    return _format_notion_id(matches[-1])


def parse_notion_id(text: str) -> Optional[str]:
    """Extract a Notion page, database, or data-source id from a URL or raw id.

    Board links use ``?v=<view_id>`` — query parameters are ignored.
    ``collection://uuid`` in ``ntn pages get`` output is a data source.
    """
    if not text:
        return None
    stripped = text.strip().strip("<>")
    collection = _COLLECTION_RE.search(stripped)
    if collection:
        return collection.group(1).lower()
    if _UUID_RE.fullmatch(stripped):
        return stripped.lower()

    for token in stripped.split():
        token = token.strip("<>").split("|", 1)[0]
        parsed = urlparse(token)
        if parsed.scheme in ("http", "https") or "notion.so" in token or "notion.com" in token:
            found = _id_from_path(parsed.path)
            if found:
                return found

    return _id_from_path(stripped.split("?", 1)[0])


def _normalize_argv(raw: Union[List[Any], str, None]) -> Optional[List[str]]:
    if raw is None:
        return None
    if isinstance(raw, str):
        try:
            argv = shlex.split(raw)
        except ValueError:
            return None
    elif isinstance(raw, list):
        argv = [str(item) for item in raw]
    else:
        return None
    if argv and argv[0] in (NOTION_BINARY, f"{NOTION_BINARY}.exe"):
        argv = argv[1:]
    return argv


def _is_forbidden_argv(argv: List[str]) -> Optional[str]:
    if not argv:
        return None
    if argv[0] in ("login", "logout"):
        return f"Refusing to run `ntn {argv[0]}` (interactive credentials)."
    if argv[:3] == ["workers", "oauth", "token"]:
        return "Refusing to run `ntn workers oauth token` (would expose credentials)."
    return None


def _ntn_env() -> Dict[str, str]:
    env = os.environ.copy()
    if not (env.get(NOTION_API_TOKEN_ENV_VAR) or "").strip():
        key = (env.get(NOTION_API_KEY_ENV_VAR) or "").strip().strip('"').strip("'")
        if key:
            env[NOTION_API_TOKEN_ENV_VAR] = key
    return env


def execute_ntn(argv: List[str], timeout_s: int = DEFAULT_TIMEOUT_S) -> ToolResult:
    """Run `ntn` with argv. Used by the tool and by link-notion probing."""
    if shutil.which(NOTION_BINARY) is None:
        return ToolResult(
            success=False,
            error=(
                "ntn is not installed on the host running Benedict. "
                "Install the Notion CLI (`curl -fsSL https://ntn.dev | bash`) and run `ntn login`."
            ),
        )
    command = [NOTION_BINARY, *argv]
    logger.info("Running Notion CLI: %s", command)
    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout_s,
            check=False,
            env=_ntn_env(),
        )
    except subprocess.TimeoutExpired:
        return ToolResult(success=False, error=f"ntn timed out after {timeout_s}s")
    except FileNotFoundError:
        return ToolResult(
            success=False,
            error="ntn is not installed on the host running Benedict.",
        )
    except OSError as exc:
        logger.error("Failed to run ntn: %s", exc, exc_info=True)
        return ToolResult(success=False, error=str(exc))

    stdout = _redact_tokens(_truncate(completed.stdout or ""))
    stderr = _redact_tokens(_truncate(completed.stderr or ""))
    if completed.returncode == 0:
        message = stdout or "ntn exited 0 with no output"
    else:
        details = stderr or stdout or "no output"
        message = f"ntn exited {completed.returncode}\n{details}"
    return ToolResult(
        success=True,
        message=message,
        data={"exit_code": completed.returncode, "stdout": stdout, "stderr": stderr},
    )


def _command_ok(result: ToolResult) -> bool:
    if not result.success:
        return False
    data = result.data or {}
    exit_code = data.get("exit_code", 1)
    return bool(exit_code == 0)


def _stdout_json(result: ToolResult) -> Optional[Dict[str, Any]]:
    stdout = (result.data or {}).get("stdout") or result.message or ""
    stripped = stdout.strip()
    if not stripped.startswith("{") and not stripped.startswith("["):
        return None
    try:
        payload = json.loads(stripped)
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


def _plain_text(rich_text: Any) -> str:
    if not isinstance(rich_text, list):
        return ""
    return "".join(item.get("plain_text", "") for item in rich_text if isinstance(item, dict))


def _title_from_api_object(payload: Dict[str, Any], fallback: str) -> str:
    title = _plain_text(payload.get("title") or [])
    if title:
        return title
    properties = payload.get("properties") or {}
    for prop in properties.values():
        if isinstance(prop, dict) and prop.get("type") == "title":
            found = _plain_text(prop.get("title") or [])
            if found:
                return found
    return payload.get("name") or fallback


def _title_from_markdown(text: str, fallback: str) -> str:
    for line in text.splitlines():
        if line.startswith("Project name:"):
            value = line.split(":", 1)[1].strip()
            if value:
                return value
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            return stripped[2:].strip() or fallback
    return fallback


def probe_notion_id(
    notion_id: str, execute: Optional[ExecuteFn] = None
) -> Tuple[bool, str, Dict[str, str]]:
    """Check that ntn can see this id. Stores page, database, and/or data source ids."""
    run = execute or execute_ntn

    page = run(["api", f"v1/pages/{notion_id}"])
    payload = _stdout_json(page)
    if _command_ok(page) and payload and payload.get("object") == "page":
        title = _title_from_api_object(payload, notion_id)
        state = {"page_id": notion_id, "url": payload.get("url") or "", "title": title}
        parent = payload.get("parent") or {}
        if parent.get("database_id"):
            state["database_id"] = parent["database_id"]
        if parent.get("data_source_id"):
            state["data_source_id"] = parent["data_source_id"]
        return True, title, state

    database = run(["api", f"v1/databases/{notion_id}"])
    payload = _stdout_json(database)
    if _command_ok(database) and payload and payload.get("object") == "database":
        title = _title_from_api_object(payload, notion_id)
        state = {"database_id": notion_id, "url": payload.get("url") or "", "title": title}
        for source in payload.get("data_sources") or []:
            if isinstance(source, dict) and source.get("id"):
                state["data_source_id"] = source["id"]
                break
        return True, title, state

    resolved = run(["datasources", "resolve", notion_id])
    if _command_ok(resolved):
        stdout = (resolved.data or {}).get("stdout") or resolved.message or ""
        found = parse_notion_id(stdout) or notion_id
        state = {"database_id": notion_id, "data_source_id": found, "title": notion_id}
        return True, notion_id, state

    markdown = run(["pages", "get", notion_id])
    if _command_ok(markdown):
        text = (markdown.data or {}).get("stdout") or markdown.message or ""
        title = _title_from_markdown(text, notion_id)
        return True, title, {"page_id": notion_id, "title": title}

    last = markdown.message or database.message or page.message or "ntn could not read that id"
    return (
        False,
        f"I can't see Notion object `{notion_id}` with ntn on this machine. "
        "Install the Notion CLI, run `ntn login`, or set NOTION_API_KEY "
        f"(copied to NOTION_API_TOKEN for ntn). {last}",
        {},
    )


class RunNotionTool(Tool):
    """Run `ntn` for conversational Notion access. Not a general shell."""

    def __init__(self, timeout_s: int = DEFAULT_TIMEOUT_S, execute: Optional[ExecuteFn] = None):
        super().__init__(
            name="run_notion",
            description=(
                "Run the Notion CLI (`ntn`). Pass arguments only — do not include `ntn`. "
                'Examples: argv=["datasources", "query", "DATA_SOURCE_ID"], '
                'argv=["pages", "get", "PAGE_ID"], '
                'argv=["datasources", "resolve", "DATABASE_ID"], '
                'argv=["api", "v1/pages/PAGE_ID"]. '
                "Follow ids in the output: collection://uuid is a data source; "
                "nested page urls are pages. Call this tool as many times as needed "
                "to walk board → page → nested database → tasks. "
                "Ask the user before mutating (pages create, pages edit, pages trash). "
                "This is not a general shell."
            ),
        )
        self.timeout_s = timeout_s
        self._execute = execute or execute_ntn

    def get_schema(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": {
                "type": "object",
                "properties": {
                    "argv": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": (
                            "Arguments for `ntn` (without the `ntn` binary). "
                            'Example: ["pages", "get", "2fc9ddda-a890-808b-a7e0-fb556ab271f6"]'
                        ),
                    }
                },
                "required": ["argv"],
            },
        }

    def execute(
        self, arguments: Dict[str, Any], context: Optional[Dict[str, Any]] = None
    ) -> ToolResult:
        argv = _normalize_argv(arguments.get("argv"))
        if argv is None:
            return ToolResult(
                success=False,
                error="argv must be a list of strings or a shell-style string",
            )
        if not argv:
            return ToolResult(success=False, error="argv must not be empty")
        if any("\x00" in part for part in argv):
            return ToolResult(success=False, error="argv contains invalid characters")
        blocked = _is_forbidden_argv(argv)
        if blocked:
            return ToolResult(success=False, error=blocked)
        if self._execute is execute_ntn:
            return execute_ntn(argv, timeout_s=self.timeout_s)
        return self._execute(argv)

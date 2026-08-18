"""Notion API tool for conversational read and write access."""

import logging
import os
import re
from typing import Any, Dict, List, Optional, Tuple

from notion_client import Client
from notion_client.errors import APIResponseError

from .tool_framework import Tool, ToolResult

logger = logging.getLogger(__name__)

NOTION_API_KEY_ENV_VAR = "NOTION_API_KEY"
DEFAULT_PAGE_SIZE = 10
MAX_PAGE_SIZE = 100
MAX_OUTPUT_CHARS = 32000
_TOKEN_RE = re.compile(r"(secret_[A-Za-z0-9]+|ntn_[A-Za-z0-9]+)")
_NOTION_HEX_RE = re.compile(r"[0-9a-fA-F]{32}")
_UUID_RE = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)
READ_ACTIONS = frozenset({"search", "get_page", "query_database"})
WRITE_ACTIONS = frozenset({"create_page", "update_page", "append_content"})
SUPPORTED_ACTIONS = tuple(sorted(READ_ACTIONS | WRITE_ACTIONS))


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


def _sanitize_output(value: Any) -> Any:
    if isinstance(value, str):
        return _redact_tokens(_truncate(value))
    if isinstance(value, list):
        return [_sanitize_output(item) for item in value]
    if isinstance(value, dict):
        return {key: _sanitize_output(item) for key, item in value.items()}
    return value


def parse_notion_id(text: str) -> Optional[str]:
    """Extract a Notion page or database id from a URL or raw id."""
    if not text:
        return None
    stripped = text.strip().strip("<>")
    if _UUID_RE.fullmatch(stripped):
        return stripped.lower()
    compact = stripped.replace("-", "")
    matches = _NOTION_HEX_RE.findall(compact)
    if not matches:
        return None
    hex_id = matches[-1].lower()
    return f"{hex_id[0:8]}-{hex_id[8:12]}-{hex_id[12:16]}-{hex_id[16:20]}-{hex_id[20:32]}"


def _plain_text(rich_text: Any) -> str:
    if not isinstance(rich_text, list):
        return ""
    return "".join(item.get("plain_text", "") for item in rich_text if isinstance(item, dict))


def _block_to_text(block: Dict[str, Any]) -> str:
    block_type = block.get("type")
    payload = block.get(block_type) if isinstance(block_type, str) else None
    if not isinstance(payload, dict):
        return ""
    text = _plain_text(payload.get("rich_text") or payload.get("text") or [])
    if block_type == "to_do":
        mark = "x" if payload.get("checked") else " "
        return f"- [{mark}] {text}"
    if block_type in ("heading_1", "heading_2", "heading_3"):
        hashes = "#" * int(block_type[-1])
        return f"{hashes} {text}"
    if block_type in ("bulleted_list_item", "numbered_list_item"):
        return f"- {text}"
    if block_type == "code":
        lang = payload.get("language") or ""
        return f"```{lang}\n{text}\n```"
    return text


def _page_title(page: Dict[str, Any]) -> str:
    properties = page.get("properties") or {}
    for prop in properties.values():
        if isinstance(prop, dict) and prop.get("type") == "title":
            title = _plain_text(prop.get("title") or [])
            if title:
                return title
    return page.get("id", "untitled")


def _summarize_page(page: Dict[str, Any]) -> Dict[str, Any]:
    properties = {}
    for name, prop in (page.get("properties") or {}).items():
        if not isinstance(prop, dict):
            continue
        prop_type = prop.get("type")
        value: Any = None
        if prop_type == "title":
            value = _plain_text(prop.get("title") or [])
        elif prop_type == "rich_text":
            value = _plain_text(prop.get("rich_text") or [])
        elif prop_type in ("status", "select"):
            option = prop.get(prop_type) or {}
            value = option.get("name") if isinstance(option, dict) else None
        elif prop_type == "multi_select":
            value = [
                item.get("name") for item in prop.get("multi_select") or [] if item.get("name")
            ]
        elif prop_type in ("checkbox", "number", "url", "email"):
            value = prop.get(prop_type)
        elif prop_type == "date":
            date_value = prop.get("date") or {}
            value = date_value.get("start") if isinstance(date_value, dict) else None
        elif prop_type == "people":
            value = [
                person.get("name") or person.get("id")
                for person in prop.get("people") or []
                if isinstance(person, dict)
            ]
        if value not in (None, "", []):
            properties[name] = value
    return {
        "id": page.get("id"),
        "url": page.get("url"),
        "title": _page_title(page),
        "archived": page.get("archived"),
        "properties": properties,
    }


def _paragraph_blocks(content: str) -> List[Dict[str, Any]]:
    paragraphs = [part.strip() for part in content.split("\n\n") if part.strip()]
    if not paragraphs:
        paragraphs = [content.strip()] if content.strip() else []
    return [
        {
            "object": "block",
            "type": "paragraph",
            "paragraph": {"rich_text": [{"type": "text", "text": {"content": part[:2000]}}]},
        }
        for part in paragraphs
    ]


def _title_property(title: str) -> Dict[str, Any]:
    return {"title": [{"type": "text", "text": {"content": title}}]}


def _encode_property(name: str, value: Any) -> Dict[str, Any]:
    """Map a simple value to a Notion property payload."""
    if isinstance(value, dict) and any(
        key in value
        for key in ("title", "rich_text", "status", "select", "date", "checkbox", "number", "url")
    ):
        return value
    key = name.lower().strip()
    if key in ("title", "name"):
        return _title_property(str(value))
    if key == "status":
        return {"status": {"name": str(value)}}
    if isinstance(value, bool):
        return {"checkbox": value}
    if isinstance(value, (int, float)):
        return {"number": value}
    if key in ("date", "due", "due date"):
        return {"date": {"start": str(value)}}
    if key == "url":
        return {"url": str(value)}
    return {"rich_text": [{"type": "text", "text": {"content": str(value)}}]}


def _encode_properties(properties: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not properties:
        return {}
    return {name: _encode_property(name, value) for name, value in properties.items()}


def _context_notion(context: Optional[Dict[str, Any]]) -> Dict[str, str]:
    if not context:
        return {}
    notion = context.get("notion") or {}
    return {
        "page_id": notion.get("page_id") or "",
        "database_id": notion.get("database_id") or "",
    }


def _missing_id_error(kind: str) -> ToolResult:
    return ToolResult(
        success=False,
        error=(
            f"{kind} is required. Pass it in the tool call, or "
            f"`@benedict link notion <url>` in this channel first."
        ),
    )


class RunNotionTool(Tool):
    """Read and write Notion via the host's integration token."""

    def __init__(self, client: Optional[Any] = None):
        super().__init__(
            name="run_notion",
            description=(
                "Read and write Notion using NOTION_API_KEY. "
                "Reads: search, get_page, query_database. "
                "Writes: create_page, update_page (properties / card status), append_content. "
                "Prefer this channel's linked page_id or database_id when the user does not pass an id. "
                "Ask the user before creating or editing pages or cards. "
                "Share target pages with the integration or Notion returns object_not_found."
            ),
        )
        self._client = client

    def get_schema(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": list(SUPPORTED_ACTIONS),
                        "description": "Notion action to perform.",
                    },
                    "query": {"type": "string", "description": "Search query for action=search."},
                    "page_id": {
                        "type": "string",
                        "description": "Page or card id. Defaults to the channel's linked page.",
                    },
                    "database_id": {
                        "type": "string",
                        "description": "Database/board id. Defaults to the channel's linked database.",
                    },
                    "parent_page_id": {
                        "type": "string",
                        "description": "Parent page for create_page when not creating a database card.",
                    },
                    "title": {"type": "string", "description": "Title for create_page."},
                    "content": {
                        "type": "string",
                        "description": "Markdown-ish paragraphs for create_page or append_content.",
                    },
                    "properties": {
                        "type": "object",
                        "description": (
                            "Page/card properties. Simple strings are fine: "
                            '{"Name":"Fix login","Status":"In progress"}.'
                        ),
                    },
                    "filter": {
                        "type": "object",
                        "description": "Notion database filter object for query_database.",
                    },
                    "page_size": {
                        "type": "integer",
                        "description": f"Max items for search/query. Default {DEFAULT_PAGE_SIZE}, max {MAX_PAGE_SIZE}.",
                    },
                    "start_cursor": {"type": "string", "description": "Pagination cursor."},
                },
                "required": ["action"],
            },
        }

    def _client_or_error(self) -> Tuple[Optional[Any], Optional[ToolResult]]:
        if self._client is not None:
            return self._client, None
        api_key = os.getenv(NOTION_API_KEY_ENV_VAR)
        if not api_key:
            return None, ToolResult(
                success=False,
                error=(
                    f"{NOTION_API_KEY_ENV_VAR} is not configured on the host running Benedict. "
                    "Create a Notion internal integration, share pages with it, and set the token."
                ),
            )
        return Client(auth=api_key), None

    def execute(
        self, arguments: Dict[str, Any], context: Optional[Dict[str, Any]] = None
    ) -> ToolResult:
        client, error = self._client_or_error()
        if error:
            return error

        action = arguments.get("action")
        linked = _context_notion(context)
        page_size = min(max(int(arguments.get("page_size") or DEFAULT_PAGE_SIZE), 1), MAX_PAGE_SIZE)
        start_cursor = arguments.get("start_cursor")
        page_id = arguments.get("page_id") or linked.get("page_id")
        database_id = arguments.get("database_id") or linked.get("database_id")

        try:
            if action == "search":
                query = arguments.get("query")
                if not query:
                    return ToolResult(success=False, error="query is required when action=search")
                kwargs: Dict[str, Any] = {"query": query, "page_size": page_size}
                if start_cursor:
                    kwargs["start_cursor"] = start_cursor
                result = client.search(**kwargs)
                pages = [
                    _summarize_page(item)
                    for item in result.get("results") or []
                    if item.get("object") in ("page", "database")
                ]
                return ToolResult(
                    success=True,
                    data=_sanitize_output(
                        {
                            "results": pages,
                            "next_cursor": result.get("next_cursor"),
                            "has_more": result.get("has_more"),
                        }
                    ),
                )

            if action == "get_page":
                if not page_id:
                    return _missing_id_error("page_id")
                page = client.pages.retrieve(page_id=page_id)
                children = client.blocks.children.list(block_id=page_id, page_size=page_size)
                lines = [_block_to_text(block) for block in children.get("results") or []]
                summary = _summarize_page(page)
                summary["content"] = "\n".join(line for line in lines if line)
                summary["has_more_blocks"] = children.get("has_more")
                return ToolResult(success=True, data=_sanitize_output(summary))

            if action == "query_database":
                if not database_id:
                    return _missing_id_error("database_id")
                kwargs = {"database_id": database_id, "page_size": page_size}
                if arguments.get("filter"):
                    kwargs["filter"] = arguments["filter"]
                if start_cursor:
                    kwargs["start_cursor"] = start_cursor
                result = client.databases.query(**kwargs)
                return ToolResult(
                    success=True,
                    data=_sanitize_output(
                        {
                            "results": [
                                _summarize_page(item) for item in result.get("results") or []
                            ],
                            "next_cursor": result.get("next_cursor"),
                            "has_more": result.get("has_more"),
                        }
                    ),
                )

            if action == "create_page":
                title = arguments.get("title")
                if not title:
                    return ToolResult(
                        success=False, error="title is required when action=create_page"
                    )
                parent_database = arguments.get("database_id") or (
                    None if arguments.get("parent_page_id") else linked.get("database_id")
                )
                parent_page_id = arguments.get("parent_page_id") or (
                    None if parent_database else linked.get("page_id")
                )
                properties = _encode_properties(arguments.get("properties"))
                if parent_database:
                    parent = {"database_id": parent_database}
                    has_title = any(name.lower() in ("name", "title") for name in properties)
                    if not has_title:
                        properties["Name"] = _title_property(title)
                elif parent_page_id:
                    parent = {"page_id": parent_page_id}
                    properties["title"] = _title_property(title)
                else:
                    return ToolResult(
                        success=False,
                        error=(
                            "create_page needs database_id or parent_page_id "
                            "(or a linked Notion page/database on this channel)."
                        ),
                    )
                payload: Dict[str, Any] = {"parent": parent, "properties": properties}
                content = arguments.get("content")
                if content:
                    payload["children"] = _paragraph_blocks(content)
                created = client.pages.create(**payload)
                return ToolResult(
                    success=True,
                    message=f"Created Notion page `{_page_title(created)}`",
                    data=_sanitize_output(_summarize_page(created)),
                )

            if action == "update_page":
                if not page_id:
                    return _missing_id_error("page_id")
                properties = arguments.get("properties")
                if not properties:
                    return ToolResult(
                        success=False,
                        error="properties is required when action=update_page",
                    )
                updated = client.pages.update(
                    page_id=page_id, properties=_encode_properties(properties)
                )
                return ToolResult(
                    success=True,
                    message=f"Updated Notion page `{_page_title(updated)}`",
                    data=_sanitize_output(_summarize_page(updated)),
                )

            if action == "append_content":
                if not page_id:
                    return _missing_id_error("page_id")
                content = arguments.get("content")
                if not content:
                    return ToolResult(
                        success=False, error="content is required when action=append_content"
                    )
                client.blocks.children.append(block_id=page_id, children=_paragraph_blocks(content))
                return ToolResult(
                    success=True, message=f"Appended content to Notion page `{page_id}`"
                )

            return ToolResult(success=False, error=f"Unsupported Notion action: {action}")
        except APIResponseError as exc:
            logger.warning("Notion API error while running %s: %s", action, exc)
            code = getattr(exc, "code", None)
            hint = ""
            if code in ("object_not_found", "unauthorized"):
                hint = (
                    " Share the page or database with the Benedict integration in Notion, "
                    "then try again."
                )
            return ToolResult(
                success=False,
                error=f"Notion API error for {action}: {code or 'unknown_error'}: {exc}.{hint}",
            )


def probe_notion_id(
    notion_id: str, client: Optional[Any] = None
) -> Tuple[bool, str, Dict[str, str]]:
    """Return whether the integration can see this id, and whether it is a page or database."""
    tool = RunNotionTool(client=client)
    live_client, error = tool._client_or_error()
    if error:
        return False, error.error or "Notion is not configured.", {}
    try:
        page = live_client.pages.retrieve(page_id=notion_id)
        title = _page_title(page)
        state = {"page_id": notion_id, "url": page.get("url") or "", "title": title}
        parent = page.get("parent") or {}
        if parent.get("type") == "database_id" and parent.get("database_id"):
            state["database_id"] = parent["database_id"]
        return True, title, state
    except APIResponseError:
        pass
    try:
        database = live_client.databases.retrieve(database_id=notion_id)
        title = _plain_text(database.get("title") or []) or notion_id
        return (
            True,
            title,
            {
                "database_id": notion_id,
                "url": database.get("url") or "",
                "title": title,
            },
        )
    except APIResponseError as exc:
        code = getattr(exc, "code", None)
        message = (
            "I can't see that page with the Notion integration on this machine. "
            "In Notion, open it → Share → invite the Benedict integration, then run "
            "`link notion` again."
        )
        if code:
            message = f"{message} ({code})"
        return False, message, {}

"""Notion API tools for conversational read access."""

import logging
import os
import re
from typing import Any, Dict, Optional

from notion_client import Client
from notion_client.errors import APIResponseError

from .tool_framework import Tool, ToolResult

logger = logging.getLogger(__name__)

NOTION_API_KEY_ENV_VAR = "NOTION_API_KEY"
DEFAULT_PAGE_SIZE = 10
MAX_PAGE_SIZE = 100
MAX_OUTPUT_CHARS = 32000
_TOKEN_RE = re.compile(r"(secret_[A-Za-z0-9]+|ntn_[A-Za-z0-9]+)")


def _truncate(text: str, limit: int = MAX_OUTPUT_CHARS) -> str:
    """Truncate text and note if it was cut."""
    if text is None:
        return ""
    if len(text) <= limit:
        return text
    return text[:limit] + f"\n...[truncated, {len(text) - limit} chars omitted]"


def _redact_tokens(text: str) -> str:
    """Redact Notion token-shaped strings from tool output."""
    if not text:
        return text
    return _TOKEN_RE.sub("[redacted-token]", text)


def _sanitize_output(value: Any) -> Any:
    """Recursively redact secrets and cap oversized string payloads."""
    if isinstance(value, str):
        return _redact_tokens(_truncate(value))
    if isinstance(value, list):
        return [_sanitize_output(item) for item in value]
    if isinstance(value, dict):
        return {key: _sanitize_output(item) for key, item in value.items()}
    return value


class RunNotionTool(Tool):
    """Read-only Notion API tool for Benedict conversations."""

    def __init__(self):
        super().__init__(
            name="run_notion",
            description=(
                "Read from Notion using the host's NOTION_API_KEY. Supported actions are "
                "`search`, `retrieve_page`, `retrieve_page_markdown`, and "
                "`list_block_children`. This tool is read-only."
            ),
        )

    def get_schema(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": [
                            "search",
                            "retrieve_page",
                            "retrieve_page_markdown",
                            "list_block_children",
                        ],
                        "description": "Read-only Notion action to perform.",
                    },
                    "query": {
                        "type": "string",
                        "description": "Search query to use when action=`search`.",
                    },
                    "page_id": {
                        "type": "string",
                        "description": (
                            "Notion page ID for `retrieve_page` or `retrieve_page_markdown`."
                        ),
                    },
                    "block_id": {
                        "type": "string",
                        "description": "Notion block ID for `list_block_children`.",
                    },
                    "page_size": {
                        "type": "integer",
                        "description": (
                            f"Maximum items to return for paginated actions. "
                            f"Defaults to {DEFAULT_PAGE_SIZE}; max {MAX_PAGE_SIZE}."
                        ),
                    },
                    "start_cursor": {
                        "type": "string",
                        "description": "Pagination cursor returned by a previous Notion response.",
                    },
                },
                "required": ["action"],
            },
        }

    def execute(
        self, arguments: Dict[str, Any], context: Optional[Dict[str, Any]] = None
    ) -> ToolResult:
        api_key = os.getenv(NOTION_API_KEY_ENV_VAR)
        if not api_key:
            return ToolResult(
                success=False,
                error=(
                    f"{NOTION_API_KEY_ENV_VAR} is not configured on the host running Benedict. "
                    "Add a Notion integration token before using run_notion."
                ),
            )

        action = arguments.get("action")
        page_size = min(max(arguments.get("page_size", DEFAULT_PAGE_SIZE), 1), MAX_PAGE_SIZE)
        start_cursor = arguments.get("start_cursor")

        client = Client(auth=api_key)

        try:
            if action == "search":
                query = arguments.get("query")
                if not query:
                    return ToolResult(
                        success=False,
                        error="query is required when action=search",
                    )
                result = client.search(
                    query=query,
                    page_size=page_size,
                    **({"start_cursor": start_cursor} if start_cursor else {}),
                )
                sanitized = _sanitize_output(result)
                return ToolResult(success=True, data=sanitized)

            if action == "retrieve_page":
                page_id = arguments.get("page_id")
                if not page_id:
                    return ToolResult(
                        success=False,
                        error="page_id is required when action=retrieve_page",
                    )
                sanitized = _sanitize_output(client.pages.retrieve(page_id=page_id))
                return ToolResult(success=True, data=sanitized)

            if action == "retrieve_page_markdown":
                page_id = arguments.get("page_id")
                if not page_id:
                    return ToolResult(
                        success=False,
                        error="page_id is required when action=retrieve_page_markdown",
                    )
                markdown = client.pages.retrieve_markdown(page_id=page_id)
                return ToolResult(success=True, message=_sanitize_output(markdown))

            if action == "list_block_children":
                block_id = arguments.get("block_id")
                if not block_id:
                    return ToolResult(
                        success=False,
                        error="block_id is required when action=list_block_children",
                    )
                result = client.blocks.children.list(
                    block_id=block_id,
                    page_size=page_size,
                    **({"start_cursor": start_cursor} if start_cursor else {}),
                )
                sanitized = _sanitize_output(result)
                return ToolResult(success=True, data=sanitized)

            return ToolResult(success=False, error=f"Unsupported Notion action: {action}")
        except APIResponseError as exc:
            logger.warning("Notion API error while running %s: %s", action, exc)
            code = getattr(exc, "code", None)
            return ToolResult(
                success=False,
                error=f"Notion API error for {action}: {code or 'unknown_error'}: {exc}",
            )

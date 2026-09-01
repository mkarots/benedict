"""Structured Slack replies from agent handlers.

Handlers return these instead of emoji-prefixed strings. ``slack.messages``
renders them to Block Kit. Conversation LLM text stays ``MarkdownPayload``.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Dict, Mapping, Optional, Sequence, Tuple, Union


@dataclass(frozen=True)
class StatusPayload:
    """Channel status as title plus fields, not a formatted string."""

    success: bool
    title: str
    fields: Dict[str, str]
    emoji: str = "📊"

    def text(self) -> str:
        """Plain-text form for the operator log."""
        lines = [f"{self.emoji} *{self.title}*"]
        lines.extend(f"{key}: {value}" for key, value in self.fields.items())
        return "\n".join(lines)


@dataclass(frozen=True)
class ErrorPayload:
    """Typed error for Block Kit. ``success`` is always false."""

    error_type: str
    message: str
    next_steps: Optional[Tuple[str, ...]] = None
    success: bool = False

    def text(self) -> str:
        """Plain-text form for the operator log."""
        parts = [f"⚠️ {self.error_type}", "", self.message]
        if self.next_steps:
            parts.extend(["", "*Next steps:*"])
            parts.extend(f"• {step}" for step in self.next_steps)
        return "\n".join(parts)


@dataclass(frozen=True)
class MarkdownPayload:
    """Command copy or LLM markdown. Slack chooses Block Kit vs auto."""

    success: bool
    markdown: str

    def text(self) -> str:
        """Plain-text form for the operator log."""
        return self.markdown


def markdown(success: bool, text: str) -> MarkdownPayload:
    """Build a markdown reply (commands and conversation)."""
    return MarkdownPayload(success=success, markdown=text)


def error(
    error_type: str,
    message: str,
    next_steps: Optional[Sequence[str]] = None,
) -> ErrorPayload:
    """Build an error reply with optional next-step lines."""
    steps = tuple(next_steps) if next_steps is not None else None
    return ErrorPayload(error_type=error_type, message=message, next_steps=steps)


def with_channel_name(payload: StatusPayload, channel_name: str) -> StatusPayload:
    """Put the Slack channel first in status fields."""
    fields = {"Channel": f"#{channel_name}", **payload.fields}
    return replace(payload, fields=fields)


def status(
    *,
    title: str,
    fields: Mapping[str, str],
    emoji: str = "📊",
    success: bool = True,
) -> StatusPayload:
    """Build a status reply from already-structured fields."""
    return StatusPayload(success=success, title=title, fields=dict(fields), emoji=emoji)


SlackPayload = Union[StatusPayload, ErrorPayload, MarkdownPayload]

"""Slack message delivery.

Owns how Benedict replies look in Slack: message type, Block Kit vs plain text,
chunking to API limits, and calling Bolt ``say``. Event handlers stay in
``slack.app``; mrkdwn and Block Kit construction stay in ``slack.formatter``.
"""

import re
from typing import Any, Dict, List, Optional, Tuple

from .formatter import BlockKitFormatter, SlackFormatter

# Agent status strings use these title emojis: "📊 *Channel Status*"
_STATUS_TITLE_EMOJIS = ("📊", "✅", "⚠️")
_STATUS_FIELD_EMOJI_PATTERN = r"([📊🔗⏰👤📺])\s*(.+?):\s*(.+)"


def parse_error_message(message: str) -> Tuple[str, str, Optional[List[str]]]:
    """Split an agent error string into header, body, and optional next steps.

    Accepts both `⚠️ Type\\n\\nbody` and `⚠️ Type:\\n- detail` so Slack does not
    wrap the original warning in a second "Error" header.
    """
    error_match = re.match(r"⚠️\s*(.+?)\n+(.+)", message, re.DOTALL)
    if not error_match:
        return "Error", message, None

    error_type = error_match.group(1).strip().rstrip(":")
    error_msg = error_match.group(2).strip()
    next_steps_match = re.search(r"Next steps?[:\n]+(.+)", error_msg, re.IGNORECASE)
    next_steps = None
    if next_steps_match:
        steps_text = next_steps_match.group(1)
        next_steps = [s.strip() for s in steps_text.split("\n") if s.strip()]
    return error_type, error_msg, next_steps


def parse_status_message(message: str) -> Tuple[str, Dict[str, str], Optional[str]]:
    """Parse an agent status string into title, fields, and emoji.

    Expected shape::

        📊 *Title*
        ━━━━━━━━━━━━━━━
        🔗 Field: value

    Returns:
        ``(title, fields, emoji)``. ``title`` is empty when parsing fails.
    """
    title = ""
    fields: Dict[str, str] = {}

    for line in message.split("\n"):
        line = line.strip()
        if not line:
            continue

        if not title and any(emoji in line for emoji in _STATUS_TITLE_EMOJIS):
            title = _status_title_from_line(line)
            continue

        if line.startswith("━") or line.startswith("─"):
            continue

        field_match = re.match(_STATUS_FIELD_EMOJI_PATTERN, line)
        if field_match:
            _emoji, key, value = field_match.groups()
            fields[_strip_markdown(key)] = value.strip()
            continue

        key_value_match = re.match(r"(.+?):\s*(.+)", line)
        if key_value_match:
            key, value = key_value_match.groups()
            fields[_strip_markdown(key)] = value.strip()

    emoji = next((mark for mark in _STATUS_TITLE_EMOJIS if mark in message), None)
    return title, fields, emoji


def format_message_payload(
    message: str,
    message_type: str = "conversation",
    use_block_kit: Optional[bool] = None,
) -> Optional[Dict[str, Any]]:
    """Build a Slack ``say`` payload for ``message``.

    Args:
        message: Agent reply text.
        message_type: ``conversation``, ``status``, ``error``, or ``command``.
        use_block_kit: Force Block Kit (auto-detect if None).

    Returns:
        Keyword arguments for ``say`` (without ``thread_ts``), or ``None``
        when ``message`` is empty.
    """
    if not message:
        return None

    if message_type == "status":
        title, fields, emoji = parse_status_message(message)
        if title and fields:
            return BlockKitFormatter.format_status_message(title, fields, emoji)
        return BlockKitFormatter.format_message(message, use_block_kit=use_block_kit)

    if message_type == "error":
        error_type, error_msg, next_steps = parse_error_message(message)
        return BlockKitFormatter.format_error_message(error_type, error_msg, next_steps)

    if message_type == "command":
        return BlockKitFormatter.format_message(message, use_block_kit=True)

    return BlockKitFormatter.format_message(message, use_block_kit=use_block_kit)


def format_and_send_message(
    say: Any,
    message: str,
    thread_ts: Optional[str] = None,
    message_type: str = "conversation",
    use_block_kit: Optional[bool] = None,
) -> None:
    """Format and send a message to Slack.

    Handles message formatting, chunking, and Block Kit formatting based on
    message type and content.

    Args:
        say: Slack say function
        message: Message text to send
        thread_ts: Optional thread timestamp for replies
        message_type: Type of message ("conversation", "status", "error", "command")
        use_block_kit: Force Block Kit usage (auto-detect if None)
    """
    formatted = format_message_payload(message, message_type, use_block_kit)
    if formatted is None:
        return
    _deliver_formatted(say, formatted, original_message=message, thread_ts=thread_ts)


def _status_title_from_line(line: str) -> str:
    title_match = re.search(r"[📊✅⚠️]\s*\*{1,2}(.+?)\*{1,2}", line)
    if title_match:
        return title_match.group(1).strip()
    if line.startswith(_STATUS_TITLE_EMOJIS):
        title = line
        for mark in _STATUS_TITLE_EMOJIS:
            title = title.replace(mark, "")
        return title.replace("*", "").strip()
    return ""


def _strip_markdown(text: str) -> str:
    return re.sub(r"\*+", "", text).strip()


def _section_text_length(formatted: Dict[str, Any]) -> int:
    return sum(
        len(block.get("text", {}).get("text", ""))
        for block in formatted.get("blocks", [])
        if block.get("type") == "section" and "text" in block
    )


def _deliver_formatted(
    say: Any,
    formatted: Dict[str, Any],
    *,
    original_message: str,
    thread_ts: Optional[str],
) -> None:
    if "blocks" in formatted:
        if _section_text_length(formatted) > SlackFormatter.MAX_MESSAGE_LENGTH:
            chunks = SlackFormatter.split_message(original_message)
            for i, chunk in enumerate(chunks):
                chunk_formatted = BlockKitFormatter.format_message(chunk, use_block_kit=True)
                if len(chunks) > 1 and i == 0 and "blocks" in chunk_formatted:
                    chunk_formatted["blocks"].insert(
                        0, BlockKitFormatter.create_context(f"_Part {i + 1} of {len(chunks)}_")
                    )
                say(**chunk_formatted, thread_ts=thread_ts)
            return
        say(**formatted, thread_ts=thread_ts)
        return

    text = formatted.get("text", "")
    if len(text) > SlackFormatter.MAX_MESSAGE_LENGTH:
        chunks = SlackFormatter.split_message(text)
        for i, chunk in enumerate(chunks):
            if len(chunks) > 1:
                chunk = f"_Part {i + 1} of {len(chunks)}_\n\n{chunk}"
            say(text=chunk, thread_ts=thread_ts)
        return
    say(**formatted, thread_ts=thread_ts)

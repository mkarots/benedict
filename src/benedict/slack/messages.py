"""Slack message delivery.

Owns how Benedict replies look in Slack: payload type, Block Kit vs plain text,
chunking to API limits, and calling Bolt ``say``. Event handlers stay in
``slack.app``; mrkdwn and Block Kit construction stay in ``slack.formatter``.
"""

from typing import Any, Dict, Optional

from .formatter import BlockKitFormatter, SlackFormatter
from .payloads import ErrorPayload, SlackPayload, StatusPayload


def render(payload: SlackPayload) -> Optional[Dict[str, Any]]:
    """Turn a handler reply into Slack ``say`` keyword arguments.

    Returns:
        Keyword arguments for ``say`` (without ``thread_ts``), or ``None``
        when markdown is empty.
    """
    if isinstance(payload, StatusPayload):
        if payload.title and payload.fields:
            return BlockKitFormatter.format_status_message(
                payload.title, payload.fields, payload.emoji
            )
        return BlockKitFormatter.format_message(payload.text())

    if isinstance(payload, ErrorPayload):
        next_steps = list(payload.next_steps) if payload.next_steps else None
        return BlockKitFormatter.format_error_message(
            payload.error_type, payload.message, next_steps
        )

    if not payload.markdown:
        return None

    return BlockKitFormatter.format_message(payload.markdown, use_block_kit=payload.force_block_kit)


def post_reply(
    payload: SlackPayload,
    *,
    say: Any,
    thread_ts: Optional[str] = None,
) -> None:
    """Post this handler reply to Slack, in ``thread_ts`` when given.

    ``say`` is Bolt's post function. The payload already knows whether it is
    status, error, command, or conversation markdown.
    """
    formatted = render(payload)
    if formatted is None:
        return
    _deliver_formatted(say, formatted, original_message=payload.text(), thread_ts=thread_ts)


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

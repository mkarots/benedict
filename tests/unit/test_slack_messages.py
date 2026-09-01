"""Tests for Slack message delivery."""

from unittest.mock import Mock

from benedict.slack.messages import (
    _deliver_formatted,
    format_and_send_message,
    format_message_payload,
)
from benedict.slack.payloads import error, markdown, status


def test_format_message_payload_empty_markdown_returns_none():
    assert format_message_payload(markdown(True, "")) is None


def test_format_message_payload_status_uses_header_and_fields():
    payload = format_message_payload(
        status(title="Channel Status", fields={"Repository": "`org/repo`"}),
    )
    assert payload is not None
    assert "blocks" in payload
    header = payload["blocks"][0]
    assert header["type"] == "header"
    assert "Channel Status" in header["text"]["text"]
    field_text = payload["blocks"][2]["fields"][0]["text"]
    assert "*Repository:*" in field_text
    assert "`org/repo`" in field_text


def test_format_message_payload_status_falls_back_without_fields():
    payload = format_message_payload(status(title="Empty", fields={}))
    assert payload is not None
    assert "blocks" in payload or "text" in payload


def test_format_message_payload_error_does_not_double_wrap_header():
    payload = format_message_payload(
        error("Some operations failed", "- Metadata file not found"),
    )
    assert payload is not None
    headers = [block["text"]["text"] for block in payload["blocks"] if block["type"] == "header"]
    assert headers == ["⚠️ Some operations failed"]


def test_format_message_payload_error_puts_next_steps_in_own_section():
    payload = format_message_payload(
        error(
            "Not Onboarded",
            "This channel hasn't been onboarded yet.",
            next_steps=["Use onboard"],
        ),
    )
    assert payload is not None
    texts = [
        block.get("text", {}).get("text", "")
        for block in payload["blocks"]
        if block.get("type") == "section" and "text" in block
    ]
    assert any("hasn't been onboarded" in text for text in texts)
    assert any("*Next steps:*" in text and "Use onboard" in text for text in texts)
    assert sum("*Next steps:*" in text for text in texts) == 1


def test_format_message_payload_command_uses_block_kit():
    payload = format_message_payload(
        markdown(True, "Onboarded `org/repo`."),
        message_type="command",
    )
    assert payload is not None
    assert "blocks" in payload


def test_format_and_send_message_skips_empty():
    say = Mock()
    format_and_send_message(say, markdown(True, ""))
    say.assert_not_called()


def test_format_and_send_message_conversation_passes_thread_ts():
    say = Mock()
    format_and_send_message(
        say, markdown(True, "hello"), thread_ts="123.456", message_type="conversation"
    )
    say.assert_called_once()
    kwargs = say.call_args.kwargs
    assert kwargs["thread_ts"] == "123.456"


def test_format_and_send_message_status_sends_blocks():
    say = Mock()
    format_and_send_message(
        say,
        status(title="Channel Status", fields={"Repository": "`org/repo`"}),
        thread_ts="9.9",
    )
    say.assert_called_once()
    kwargs = say.call_args.kwargs
    assert kwargs["thread_ts"] == "9.9"
    assert kwargs["blocks"][0]["type"] == "header"


def test_deliver_formatted_plain_text_chunks_when_over_limit():
    say = Mock()
    long_text = "word " * 1000
    _deliver_formatted(
        say,
        {"text": long_text},
        original_message=long_text,
        thread_ts="1.0",
    )
    assert say.call_count > 1
    assert "Part 1 of" in say.call_args_list[0].kwargs["text"]
    assert say.call_args_list[0].kwargs["thread_ts"] == "1.0"


def test_format_and_send_message_block_kit_chunks_when_over_limit():
    say = Mock()
    format_and_send_message(
        say,
        markdown(True, "paragraph of details about the repo. " * 200),
        message_type="conversation",
        use_block_kit=True,
    )
    assert say.call_count > 1
    first_blocks = say.call_args_list[0].kwargs["blocks"]
    assert first_blocks[0]["type"] == "context"
    assert "Part 1 of" in first_blocks[0]["elements"][0]["text"]

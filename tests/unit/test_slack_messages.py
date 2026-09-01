"""Tests for Slack message delivery."""

from unittest.mock import Mock

from benedict.slack.messages import (
    _deliver_formatted,
    post_reply,
    render,
)
from benedict.slack.payloads import command, error, markdown, status


def test_render_empty_markdown_returns_none():
    assert render(markdown(True, "")) is None


def test_render_status_uses_header_and_fields():
    payload = render(
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


def test_render_status_falls_back_without_fields():
    payload = render(status(title="Empty", fields={}))
    assert payload is not None
    assert "blocks" in payload or "text" in payload


def test_render_error_does_not_double_wrap_header():
    payload = render(
        error("Some operations failed", "- Metadata file not found"),
    )
    assert payload is not None
    headers = [block["text"]["text"] for block in payload["blocks"] if block["type"] == "header"]
    assert headers == ["⚠️ Some operations failed"]


def test_render_error_puts_next_steps_in_own_section():
    payload = render(
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


def test_render_command_uses_block_kit():
    payload = render(command(True, "Onboarded `org/repo`."))
    assert payload is not None
    assert "blocks" in payload


def test_post_reply_skips_empty():
    say = Mock()
    post_reply(markdown(True, ""), say=say)
    say.assert_not_called()


def test_post_reply_passes_thread_ts():
    say = Mock()
    post_reply(markdown(True, "hello"), say=say, thread_ts="123.456")
    say.assert_called_once()
    kwargs = say.call_args.kwargs
    assert kwargs["thread_ts"] == "123.456"


def test_post_reply_status_sends_blocks():
    say = Mock()
    post_reply(
        status(title="Channel Status", fields={"Repository": "`org/repo`"}),
        say=say,
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


def test_post_reply_block_kit_chunks_when_over_limit():
    say = Mock()
    post_reply(
        markdown(True, "paragraph of details about the repo. " * 200, force_block_kit=True),
        say=say,
    )
    assert say.call_count > 1
    first_blocks = say.call_args_list[0].kwargs["blocks"]
    assert first_blocks[0]["type"] == "context"
    assert "Part 1 of" in first_blocks[0]["elements"][0]["text"]

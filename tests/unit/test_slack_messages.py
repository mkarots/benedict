"""Tests for Slack message delivery."""

from unittest.mock import Mock

from benedict.slack_messages import (
    _deliver_formatted,
    format_and_send_message,
    format_message_payload,
    parse_error_message,
    parse_status_message,
)


def test_parse_error_message_blank_line_body():
    error_type, body, next_steps = parse_error_message(
        "⚠️ Repository Read Error\n\nError reading repository `example`."
    )
    assert error_type == "Repository Read Error"
    assert "Error reading repository" in body
    assert next_steps is None


def test_parse_error_message_single_newline_does_not_double_wrap():
    error_type, body, next_steps = parse_error_message(
        "⚠️ Some operations failed:\n- Metadata file not found"
    )
    assert error_type == "Some operations failed"
    assert body == "- Metadata file not found"
    assert next_steps is None


def test_parse_error_message_plain_text_fallback():
    error_type, body, next_steps = parse_error_message("something went wrong")
    assert error_type == "Error"
    assert body == "something went wrong"
    assert next_steps is None


def test_parse_error_message_extracts_next_steps():
    error_type, body, next_steps = parse_error_message(
        "⚠️ Not Onboarded\n\nThis channel is not onboarded.\n\nNext steps:\nUse onboard"
    )
    assert error_type == "Not Onboarded"
    assert "not onboarded" in body
    assert next_steps == ["Use onboard"]


def test_parse_status_message_channel_status():
    title, fields, emoji = parse_status_message(
        "📊 *Channel Status*\n"
        "\n"
        "━━━━━━━━━━━━━━━\n"
        "🔗 Repository: `org/repo`\n"
        "⏰ Onboarded: 2026-09-01 12:00 UTC\n"
        "👤 By: <@U123>\n"
        "📺 Channel: #eng"
    )
    assert title == "Channel Status"
    assert emoji == "📊"
    assert fields["Repository"] == "`org/repo`"
    assert fields["Onboarded"] == "2026-09-01 12:00 UTC"
    assert fields["By"] == "<@U123>"
    assert fields["Channel"] == "#eng"


def test_parse_status_message_key_value_without_emoji():
    title, fields, emoji = parse_status_message("📊 *Status*\nRepo: org/repo")
    assert title == "Status"
    assert emoji == "📊"
    assert fields["Repo"] == "org/repo"


def test_parse_status_message_unstructured_has_empty_title():
    title, fields, emoji = parse_status_message("just a line of text")
    assert title == ""
    assert fields == {}
    assert emoji is None


def test_parse_status_message_title_without_bold():
    title, fields, emoji = parse_status_message("📊 Channel Status\n🔗 Repository: `org/repo`")
    assert title == "Channel Status"
    assert emoji == "📊"
    assert fields["Repository"] == "`org/repo`"


def test_format_message_payload_empty_returns_none():
    assert format_message_payload("") is None


def test_format_message_payload_status_uses_header_and_fields():
    payload = format_message_payload(
        "📊 *Channel Status*\n━━━━━━━━━━━━━━━\n🔗 Repository: `org/repo`",
        message_type="status",
    )
    assert payload is not None
    assert "blocks" in payload
    header = payload["blocks"][0]
    assert header["type"] == "header"
    assert "Channel Status" in header["text"]["text"]


def test_format_message_payload_status_falls_back_without_fields():
    payload = format_message_payload("📊 *Empty*", message_type="status")
    assert payload is not None
    assert "blocks" in payload or "text" in payload


def test_format_message_payload_error_uses_error_header():
    payload = format_message_payload(
        "⚠️ Validation Error\n\nRepo path is missing.",
        message_type="error",
    )
    assert payload is not None
    header = payload["blocks"][0]
    assert header["type"] == "header"
    assert "Validation Error" in header["text"]["text"]


def test_format_message_payload_command_uses_block_kit():
    payload = format_message_payload("Onboarded `org/repo`.", message_type="command")
    assert payload is not None
    assert "blocks" in payload


def test_format_and_send_message_skips_empty():
    say = Mock()
    format_and_send_message(say, "")
    say.assert_not_called()


def test_format_and_send_message_conversation_passes_thread_ts():
    say = Mock()
    format_and_send_message(say, "hello", thread_ts="123.456", message_type="conversation")
    say.assert_called_once()
    kwargs = say.call_args.kwargs
    assert kwargs["thread_ts"] == "123.456"


def test_format_and_send_message_status_sends_blocks():
    say = Mock()
    format_and_send_message(
        say,
        "📊 *Channel Status*\n━━━━━━━━━━━━━━━\n🔗 Repository: `org/repo`",
        thread_ts="9.9",
        message_type="status",
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
        "paragraph of details about the repo. " * 200,
        message_type="conversation",
        use_block_kit=True,
    )
    assert say.call_count > 1
    first_blocks = say.call_args_list[0].kwargs["blocks"]
    assert first_blocks[0]["type"] == "context"
    assert "Part 1 of" in first_blocks[0]["elements"][0]["text"]

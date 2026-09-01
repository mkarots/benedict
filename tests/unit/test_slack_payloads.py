"""Tests for structured Slack handler payloads."""

from dataclasses import FrozenInstanceError

import pytest

from benedict.slack.payloads import (
    ErrorPayload,
    MarkdownPayload,
    StatusPayload,
    error,
    markdown,
    status,
    with_channel_name,
)


def test_status_payload_text_lists_fields():
    payload = status(title="Channel Status", fields={"Repository": "`org/repo`"})
    assert payload.success is True
    assert payload.emoji == "📊"
    text = payload.text()
    assert "Channel Status" in text
    assert "Repository: `org/repo`" in text


def test_status_payload_is_frozen():
    payload = status(title="Channel Status", fields={"Repository": "`org/repo`"})
    with pytest.raises(FrozenInstanceError):
        payload.title = "Other"  # type: ignore[misc]


def test_with_channel_name_puts_channel_first():
    payload = status(
        title="Channel Status",
        fields={"Repository": "`org/repo`", "Onboarded": "today"},
    )
    updated = with_channel_name(payload, "eng")
    assert list(updated.fields.keys())[0] == "Channel"
    assert updated.fields["Channel"] == "#eng"
    assert updated.fields["Repository"] == "`org/repo`"
    assert payload.fields.get("Channel") is None


def test_error_payload_text_includes_next_steps():
    payload = error(
        "Not Onboarded",
        "This channel hasn't been onboarded yet.",
        next_steps=["Use onboard"],
    )
    assert payload.success is False
    assert isinstance(payload, ErrorPayload)
    text = payload.text()
    assert "⚠️ Not Onboarded" in text
    assert "hasn't been onboarded" in text
    assert "*Next steps:*" in text
    assert "• Use onboard" in text


def test_markdown_payload_text_is_the_markdown():
    payload = markdown(True, "✅ Onboarded `org/repo`.")
    assert isinstance(payload, MarkdownPayload)
    assert payload.success is True
    assert payload.text() == "✅ Onboarded `org/repo`."


def test_status_constructor_copies_fields():
    fields = {"Repository": "`org/repo`"}
    payload = status(title="Channel Status", fields=fields)
    fields["Repository"] = "mutated"
    assert payload.fields["Repository"] == "`org/repo`"
    assert isinstance(payload, StatusPayload)

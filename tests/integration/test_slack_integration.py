"""Integration-style tests for Slack message sending without a live Slack API."""

from benedict.slack_app import format_and_send_message


class FakeSay:
    def __init__(self):
        self.calls = []

    def __call__(self, **kwargs):
        self.calls.append(kwargs)


def test_format_and_send_skips_empty_message():
    say = FakeSay()
    format_and_send_message(say, "")
    assert say.calls == []


def test_format_and_send_status_message():
    say = FakeSay()
    message = (
        "📊 *Channel Status*\n"
        "━━━━━━━━━━━━━━━\n"
        "🔗 Repository: `example-org/example-repo`\n"
        "⏰ Onboarded: 2026-02-01 20:30 UTC\n"
        "👤 By: <@Ualice>"
    )
    format_and_send_message(say, message, thread_ts="111.222", message_type="status")
    assert len(say.calls) == 1
    assert say.calls[0]["thread_ts"] == "111.222"
    payload = say.calls[0]
    assert "text" in payload or "blocks" in payload

"""slack.app is Bolt routing; delivery lives in slack.messages."""

import benedict.slack.app as slack_app
from benedict.slack import messages as slack_messages
from benedict.slack.messages import format_and_send_message


def test_slack_app_reuses_slack_messages_send():
    assert slack_app.format_and_send_message is format_and_send_message
    assert not hasattr(slack_app, "parse_error_message")
    assert not hasattr(slack_app, "parse_status_message")


def test_slack_messages_has_no_string_parser():
    assert not hasattr(slack_messages, "parse_error_message")
    assert not hasattr(slack_messages, "parse_status_message")

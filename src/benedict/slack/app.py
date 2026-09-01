"""Slack App Setup

Slack Bolt app configuration and event handlers.
"""

import json
import logging
import re
import os
from typing import Any
from slack_bolt import App
from benedict.agent import RepoAgent
from benedict.operator_ui.recorder import NullActiveRun
from benedict.slack.messages import format_and_send_message
from benedict.slack.payloads import (
    MarkdownPayload,
    SlackPayload,
    StatusPayload,
    error,
    with_channel_name,
)

logger = logging.getLogger(__name__)

# Slack app will be initialized in create_slack_app() after .env is loaded
app = None


def _begin_slack_run(
    agent: RepoAgent, *, query: Any, channel_id: Any, user_id: Any, thread_ts: Any
) -> Any:
    recorder = getattr(agent, "run_recorder", None)
    if recorder is None:
        return NullActiveRun()
    repo = ""
    try:
        repo = agent.get_channel_repo(channel_id) or ""
    except Exception:
        pass
    return recorder.begin(
        source="slack",
        kind="conversation",
        query=query,
        channel_id=channel_id,
        user_id=user_id or "",
        thread_ts=thread_ts or "",
        repo=repo,
        route="",
    )


def _route_run(run: Any, *, kind: str, route: str, label: str, repo: Any = None) -> None:
    fields = {"kind": kind, "route": route}
    if repo is not None:
        fields["repo"] = repo
    run.set(**fields)
    run.add_stage("route", label=label, detail={"matched": route})


def _finish_run(run: Any, payload: SlackPayload) -> None:
    message = payload.text()
    success = payload.success
    try:
        run.add_stage(
            "reply",
            status="ok" if success else "error",
            label="slack",
            detail={"chars": len(message or "")},
        )
        run.finish(
            status="ok" if success else "error",
            reply=message,
            error=None if success else (message or "error")[:500],
        )
    except Exception:
        logger.warning("Failed to finish operator run", exc_info=True)


def create_slack_app(agent: RepoAgent) -> App:
    """Create and configure Slack app with agent.

    Args:
        agent: RepoAgent instance

    Returns:
        Configured Slack app
    """
    # Initialize Slack app (after .env is loaded)
    global app
    bot_token = os.environ.get("SLACK_BOT_TOKEN")
    if not bot_token:
        raise ValueError("SLACK_BOT_TOKEN not found in environment variables")
    app = App(token=bot_token)

    # Get bot user ID for thread detection
    bot_user_id = None
    try:
        auth_response = app.client.auth_test()
        if auth_response.get("ok"):
            bot_user_id = auth_response.get("user_id")
            logger.info(f"Bot user ID: {bot_user_id}")
    except Exception as e:
        logger.warning(f"Could not get bot user ID: {e}")

    # Register event handlers
    @app.event("app_mention")
    def handle_app_mention(event: Any, say: Any, client: Any) -> None:
        """Handle @mentions of the bot."""
        logger.info("=" * 60)
        logger.info("APP_MENTION EVENT RECEIVED!")
        logger.info(f"Full event: {json.dumps(event, indent=2)}")
        logger.info("=" * 60)

        try:
            channel_id = event["channel"]
            user_id = event["user"]
            text = event["text"]
            thread_ts = event.get("thread_ts") or event.get("ts")

            # Remove bot mention from text
            text_clean = re.sub(r"<@[A-Z0-9]+>", "", text).strip()

            logger.info(f"Processing mention in channel {channel_id}")
            logger.info(f"User: {user_id}")
            logger.info(f"Cleaned text: {text_clean}")

            run = _begin_slack_run(
                agent,
                query=text_clean,
                channel_id=channel_id,
                user_id=user_id,
                thread_ts=thread_ts,
            )
            payload: SlackPayload = MarkdownPayload(success=False, markdown="")

            try:
                try:
                    channel_info = client.conversations_info(channel=channel_id)
                    run.set(channel_name=channel_info["channel"]["name"])
                except Exception:
                    pass

                if agent.is_progress_command(text_clean):
                    _route_run(run, kind="progress", route="handle_progress", label="command")
                    payload = agent.handle_progress(channel_id, text_clean)
                    format_and_send_message(
                        say,
                        payload,
                        thread_ts,
                        message_type="command",
                    )
                    return

                if agent.is_architect_onboard_command(text_clean):
                    _route_run(
                        run, kind="command", route="handle_onboard_architect", label="command"
                    )
                    payload = agent.handle_onboard_architect(channel_id, user_id, text_clean)
                    format_and_send_message(say, payload, thread_ts, message_type="command")
                    return

                architect_channel = agent.get_architect_channel()
                if architect_channel == channel_id:
                    _route_run(
                        run, kind="architect", route="handle_architect_query", label="architect"
                    )
                    payload = agent.handle_architect_query(channel_id, text_clean, thread_ts)
                    format_and_send_message(say, payload, thread_ts, message_type="conversation")
                    return

                if agent.is_onboard_command(text_clean):
                    _route_run(run, kind="command", route="handle_onboard", label="command")
                    payload = agent.handle_onboard(channel_id, user_id, text_clean)
                    format_and_send_message(say, payload, thread_ts, message_type="command")

                elif agent.is_unlink_notion_command(text_clean):
                    _route_run(run, kind="command", route="handle_unlink_notion", label="command")
                    payload = agent.handle_unlink_notion(channel_id)
                    format_and_send_message(say, payload, thread_ts, message_type="command")

                elif agent.is_link_notion_command(text_clean):
                    _route_run(run, kind="command", route="handle_link_notion", label="command")
                    payload = agent.handle_link_notion(channel_id, text_clean)
                    format_and_send_message(say, payload, thread_ts, message_type="command")

                elif agent.is_offboard_command(text_clean):
                    _route_run(run, kind="command", route="handle_offboard", label="command")
                    payload = agent.handle_offboard(channel_id, user_id)
                    format_and_send_message(say, payload, thread_ts, message_type="command")

                elif agent.is_status_command(text_clean):
                    _route_run(run, kind="command", route="handle_status", label="command")
                    payload = agent.handle_status(channel_id)
                    if isinstance(payload, StatusPayload):
                        try:
                            channel_info = client.conversations_info(channel=channel_id)
                            payload = with_channel_name(payload, channel_info["channel"]["name"])
                        except Exception:
                            pass
                    format_and_send_message(say, payload, thread_ts)

                elif agent.is_update_index_command(text_clean):
                    _route_run(
                        run, kind="index", route="handle_update_index", label="command · index"
                    )
                    payload = agent.handle_update_index(channel_id, user_id, text_clean)
                    format_and_send_message(say, payload, thread_ts, message_type="command")

                else:
                    _route_run(
                        run,
                        kind="conversation",
                        route="handle_conversation",
                        label="conversation",
                    )
                    payload = agent.handle_conversation(channel_id, text_clean, thread_ts)
                    format_and_send_message(say, payload, thread_ts, message_type="conversation")
            finally:
                _finish_run(run, payload)

        except Exception as e:
            logger.error(f"Error handling app_mention: {e}", exc_info=True)
            thread_ts = event.get("thread_ts") or event.get("ts")
            format_and_send_message(
                say,
                error(
                    "Error",
                    f"Sorry, I encountered an error processing your request: {str(e)}",
                ),
                thread_ts,
            )

    # Register message event handler for automatic background indexing and thread replies
    @app.event("message")
    def handle_message(event: Any, say: Any, client: Any) -> None:
        """Handle message events for automatic background indexing and thread replies."""
        try:
            # Skip bot messages and messages without text
            if event.get("subtype") or not event.get("text"):
                return

            channel_id = event.get("channel")
            user_id = event.get("user")
            text = event.get("text", "")
            thread_ts = event.get("thread_ts")
            message_ts = event.get("ts")

            if not channel_id:
                return

            # Skip messages from the bot itself
            if bot_user_id and user_id == bot_user_id:
                return

            if thread_ts and getattr(agent, "progress_service", None):
                try:
                    agent.progress_service.acknowledge_reply(channel_id, thread_ts)
                except Exception:
                    logger.debug("Progress acknowledge failed", exc_info=True)

            # Skip messages that mention the bot - app_mention handler will process those
            # Check if message contains bot mention to avoid duplicate processing
            if bot_user_id and f"<@{bot_user_id}>" in text:
                return

            # Check if channel is onboarded (regular project or architect)
            repo = agent.get_channel_repo(channel_id)
            architect_channel = agent.get_architect_channel()
            is_architect_channel = architect_channel == channel_id

            if not repo and not is_architect_channel:
                return  # Channel not onboarded, skip processing

            # Check if this is a thread reply where Benedict has already participated
            is_thread_reply = thread_ts is not None
            should_respond = False

            if is_thread_reply and bot_user_id:
                try:
                    # Check if bot has messages in this thread
                    thread_replies = client.conversations_replies(channel=channel_id, ts=thread_ts)
                    if thread_replies.get("ok"):
                        messages = thread_replies.get("messages", [])
                        # Check if bot has any messages in this thread
                        bot_has_messages = any(msg.get("user") == bot_user_id for msg in messages)
                        if bot_has_messages:
                            should_respond = True
                            logger.info(
                                f"Detected thread reply to Benedict in thread {thread_ts} "
                                f"in channel {channel_id}"
                            )
                except Exception as e:
                    logger.debug(f"Error checking thread for bot participation: {e}")

            # If not a thread reply, check if message seems directed at the bot
            if not should_respond and not is_thread_reply:
                if agent.is_message_directed_at_bot(text):
                    should_respond = True
                    logger.info(
                        f"Detected message directed at Benedict in channel {channel_id}: {text[:50]}..."
                    )

            # If message is directed at Benedict, handle it as a conversation
            if should_respond:
                conversation_ts = thread_ts or message_ts
                run = _begin_slack_run(
                    agent,
                    query=text,
                    channel_id=channel_id,
                    user_id=user_id,
                    thread_ts=conversation_ts,
                )
                payload: SlackPayload = MarkdownPayload(success=False, markdown="")
                try:
                    if is_architect_channel:
                        _route_run(
                            run,
                            kind="architect",
                            route="handle_architect_query",
                            label="architect",
                        )
                        payload = agent.handle_architect_query(channel_id, text, conversation_ts)
                    else:
                        _route_run(
                            run,
                            kind="conversation",
                            route="handle_conversation",
                            label="conversation",
                        )
                        payload = agent.handle_conversation(channel_id, text, conversation_ts)

                    format_and_send_message(
                        say, payload, conversation_ts, message_type="conversation"
                    )
                except Exception as e:
                    logger.error(f"Error handling message directed at bot: {e}", exc_info=True)
                    payload = MarkdownPayload(success=False, markdown=str(e))
                finally:
                    _finish_run(run, payload)

            # Trigger background indexing of new messages
            # This runs asynchronously and doesn't block the response
            try:
                agent.index_new_slack_messages(channel_id)
            except Exception as e:
                logger.warning(
                    f"Error in background indexing for channel {channel_id}: {e}", exc_info=True
                )
                # Don't fail - background indexing errors shouldn't affect the app

        except Exception as e:
            logger.debug(f"Error handling message event: {e}")

    return app

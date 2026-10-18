"""Localhost HTTP chat API for non-Slack clients (phone cell, scripts).

Binds to loopback only. Same RepoAgent as Slack, so one process owns
channel state. The operator UI stays read-only.
"""

from __future__ import annotations

import json
import logging
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict, Optional, Protocol, Tuple
from urllib.parse import urlparse

from benedict.operator_ui.recorder import NullActiveRun
from benedict.slack.payloads import SlackPayload


class ConversationAgent(Protocol):
    """Minimum agent surface the chat API needs."""

    def handle_conversation(self, channel_id: str, text: str, thread_ts: str) -> SlackPayload:
        """Run one conversation turn."""
        ...


logger = logging.getLogger(__name__)

JSON_TYPE = "application/json"


def chat_api_enabled() -> bool:
    """True unless BENEDICT_CHAT_API is an explicit off value."""
    raw = os.environ.get("BENEDICT_CHAT_API", "1").strip().lower()
    return raw not in {"0", "false", "off", "no"}


def handle_chat(agent: ConversationAgent, body: Dict[str, Any]) -> Tuple[int, Dict[str, Any]]:
    """Run one conversation turn. Returns HTTP status and JSON payload."""
    channel_id = body.get("channel_id")
    text = body.get("text")
    session_id = body.get("session_id")
    if not isinstance(channel_id, str) or not channel_id.strip():
        return 400, {"ok": False, "error": "channel_id is required"}
    if not isinstance(text, str) or not text.strip():
        return 400, {"ok": False, "error": "text is required"}
    if not isinstance(session_id, str) or not session_id.strip():
        return 400, {"ok": False, "error": "session_id is required"}

    channel_id = channel_id.strip()
    text = text.strip()
    session_id = session_id.strip()

    run = _begin_run(agent, channel_id=channel_id, text=text, session_id=session_id)
    try:
        payload: SlackPayload = agent.handle_conversation(channel_id, text, thread_ts=session_id)
    except Exception as exc:
        logger.exception("Chat API conversation failed")
        _finish_run(run, success=False, message=str(exc))
        return 500, {"ok": False, "error": "internal error"}

    message = payload.text()
    _finish_run(run, success=payload.success, message=message)
    return 200, {"ok": True, "text": message, "success": payload.success}


def _begin_run(agent: ConversationAgent, *, channel_id: str, text: str, session_id: str) -> Any:
    recorder = getattr(agent, "run_recorder", None)
    if recorder is None:
        return NullActiveRun()
    repo = ""
    lookup = getattr(agent, "get_channel_repo", None)
    if callable(lookup):
        try:
            repo = lookup(channel_id) or ""
        except Exception:
            pass
    return recorder.begin(
        source="phone",
        kind="conversation",
        query=text,
        channel_id=channel_id,
        thread_ts=session_id,
        repo=repo,
        route="handle_conversation",
    )


def _finish_run(run: Any, *, success: bool, message: str) -> None:
    try:
        run.finish(
            status="ok" if success else "error",
            reply=message,
            error=None if success else (message or "error")[:500],
        )
    except Exception:
        logger.warning("Failed to finish chat API run", exc_info=True)


class _Handler(BaseHTTPRequestHandler):
    agent: ConversationAgent

    def log_message(self, fmt: str, *args: Any) -> None:
        logger.debug("chat-api " + fmt, *args)

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path == "/health":
            self._json(200, {"status": "ok"})
            return
        self._json(404, {"ok": False, "error": "not found"})

    def do_POST(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path != "/v1/chat":
            self._json(404, {"ok": False, "error": "not found"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0") or "0")
        except ValueError:
            self._json(400, {"ok": False, "error": "invalid Content-Length"})
            return
        raw = self.rfile.read(length) if length > 0 else b"{}"
        try:
            body = json.loads(raw.decode("utf-8") or "{}")
        except (UnicodeDecodeError, json.JSONDecodeError):
            self._json(400, {"ok": False, "error": "invalid JSON"})
            return
        if not isinstance(body, dict):
            self._json(400, {"ok": False, "error": "JSON object required"})
            return
        status, payload = handle_chat(self.agent, body)
        self._json(status, payload)

    def _json(self, code: int, payload: Dict[str, Any]) -> None:
        body = json.dumps(payload, default=str).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", JSON_TYPE)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)


def start_chat_api(
    agent: ConversationAgent,
    *,
    host: Optional[str] = None,
    port: Optional[int] = None,
) -> Optional[ThreadingHTTPServer]:
    """Start the chat API in a daemon thread. Returns the server or None."""
    if not chat_api_enabled():
        logger.info("Chat API disabled (BENEDICT_CHAT_API=0)")
        return None
    bind_host = host or os.environ.get("BENEDICT_CHAT_API_HOST", "127.0.0.1")
    bind_port = port if port is not None else int(os.environ.get("BENEDICT_CHAT_API_PORT", "8766"))
    _Handler.agent = agent
    try:
        server = ThreadingHTTPServer((bind_host, bind_port), _Handler)
    except OSError as exc:
        logger.warning("Chat API did not start on %s:%s: %s", bind_host, bind_port, exc)
        return None
    thread = threading.Thread(target=server.serve_forever, name="chat-api", daemon=True)
    thread.start()
    actual_host, actual_port = server.server_address[:2]
    logger.info("Chat API http://%s:%s/v1/chat", actual_host, actual_port)
    return server

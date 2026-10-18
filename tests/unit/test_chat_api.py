"""Localhost chat API for non-Slack clients."""

import json
from http.client import HTTPConnection
from pathlib import Path
from typing import Any, Dict, Optional

from benedict.agent import RepoAgent
from benedict.chat_api import handle_chat, start_chat_api
from benedict.conversation_repository.conversation_repository_mock import (
    MockConversationRepository,
)
from benedict.operator_ui.recorder import JsonlRunRecorder
from benedict.slack.payloads import SlackPayload, markdown


class _FakeAgent:
    def __init__(self, payload: Any = None, recorder: Any = None) -> None:
        self.payload = payload or markdown(True, "hello from benedict")
        self.calls: list[tuple[str, str, str]] = []
        self.run_recorder = recorder
        self.repo: Optional[str] = "acme/x"

    def get_channel_repo(self, channel_id: str) -> Optional[str]:
        return self.repo

    def handle_conversation(self, channel_id: str, text: str, thread_ts: str) -> SlackPayload:
        self.calls.append((channel_id, text, thread_ts))
        return self.payload


def test_handle_chat_requires_fields() -> None:
    agent = _FakeAgent()
    status, body = handle_chat(agent, {})
    assert status == 400
    assert body["ok"] is False
    assert "channel_id" in body["error"]

    status, body = handle_chat(agent, {"channel_id": "C1", "session_id": "s1"})
    assert status == 400
    assert "text" in body["error"]

    status, body = handle_chat(agent, {"channel_id": "C1", "text": "hi"})
    assert status == 400
    assert "session_id" in body["error"]


def test_handle_chat_calls_repo_agent() -> None:
    agent = _FakeAgent()
    status, body = handle_chat(
        agent,
        {"channel_id": " C1 ", "text": "  what's the architecture?  ", "session_id": " call-1 "},
    )
    assert status == 200
    assert body == {"ok": True, "text": "hello from benedict", "success": True}
    assert agent.calls == [("C1", "what's the architecture?", "call-1")]


def test_handle_chat_records_a_phone_run(tmp_path: Path) -> None:
    recorder = JsonlRunRecorder(tmp_path / "runs.jsonl")
    agent = _FakeAgent(recorder=recorder)
    status, body = handle_chat(
        agent,
        {"channel_id": "C1", "text": "hi", "session_id": "sid"},
    )
    assert status == 200
    assert body["success"] is True
    listed = recorder.list_runs(limit=10)
    assert len(listed) == 1
    assert listed[0]["source"] == "phone"
    assert listed[0]["query"] == "hi"
    assert listed[0]["thread_ts"] == "sid"
    assert listed[0]["status"] == "ok"


def test_handle_chat_on_real_repo_agent_not_onboarded(tmp_path: Path) -> None:
    agent = RepoAgent(
        state_file=str(tmp_path / "state.json"),
        conversation_repository=MockConversationRepository(),
    )
    status, body = handle_chat(
        agent,
        {"channel_id": "Cnone", "text": "hello", "session_id": "1.2"},
    )
    assert status == 200
    assert body["ok"] is True
    assert body["success"] is False
    assert "Not Onboarded" in body["text"]


def test_chat_api_http_health_and_chat() -> None:
    agent = _FakeAgent()
    server = start_chat_api(agent, host="127.0.0.1", port=0)
    assert server is not None
    try:
        port = int(server.server_address[1])
        conn = HTTPConnection("127.0.0.1", port, timeout=5)
        conn.request("GET", "/health")
        health = json.loads(conn.getresponse().read().decode("utf-8"))
        assert health == {"status": "ok"}

        payload = json.dumps({"channel_id": "C1", "text": "status please", "session_id": "CA123"})
        conn.request(
            "POST",
            "/v1/chat",
            body=payload,
            headers={"Content-Type": "application/json"},
        )
        response = conn.getresponse()
        body: Dict[str, Any] = json.loads(response.read().decode("utf-8"))
        assert response.status == 200
        assert body["text"] == "hello from benedict"
        assert agent.calls[0][2] == "CA123"
        conn.close()
    finally:
        server.shutdown()
        server.server_close()


def test_chat_api_disabled(monkeypatch: Any) -> None:
    from benedict.chat_api import chat_api_enabled

    monkeypatch.setenv("BENEDICT_CHAT_API", "0")
    assert chat_api_enabled() is False
    assert start_chat_api(_FakeAgent()) is None

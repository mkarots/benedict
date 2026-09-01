"""Tests for the unattended progress loop."""

import json
from unittest.mock import Mock

from benedict.agent import RepoAgent
from benedict.tools.tool_framework import ToolResult
from benedict.progress.cycle import ProgressService, format_cycle_message
from benedict.progress.decide import ActionDecider, parse_decision, snapshot_to_prompt
from benedict.progress.execute import ActionExecutor, NullPoster
from benedict.progress.models import GithubItem, ProjectRef, ProjectSnapshot
from benedict.progress.scheduler import ProgressScheduler, progress_enabled
from benedict.progress.snapshot import (
    ROADMAP_CANDIDATES,
    SnapshotCollector,
    _parse_items,
    _purpose_from_metadata,
)
from benedict.progress.store import ProgressStore


def _state(tmp_path, repo="acme/widget"):
    path = tmp_path / "state.json"
    path.write_text(
        json.dumps(
            {
                "channels": {
                    "C1": {
                        "repo": repo,
                        "onboarded_at": "2026-08-01T10:00:00Z",
                        "onboarded_by": "U1",
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    return path


def _load_save(path):
    def load():
        return json.loads(path.read_text(encoding="utf-8"))

    def save(state):
        path.write_text(json.dumps(state), encoding="utf-8")

    return load, save


class FakeGithub:
    def __init__(self):
        self.calls = []
        self.issues = [
            {"number": 1, "title": "Existing work", "url": "https://example/1", "labels": []}
        ]
        self.prs = []
        self.labels = [{"name": "enhancement"}]
        self.create_exit = 0
        self.create_stdout = "https://example/issues/2"

    def execute(self, arguments, context=None):
        argv = arguments["argv"]
        self.calls.append(argv)
        if argv[:2] == ["issue", "list"]:
            return ToolResult(
                success=True,
                data={"exit_code": 0, "stdout": json.dumps(self.issues), "stderr": ""},
            )
        if argv[:2] == ["pr", "list"]:
            return ToolResult(
                success=True,
                data={"exit_code": 0, "stdout": json.dumps(self.prs), "stderr": ""},
            )
        if argv[:2] == ["label", "list"]:
            return ToolResult(
                success=True,
                data={"exit_code": 0, "stdout": json.dumps(self.labels), "stderr": ""},
            )
        if argv[:2] == ["issue", "create"]:
            return ToolResult(
                success=True,
                message=self.create_stdout,
                data={
                    "exit_code": self.create_exit,
                    "stdout": self.create_stdout,
                    "stderr": "",
                },
            )
        return ToolResult(success=False, error="unexpected argv")


class ScriptedLLM:
    def __init__(self, reply):
        self.reply = reply
        self.calls = []

    def generate(self, messages, system="", max_tokens=2000, tools=None):
        self.calls.append({"messages": messages, "system": system})
        return self.reply


def _service(tmp_path, llm_reply, github=None, poster=None):
    state_path = _state(tmp_path)
    load, save = _load_save(state_path)
    repo_dir = tmp_path / "workspaces" / "C1" / "acme" / "widget"
    repo_dir.mkdir(parents=True)
    (repo_dir / "README.md").write_text(
        "# Widget\nNext: ship the progress loop.\n", encoding="utf-8"
    )
    github = github or FakeGithub()
    store = ProgressStore(load, save)
    poster = poster or NullPoster()
    service = ProgressService(
        load_state=load,
        workspace_path_for=lambda _cid: tmp_path / "workspaces" / "C1",
        collector=SnapshotCollector(github=github, store=store),
        decider=ActionDecider(ScriptedLLM(llm_reply)),
        executor=ActionExecutor(poster, github=github),
        store=store,
    )
    return service, store, github, poster, repo_dir


def test_parse_decision_json_and_aliases():
    parsed = parse_decision('```json\n{"action": "pr", "reason": "code", "title": "Do it"}\n```')
    assert parsed is not None
    assert parsed.action == "implement"
    assert parsed.title == "Do it"
    assert parse_decision("not json") is None
    assert parse_decision({"action": "explode", "reason": "x"}) is None
    assert parse_decision({"action": "ask", "reason": "need input"}) is None
    ask = parse_decision(
        {"action": "ask", "reason": "need input", "title": "API?", "body": "REST or GraphQL?"}
    )
    assert ask is not None and ask.action == "ask"


def test_parse_decision_filters_require_body_for_issue():
    assert parse_decision({"action": "issue", "reason": "x", "title": "T"}) is None
    ok = parse_decision({"action": "issue", "reason": "x", "title": "T", "body": "Do T."})
    assert ok is not None
    assert ok.body == "Do T."


def test_roadmap_candidates_are_generic_roadmap_files():
    assert "plans/MILESTONE_STATUS.md" not in ROADMAP_CANDIDATES
    assert "ROADMAP.md" in ROADMAP_CANDIDATES


def test_snapshot_reads_readme_and_github(tmp_path):
    repo = tmp_path / "acme" / "widget"
    repo.mkdir(parents=True)
    (repo / "README.md").write_text("# Hello", encoding="utf-8")
    (repo / ".metadata.benedict").write_text(
        json.dumps({"purpose": "A demo widget"}), encoding="utf-8"
    )
    github = FakeGithub()
    snap = SnapshotCollector(github=github).collect(
        ProjectRef(
            channel_id="C1", repo="acme/widget", repo_path=str(repo), workspace_path=str(tmp_path)
        )
    )
    assert "Hello" in snap.readme
    assert snap.purpose == "A demo widget"
    assert snap.open_issues[0].title == "Existing work"
    assert "enhancement" in snap.known_labels
    assert any(call[0] == "issue" for call in github.calls)


def test_purpose_from_metadata_non_json(tmp_path):
    path = tmp_path / ".metadata.benedict"
    path.write_text("plain purpose text", encoding="utf-8")
    assert "plain purpose" in _purpose_from_metadata(tmp_path)


def test_parse_items_ignores_bad_rows():
    raw = json.dumps(
        [
            {"number": 3, "title": "Ok", "url": "u", "labels": [{"name": "bug"}, "enhancement"]},
            "nope",
        ]
    )
    items = _parse_items(raw, "issue")
    assert len(items) == 1
    assert items[0].labels == ["bug", "enhancement"]


def test_cycle_creates_issue_and_posts(tmp_path):
    poster = Mock()
    poster.post.return_value = "111.222"
    reply = json.dumps(
        {
            "action": "issue",
            "reason": "Next milestone step is missing an issue.",
            "title": "Add progress loop",
            "body": "Ship the unattended cycle.",
            "labels": ["enhancement", "does-not-exist"],
        }
    )
    github = FakeGithub()
    service, store, github, _, _ = _service(tmp_path, reply, github=github, poster=poster)
    result = service.run_one("C1")
    assert result.ok is True
    assert result.action == "issue"
    assert result.url == "https://example/issues/2"
    create = [c for c in github.calls if c[:2] == ["issue", "create"]][0]
    assert "--title" in create
    assert "does-not-exist" not in create
    assert "enhancement" in create
    poster.post.assert_called_once()
    entry = store.project("C1")
    assert entry["last_kind"] == "issue"
    assert entry["pending_thread_ts"] is None


def test_cycle_skips_duplicate_issue_title(tmp_path):
    poster = Mock()
    poster.post.return_value = "1.2"
    github = FakeGithub()
    github.issues = [
        {"number": 9, "title": "Add progress loop", "url": "https://example/9", "labels": []}
    ]
    reply = json.dumps(
        {
            "action": "issue",
            "reason": "Need an issue.",
            "title": "Add progress loop",
            "body": "Duplicate.",
        }
    )
    service, _, _, _, _ = _service(tmp_path, reply, github=github, poster=poster)
    result = service.run_one("C1")
    assert result.skipped is True
    assert result.action == "skip"
    poster.post.assert_not_called()
    assert not any(c[:2] == ["issue", "create"] for c in github.calls)


def test_cycle_asks_and_blocks_until_reply(tmp_path):
    poster = Mock()
    poster.post.return_value = "99.1"
    reply = json.dumps(
        {
            "action": "ask",
            "reason": "Need a product choice.",
            "title": "Which API?",
            "body": "REST or GraphQL for v1?",
        }
    )
    service, store, _, _, _ = _service(tmp_path, reply, poster=poster)
    first = service.run_one("C1")
    assert first.action == "ask"
    assert store.project("C1")["pending_thread_ts"] == "99.1"

    second = service.run_one("C1")
    assert second.skipped is True
    assert "Waiting" in second.summary

    assert store.acknowledge_reply("C1", "99.1") is True
    assert store.project("C1")["pending_thread_ts"] is None

    forced = service.run_one("C1", force=True)
    assert forced.action == "ask"


def test_cycle_implement_points_at_existing_issue(tmp_path):
    poster = Mock()
    poster.post.return_value = "3.3"
    github = FakeGithub()
    github.issues = [{"number": 4, "title": "Wire MCP", "url": "https://example/4", "labels": []}]
    reply = json.dumps(
        {
            "action": "implement",
            "reason": "Issue is ready to code.",
            "title": "Wire MCP",
            "issue_number": 4,
        }
    )
    service, _, github, _, _ = _service(tmp_path, reply, github=github, poster=poster)
    result = service.run_one("C1")
    assert result.ok is True
    assert result.action == "implement"
    assert "4" in result.summary
    assert not any(c[:2] == ["issue", "create"] for c in github.calls)
    assert "does not open pull requests" in poster.post.call_args[0][1]


def test_run_all_and_format_message(tmp_path):
    reply = json.dumps({"action": "skip", "reason": "Nothing to do."})
    service, _, _, _, _ = _service(tmp_path, reply)
    results = service.run_all()
    assert len(results) == 1
    assert results[0].action == "skip"
    text = format_cycle_message(results)
    assert "Progress cycle" in text
    assert "acme/widget" in text


def test_run_one_missing_channel(tmp_path):
    reply = json.dumps({"action": "skip", "reason": "x"})
    service, _, _, _, _ = _service(tmp_path, reply)
    result = service.run_one("C-missing")
    assert result.ok is False
    assert "not onboarded" in result.summary


def test_decider_skips_unusable_llm():
    snap = ProjectSnapshot(
        project=ProjectRef(channel_id="C1", repo="acme/widget", repo_path="/tmp/x")
    )
    decision = ActionDecider(ScriptedLLM("sorry, here is a paragraph")).decide(snap)
    assert decision.action == "skip"


def test_snapshot_to_prompt_includes_issues():
    snap = ProjectSnapshot(
        project=ProjectRef(channel_id="C1", repo="acme/widget", repo_path="/tmp/x"),
        open_issues=[GithubItem(number=1, title="A", url="u")],
        readme="hello",
    )
    text = snapshot_to_prompt(snap)
    assert "acme/widget" in text
    assert "#1 A" in text
    assert "hello" in text


def test_create_issue_retries_without_labels(tmp_path):
    github = FakeGithub()
    github.create_exit = 1
    github.create_stdout = "unknown label"
    calls = {"n": 0}

    def execute(arguments, context=None):
        argv = arguments["argv"]
        if argv[:2] == ["issue", "create"]:
            calls["n"] += 1
            if "--label" in argv:
                return ToolResult(
                    success=True,
                    message="unknown label",
                    data={"exit_code": 1, "stdout": "", "stderr": "unknown label"},
                )
            return ToolResult(
                success=True,
                message="https://example/3",
                data={"exit_code": 0, "stdout": "https://example/3", "stderr": ""},
            )
        return FakeGithub().execute(arguments, context)

    github.execute = execute
    poster = Mock()
    poster.post.return_value = "1.1"
    reply = json.dumps(
        {
            "action": "issue",
            "reason": "Need it.",
            "title": "Retry labels",
            "body": "Body",
            "labels": ["enhancement"],
        }
    )
    service, _, _, _, _ = _service(tmp_path, reply, github=github, poster=poster)
    result = service.run_one("C1")
    assert result.ok is True
    assert result.url == "https://example/3"
    assert calls["n"] == 2


def test_run_one_missing_checkout(tmp_path):
    state_path = _state(tmp_path)
    load, save = _load_save(state_path)
    github = FakeGithub()
    store = ProgressStore(load, save)
    service = ProgressService(
        load_state=load,
        workspace_path_for=lambda _cid: tmp_path / "workspaces" / "C1",
        collector=SnapshotCollector(github=github, store=store),
        decider=ActionDecider(ScriptedLLM('{"action": "skip", "reason": "x"}')),
        executor=ActionExecutor(NullPoster(), github=github),
        store=store,
    )
    result = service.run_one("C1")
    assert result.ok is False
    assert "missing" in result.summary.lower()


def test_scheduler_stops_before_cycle():
    service = Mock()
    scheduler = ProgressScheduler(service, interval_s=30, start_delay_s=5)
    scheduler.start()
    scheduler.stop()
    if scheduler._thread is not None:
        scheduler._thread.join(timeout=2)
    service.run_all.assert_not_called()


def test_progress_enabled(monkeypatch):
    monkeypatch.delenv("BENEDICT_PROGRESS", raising=False)
    assert progress_enabled() is True
    monkeypatch.setenv("BENEDICT_PROGRESS", "0")
    assert progress_enabled() is False
    monkeypatch.setenv("BENEDICT_PROGRESS", "false")
    assert progress_enabled() is False


def test_is_progress_command(temp_state_file):
    agent = RepoAgent(state_file=str(temp_state_file))
    assert agent.is_progress_command("progress")
    assert agent.is_progress_command("progress now")
    assert agent.is_progress_command("progress all")
    assert agent.is_progress_command("run progress")
    assert agent.is_progress_command("progress now all")
    assert not agent.is_progress_command("what's the progress on auth")
    assert not agent.is_progress_command("status")


def test_handle_progress_without_service(temp_state_file):
    agent = RepoAgent(state_file=str(temp_state_file))
    reply = agent.handle_progress("C1", "progress")
    assert reply.success is False
    assert "not running" in reply.text().lower()


def test_handle_progress_this_channel(tmp_path, temp_state_file):
    reply_json = json.dumps({"action": "skip", "reason": "Idle."})
    service, _, _, _, _ = _service(tmp_path, reply_json)
    agent = RepoAgent(state_file=str(temp_state_file), progress_service=service)
    reply = agent.handle_progress("C1", "progress")
    assert reply.success is True
    assert "skip" in reply.text()

"""Tests for lifecycle-state parsing and prompt overlay."""

from pathlib import Path

from benedict.method import (
    METHOD_FILENAME,
    format_method_overlay,
    load_method_from_path,
    load_method_from_text,
)
from benedict.repo_reader.repo_reader_mock import MockRepoReader
from benedict.context import build_context
from benedict.progress.decide import snapshot_to_prompt
from benedict.progress.models import ProjectRef, ProjectSnapshot
from benedict.progress.snapshot import SnapshotCollector

from tests.unit.test_progress import FakeGithub

SAMPLE = """
method:
  pc:
    phase: sprint
    iteration: 3
    step: document
  concerns:
    scope: locked
    documentation: in_progress
    development: active
  sequence:
    sprint:
      loop: build → document → communicate
      exit: feature is delivered, documented, and communicated
      concerns:
        scope:
          rule: scope is locked — no new features unless gated through review
        documentation:
          rule: every delivered feature must be documented before it is communicated
        development:
          rule: build only what is on the roadmap for this sprint
"""


def test_load_method_from_text_reads_program_counter():
    state = load_method_from_text(SAMPLE)
    assert state is not None
    assert state.phase == "sprint"
    assert state.iteration == 3
    assert state.step == "document"
    assert state.concerns["scope"] == "locked"
    assert state.concerns["documentation"] == "in_progress"
    assert state.phase_loop.startswith("build")
    assert any(rule.startswith("scope:") for rule in state.phase_rules)
    assert any("documented" in rule for rule in state.phase_rules)


def test_load_method_from_text_strips_trailing_backslash_on_step():
    state = load_method_from_text("method:\n  pc:\n    phase: sprint\n    step: document\\\n")
    assert state is not None
    assert state.step == "document"


def test_load_method_from_text_accepts_unwrapped_root():
    state = load_method_from_text("pc:\n  phase: review\n  step: measure\n")
    assert state is not None
    assert state.phase == "review"
    assert state.step == "measure"


def test_load_method_from_text_rejects_empty_and_invalid():
    assert load_method_from_text("") is None
    assert load_method_from_text("   ") is None
    assert load_method_from_text("not: [unterminated") is None
    assert load_method_from_text("method:\n  other: true\n") is None
    assert load_method_from_text("- just a list") is None
    assert load_method_from_text("pc:\n  phase: sprint\n  iteration: nope\n") is not None


def test_load_method_skips_empty_concerns_and_rules():
    raw = """
method:
  pc:
    phase: sprint
  concerns:
    "": ignored
    scope: ""
    documentation: in_progress
  sequence:
    sprint:
      concerns:
        development: not-a-map
        communication:
          expected_state: drafting
        scope:
          rule: stay locked
"""
    state = load_method_from_text(raw)
    assert state is not None
    assert state.concerns == {"documentation": "in_progress"}
    assert state.phase_rules == ["scope: stay locked"]
    assert state.iteration is None


def test_repo_method_file_parses():
    repo_root = Path(__file__).resolve().parents[2]
    state = load_method_from_path(repo_root)
    assert state is not None
    assert state.phase
    assert state.step


def test_load_method_from_path_missing_and_present(tmp_path: Path):
    assert load_method_from_path(tmp_path) is None
    (tmp_path / METHOD_FILENAME).write_text(SAMPLE, encoding="utf-8")
    state = load_method_from_path(tmp_path)
    assert state is not None
    assert state.phase == "sprint"


def test_load_method_reads_stamp():
    state = load_method_from_text(
        "method:\n  pc:\n    phase: sprint\n  stamp:\n    last_action: issue\n"
        "    updated_at: 2026-09-12T16:00:00Z\n"
    )
    assert state is not None
    assert state.last_action == "issue"
    assert "2026-09-12" in state.updated_at
    overlay = format_method_overlay(state)
    assert "Last agent action: issue" in overlay


def test_format_method_overlay_is_short_and_actionable():
    overlay = format_method_overlay(load_method_from_text(SAMPLE))
    assert METHOD_FILENAME in overlay
    assert "Phase: sprint (iteration 3), step: document" in overlay
    assert "scope=locked" in overlay
    assert "Loop: build → document → communicate" in overlay
    assert "Rules now:" in overlay
    assert "scope is locked" in overlay
    assert format_method_overlay(None) == ""


def test_build_context_stuffs_process_overlay():
    reader = MockRepoReader(repos={"acme/x": {"README.md": "# Hello\n", METHOD_FILENAME: SAMPLE}})
    text = build_context("acme/x", "what should we do next", reader)
    assert "Project process" in text
    assert "step: document" in text
    assert "scope=locked" in text


def test_build_context_is_silent_when_method_file_is_missing():
    reader = MockRepoReader(repos={"acme/x": {"README.md": "# Hello\n"}})
    text = build_context("acme/x", "what should we do next", reader)
    assert "Project process" not in text
    assert METHOD_FILENAME not in text


def test_snapshot_reads_method_overlay(tmp_path: Path):
    repo = tmp_path / "acme" / "widget"
    repo.mkdir(parents=True)
    (repo / "README.md").write_text("# Hello", encoding="utf-8")
    (repo / METHOD_FILENAME).write_text(SAMPLE, encoding="utf-8")
    snap = SnapshotCollector(github=FakeGithub()).collect(
        ProjectRef(
            channel_id="C1", repo="acme/widget", repo_path=str(repo), workspace_path=str(tmp_path)
        )
    )
    assert "step: document" in snap.method
    assert "scope=locked" in snap.method


def test_snapshot_ensures_lifecycle_when_file_missing(tmp_path: Path):
    repo = tmp_path / "acme" / "widget"
    repo.mkdir(parents=True)
    (repo / "README.md").write_text("# Hello", encoding="utf-8")
    snap = SnapshotCollector(github=FakeGithub()).collect(
        ProjectRef(
            channel_id="C1", repo="acme/widget", repo_path=str(repo), workspace_path=str(tmp_path)
        )
    )
    assert "Phase: conception" in snap.method
    assert (repo / METHOD_FILENAME).is_file()


def test_snapshot_to_prompt_includes_method_overlay():
    snap = ProjectSnapshot(
        project=ProjectRef(channel_id="C1", repo="acme/widget", repo_path="/tmp/x"),
        method="Phase: sprint, step: document",
        readme="hello",
    )
    text = snapshot_to_prompt(snap)
    assert "Phase: sprint, step: document" in text
    assert "hello" in text

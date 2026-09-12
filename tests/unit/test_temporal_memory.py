"""Tests for repo-scoped temporal memory CRUD."""

from pathlib import Path

import pytest
import yaml

from benedict.method import (
    METHOD_FILENAME,
    InMemoryTemporalMemory,
    LifecyclePatch,
    MethodState,
    YamlFileTemporalMemory,
    create_temporal_memory,
    default_lifecycle_state,
    load_method_from_text,
)


def test_create_temporal_memory_backends():
    assert isinstance(create_temporal_memory("yaml"), YamlFileTemporalMemory)
    assert isinstance(create_temporal_memory("memory"), InMemoryTemporalMemory)
    with pytest.raises(ValueError):
        create_temporal_memory("chroma")


def test_in_memory_crud_round_trip():
    memory = InMemoryTemporalMemory()
    repo = "/tmp/widget"
    assert memory.get(repo) is None
    assert memory.exists(repo) is False

    created = memory.ensure(repo)
    assert created.phase == "conception"
    assert created.step == "define"
    assert memory.exists(repo) is True
    assert memory.ensure(repo) is created

    updated = memory.update(
        repo, LifecyclePatch(phase="sprint", step="document", last_action="issue")
    )
    assert updated.phase == "sprint"
    assert updated.step == "document"
    assert updated.last_action == "issue"
    assert updated.updated_at
    assert updated.concerns["scope"] == "fluid"

    memory.put(
        repo, MethodState(phase="review", step="measure", concerns={"scope": "reconsidering"})
    )
    stored = memory.get(repo)
    assert stored is not None
    assert stored.phase == "review"
    assert stored.concerns["scope"] == "reconsidering"

    memory.delete(repo)
    assert memory.get(repo) is None
    assert memory.exists(repo) is False


def test_yaml_store_creates_and_patches_without_dropping_sequence(tmp_path: Path):
    repo = tmp_path / "acme" / "widget"
    repo.mkdir(parents=True)
    (repo / METHOD_FILENAME).write_text(
        """
method:
  pc:
    phase: sprint
    iteration: 3
    step: document
  concerns:
    scope: locked
  sequence:
    sprint:
      loop: build → document → communicate
""",
        encoding="utf-8",
    )
    memory = YamlFileTemporalMemory()
    assert memory.exists(repo) is True
    assert memory.ensure(repo).phase == "sprint"

    updated = memory.update(repo, LifecyclePatch(last_action="issue", step="communicate"))
    assert updated.step == "communicate"
    assert updated.last_action == "issue"
    assert updated.phase == "sprint"

    raw = yaml.safe_load((repo / METHOD_FILENAME).read_text(encoding="utf-8"))
    assert raw["method"]["sequence"]["sprint"]["loop"].startswith("build")
    assert raw["method"]["stamp"]["last_action"] == "issue"
    assert raw["method"]["pc"]["iteration"] == 3


def test_yaml_store_ensure_writes_default_when_missing(tmp_path: Path):
    repo = tmp_path / "new-project"
    repo.mkdir()
    memory = YamlFileTemporalMemory()
    state = memory.ensure(repo)
    assert state.phase == "conception"
    assert (repo / METHOD_FILENAME).is_file()
    assert load_method_from_text((repo / METHOD_FILENAME).read_text(encoding="utf-8")) is not None


def test_yaml_store_does_not_create_missing_checkout(tmp_path: Path):
    missing = tmp_path / "no-such-repo"
    memory = YamlFileTemporalMemory()
    with pytest.raises(FileNotFoundError):
        memory.ensure(missing)
    assert not missing.exists()


def test_yaml_store_delete(tmp_path: Path):
    repo = tmp_path / "gone"
    repo.mkdir()
    memory = YamlFileTemporalMemory()
    memory.ensure(repo)
    memory.delete(repo)
    assert memory.exists(repo) is False
    memory.delete(repo)


def test_default_lifecycle_state_is_conception():
    state = default_lifecycle_state()
    assert state.phase == "conception"
    assert state.iteration == 1
    assert "scope" in state.concerns

"""Temporal-memory implementations. YAML is the simple store, not the product."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, Optional

import yaml

from benedict.lib.dateutil import utc_now_iso
from benedict.method.overlay import (
    METHOD_FILENAME,
    MethodState,
    load_method_from_text,
)
from benedict.method.protocol import LifecyclePatch, RepoKey

logger = logging.getLogger(__name__)


def default_lifecycle_state() -> MethodState:
    """Starting clock for a repo that has no lifecycle state yet."""
    return MethodState(
        phase="conception",
        iteration=1,
        step="define",
        concerns={
            "scope": "fluid",
            "documentation": "drafting",
            "development": "not_started",
            "communication": "not_applicable",
            "operations": "not_applicable",
            "feedback": "collecting",
        },
    )


def _key(repo_path: RepoKey) -> str:
    return str(Path(repo_path))


class InMemoryTemporalMemory:
    """Process-local store for tests and as a stand-in backend."""

    def __init__(self) -> None:
        self._states: Dict[str, MethodState] = {}

    def get(self, repo_path: RepoKey) -> Optional[MethodState]:
        return self._states.get(_key(repo_path))

    def put(self, repo_path: RepoKey, state: MethodState) -> MethodState:
        stored = _with_stamp(state, state.last_action) if state.last_action else state
        self._states[_key(repo_path)] = stored
        return stored

    def update(self, repo_path: RepoKey, patch: LifecyclePatch) -> MethodState:
        current = self.get(repo_path) or default_lifecycle_state()
        merged = _apply_patch(current, patch)
        self._states[_key(repo_path)] = merged
        return merged

    def delete(self, repo_path: RepoKey) -> None:
        self._states.pop(_key(repo_path), None)

    def exists(self, repo_path: RepoKey) -> bool:
        return _key(repo_path) in self._states

    def ensure(self, repo_path: RepoKey) -> MethodState:
        current = self.get(repo_path)
        if current is not None:
            return current
        return self.put(repo_path, default_lifecycle_state())


class YamlFileTemporalMemory:
    """Persist lifecycle state as `.benedict.method.yaml` in the checkout.

    This is the simplest store. It is not a durable timeline. Replacing it
    should not require changing progress, onboard, or context callers.
    """

    def get(self, repo_path: RepoKey) -> Optional[MethodState]:
        path = _method_path(repo_path)
        try:
            if not path.is_file():
                return None
            return load_method_from_text(path.read_text(encoding="utf-8", errors="replace"))
        except OSError as exc:
            logger.warning("Error reading lifecycle store %s: %s", path, exc)
            return None

    def put(self, repo_path: RepoKey, state: MethodState) -> MethodState:
        patch = LifecyclePatch(
            phase=state.phase,
            iteration=state.iteration,
            step=state.step,
            concerns=dict(state.concerns),
            last_action=state.last_action or None,
        )
        return self.update(repo_path, patch)

    def update(self, repo_path: RepoKey, patch: LifecyclePatch) -> MethodState:
        path = _method_path(repo_path)
        if not path.parent.is_dir():
            raise FileNotFoundError(f"Repository path does not exist: {path.parent}")
        document = _read_document(path)
        _patch_document(document, patch)
        path.write_text(
            yaml.safe_dump(document, sort_keys=False, allow_unicode=True),
            encoding="utf-8",
        )
        loaded = self.get(repo_path)
        if loaded is None:
            raise RuntimeError(f"Lifecycle store write did not persist at {path}")
        return loaded

    def delete(self, repo_path: RepoKey) -> None:
        path = _method_path(repo_path)
        try:
            path.unlink(missing_ok=True)
        except OSError as exc:
            logger.warning("Error deleting lifecycle store %s: %s", path, exc)
            raise

    def exists(self, repo_path: RepoKey) -> bool:
        return _method_path(repo_path).is_file()

    def ensure(self, repo_path: RepoKey) -> MethodState:
        current = self.get(repo_path)
        if current is not None:
            return current
        return self.put(repo_path, default_lifecycle_state())


def create_temporal_memory(
    backend: str = "yaml",
) -> InMemoryTemporalMemory | YamlFileTemporalMemory:
    """Compose a temporal-memory store. Call from the composition root."""
    if backend == "yaml":
        return YamlFileTemporalMemory()
    if backend == "memory":
        return InMemoryTemporalMemory()
    raise ValueError(f"Unknown temporal memory backend: {backend}")


def _method_path(repo_path: RepoKey) -> Path:
    return Path(repo_path) / METHOD_FILENAME


def _read_document(path: Path) -> Dict[str, Any]:
    if not path.is_file():
        return {"method": {}}
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8", errors="replace"))
    except (OSError, yaml.YAMLError) as exc:
        logger.warning("Replacing unreadable lifecycle document %s: %s", path, exc)
        return {"method": {}}
    if not isinstance(payload, dict):
        return {"method": {}}
    inner = payload.get("method")
    if not isinstance(inner, dict):
        if any(key in payload for key in ("pc", "concerns", "sequence")):
            return {"method": payload}
        return {"method": {}}
    return payload


def _patch_document(document: Dict[str, Any], patch: LifecyclePatch) -> None:
    method = document.setdefault("method", {})
    if not isinstance(method, dict):
        method = {}
        document["method"] = method
    pc = method.setdefault("pc", {})
    if not isinstance(pc, dict):
        pc = {}
        method["pc"] = pc
    if patch.phase is not None:
        pc["phase"] = patch.phase
    if patch.iteration is not None:
        pc["iteration"] = patch.iteration
    if patch.step is not None:
        pc["step"] = patch.step
    if patch.concerns is not None:
        concerns = method.get("concerns")
        if not isinstance(concerns, dict):
            concerns = {}
        concerns.update(patch.concerns)
        method["concerns"] = concerns
    if patch.last_action is not None:
        stamp = method.setdefault("stamp", {})
        if not isinstance(stamp, dict):
            stamp = {}
            method["stamp"] = stamp
        stamp["last_action"] = patch.last_action
        stamp["updated_at"] = utc_now_iso()


def _apply_patch(current: MethodState, patch: LifecyclePatch) -> MethodState:
    concerns = dict(current.concerns)
    if patch.concerns:
        concerns.update(patch.concerns)
    action = patch.last_action if patch.last_action is not None else current.last_action
    return MethodState(
        phase=patch.phase if patch.phase is not None else current.phase,
        iteration=patch.iteration if patch.iteration is not None else current.iteration,
        step=patch.step if patch.step is not None else current.step,
        concerns=concerns,
        phase_loop=current.phase_loop,
        phase_exit=current.phase_exit,
        phase_rules=list(current.phase_rules),
        last_action=action,
        updated_at=utc_now_iso() if patch.last_action is not None else current.updated_at,
    )


def _with_stamp(state: MethodState, last_action: str) -> MethodState:
    return MethodState(
        phase=state.phase,
        iteration=state.iteration,
        step=state.step,
        concerns=dict(state.concerns),
        phase_loop=state.phase_loop,
        phase_exit=state.phase_exit,
        phase_rules=list(state.phase_rules),
        last_action=last_action,
        updated_at=utc_now_iso(),
    )

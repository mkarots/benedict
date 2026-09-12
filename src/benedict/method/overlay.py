"""Lifecycle state view: program counter, concerns, and the rules that apply now.

Parsing and prompt formatting live here. Persistence is `TemporalMemory`.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import yaml

logger = logging.getLogger(__name__)

METHOD_FILENAME = ".benedict.method.yaml"


@dataclass(frozen=True)
class MethodState:
    """The live program counter and the rules that apply in this phase."""

    phase: str = ""
    iteration: Optional[int] = None
    step: str = ""
    concerns: Dict[str, str] = field(default_factory=dict)
    phase_loop: str = ""
    phase_exit: str = ""
    phase_rules: List[str] = field(default_factory=list)
    last_action: str = ""
    updated_at: str = ""


def load_method_from_text(raw: str) -> Optional[MethodState]:
    """Parse method YAML text. Returns None if empty or unusable."""
    if not raw or not str(raw).strip():
        return None
    try:
        payload = yaml.safe_load(raw)
    except yaml.YAMLError as exc:
        logger.warning("Method file is not valid YAML: %s", exc)
        return None
    return _state_from_mapping(payload)


def load_method_from_path(directory: Union[str, Path]) -> Optional[MethodState]:
    """Read `.benedict.method.yaml` from a checkout directory."""
    path = Path(directory) / METHOD_FILENAME
    try:
        if not path.is_file():
            return None
        return load_method_from_text(path.read_text(encoding="utf-8", errors="replace"))
    except OSError as exc:
        logger.warning("Error reading method file %s: %s", path, exc)
        return None


def format_method_overlay(state: Optional[MethodState]) -> str:
    """Short summary for conversation context and the progress snapshot."""
    if state is None or not (
        state.phase or state.step or state.concerns or state.phase_rules or state.last_action
    ):
        return ""

    lines = [f"# Project process ({METHOD_FILENAME})"]
    counter = _format_counter(state)
    if counter:
        lines.append(counter)
    if state.concerns:
        pairs = ", ".join(f"{name}={value}" for name, value in state.concerns.items())
        lines.append(f"Concerns: {pairs}")
    if state.phase_loop:
        lines.append(f"Loop: {state.phase_loop}")
    if state.phase_exit:
        lines.append(f"Exit: {state.phase_exit}")
    if state.last_action:
        stamp = f"Last agent action: {state.last_action}"
        if state.updated_at:
            stamp += f" ({state.updated_at})"
        lines.append(stamp)
    if state.phase_rules:
        lines.append("Rules now:")
        for rule in state.phase_rules:
            lines.append(f"- {rule}")
    return "\n".join(lines)


def _format_counter(state: MethodState) -> str:
    parts: List[str] = []
    if state.phase:
        label = f"Phase: {state.phase}"
        if state.iteration is not None:
            label += f" (iteration {state.iteration})"
        parts.append(label)
    if state.step:
        parts.append(f"step: {state.step}")
    return ", ".join(parts)


def _state_from_mapping(payload: Any) -> Optional[MethodState]:
    root = _method_root(payload)
    if not root:
        return None

    pc_raw = root.get("pc")
    pc: Dict[str, Any] = pc_raw if isinstance(pc_raw, dict) else {}
    phase = _as_text(pc.get("phase"))
    step = _as_text(pc.get("step")).rstrip("\\")
    iteration = _as_int(pc.get("iteration"))

    concerns_raw = root.get("concerns")
    concerns: Dict[str, str] = {}
    if isinstance(concerns_raw, dict):
        for name, value in concerns_raw.items():
            key = _as_text(name)
            state = _as_text(value)
            if key and state:
                concerns[key] = state

    sequence_raw = root.get("sequence")
    sequence: Dict[str, Any] = sequence_raw if isinstance(sequence_raw, dict) else {}
    phase_raw = sequence.get(phase) if phase else None
    phase_def: Dict[str, Any] = phase_raw if isinstance(phase_raw, dict) else {}
    phase_loop = _as_text(phase_def.get("loop"))
    phase_exit = _as_text(phase_def.get("exit"))
    phase_rules = _phase_rules(phase_def)
    stamp_raw = root.get("stamp")
    stamp: Dict[str, Any] = stamp_raw if isinstance(stamp_raw, dict) else {}
    last_action = _as_text(stamp.get("last_action"))
    updated_at = _as_text(stamp.get("updated_at"))

    if not (phase or step or concerns or phase_rules or last_action):
        return None
    return MethodState(
        phase=phase,
        iteration=iteration,
        step=step,
        concerns=concerns,
        phase_loop=phase_loop,
        phase_exit=phase_exit,
        phase_rules=phase_rules,
        last_action=last_action,
        updated_at=updated_at,
    )


def _method_root(payload: Any) -> Dict[str, Any]:
    if not isinstance(payload, dict):
        return {}
    inner = payload.get("method")
    if isinstance(inner, dict):
        return inner
    return payload


def _phase_rules(phase_def: Dict[str, Any]) -> List[str]:
    concerns = phase_def.get("concerns")
    if not isinstance(concerns, dict):
        return []
    rules: List[str] = []
    for name, body in concerns.items():
        if not isinstance(body, dict):
            continue
        rule = _as_text(body.get("rule"))
        if not rule:
            continue
        label = _as_text(name)
        rules.append(f"{label}: {rule}" if label else rule)
    return rules


def _as_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _as_int(value: Any) -> Optional[int]:
    if isinstance(value, bool) or value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None

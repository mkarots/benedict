"""Progress-loop fields in state.json."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Callable, Dict, Optional


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S") + "Z"


class ProgressStore:
    """Read and write `state["progress"]` without owning the rest of state."""

    def __init__(
        self, load_state: Callable[[], Dict[str, Any]], save_state: Callable[[Dict[str, Any]], None]
    ):
        self._load = load_state
        self._save = save_state

    def _progress(self, state: Dict[str, Any]) -> Dict[str, Any]:
        progress = state.setdefault("progress", {})
        progress.setdefault("projects", {})
        return progress

    def project(self, channel_id: str) -> Dict[str, Any]:
        state = self._load()
        projects = self._progress(state).setdefault("projects", {})
        return dict(projects.get(channel_id) or {})

    def mark_cycle(self) -> None:
        state = self._load()
        progress = self._progress(state)
        progress["last_cycle_at"] = _utc_now()
        self._save(state)

    def record_action(
        self,
        channel_id: str,
        *,
        kind: str,
        title: str = "",
        url: str = "",
        thread_ts: Optional[str] = None,
        pending: bool = False,
    ) -> None:
        state = self._load()
        progress = self._progress(state)
        projects = progress.setdefault("projects", {})
        entry = dict(projects.get(channel_id) or {})
        recent = list(entry.get("recent_titles") or [])
        if title:
            recent = [title, *[t for t in recent if t != title]][:20]
        entry.update(
            {
                "last_action_at": _utc_now(),
                "last_kind": kind,
                "last_title": title,
                "last_url": url,
                "pending_thread_ts": thread_ts if pending else None,
                "recent_titles": recent,
            }
        )
        projects[channel_id] = entry
        self._save(state)

    def acknowledge_reply(self, channel_id: str, thread_ts: str) -> bool:
        """Clear a pending question when the human replies in that thread."""
        if not thread_ts:
            return False
        state = self._load()
        progress = self._progress(state)
        entry = (progress.get("projects") or {}).get(channel_id) or {}
        pending = entry.get("pending_thread_ts")
        if not pending or pending != thread_ts:
            return False
        entry["pending_thread_ts"] = None
        progress["projects"][channel_id] = entry
        self._save(state)
        return True

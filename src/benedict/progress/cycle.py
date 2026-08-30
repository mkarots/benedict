"""Run one progress cycle across onboarded projects."""

from __future__ import annotations

import logging
import threading
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from benedict.progress.decide import ActionDecider
from benedict.progress.execute import ActionExecutor
from benedict.progress.models import ActionResult, Decision, ProjectRef
from benedict.progress.snapshot import SnapshotCollector
from benedict.progress.store import ProgressStore

logger = logging.getLogger(__name__)


class ProgressService:
    """Survey each onboarded repo and take at most one action."""

    def __init__(
        self,
        *,
        load_state: Callable[[], Dict[str, Any]],
        workspace_path_for: Callable[[str], Path],
        collector: SnapshotCollector,
        decider: ActionDecider,
        executor: ActionExecutor,
        store: ProgressStore,
        run_recorder: Any = None,
    ) -> None:
        self._load_state = load_state
        self._workspace_path_for = workspace_path_for
        self.collector = collector
        self.decider = decider
        self.executor = executor
        self.store = store
        self.run_recorder = run_recorder
        self._lock = threading.Lock()

    def list_projects(self) -> List[ProjectRef]:
        state = self._load_state()
        channels = state.get("channels") or {}
        projects: List[ProjectRef] = []
        for channel_id, config in channels.items():
            repo = (config or {}).get("repo")
            if not channel_id or not repo:
                continue
            workspace = self._workspace_path_for(channel_id)
            repo_path = Path(workspace) / repo
            projects.append(
                ProjectRef(
                    channel_id=channel_id,
                    repo=repo,
                    repo_path=str(repo_path),
                    workspace_path=str(workspace),
                )
            )
        return projects

    def acknowledge_reply(self, channel_id: str, thread_ts: str) -> bool:
        return self.store.acknowledge_reply(channel_id, thread_ts)

    def run_all(self, *, force: bool = False) -> List[ActionResult]:
        results = []
        for project in self.list_projects():
            results.append(self.run_one(project.channel_id, force=force))
        self.store.mark_cycle()
        return results

    def run_one(self, channel_id: str, *, force: bool = False) -> ActionResult:
        with self._lock:
            return self._run_one_locked(channel_id, force=force)

    def _run_one_locked(self, channel_id: str, *, force: bool) -> ActionResult:
        project = next((p for p in self.list_projects() if p.channel_id == channel_id), None)
        if project is None:
            return ActionResult(
                channel_id=channel_id,
                repo="",
                action="skip",
                ok=False,
                summary="Channel is not onboarded.",
                skipped=True,
            )

        run = self._begin_run(project, force=force)
        try:
            snapshot = self.collector.collect(project)
            run.add_stage(
                "snapshot",
                label="snapshot",
                detail={
                    "issues": len(snapshot.open_issues),
                    "prs": len(snapshot.open_prs),
                    "github_error": snapshot.github_error,
                },
            )
            if snapshot.pending_thread_ts and not force:
                result = ActionResult(
                    channel_id=channel_id,
                    repo=project.repo,
                    action="skip",
                    ok=True,
                    summary="Waiting on a reply to the last progress question.",
                    thread_ts=snapshot.pending_thread_ts,
                    skipped=True,
                )
                self._finish_run(run, result)
                return result

            if not Path(project.repo_path).is_dir():
                result = ActionResult(
                    channel_id=channel_id,
                    repo=project.repo,
                    action="skip",
                    ok=False,
                    summary=f"Workspace checkout missing: {project.repo_path}",
                    skipped=True,
                )
                self._finish_run(run, result)
                return result

            decision = self.decider.decide(snapshot)
            run.add_stage(
                "decide",
                label="decide",
                detail={
                    "action": decision.action,
                    "reason": decision.reason,
                    "title": decision.title,
                },
            )
            result = self.executor.execute(snapshot, decision)
            self._record_store(result, decision)
            self._log_workspace(channel_id, result)
            run.add_stage(
                "execute",
                status="ok" if result.ok else "error",
                label=result.action,
                detail={"summary": result.summary, "url": result.url},
            )
            self._finish_run(run, result)
            return result
        except Exception as exc:
            logger.exception("Progress cycle failed for %s", project.repo)
            result = ActionResult(
                channel_id=channel_id,
                repo=project.repo,
                action="skip",
                ok=False,
                summary=str(exc),
                skipped=True,
            )
            self._finish_run(run, result, error=str(exc))
            return result

    def _record_store(self, result: ActionResult, decision: Decision) -> None:
        pending = result.ok and result.action == "ask"
        self.store.record_action(
            result.channel_id,
            kind=result.action,
            title=decision.title or result.summary,
            url=result.url or "",
            thread_ts=result.thread_ts,
            pending=pending,
        )

    def _log_workspace(self, channel_id: str, result: ActionResult) -> None:
        if not result.ok or result.skipped:
            return
        try:
            from benedict.workspace import ActionLogger

            ActionLogger(self._workspace_path_for(channel_id)).log_action(
                action="progress",
                content_type="progress",
                resource=result.action,
                summary=result.summary,
                url=result.url,
            )
        except Exception:
            logger.debug("Failed to log progress action", exc_info=True)

    def _begin_run(self, project: ProjectRef, *, force: bool) -> Any:
        recorder = self.run_recorder
        if recorder is None:
            from benedict.operator_ui.recorder import NullRunRecorder

            recorder = NullRunRecorder()
        return recorder.begin(
            source="progress",
            kind="progress",
            query="progress now" if force else "progress",
            channel_id=project.channel_id,
            repo=project.repo,
            route="progress.run_one",
        )

    def _finish_run(self, run: Any, result: ActionResult, error: Optional[str] = None) -> None:
        run.set(route="progress.run_one")
        run.finish(
            status="ok" if result.ok else "error",
            reply=result.summary,
            error=error or (None if result.ok else result.summary),
        )


def format_cycle_message(results: List[ActionResult]) -> str:
    """Slack text summarizing a progress run."""
    if not results:
        return "No onboarded projects to progress."
    lines = ["*Progress cycle*", ""]
    for result in results:
        mark = "•"
        if not result.ok:
            mark = "⚠️"
        elif result.skipped:
            mark = "–"
        elif result.action == "issue":
            mark = "✅"
        elif result.action == "ask":
            mark = "❓"
        elif result.action == "implement":
            mark = "🛠️"
        target = result.url or result.summary
        lines.append(f"{mark} `{result.repo or result.channel_id}` · {result.action}: {target}")
    return "\n".join(lines)

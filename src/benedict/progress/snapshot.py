"""Build a project snapshot from the workspace and GitHub CLI."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from benedict.tools.github_tools import RunGithubTool
from benedict.progress.models import GithubItem, ProjectRef, ProjectSnapshot
from benedict.progress.store import ProgressStore
from benedict.workspace import ActionLogger

logger = logging.getLogger(__name__)

README_CHARS = 4000
ROADMAP_CHARS = 3000
METADATA_NAME = ".metadata.benedict"
ROADMAP_CANDIDATES = (
    "ROADMAP.md",
    "roadmap.md",
    "docs/ROADMAP.md",
)


@dataclass
class GhOutput:
    stdout: str
    error: Optional[str]


def _read_text(path: Path, limit: int) -> str:
    try:
        if not path.is_file():
            return ""
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    text = text.strip()
    if len(text) <= limit:
        return text
    return text[:limit] + "\n...[truncated]"


def _purpose_from_metadata(repo_path: Path) -> str:
    raw = _read_text(repo_path / METADATA_NAME, 2000)
    if not raw:
        return ""
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return raw[:400]
    if isinstance(payload, dict):
        for key in ("purpose", "summary", "description"):
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()[:800]
    return ""


def _roadmap(repo_path: Path) -> str:
    for relative in ROADMAP_CANDIDATES:
        text = _read_text(repo_path / relative, ROADMAP_CHARS)
        if text:
            return f"## {relative}\n{text}"
    return ""


def _parse_items(raw: str, kind: str) -> List[GithubItem]:
    if not raw.strip():
        return []
    try:
        rows = json.loads(raw)
    except json.JSONDecodeError:
        return []
    if not isinstance(rows, list):
        return []
    items: List[GithubItem] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        number = row.get("number")
        title = row.get("title")
        if not isinstance(number, int) or not isinstance(title, str):
            continue
        labels = []
        for label in row.get("labels") or []:
            if isinstance(label, dict) and label.get("name"):
                labels.append(str(label["name"]))
            elif isinstance(label, str):
                labels.append(label)
        items.append(
            GithubItem(
                number=number,
                title=title,
                url=str(row.get("url") or ""),
                kind=kind,
                labels=labels,
            )
        )
    return items


def _label_names(raw: str) -> List[str]:
    if not raw.strip():
        return []
    try:
        rows = json.loads(raw)
    except json.JSONDecodeError:
        return []
    if not isinstance(rows, list):
        return []
    names = []
    for row in rows:
        if isinstance(row, dict) and row.get("name"):
            names.append(str(row["name"]))
        elif isinstance(row, str):
            names.append(row)
    return names


class SnapshotCollector:
    """Collect code + GitHub facts for one project. No Slack history."""

    def __init__(
        self, github: Optional[RunGithubTool] = None, store: Optional[ProgressStore] = None
    ):
        self.github = github or RunGithubTool()
        self.store = store

    def collect(self, project: ProjectRef) -> ProjectSnapshot:
        repo_path = Path(project.repo_path)
        snapshot = ProjectSnapshot(
            project=project,
            purpose=_purpose_from_metadata(repo_path),
            readme=_read_text(repo_path / "README.md", README_CHARS),
            roadmap=_roadmap(repo_path),
        )
        if self.store:
            entry = self.store.project(project.channel_id)
            snapshot.last_kind = entry.get("last_kind")
            snapshot.pending_thread_ts = entry.get("pending_thread_ts")

        try:
            workspace = (
                Path(project.workspace_path)
                if project.workspace_path
                else Path(project.repo_path).parent
            )
            snapshot.recent_actions = self._recent_actions(project.channel_id, workspace)
        except Exception:
            logger.warning("Failed to read action log for %s", project.channel_id, exc_info=True)

        context = {"workspace_path": str(repo_path)}
        issues = self._gh(
            [
                "issue",
                "list",
                "--state",
                "open",
                "--limit",
                "20",
                "--json",
                "number,title,url,labels",
            ],
            context,
        )
        if issues.error:
            snapshot.github_error = issues.error
        else:
            snapshot.open_issues = _parse_items(issues.stdout, "issue")

        prs = self._gh(
            ["pr", "list", "--limit", "10", "--json", "number,title,url,author"],
            context,
        )
        if prs.error and not snapshot.github_error:
            snapshot.github_error = prs.error
        elif not prs.error:
            snapshot.open_prs = _parse_items(prs.stdout, "pr")

        labels = self._gh(["label", "list", "--limit", "50", "--json", "name"], context)
        if not labels.error:
            snapshot.known_labels = _label_names(labels.stdout)

        return snapshot

    def _recent_actions(self, channel_id: str, workspace_path: Path) -> List[str]:
        logger.debug("Reading actions for channel %s from %s", channel_id, workspace_path)
        actions = ActionLogger(workspace_path).get_recent_actions(limit=8)
        lines = []
        for action in actions:
            name = action.get("action") or "action"
            resource = action.get("resource") or ""
            when = action.get("timestamp") or ""
            lines.append(f"{when} {name} {resource}".strip())
        return lines

    def _gh(self, argv: List[str], context: Dict[str, Any]) -> GhOutput:
        result = self.github.execute({"argv": argv}, context)
        data = result.data or {}
        exit_code = data.get("exit_code", 0 if result.success else 1)
        stdout = data.get("stdout") or ""
        if not result.success:
            return GhOutput(stdout="", error=result.error or result.message or "gh failed")
        if exit_code != 0:
            return GhOutput(stdout="", error=result.message or f"gh exited {exit_code}")
        return GhOutput(stdout=stdout or (result.message or ""), error=None)

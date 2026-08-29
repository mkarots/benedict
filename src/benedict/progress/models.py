"""Data types for the progress loop."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

ACTIONS = ("skip", "ask", "issue", "implement")


@dataclass
class ProjectRef:
    """One onboarded Slack channel and its local repo."""

    channel_id: str
    repo: str
    repo_path: str
    workspace_path: str = ""


@dataclass
class GithubItem:
    """A GitHub issue or pull request in the snapshot."""

    number: int
    title: str
    url: str = ""
    kind: str = "issue"
    labels: List[str] = field(default_factory=list)


@dataclass
class ProjectSnapshot:
    """What the decider may use. No Slack history."""

    project: ProjectRef
    purpose: str = ""
    readme: str = ""
    roadmap: str = ""
    recent_actions: List[str] = field(default_factory=list)
    open_issues: List[GithubItem] = field(default_factory=list)
    open_prs: List[GithubItem] = field(default_factory=list)
    known_labels: List[str] = field(default_factory=list)
    last_kind: Optional[str] = None
    pending_thread_ts: Optional[str] = None
    github_error: Optional[str] = None


@dataclass
class Decision:
    """One next action for a project."""

    action: str
    reason: str
    title: str = ""
    body: str = ""
    labels: List[str] = field(default_factory=list)
    issue_number: Optional[int] = None

    def is_valid(self) -> bool:
        return self.action in ACTIONS


@dataclass
class ActionResult:
    """Outcome of executing a decision."""

    channel_id: str
    repo: str
    action: str
    ok: bool
    summary: str
    url: Optional[str] = None
    thread_ts: Optional[str] = None
    skipped: bool = False

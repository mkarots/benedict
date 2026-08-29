"""Execute a progress decision: Slack question, GitHub issue, or implement note."""

from __future__ import annotations

import logging
from typing import List, Optional, Protocol

from benedict.commands.github_tools import RunGithubTool
from benedict.progress.models import ActionResult, Decision, ProjectSnapshot

logger = logging.getLogger(__name__)


class ChannelPoster(Protocol):
    """Post a message to a Slack channel. Returns the message timestamp."""

    def post(
        self, channel_id: str, text: str, thread_ts: Optional[str] = None
    ) -> Optional[str]: ...


class NullPoster:
    """No-op poster for tests and when Slack is unavailable."""

    def post(self, channel_id: str, text: str, thread_ts: Optional[str] = None) -> Optional[str]:
        logger.info(
            "NullPoster skip post channel=%s thread=%s chars=%s", channel_id, thread_ts, len(text)
        )
        return None


class SlackWebClientPoster:
    """Poster backed by slack_sdk WebClient."""

    def __init__(self, client):
        self.client = client

    def post(self, channel_id: str, text: str, thread_ts: Optional[str] = None) -> Optional[str]:
        kwargs = {"channel": channel_id, "text": text}
        if thread_ts:
            kwargs["thread_ts"] = thread_ts
        response = self.client.chat_postMessage(**kwargs)
        if not response.get("ok"):
            raise RuntimeError(response.get("error") or "chat.postMessage failed")
        return response.get("ts")


class ActionExecutor:
    """Turn a Decision into GitHub and Slack side effects."""

    def __init__(self, poster: ChannelPoster, github: Optional[RunGithubTool] = None):
        self.poster = poster
        self.github = github or RunGithubTool()

    def execute(self, snapshot: ProjectSnapshot, decision: Decision) -> ActionResult:
        project = snapshot.project
        if decision.action == "skip":
            return ActionResult(
                channel_id=project.channel_id,
                repo=project.repo,
                action="skip",
                ok=True,
                summary=decision.reason,
                skipped=True,
            )
        if decision.action == "ask":
            return self._ask(snapshot, decision)
        if decision.action == "issue":
            return self._issue(snapshot, decision)
        if decision.action == "implement":
            return self._implement(snapshot, decision)
        return ActionResult(
            channel_id=project.channel_id,
            repo=project.repo,
            action=decision.action,
            ok=False,
            summary=f"Unknown action {decision.action}",
        )

    def _ask(self, snapshot: ProjectSnapshot, decision: Decision) -> ActionResult:
        project = snapshot.project
        text = (
            f"*Need a decision to keep going on `{project.repo}`*\n\n"
            f"*{decision.title}*\n\n"
            f"{decision.body}\n\n"
            f"_{decision.reason}_\n\n"
            "Reply in this thread. I will not take another unattended action on this repo until you do."
        )
        ts = self.poster.post(project.channel_id, text)
        return ActionResult(
            channel_id=project.channel_id,
            repo=project.repo,
            action="ask",
            ok=True,
            summary=decision.title,
            thread_ts=ts,
        )

    def _issue(self, snapshot: ProjectSnapshot, decision: Decision) -> ActionResult:
        project = snapshot.project
        if _title_exists(decision.title, snapshot):
            return ActionResult(
                channel_id=project.channel_id,
                repo=project.repo,
                action="skip",
                ok=True,
                summary=f"An open issue already covers: {decision.title}",
                skipped=True,
            )
        created = self._create_issue(snapshot, decision)
        if not created.ok:
            return created
        notice = (
            f"*Progress on `{project.repo}`: opened an issue*\n\n"
            f"{created.url or created.summary}\n\n"
            f"_{decision.reason}_"
        )
        ts = self.poster.post(project.channel_id, notice)
        created.thread_ts = ts
        return created

    def _implement(self, snapshot: ProjectSnapshot, decision: Decision) -> ActionResult:
        """v1 cannot open a PR. File or point at an issue, then tell Slack it is ready to code."""
        project = snapshot.project
        issue_url = None
        issue_ref = None
        if decision.issue_number:
            match = next(
                (item for item in snapshot.open_issues if item.number == decision.issue_number),
                None,
            )
            if match:
                issue_url = match.url
                issue_ref = f"#{match.number} {match.title}"
        if issue_ref is None:
            if _title_exists(decision.title, snapshot):
                match = _matching_issue(decision.title, snapshot)
                if match:
                    issue_url = match.url
                    issue_ref = f"#{match.number} {match.title}"
            else:
                created = self._create_issue(snapshot, decision)
                if not created.ok:
                    return created
                issue_url = created.url
                issue_ref = created.summary

        text = (
            f"*Progress on `{project.repo}`: ready to implement*\n\n"
            f"{issue_ref or decision.title}\n\n"
            f"{decision.body or decision.reason}\n\n"
            "_Benedict does not open pull requests yet. Implement this in Cursor "
            "(Benedict MCP can supply repo context), or reply here and I will keep going "
            "on planning once you say it is done._"
        )
        ts = self.poster.post(project.channel_id, text)
        return ActionResult(
            channel_id=project.channel_id,
            repo=project.repo,
            action="implement",
            ok=True,
            summary=issue_ref or decision.title,
            url=issue_url,
            thread_ts=ts,
        )

    def _create_issue(self, snapshot: ProjectSnapshot, decision: Decision) -> ActionResult:
        project = snapshot.project
        body = decision.body.strip() + (
            "\n\n---\nFiled by Benedict progress loop. " f"{decision.reason}".rstrip()
        )
        argv: List[str] = ["issue", "create", "--title", decision.title, "--body", body]
        for label in decision.labels:
            argv.extend(["--label", label])
        result = self.github.execute({"argv": argv}, {"workspace_path": project.repo_path})
        data = result.data or {}
        if not result.success or data.get("exit_code", 1) not in (0, None):
            if decision.labels:
                retry = Decision(
                    action="issue",
                    reason=decision.reason,
                    title=decision.title,
                    body=decision.body,
                    labels=[],
                )
                return self._create_issue(snapshot, retry)
            return ActionResult(
                channel_id=project.channel_id,
                repo=project.repo,
                action="issue",
                ok=False,
                summary=result.error or result.message or "gh issue create failed",
            )
        url = (data.get("stdout") or result.message or "").strip().splitlines()[-1]
        return ActionResult(
            channel_id=project.channel_id,
            repo=project.repo,
            action="issue",
            ok=True,
            summary=decision.title,
            url=url or None,
        )


def _normalize_title(title: str) -> str:
    return " ".join(title.lower().split())


def _title_exists(title: str, snapshot: ProjectSnapshot) -> bool:
    return _matching_issue(title, snapshot) is not None


def _matching_issue(title: str, snapshot: ProjectSnapshot):
    needle = _normalize_title(title)
    if not needle:
        return None
    for item in snapshot.open_issues:
        if _normalize_title(item.title) == needle:
            return item
    return None

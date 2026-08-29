"""Decide the next progress action from a snapshot."""

from __future__ import annotations

import json
import logging
import re
from typing import Any, List, Optional

from benedict.progress.models import Decision, GithubItem, ProjectSnapshot

logger = logging.getLogger(__name__)

DECISION_SYSTEM = """You are Benedict's progress loop. You pick exactly one next action for a software project.

You are not chatting. You do not write code. You do not merge. You do not close issues.

Return ONLY a JSON object with these keys:
- action: one of skip, ask, issue, implement
- reason: one sentence why this is the next step
- title: short title (required for ask, issue, implement)
- body: Slack question or GitHub issue body (required for ask and issue)
- labels: optional list of label names that already exist on the repo
- issue_number: optional existing issue number when action is implement

Rules:
1. skip if nothing useful can be done, GitHub is unavailable and you would need it, or the same work is already an open issue or PR.
2. ask if you need a human decision, preference, or missing product fact before the next milestone step. Ask one concrete question. Do not ask something the snapshot already answers.
3. issue if the next milestone step is clear and no open issue already covers it. Write a scoped GitHub issue (title + body with context and acceptance). Prefer one small step over a large epic.
4. implement if an existing open issue is ready to turn into a pull request, or the next step is a bounded code change with enough context. Set issue_number when an issue already exists.

Do not duplicate titles already in open issues. Notion is not available. Cursor cannot be invoked from this loop.
"""

_FENCE = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL)
_OBJECT = re.compile(r"\{.*\}", re.DOTALL)


def snapshot_to_prompt(snapshot: ProjectSnapshot) -> str:
    """Turn a snapshot into the user message for the decider."""
    project = snapshot.project
    lines: List[str] = [
        f"Repo: {project.repo}",
        f"Local path: {project.repo_path}",
    ]
    if snapshot.purpose:
        lines.append(f"Purpose: {snapshot.purpose}")
    if snapshot.last_kind:
        lines.append(f"Last progress action: {snapshot.last_kind}")
    if snapshot.pending_thread_ts:
        lines.append(f"Pending question thread: {snapshot.pending_thread_ts}")
    if snapshot.github_error:
        lines.append(f"GitHub error: {snapshot.github_error}")
    lines.append(_item_block("Open issues", snapshot.open_issues))
    lines.append(_item_block("Open pull requests", snapshot.open_prs))
    if snapshot.known_labels:
        lines.append("Known labels: " + ", ".join(snapshot.known_labels[:30]))
    if snapshot.recent_actions:
        lines.append(
            "Recent workspace actions:\n" + "\n".join(f"- {a}" for a in snapshot.recent_actions)
        )
    if snapshot.roadmap:
        lines.append(snapshot.roadmap)
    if snapshot.readme:
        lines.append("## README.md\n" + snapshot.readme)
    lines.append("Pick the single next action.")
    return "\n\n".join(lines)


def _item_block(heading: str, items: List[GithubItem]) -> str:
    if not items:
        return f"{heading}: none"
    rows = []
    for item in items:
        labels = f" [{', '.join(item.labels)}]" if item.labels else ""
        rows.append(f"- #{item.number} {item.title}{labels} {item.url}".strip())
    return f"{heading}:\n" + "\n".join(rows)


def parse_decision(raw: Any) -> Optional[Decision]:
    """Parse a model reply into a Decision, or None if unusable."""
    if isinstance(raw, dict):
        payload = raw
    elif isinstance(raw, str):
        payload = _extract_json(raw)
        if payload is None:
            return None
    else:
        return None

    action = str(payload.get("action") or "").strip().lower()
    if action == "pr":
        action = "implement"
    reason = str(payload.get("reason") or "").strip()
    title = str(payload.get("title") or "").strip()
    body = str(payload.get("body") or "").strip()
    labels_raw = payload.get("labels") or []
    labels = (
        [str(item).strip() for item in labels_raw if str(item).strip()]
        if isinstance(labels_raw, list)
        else []
    )
    issue_number = payload.get("issue_number")
    if issue_number is not None:
        try:
            issue_number = int(issue_number)
        except (TypeError, ValueError):
            issue_number = None

    decision = Decision(
        action=action,
        reason=reason or "No reason given.",
        title=title,
        body=body,
        labels=labels,
        issue_number=issue_number,
    )
    if not decision.is_valid():
        return None
    if decision.action in ("ask", "issue") and not (decision.title and decision.body):
        return None
    if decision.action == "implement" and not (decision.title or decision.issue_number):
        return None
    return decision


def _extract_json(text: str) -> Optional[dict]:
    text = text.strip()
    fenced = _FENCE.search(text)
    if fenced:
        text = fenced.group(1)
    else:
        match = _OBJECT.search(text)
        if not match:
            return None
        text = match.group(0)
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


class ActionDecider:
    """LLM-backed choice of the next action."""

    def __init__(self, llm):
        self.llm = llm

    def decide(self, snapshot: ProjectSnapshot) -> Decision:
        prompt = snapshot_to_prompt(snapshot)
        try:
            raw = self.llm.generate(
                messages=[{"role": "user", "content": prompt}],
                system=DECISION_SYSTEM,
                max_tokens=800,
            )
        except Exception:
            logger.exception("Progress decider LLM failed for %s", snapshot.project.repo)
            return Decision(action="skip", reason="The progress decider could not call the model.")

        if isinstance(raw, dict) and "tool_calls" in raw:
            return Decision(
                action="skip", reason="The progress decider returned tool calls instead of JSON."
            )

        parsed = parse_decision(raw)
        if parsed is None:
            logger.warning("Progress decider returned unusable output: %r", raw)
            return Decision(
                action="skip", reason="The progress decider did not return a usable action."
            )
        parsed.labels = [label for label in parsed.labels if label in set(snapshot.known_labels)]
        return parsed

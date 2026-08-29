#!/usr/bin/env python3
"""Gate `gh pr create` until README/docs are in the branch when code changed."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Iterable, List, Set

DOC_PREFIXES = (
    "README.md",
    "CHANGELOG.md",
    "docs/",
    "plans/",
    "CLAUDE.md",
    "AGENTS.md",
    "OPEN_SOURCE",
)

CODE_PREFIXES = (
    "src/",
    "tests/",
    "Makefile",
    "pyproject.toml",
)


def _emit(payload: dict) -> None:
    sys.stdout.write(json.dumps(payload))


def _git(args: List[str], cwd: Path) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return ""
    return result.stdout


def _repo_root(cwd: Path) -> Path:
    out = _git(["rev-parse", "--show-toplevel"], cwd).strip()
    return Path(out) if out else cwd


def _default_base(repo: Path) -> str:
    for candidate in ("origin/main", "main", "origin/master", "master"):
        probe = _git(["rev-parse", "--verify", candidate], repo).strip()
        if probe:
            return candidate
    return "HEAD"


def _names(text: str) -> Set[str]:
    return {line.strip() for line in text.splitlines() if line.strip()}


def _matches(path: str, prefixes: Iterable[str]) -> bool:
    return any(path == prefix or path.startswith(prefix) for prefix in prefixes)


def _agent_message(code_files: List[str], uncommitted_docs: List[str]) -> str:
    code_list = "\n".join(f"- `{path}`" for path in code_files[:20]) or "- (code changes on this branch)"
    extra = ""
    if uncommitted_docs:
        extra = (
            "\n\nYou already edited documentation but have not committed it:\n"
            + "\n".join(f"- `{path}`" for path in uncommitted_docs)
            + "\nCommit those files, then retry `gh pr create`."
        )
    return (
        "This pull request includes code changes without updated documentation.\n\n"
        "Before creating the PR, update documentation to match the current system:\n"
        "1. Update `README.md` (commands, setup, current status, configuration).\n"
        "2. Update files under `docs/` (and `plans/` if architecture changed).\n"
        "3. Update `CHANGELOG.md` and the version in `pyproject.toml`.\n"
        "4. Commit those files on this branch, then retry `gh pr create`.\n\n"
        "Code files in this PR:\n"
        f"{code_list}"
        f"{extra}"
    )


def main() -> int:
    try:
        raw = sys.stdin.read()
        data = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError:
        _emit({"permission": "allow"})
        return 0

    command = data.get("command") or ""
    if "gh pr create" not in command.replace("\t", " "):
        _emit({"permission": "allow"})
        return 0

    cwd = Path(data.get("cwd") or Path.cwd())
    repo = _repo_root(cwd)
    base = _default_base(repo)

    committed = _names(_git(["diff", "--name-only", "--diff-filter=ACMR", f"{base}...HEAD"], repo))
    unstaged = _names(_git(["diff", "--name-only", "--diff-filter=ACMR"], repo))
    staged = _names(_git(["diff", "--name-only", "--cached", "--diff-filter=ACMR"], repo))
    untracked = _names(_git(["ls-files", "--others", "--exclude-standard"], repo))

    pr_files = committed
    worktree = unstaged | staged | untracked
    all_files = pr_files | worktree

    code_in_pr = sorted(path for path in pr_files if _matches(path, CODE_PREFIXES))
    code_anywhere = sorted(path for path in all_files if _matches(path, CODE_PREFIXES))
    docs_in_pr = sorted(path for path in pr_files if _matches(path, DOC_PREFIXES))
    uncommitted_docs = sorted(path for path in worktree if _matches(path, DOC_PREFIXES))

    # Docs-only PRs, or code PRs that already include docs, may proceed.
    if docs_in_pr or not (code_in_pr or code_anywhere):
        _emit({"permission": "allow"})
        return 0

    _emit(
        {
            "permission": "deny",
            "user_message": "PR creation blocked until README.md and docs match the current system.",
            "agent_message": _agent_message(code_in_pr or code_anywhere, uncommitted_docs),
        }
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

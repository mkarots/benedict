"""CI workflow matches the advertised jobs and Python versions."""

from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "ci.yml"


def _workflow() -> dict:
    return yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))


def test_ci_workflow_exists():
    assert WORKFLOW.is_file()


def test_ci_runs_on_push_and_pull_request():
    # PyYAML 1.1 treats the unquoted key `on` as boolean True.
    triggers = _workflow().get("on") or _workflow().get(True)
    assert triggers is not None
    assert "push" in triggers
    assert "pull_request" in triggers
    assert "main" in triggers["push"]["branches"]


def test_ci_has_lint_typecheck_and_test_jobs():
    jobs = _workflow()["jobs"]
    assert set(jobs) == {"lint", "typecheck", "test"}


def test_test_job_runs_python_3_12_only():
    job = _workflow()["jobs"]["test"]
    assert "strategy" not in job
    versions = [
        step["with"]["python-version"]
        for step in job["steps"]
        if "with" in step and "python-version" in step["with"]
    ]
    assert versions == ["3.12"]

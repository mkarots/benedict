"""GitHub pull request template exists at the default path with required sections."""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
PR_TEMPLATE = REPO_ROOT / ".github" / "PULL_REQUEST_TEMPLATE.md"

REQUIRED_HEADINGS = (
    "## Description",
    "## Related issues",
    "## Type of change",
    "## Testing done",
    "## Screenshots",
)

CHECKLIST_ITEMS = (
    "Tests added or updated",
    "Docs match the code",
    "CHANGELOG.md",
)

TYPE_OF_CHANGE = (
    "Bug fix",
    "New feature",
    "Documentation",
)


def test_pr_template_is_at_github_default_path():
    """GitHub pre-fills new PRs from .github/PULL_REQUEST_TEMPLATE.md on the default branch."""
    assert PR_TEMPLATE.is_file(), ".github/PULL_REQUEST_TEMPLATE.md is missing"


def test_pr_template_has_required_sections():
    text = PR_TEMPLATE.read_text(encoding="utf-8")
    missing = [heading for heading in REQUIRED_HEADINGS if heading not in text]
    assert missing == [], f"PULL_REQUEST_TEMPLATE.md missing headings: {missing}"


def test_pr_template_covers_change_types_and_checklist():
    text = PR_TEMPLATE.read_text(encoding="utf-8")
    missing_types = [label for label in TYPE_OF_CHANGE if label not in text]
    assert missing_types == [], f"type of change missing: {missing_types}"
    missing_checks = [item for item in CHECKLIST_ITEMS if item not in text]
    assert missing_checks == [], f"checklist missing: {missing_checks}"
    assert "Fixes #" in text
    assert "operator UI" in text
    assert "docs/assets/" in text

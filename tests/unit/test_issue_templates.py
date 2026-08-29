"""GitHub issue templates exist and include the required reporter fields."""

from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
TEMPLATE_DIR = REPO_ROOT / ".github" / "ISSUE_TEMPLATE"
FEATURE_REQUEST = TEMPLATE_DIR / "feature_request.md"
CONFIG = TEMPLATE_DIR / "config.yml"

FEATURE_HEADINGS = (
    "## Feature description",
    "## Use case",
    "## Proposed solution",
    "## Alternatives considered",
)


def test_feature_request_template_has_required_sections():
    text = FEATURE_REQUEST.read_text(encoding="utf-8")
    assert text.startswith("---\n")
    missing = [heading for heading in FEATURE_HEADINGS if heading not in text]
    assert missing == [], f"feature_request.md missing headings: {missing}"
    assert "labels: enhancement" in text
    frontmatter = text.split("---\n", 2)[1]
    meta = yaml.safe_load(frontmatter)
    assert meta["name"] == "Feature request"


def test_feature_request_appears_in_template_dir_with_chooser():
    """GitHub lists every markdown template next to config.yml in the chooser."""
    assert FEATURE_REQUEST.is_file()
    cfg = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    assert cfg["blank_issues_enabled"] is True
    names = [path.name for path in TEMPLATE_DIR.glob("*.md")]
    assert "feature_request.md" in names
    assert "bug_report.md" in names

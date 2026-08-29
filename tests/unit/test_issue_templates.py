"""GitHub issue templates exist and include the required reporter fields."""

from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
TEMPLATE_DIR = REPO_ROOT / ".github" / "ISSUE_TEMPLATE"
BUG_REPORT = TEMPLATE_DIR / "bug_report.md"
CONFIG = TEMPLATE_DIR / "config.yml"

REQUIRED_HEADINGS = (
    "## Description",
    "## Steps to reproduce",
    "## Expected behavior",
    "## Actual behavior",
    "## Environment",
    "## Logs / screenshots",
)


def test_bug_report_template_has_required_sections():
    text = BUG_REPORT.read_text(encoding="utf-8")
    assert text.startswith("---\n")
    missing = [heading for heading in REQUIRED_HEADINGS if heading not in text]
    assert missing == [], f"bug_report.md missing headings: {missing}"
    assert "labels: bug" in text


def test_issue_template_config_enables_chooser():
    cfg = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    assert cfg["blank_issues_enabled"] is True
    names = [link["name"] for link in cfg["contact_links"]]
    assert "Report a security vulnerability" in names
    assert "Code of Conduct" in names

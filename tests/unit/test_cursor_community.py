"""Project .cursor rules and skills point at community files."""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
GITIGNORE = REPO_ROOT / ".gitignore"
COMMUNITY_RULE = REPO_ROOT / ".cursor" / "rules" / "community.mdc"
GITHUB_ISSUE_SKILL = REPO_ROOT / ".cursor" / "skills" / "github-issue" / "SKILL.md"
PR_TEMPLATE = REPO_ROOT / ".github" / "PULL_REQUEST_TEMPLATE.md"
BUG_TEMPLATE = REPO_ROOT / ".github" / "ISSUE_TEMPLATE" / "bug_report.md"
CONTRIBUTING = REPO_ROOT / "CONTRIBUTING.md"
CODE_OF_CONDUCT = REPO_ROOT / "CODE_OF_CONDUCT.md"


def test_community_files_exist():
    missing = [
        path.name
        for path in (
            CONTRIBUTING,
            CODE_OF_CONDUCT,
            PR_TEMPLATE,
            BUG_TEMPLATE,
            COMMUNITY_RULE,
            GITHUB_ISSUE_SKILL,
        )
        if not path.is_file()
    ]
    assert missing == [], f"missing community files: {missing}"


def test_community_rule_points_at_sources_of_truth():
    text = COMMUNITY_RULE.read_text(encoding="utf-8")
    for needle in (
        "CONTRIBUTING.md",
        "CODE_OF_CONDUCT.md",
        "bug_report.md",
        "PULL_REQUEST_TEMPLATE.md",
        "github-issue",
    ):
        assert needle in text, f"community rule must mention {needle}"


def test_github_issue_skill_is_discoverable():
    text = GITHUB_ISSUE_SKILL.read_text(encoding="utf-8")
    assert "name: github-issue" in text
    assert "/github-issue" in text
    assert "disable-model-invocation" not in text


def test_gitignore_does_not_ignore_cursor_rules_or_skills():
    text = GITIGNORE.read_text(encoding="utf-8")
    assert ".cursor/" not in text.splitlines()
    assert ".cursor/mcp.json" in text


def test_contributing_mentions_cursor_agents():
    text = CONTRIBUTING.read_text(encoding="utf-8")
    assert "## AI agents" in text
    assert ".cursor/" in text
    assert "PULL_REQUEST_TEMPLATE.md" in text

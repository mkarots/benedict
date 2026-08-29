"""Cursor agent rules exist and are the source of truth for CLAUDE.md."""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
RULES_DIR = REPO_ROOT / ".cursor" / "rules"
CLAUDE = REPO_ROOT / "CLAUDE.md"
PROCESS = REPO_ROOT / "docs" / "PROCESS.md"
GITIGNORE = REPO_ROOT / ".gitignore"

RULE_FILES = (
    "technical-writing.mdc",
    "design-documents.mdc",
    "code-architecture.mdc",
    "version-bump.mdc",
)


def test_cursor_rule_files_exist():
    missing = [name for name in RULE_FILES if not (RULES_DIR / name).is_file()]
    assert missing == [], f"Missing Cursor rules: {missing}"


def test_each_rule_has_frontmatter_description():
    for name in RULE_FILES:
        text = (RULES_DIR / name).read_text(encoding="utf-8")
        assert text.startswith("---\n"), f"{name} must start with YAML frontmatter"
        assert "description:" in text, f"{name} must set description"


def test_version_bump_rule_names_version_files():
    text = (RULES_DIR / "version-bump.mdc").read_text(encoding="utf-8")
    assert "alwaysApply: true" in text
    assert "pyproject.toml" in text
    assert "CHANGELOG.md" in text
    assert "src/benedict/__init__.py" in text
    assert "README.md" in text


def test_design_documents_rule_requires_core_sections():
    text = (RULES_DIR / "design-documents.mdc").read_text(encoding="utf-8")
    for section in ("Overview", "Non-Goals", "Happy Path Example", "Edge Cases"):
        assert section in text, f"design-documents.mdc must include {section}"


def test_claude_md_is_an_index_to_cursor_rules():
    text = CLAUDE.read_text(encoding="utf-8")
    assert ".cursor/rules/" in text
    for name in RULE_FILES:
        assert name in text, f"CLAUDE.md must point at {name}"
    assert "<TECHNICAL_DOCUMENTATION>" not in text
    assert "<DESIGN_DOCUMENT>" not in text


def test_readme_and_contributing_point_at_cursor_rules():
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    contributing = (REPO_ROOT / "CONTRIBUTING.md").read_text(encoding="utf-8")
    assert ".cursor/rules/" in readme
    assert ".cursor/rules/" in contributing


def test_process_doc_points_at_design_documents_rule():
    text = PROCESS.read_text(encoding="utf-8")
    assert ".cursor/rules/design-documents.mdc" in text
    assert "CLAUDE.md" not in text


def test_gitignore_tracks_cursor_rules():
    text = GITIGNORE.read_text(encoding="utf-8")
    assert ".cursor/*" in text
    assert "!.cursor/rules/" in text
    assert "!.cursor/rules/**" in text

"""Published system-design page follows the design-document outline."""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
PAGE = REPO_ROOT / "docs" / "architecture.md"

REQUIRED_HEADINGS = [
    "## 1. Overview",
    "## 2. Non-Goals",
    "## 3. Key Concepts & Terminology",
    "## 4. High-Level Design",
    "## 5. API / Interface",
    "## 6. Happy Path Example",
    "## 7. Edge Cases & Failure Modes",
    "## 8. Constraints & Assumptions",
    "## 9. Alternatives Considered",
    "## 10. Open Questions",
]

REQUIRED_CLAIMS = [
    "RepoAgent",
    "benedict-mcp",
    "POST /v1/chat",
    "127.0.0.1:8765",
    "run_github",
    "run_notion",
    "ProgressService",
    "state.json",
    "one channel, one repo",
]


def test_architecture_page_is_current_design_doc():
    text = PAGE.read_text(encoding="utf-8")
    assert text.startswith("Status: Current")
    assert "One-sentence summary:" in text
    for heading in REQUIRED_HEADINGS:
        assert heading in text, f"missing {heading}"


def test_architecture_page_names_current_components():
    text = PAGE.read_text(encoding="utf-8")
    lowered = text.lower()
    for claim in REQUIRED_CLAIMS:
        assert claim.lower() in lowered, f"missing {claim}"

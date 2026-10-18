"""The operator-UI token-usage plan follows the design-document outline."""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
TOKEN_USAGE = REPO_ROOT / "docs" / "TOKEN_USAGE.md"
ADR = REPO_ROOT / "docs" / "adr" / "0003-operator-ui-token-usage.md"

REQUIRED_SECTIONS = (
    "Overview",
    "Non-Goals",
    "Key Concepts & Terminology",
    "High-Level Design",
    "API / Interface",
    "Happy Path Example",
    "Edge Cases & Failure Modes",
    "Constraints & Assumptions",
    "Alternatives Considered",
    "Open Questions",
)


def test_token_usage_plan_exists():
    assert TOKEN_USAGE.is_file(), "docs/TOKEN_USAGE.md is missing"


def test_token_usage_plan_is_a_proposal():
    text = TOKEN_USAGE.read_text(encoding="utf-8")
    assert text.startswith(
        "Status: Proposal"
    ), "TOKEN_USAGE.md must not claim current shipped behavior"


def test_token_usage_plan_has_design_sections():
    text = TOKEN_USAGE.read_text(encoding="utf-8")
    missing = [name for name in REQUIRED_SECTIONS if name not in text]
    assert missing == [], f"docs/TOKEN_USAGE.md is missing sections: {missing}"


def test_token_usage_plan_uses_billed_counts_not_estimates():
    text = TOKEN_USAGE.read_text(encoding="utf-8")
    assert "TokenUsage" in text
    assert "usage.jsonl" in text
    assert "billed" in text.lower()
    assert "MiniLM" in text or "sentence-transformers" in text.lower()


def test_token_usage_plan_covers_every_generate_site():
    text = TOKEN_USAGE.read_text(encoding="utf-8")
    assert "tool_loop.py" in text
    assert "llm_classifier.py" in text
    assert "decide.py" in text
    assert "mcp/service.py" in text


def test_token_usage_adr_is_proposed_and_points_at_the_plan():
    assert ADR.is_file(), "docs/adr/0003-operator-ui-token-usage.md is missing"
    text = ADR.read_text(encoding="utf-8")
    assert "Status: Proposed" in text
    assert "TOKEN_USAGE.md" in text
    assert "#131" in text
    assert "ClaudeLLM" in text

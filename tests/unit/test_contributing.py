"""CONTRIBUTING.md exists and is linked from the README."""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
CONTRIBUTING = REPO_ROOT / "CONTRIBUTING.md"
README = REPO_ROOT / "README.md"

REQUIRED_HEADINGS = (
    "Development environment",
    "Tests",
    "Code style and type checking",
    "Commit messages",
    "Issue reporting",
    "Pull requests",
)


def test_contributing_guide_exists():
    assert CONTRIBUTING.is_file(), "CONTRIBUTING.md is missing from the repository root"


def test_contributing_guide_covers_required_topics():
    text = CONTRIBUTING.read_text(encoding="utf-8")
    missing = [heading for heading in REQUIRED_HEADINGS if f"## {heading}" not in text]
    assert missing == [], f"CONTRIBUTING.md is missing sections: {missing}"


def test_readme_links_to_contributing_guide():
    text = README.read_text(encoding="utf-8")
    assert "[CONTRIBUTING.md](CONTRIBUTING.md)" in text, "README must link to CONTRIBUTING.md"


def test_contributing_and_readme_link_to_feature_request_template():
    template = "https://github.com/mkarots/benedict/issues/new?template=feature_request.md"
    contributing = CONTRIBUTING.read_text(encoding="utf-8")
    readme = README.read_text(encoding="utf-8")
    assert template in contributing, "CONTRIBUTING must link to the feature request template"
    assert template in readme, "README Community must link to the feature request template"

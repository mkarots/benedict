"""MAINTAINERS.md exists and is linked from README and CONTRIBUTING."""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
MAINTAINERS = REPO_ROOT / "MAINTAINERS.md"
README = REPO_ROOT / "README.md"
CONTRIBUTING = REPO_ROOT / "CONTRIBUTING.md"

REQUIRED_HEADINGS = (
    "Core maintainers",
    "Decision-making",
    "Becoming a maintainer",
)


def test_maintainers_file_is_at_repo_root():
    assert MAINTAINERS.is_file(), "MAINTAINERS.md is missing from the repository root"


def test_maintainers_covers_required_topics():
    text = MAINTAINERS.read_text(encoding="utf-8")
    missing = [heading for heading in REQUIRED_HEADINGS if f"## {heading}" not in text]
    assert missing == [], f"MAINTAINERS.md is missing sections: {missing}"
    assert "Michael Karotsieris" in text
    assert "https://github.com/mkarots" in text


def test_readme_and_contributing_link_to_maintainers():
    readme = README.read_text(encoding="utf-8")
    contributing = CONTRIBUTING.read_text(encoding="utf-8")
    assert "[MAINTAINERS.md](MAINTAINERS.md)" in readme
    assert "[MAINTAINERS.md](MAINTAINERS.md)" in contributing

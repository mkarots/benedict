"""README shows badges, community links, and the public clone URL."""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
README = REPO_ROOT / "README.md"


def _readme() -> str:
    return README.read_text(encoding="utf-8")


def test_readme_has_ci_license_and_python_badges():
    text = _readme()
    assert "actions/workflows/ci.yml/badge.svg" in text
    assert "License-Apache_2.0" in text
    assert "python-3.10%2B" in text


def test_readme_links_community_files():
    text = _readme()
    assert "[CONTRIBUTING.md](CONTRIBUTING.md)" in text
    assert "](CODE_OF_CONDUCT.md)" in text
    assert "[SECURITY.md](SECURITY.md)" in text
    assert "## Community" in text


def test_readme_clone_url_is_the_public_remote():
    text = _readme()
    assert "git clone https://github.com/mkarots/benedict.git" in text

"""Makefile help matches the targets contributors actually run."""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
MAKEFILE = REPO_ROOT / "Makefile"


def test_makefile_has_no_deps_target():
    text = MAKEFILE.read_text(encoding="utf-8")
    assert "make deps" not in text
    assert "\ndeps:" not in text
    assert "Checking dependencies" not in text
    phony = next(line for line in text.splitlines() if line.startswith(".PHONY:"))
    assert " deps" not in f" {phony} "

"""Standalone HTML notes live under artifacts/, not in the MkDocs sidebar."""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
ARTIFACTS = REPO_ROOT / "artifacts"

REQUIRED = (
    "REQUEST_PATH.html",
    "METADATA_SIDECAR_CHANGES.html",
)


def test_artifact_html_files_exist():
    missing = [name for name in REQUIRED if not (ARTIFACTS / name).is_file()]
    assert missing == [], f"artifacts/ is missing: {missing}"


def test_artifact_html_is_standalone():
    for name in REQUIRED:
        text = (ARTIFACTS / name).read_text(encoding="utf-8")
        assert "<!DOCTYPE html>" in text
        assert f"artifacts/{name}" in text

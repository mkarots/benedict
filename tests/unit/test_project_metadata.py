"""pyproject.toml has the package metadata GitHub and PyPI need."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

if sys.version_info >= (3, 11):
    import tomllib
else:
    tomllib = pytest.importorskip("tomli")

REPO_ROOT = Path(__file__).resolve().parents[2]
PYPROJECT = REPO_ROOT / "pyproject.toml"

REQUIRED_URLS = ("Homepage", "Repository", "Issues")
REQUIRED_CLASSIFIER_FRAGMENTS = (
    "Programming Language :: Python :: 3.10",
    "License :: OSI Approved :: Apache Software License",
)


def _project() -> dict:
    with PYPROJECT.open("rb") as handle:
        return tomllib.load(handle)["project"]


def test_license_matches_license_file():
    project = _project()
    assert project["license"]["text"] == "Apache-2.0"
    assert (REPO_ROOT / "LICENSE").read_text(encoding="utf-8").lstrip().startswith(
        "Apache License"
    )


def test_authors_and_maintainers_are_present():
    project = _project()
    authors = project.get("authors") or []
    maintainers = project.get("maintainers") or []
    assert authors, "authors must be set"
    assert maintainers, "maintainers must be set"
    assert all(entry.get("name") for entry in authors)
    assert all(entry.get("name") for entry in maintainers)


def test_classifiers_cover_python_and_license():
    classifiers = _project().get("classifiers") or []
    for fragment in REQUIRED_CLASSIFIER_FRAGMENTS:
        assert fragment in classifiers, f"missing classifier: {fragment}"


def test_project_urls_include_homepage_repository_issues():
    urls = _project().get("urls") or {}
    missing = [key for key in REQUIRED_URLS if key not in urls]
    assert not missing, f"missing project.urls keys: {missing}"
    for key in REQUIRED_URLS:
        assert urls[key].startswith("https://github.com/mkarots/benedict")


def test_keywords_are_present():
    keywords = _project().get("keywords") or []
    assert keywords, "keywords must be set"
    assert "slack-bot" in keywords
    assert "llm" in keywords


def test_requires_python_is_3_10_or_newer():
    assert _project()["requires-python"] == ">=3.10"

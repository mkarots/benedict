"""Tests for SearchHit."""

from dataclasses import FrozenInstanceError, replace

import pytest

from benedict.semantic_indexer.search_hit import SearchHit


def test_to_dict_omits_unset_project():
    hit = SearchHit(file_path="src/a.py", content="class A:", score=0.91)
    assert hit.to_dict() == {
        "file_path": "src/a.py",
        "content": "class A:",
        "score": 0.91,
    }


def test_to_dict_includes_project():
    hit = SearchHit(file_path="src/a.py", content="", score=0.5, project="acme/one")
    assert hit.to_dict()["project"] == "acme/one"


def test_replace_score_and_project():
    hit = SearchHit(file_path="src/a.py", content="x", score=0.5)
    boosted = replace(hit, score=0.6, project="acme/one")
    assert boosted.score == 0.6
    assert boosted.project == "acme/one"
    assert hit.score == 0.5
    assert hit.project is None


def test_from_mapping_fills_defaults():
    hit = SearchHit.from_mapping({"score": None, "content": "hello"})
    assert hit.file_path == "unknown"
    assert hit.content == "hello"
    assert hit.score == 0.0
    assert hit.project is None


def test_frozen():
    hit = SearchHit(file_path="src/a.py", content="", score=0.1)
    with pytest.raises(FrozenInstanceError):
        hit.score = 0.2  # type: ignore[misc]

"""Directory boost contract: order and sidecar-path non-match."""

from benedict.semantic_indexer.metadata.directory_boost import apply_directory_boost
from benedict.semantic_indexer.search_hit import SearchHit


def _hit(file_path: str, score: float) -> SearchHit:
    return SearchHit(file_path=file_path, content="", score=score)


def test_equal_scores_matched_dir_ranks_first():
    hits = [
        _hit("docs/deploy.md", 0.50),
        _hit("src/auth/session.py", 0.50),
    ]
    ranked = apply_directory_boost(hits, {"src/auth"})
    assert [row.file_path for row in ranked] == [
        "src/auth/session.py",
        "docs/deploy.md",
    ]
    assert ranked[0].score == 0.60
    assert ranked[1].score == 0.50


def test_unmatched_scores_unchanged():
    hits = [_hit("docs/deploy.md", 0.40)]
    ranked = apply_directory_boost(hits, {"src/auth"})
    assert ranked[0].score == 0.40


def test_parent_dir_boosts_nested_file():
    hits = [
        _hit("src/auth/jwt.py", 0.50),
        _hit("src/other.py", 0.50),
    ]
    ranked = apply_directory_boost(hits, {"src/auth"})
    assert ranked[0].file_path == "src/auth/jwt.py"
    assert ranked[1].file_path == "src/other.py"


def test_sidecar_path_in_relevant_dirs_does_not_boost():
    hits = [
        _hit("src/auth/session.py", 0.50),
        _hit("docs/deploy.md", 0.50),
    ]
    ranked = apply_directory_boost(hits, {".benedict/metadata/example-org/example-repo/src/auth"})
    assert [row.file_path for row in ranked] == [
        "src/auth/session.py",
        "docs/deploy.md",
    ]
    assert ranked[0].score == 0.50
    assert ranked[1].score == 0.50


def test_org_repo_prefix_does_not_match_source_dir():
    hits = [_hit("src/auth/session.py", 0.50)]
    ranked = apply_directory_boost(hits, {"example-org/example-repo/src/auth"})
    assert ranked[0].score == 0.50

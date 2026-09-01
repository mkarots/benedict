"""Skip overlay walk relative to the repo root only."""

from pathlib import Path

from benedict.semantic_indexer.metadata.source_dir_skip import should_skip_source_directory


def test_repo_under_hidden_data_dir_is_not_skipped(tmp_path: Path):
    repo = tmp_path / ".benedict" / "workspaces" / "C1" / "source_repo"
    (repo / "src").mkdir(parents=True)
    assert should_skip_source_directory(repo, repo) is False
    assert should_skip_source_directory(repo / "src", repo) is False


def test_venv_and_hidden_children_are_skipped(tmp_path: Path):
    repo = tmp_path / "repo"
    (repo / ".venv" / "lib").mkdir(parents=True)
    (repo / ".github").mkdir(parents=True)
    (repo / "node_modules" / "pkg").mkdir(parents=True)
    (repo / "src").mkdir(parents=True)
    assert should_skip_source_directory(repo / ".venv", repo) is True
    assert should_skip_source_directory(repo / ".venv" / "lib", repo) is True
    assert should_skip_source_directory(repo / ".github", repo) is True
    assert should_skip_source_directory(repo / "node_modules" / "pkg", repo) is True
    assert should_skip_source_directory(repo / "src", repo) is False


def test_path_outside_repo_is_skipped(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    other = tmp_path / "other"
    other.mkdir()
    assert should_skip_source_directory(other, repo) is True

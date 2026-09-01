"""Reader sidecar-first, then in-tree leftover."""

from pathlib import Path

from benedict.semantic_indexer.metadata import MetadataReader
from benedict.semantic_indexer.metadata.metadata_location import sidecar_path


def test_read_prefers_sidecar_over_in_tree(tmp_path: Path):
    workspace = tmp_path / "ws"
    source = workspace / "acme" / "widget" / "src"
    source.mkdir(parents=True)
    (source / ".metadata.benedict").write_text("summary: in-tree\n", encoding="utf-8")
    dest = sidecar_path(workspace, "acme/widget", "src")
    dest.parent.mkdir(parents=True)
    dest.write_text("summary: sidecar\n", encoding="utf-8")

    reader = MetadataReader()
    loaded = reader.read_metadata(source, workspace_root=workspace, repo="acme/widget")
    assert loaded["summary"] == "sidecar"


def test_read_falls_back_to_in_tree(tmp_path: Path):
    workspace = tmp_path / "ws"
    source = workspace / "acme" / "widget" / "src"
    source.mkdir(parents=True)
    (source / ".metadata.benedict").write_text("summary: leftover\n", encoding="utf-8")

    reader = MetadataReader()
    loaded = reader.read_metadata(source, workspace_root=workspace, repo="acme/widget")
    assert loaded["summary"] == "leftover"


def test_search_metadata_returns_repo_relative_paths(tmp_path: Path):
    workspace = tmp_path / "ws"
    dest = sidecar_path(workspace, "acme/widget", "src/auth")
    dest.parent.mkdir(parents=True)
    dest.write_text("summary: auth helpers\npurpose: login\n", encoding="utf-8")

    reader = MetadataReader()
    matches = reader.search_metadata(workspace, "auth", repo="acme/widget")
    assert [row["path"] for row in matches] == ["src/auth"]

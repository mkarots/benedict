"""Onboard/index writes must not enter a symlink source clone."""

from pathlib import Path

import pytest

from benedict.metadata import MetadataGenerator
from benedict.metadata.metadata_location import MetadataLocationError, sidecar_path
from benedict.workspace.workspace_manager import WorkspaceManager


def test_write_stays_in_sidecar_on_symlink_workspace(tmp_path: Path):
    source = tmp_path / "clone"
    source.mkdir()
    (source / "readme.txt").write_text("hi\n", encoding="utf-8")

    manager = WorkspaceManager(workspaces_dir=str(tmp_path / "workspaces"), copy_mode="symlink")
    manager.add_resource("C1", "repository", str(source), "acme/widget", content_type="code")
    workspace = manager.get_workspace_path("C1")
    repo_path = workspace / "acme" / "widget"

    MetadataGenerator().generate_and_write(
        repo_path, content_type="code", workspace_root=workspace, repo="acme/widget"
    )

    assert not (source / ".metadata.benedict").exists()
    assert not (repo_path / ".metadata.benedict").exists()
    assert sidecar_path(workspace, "acme/widget").is_file()
    assert (workspace / "metadata" / "acme" / "widget" / ".metadata.benedict").is_file()


def test_write_sidecar_when_workspace_lives_under_hidden_data_dir(tmp_path: Path):
    source = tmp_path / "clone"
    source.mkdir()
    (source / "src").mkdir()
    (source / "src" / "app.py").write_text("x = 1\n", encoding="utf-8")

    data = tmp_path / ".benedict"
    manager = WorkspaceManager(workspaces_dir=str(data / "workspaces"), copy_mode="symlink")
    manager.add_resource("C1", "repository", str(source), "acme/widget", content_type="code")
    workspace = manager.get_workspace_path("C1")
    repo_path = workspace / "acme" / "widget"

    MetadataGenerator().generate_and_write(
        repo_path / "src", content_type="code", workspace_root=workspace, repo="acme/widget"
    )

    assert not (source / "src" / ".metadata.benedict").exists()
    assert sidecar_path(workspace, "acme/widget", "src").is_file()


def test_write_without_locator_does_not_write_in_tree(tmp_path: Path):
    source = tmp_path / "clone"
    source.mkdir()
    generator = MetadataGenerator()
    with pytest.raises(MetadataLocationError):
        generator.write_metadata(source, {"summary": "nope"})
    assert not (source / ".metadata.benedict").exists()

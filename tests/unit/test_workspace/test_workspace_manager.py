"""Unit tests for WorkspaceManager."""

from pathlib import Path

import pytest

from benedict.workspace.workspace_manager import WorkspaceManager


def test_create_and_get_workspace(tmp_path: Path):
    manager = WorkspaceManager(workspaces_dir=str(tmp_path / "workspaces"))
    created = manager.create_workspace("C123")
    assert created.exists()
    assert created == manager.get_workspace_path("C123")


def test_add_resource_symlink_and_list(tmp_path: Path):
    source = tmp_path / "repo"
    source.mkdir()
    (source / "README.md").write_text("# repo\n", encoding="utf-8")
    (source / ".git").mkdir()

    manager = WorkspaceManager(workspaces_dir=str(tmp_path / "workspaces"), copy_mode="symlink")
    relative = manager.add_resource(
        context_id="C123",
        resource_type="repository",
        source_path=str(source),
        name="example-org/example-repo",
        content_type="code",
    )
    assert relative == "example-org/example-repo"
    assert manager.resource_exists("C123", "example-org/example-repo")

    target = manager.get_workspace_path("C123") / "example-org" / "example-repo"
    assert target.is_symlink()
    assert target.resolve() == source.resolve()

    resources = manager.list_resources("C123")
    names = {item.name for item in resources}
    assert "example-org" in names


def test_add_resource_copy_mode(tmp_path: Path):
    source = tmp_path / "repo"
    source.mkdir()
    (source / "file.txt").write_text("hi\n", encoding="utf-8")

    manager = WorkspaceManager(workspaces_dir=str(tmp_path / "workspaces"), copy_mode="copy")
    manager.add_resource("C123", "repository", str(source), "copied-repo")
    copied = manager.get_workspace_path("C123") / "copied-repo" / "file.txt"
    assert copied.read_text(encoding="utf-8") == "hi\n"
    assert not copied.is_symlink()


def test_add_resource_missing_source(tmp_path: Path):
    manager = WorkspaceManager(workspaces_dir=str(tmp_path / "workspaces"))
    with pytest.raises(FileNotFoundError):
        manager.add_resource("C123", "repository", str(tmp_path / "missing"), "repo")

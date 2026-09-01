"""Sidecar locator paths."""

from pathlib import Path

import pytest

from benedict.semantic_indexer.metadata.metadata_location import (
    MetadataLocationError,
    relative_source_dir,
    sidecar_path,
    sidecar_root,
)


def test_sidecar_path_org_repo_root():
    workspace = Path("/tmp/workspaces/C123")
    assert sidecar_path(workspace, "example-org/example-repo") == (
        workspace / "metadata" / "example-org" / "example-repo" / ".metadata.benedict"
    )


def test_sidecar_path_nested_dir():
    workspace = Path("/tmp/workspaces/C123")
    assert sidecar_path(workspace, "example-org/example-repo", "src/commands") == (
        workspace
        / "metadata"
        / "example-org"
        / "example-repo"
        / "src"
        / "commands"
        / ".metadata.benedict"
    )


def test_sidecar_root_uses_full_repo_name():
    workspace = Path("/tmp/ws")
    assert sidecar_root(workspace, "acme/widget") == (workspace / "metadata" / "acme" / "widget")


def test_relative_source_dir(tmp_path: Path):
    repo_root = tmp_path / "acme" / "widget"
    nested = repo_root / "src" / "auth"
    nested.mkdir(parents=True)
    assert relative_source_dir(nested, tmp_path, "acme/widget") == Path("src/auth")
    assert relative_source_dir(repo_root, tmp_path, "acme/widget") == Path(".")


def test_sidecar_path_rejects_absolute_relative_dir():
    with pytest.raises(MetadataLocationError):
        sidecar_path(Path("/tmp/ws"), "acme/widget", "/etc")


def test_sidecar_path_requires_repo():
    with pytest.raises(MetadataLocationError):
        sidecar_path(Path("/tmp/ws"), "")

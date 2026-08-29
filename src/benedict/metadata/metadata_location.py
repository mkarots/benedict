"""Sidecar paths for generated .metadata.benedict overlays.

Overlays live under workspace/metadata/, outside the repo symlink, so writes
do not enter the user's clone.
"""

from pathlib import Path


METADATA_FILENAME = ".metadata.benedict"
SIDECAR_METADATA_NAME = "metadata"


class MetadataLocationError(ValueError):
    """Raised when a sidecar path cannot be resolved."""


def sidecar_root(workspace_root: Path, repo: str) -> Path:
    """Return the sidecar tree root for a repo: workspace/metadata/<repo>."""
    _require_workspace_and_repo(workspace_root, repo)
    return Path(workspace_root) / SIDECAR_METADATA_NAME / Path(repo)


def sidecar_path(workspace_root: Path, repo: str, relative_dir: Path | str = ".") -> Path:
    """Map (workspace, repo, dir-relative-to-repo) to a sidecar overlay file."""
    rel = _normalize_relative_dir(relative_dir)
    return sidecar_root(workspace_root, repo) / rel / METADATA_FILENAME


def relative_source_dir(source_dir: Path, workspace_root: Path, repo: str) -> Path:
    """Return source_dir relative to the workspace repo root."""
    _require_workspace_and_repo(workspace_root, repo)
    repo_root = (Path(workspace_root) / repo).resolve()
    resolved = Path(source_dir).resolve()
    try:
        return resolved.relative_to(repo_root)
    except ValueError as exc:
        raise MetadataLocationError(
            f"{source_dir} is not inside workspace repo {repo_root}"
        ) from exc


def _require_workspace_and_repo(workspace_root: Path | None, repo: str | None) -> None:
    if workspace_root is None or not str(workspace_root).strip():
        raise MetadataLocationError("workspace_root is required for sidecar writes")
    if not repo or not str(repo).strip():
        raise MetadataLocationError("repo is required for sidecar writes")


def _normalize_relative_dir(relative_dir: Path | str) -> Path:
    rel = Path(relative_dir)
    if rel.is_absolute():
        raise MetadataLocationError(f"relative_dir must be relative, got {relative_dir}")
    if ".." in rel.parts:
        raise MetadataLocationError(f"relative_dir must not contain '..': {relative_dir}")
    if rel == Path(".") or str(rel) in ("", "."):
        return Path()
    return rel

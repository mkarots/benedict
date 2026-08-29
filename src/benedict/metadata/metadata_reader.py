"""Metadata Reader

Reads and searches .metadata.benedict files.
"""

import logging
import os
import yaml
from pathlib import Path
from typing import List, Dict, Optional, Any

from .metadata_location import (
    METADATA_FILENAME,
    MetadataLocationError,
    relative_source_dir,
    sidecar_path,
    sidecar_root,
)

logger = logging.getLogger(__name__)

# Directories to exclude when searching for metadata files
# (virtual environments, dependencies, build artifacts, etc.)
_EXCLUDE_DIRS = {
    ".venv",
    "venv",
    "env",
    ".env",
    "ENV",
    "virtualenv",
    "build-env",
    "env-build",
    "node_modules",
    ".node_modules",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".git",
    ".hg",
    ".svn",
    "build",
    "dist",
    ".build",
    ".dist",
    ".tox",
    ".coverage",
    "htmlcov",
    ".eggs",
    ".idea",
    ".vscode",
    ".vs",
    ".DS_Store",
    "target",
    ".cargo",
    ".gradle",
    ".maven",
    ".next",
    ".nuxt",
    ".cache",
    ".parcel-cache",
    "coverage",
    ".nyc_output",
    ".sass-cache",
    "site-packages",  # Python package installation directory
}


class MetadataReader:
    """Reads and searches metadata overlays."""

    def __init__(self, metadata_file_path: Optional[str] = None):
        """Initialize metadata reader.

        Args:
            metadata_file_path: Optional path to metadata file (from env var or explicit)
                               If None, uses BENEDICT_METADATA_FILE env var or defaults to .metadata.benedict
        """
        self.metadata_file_path = metadata_file_path or os.environ.get("BENEDICT_METADATA_FILE")

    @staticmethod
    def _should_exclude_path(path: Path) -> bool:
        """Check if a path should be excluded from metadata scanning.

        Args:
            path: Path to check

        Returns:
            True if path should be excluded, False otherwise
        """
        # Check if any part of the path is in excluded directories
        path_parts = path.parts
        if any(
            part in _EXCLUDE_DIRS or part.endswith(".egg-info") or part.endswith(".dist-info")
            for part in path_parts
        ):
            return True
        return False

    def read_metadata(
        self,
        directory: Path,
        workspace_root: Optional[Path] = None,
        repo: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Read metadata for a source directory.

        Order: BENEDICT_METADATA_FILE override, sidecar, then in-tree leftover.
        """
        for metadata_file in self._candidate_files(directory, workspace_root, repo):
            loaded = self._load_yaml(metadata_file)
            if loaded is not None:
                return loaded
        return None

    def metadata_exists(
        self,
        directory: Path,
        workspace_root: Optional[Path] = None,
        repo: Optional[str] = None,
    ) -> bool:
        """Check if a sidecar or in-tree overlay exists for directory."""
        return any(path.exists() for path in self._candidate_files(directory, workspace_root, repo))

    def _candidate_files(
        self,
        directory: Path,
        workspace_root: Optional[Path],
        repo: Optional[str],
    ) -> List[Path]:
        directory = Path(directory)
        if self.metadata_file_path:
            metadata_file = Path(self.metadata_file_path)
            if not metadata_file.is_absolute():
                metadata_file = directory / metadata_file
            return [metadata_file]

        candidates: List[Path] = []
        if workspace_root is not None and repo:
            try:
                rel = relative_source_dir(directory, workspace_root, repo)
                candidates.append(sidecar_path(workspace_root, repo, rel))
            except MetadataLocationError:
                pass
        candidates.append(directory / METADATA_FILENAME)
        return candidates

    def _load_yaml(self, metadata_file: Path) -> Optional[Dict[str, Any]]:
        if not metadata_file.exists() or not metadata_file.is_file():
            return None
        try:
            with open(metadata_file, "r", encoding="utf-8") as f:
                metadata = yaml.safe_load(f)
            logger.debug(f"Read .metadata.benedict from {metadata_file}")
            return metadata
        except Exception as e:
            logger.warning(f"Error reading metadata file from {metadata_file}: {e}")
            return None

    def search_metadata(
        self,
        workspace_path: Path,
        query: str,
        content_type: Optional[str] = None,
        repo: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Search overlays and return source-relative directory paths.

        Paths are relative to the repo root (``src/commands``), never sidecar
        paths. Sidecar files win over leftover in-tree files for the same dir.
        """
        workspace_path = Path(workspace_path)
        results: List[Dict[str, Any]] = []
        seen: set[str] = set()
        query_lower = query.lower()

        for rel_path, metadata_file in self._iter_overlay_files(workspace_path, repo):
            if self._should_exclude_path(metadata_file):
                continue
            if rel_path in seen:
                continue
            metadata = self._load_yaml(metadata_file)
            if not metadata:
                continue
            if content_type and metadata.get("content_type") != content_type:
                continue
            if not self._metadata_matches_query(metadata, query_lower):
                continue
            seen.add(rel_path)
            results.append({"path": rel_path, "metadata": metadata})

        logger.debug(f"Found {len(results)} metadata matches for query '{query}'")
        return results

    def _iter_overlay_files(self, workspace_path: Path, repo: Optional[str]) -> List[tuple]:
        """Yield (repo-relative dir, file path). Sidecar first, then in-tree."""
        found: List[tuple] = []
        if repo:
            sidecar = sidecar_root(workspace_path, repo)
            if sidecar.exists():
                for metadata_file in sidecar.rglob(METADATA_FILENAME):
                    rel = metadata_file.parent.relative_to(sidecar)
                    found.append((_rel_path_str(rel), metadata_file))
            in_tree_root = workspace_path / repo
            if in_tree_root.exists():
                for metadata_file in in_tree_root.rglob(METADATA_FILENAME):
                    rel = metadata_file.parent.relative_to(in_tree_root)
                    found.append((_rel_path_str(rel), metadata_file))
            return found

        for metadata_file in workspace_path.rglob(METADATA_FILENAME):
            rel = metadata_file.parent.relative_to(workspace_path)
            found.append((_rel_path_str(rel), metadata_file))
        return found

    @staticmethod
    def _metadata_matches_query(metadata: Dict[str, Any], query_lower: str) -> bool:
        summary = str(metadata.get("summary", "")).lower()
        purpose = str(metadata.get("purpose", "")).lower()
        if query_lower in summary or query_lower in purpose:
            return True
        for file_info in metadata.get("files", []):
            file_name = str(file_info.get("name", "")).lower()
            file_purpose = str(file_info.get("purpose", "")).lower()
            if query_lower in file_name or query_lower in file_purpose:
                return True
        return False

    def get_directory_summary(
        self,
        directory: Path,
        workspace_root: Optional[Path] = None,
        repo: Optional[str] = None,
    ) -> Optional[str]:
        """Get summary for a directory from its overlay."""
        metadata = self.read_metadata(directory, workspace_root=workspace_root, repo=repo)
        if metadata:
            return metadata.get("summary")
        return None

    def list_metadata_files(self, workspace_path: Path, repo: Optional[str] = None) -> List[Path]:
        """List overlay files (sidecar first, then leftover in-tree)."""
        workspace_path = Path(workspace_path)
        return [
            metadata_file
            for _, metadata_file in self._iter_overlay_files(workspace_path, repo)
            if not self._should_exclude_path(metadata_file)
        ]


def _rel_path_str(rel: Path) -> str:
    if rel == Path(".") or str(rel) in ("", "."):
        return ""
    return str(rel).replace("\\", "/")

"""Tool Registry Factory

Creates tool registries from metadata files.
"""

import logging
from pathlib import Path
from typing import Any, Optional

from .metadata_tools import (
    GetFileMetadataTool,
    GetRepositorySummaryTool,
    ListKeyFilesTool,
)
from .tool_framework import ToolRegistry

logger = logging.getLogger(__name__)


def create_tool_registry(
    metadata_reader: Any = None,
    repo_path: Optional[Path] = None,
    workspace_root: Optional[Path] = None,
    repo: Optional[str] = None,
) -> ToolRegistry:
    """Create a tool registry with metadata tools.

    Args:
        metadata_reader: MetadataReader instance
        repo_path: Optional repository path. When set, metadata tools are
            registered only if a metadata file exists there.
        workspace_root: Channel workspace (for sidecar lookup)
        repo: Workspace resource name (for sidecar lookup)

    Returns:
        ToolRegistry with registered tools
    """
    registry = ToolRegistry()

    if metadata_reader:
        if not repo_path or metadata_reader.metadata_exists(
            repo_path, workspace_root=workspace_root, repo=repo
        ):
            registry.register(GetFileMetadataTool(metadata_reader))
            registry.register(ListKeyFilesTool(metadata_reader))
            registry.register(GetRepositorySummaryTool(metadata_reader))
            logger.debug("Registered metadata tools")

    return registry

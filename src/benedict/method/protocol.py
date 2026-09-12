"""Repo-scoped temporal memory: where the project is in its lifecycle.

The method file is the first store. Callers depend on this protocol, not YAML.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional, Protocol, Union

from benedict.method.overlay import MethodState

RepoKey = Union[str, Path]


@dataclass(frozen=True)
class LifecyclePatch:
    """Partial write to lifecycle state. Omitted fields stay as they are."""

    phase: Optional[str] = None
    iteration: Optional[int] = None
    step: Optional[str] = None
    concerns: Optional[Dict[str, str]] = field(default=None)
    last_action: Optional[str] = None


class TemporalMemory(Protocol):
    """CRUD for one onboarded repo's lifecycle clock.

    `repo_path` is the checkout (or any stable per-repo key). Stores decide
    where bytes live. YAML in the tree is one implementation, not the idea.
    """

    def get(self, repo_path: RepoKey) -> Optional[MethodState]: ...

    def put(self, repo_path: RepoKey, state: MethodState) -> MethodState: ...

    def update(self, repo_path: RepoKey, patch: LifecyclePatch) -> MethodState: ...

    def delete(self, repo_path: RepoKey) -> None: ...

    def exists(self, repo_path: RepoKey) -> bool: ...

    def ensure(self, repo_path: RepoKey) -> MethodState: ...

"""A ranked chunk from repository search."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Mapping, Optional


@dataclass(frozen=True)
class SearchHit:
    """One file chunk returned by semantic or keyword search."""

    file_path: str
    content: str
    score: float
    project: Optional[str] = None

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> SearchHit:
        """Coerce a dict-like hit (Slack channel search still returns mappings)."""
        project = data.get("project")
        return cls(
            file_path=str(data.get("file_path") or "unknown"),
            content=str(data.get("content") or ""),
            score=float(data.get("score") or 0),
            project=str(project) if project else None,
        )

    def to_dict(self) -> Dict[str, Any]:
        """JSON-serializable hit. Omits ``project`` when unset."""
        data: Dict[str, Any] = {
            "file_path": self.file_path,
            "content": self.content,
            "score": self.score,
        }
        if self.project is not None:
            data["project"] = self.project
        return data

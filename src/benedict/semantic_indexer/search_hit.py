"""A ranked chunk from repository search."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class SearchHit:
    """One file chunk returned by semantic or keyword search."""

    file_path: str
    content: str
    score: float
    project: Optional[str] = None

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

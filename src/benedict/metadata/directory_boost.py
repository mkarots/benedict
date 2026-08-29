"""Directory boost applied after embedding search."""

from pathlib import Path
from typing import Any

DEFAULT_DIRECTORY_BOOST = 1.2


def apply_directory_boost(
    hits: list[dict[str, Any]],
    relevant_dirs: set[str],
    factor: float = DEFAULT_DIRECTORY_BOOST,
) -> list[dict[str, Any]]:
    """Multiply a hit's score when its directory matched a metadata search.

    ``relevant_dirs`` must be source-relative (``src/auth``), not sidecar paths.
    Hits are re-sorted by score descending. ``top_k`` is the caller's job.
    """
    boosted: list[dict[str, Any]] = []
    for hit in hits:
        score = hit["score"]
        file_dir = _source_dir(hit.get("file_path", ""))
        if _directory_matches(file_dir, relevant_dirs):
            score = score * factor
        boosted.append({**hit, "score": score})
    boosted.sort(key=lambda row: row["score"], reverse=True)
    return boosted


def _source_dir(file_path: str) -> str:
    parent = Path(file_path).parent
    if str(parent) in (".", ""):
        return ""
    return str(parent).replace("\\", "/")


def _directory_matches(file_dir: str, relevant_dirs: set[str]) -> bool:
    normalized = {_normalize_dir(item) for item in relevant_dirs}
    file_dir = _normalize_dir(file_dir)
    if not file_dir:
        return "" in normalized or "." in normalized
    for rel_dir in normalized:
        if not rel_dir or rel_dir == ".":
            continue
        if file_dir == rel_dir or file_dir.startswith(rel_dir + "/"):
            return True
    return False


def _normalize_dir(path: str) -> str:
    return str(path).replace("\\", "/").strip("/")

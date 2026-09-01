"""Repository change detector protocol and implementations."""

from .git_change_detector import GitChangeDetector
from .protocol import RepoChangeDetector

__all__ = ["GitChangeDetector", "RepoChangeDetector", "create_repo_change_detector"]


def create_repo_change_detector(detector_type: str = "git") -> RepoChangeDetector:
    """Factory function to create RepoChangeDetector instance.

    Args:
        detector_type: Type of detector. Currently only "git" is supported.

    Returns:
        RepoChangeDetector instance

    Raises:
        ValueError: If detector_type is unknown
    """
    if detector_type == "git":
        return GitChangeDetector()
    raise ValueError(f"Unknown detector_type: {detector_type}")

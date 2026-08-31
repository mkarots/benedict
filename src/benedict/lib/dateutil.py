"""Date and time utilities for benedict."""

from datetime import datetime, timezone


def utc_now_iso() -> str:
    """Current UTC time as ISO-8601 with a Z suffix.

    Example: 2026-08-31T16:31:00.123456Z
    """
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def normalize_to_utc(dt: datetime) -> datetime:
    """Normalize datetime to UTC for comparison.

    Args:
        dt: Datetime to normalize (may be timezone-aware or naive)

    Returns:
        Timezone-aware datetime in UTC
    """
    if dt.tzinfo is None:
        # Naive datetime - assume UTC
        return dt.replace(tzinfo=timezone.utc)
    else:
        # Timezone-aware datetime - convert to UTC
        return dt.astimezone(timezone.utc)
    """Normalize datetime to UTC for comparison.

    Args:
        dt: Datetime to normalize (may be timezone-aware or naive)

    Returns:
        Timezone-aware datetime in UTC
    """
    if dt.tzinfo is None:
        # Naive datetime - assume UTC
        return dt.replace(tzinfo=timezone.utc)
    else:
        # Timezone-aware datetime - convert to UTC
        return dt.astimezone(timezone.utc)

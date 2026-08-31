"""Date and time utilities for benedict."""

from datetime import datetime, timezone


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

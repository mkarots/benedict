"""Tests for UTC date helpers."""

import warnings
from datetime import datetime, timedelta, timezone

from benedict.lib.dateutil import normalize_to_utc, utc_now_iso


def test_utc_now_iso_is_zulu_and_parseable():
    stamp = utc_now_iso()
    assert stamp.endswith("Z")
    assert "+00:00" not in stamp
    parsed = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
    assert parsed.tzinfo is not None
    assert abs((datetime.now(timezone.utc) - parsed).total_seconds()) < 5


def test_utc_now_iso_does_not_warn_about_utcnow():
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always", DeprecationWarning)
        utc_now_iso()
    utcnow_warnings = [
        warning
        for warning in caught
        if issubclass(warning.category, DeprecationWarning) and "utcnow" in str(warning.message)
    ]
    assert utcnow_warnings == []


def test_normalize_naive_datetime_assumes_utc():
    naive = datetime(2026, 8, 31, 12, 0, 0)
    normalized = normalize_to_utc(naive)
    assert normalized.tzinfo == timezone.utc
    assert normalized.replace(tzinfo=None) == naive


def test_normalize_aware_datetime_converts_to_utc():
    offset = timezone(timedelta(hours=-5))
    local = datetime(2026, 8, 31, 8, 0, 0, tzinfo=offset)
    normalized = normalize_to_utc(local)
    assert normalized.tzinfo == timezone.utc
    assert normalized == datetime(2026, 8, 31, 13, 0, 0, tzinfo=timezone.utc)

"""Background ticker for the progress loop."""

from __future__ import annotations

import logging
import os
import threading
from typing import Optional

from benedict.progress.cycle import ProgressService

logger = logging.getLogger(__name__)

DEFAULT_INTERVAL_S = 6 * 60 * 60
DEFAULT_START_DELAY_S = 120


def progress_enabled() -> bool:
    raw = os.environ.get("BENEDICT_PROGRESS", "1").strip().lower()
    return raw not in {"0", "false", "off", "no"}


def _int_env(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None or not raw.strip():
        return default
    try:
        value = int(raw)
    except ValueError:
        logger.warning("Invalid %s=%r, using %s", name, raw, default)
        return default
    return max(0, value)


class ProgressScheduler:
    """Daemon thread that runs ProgressService.run_all on an interval."""

    def __init__(
        self,
        service: ProgressService,
        *,
        interval_s: Optional[int] = None,
        start_delay_s: Optional[int] = None,
    ):
        self.service = service
        self.interval_s = (
            interval_s
            if interval_s is not None
            else _int_env("BENEDICT_PROGRESS_INTERVAL_S", DEFAULT_INTERVAL_S)
        )
        self.start_delay_s = (
            start_delay_s
            if start_delay_s is not None
            else _int_env("BENEDICT_PROGRESS_START_DELAY_S", DEFAULT_START_DELAY_S)
        )
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, name="benedict-progress", daemon=True)
        self._thread.start()
        logger.info(
            "Progress scheduler started (first cycle in %ss, then every %ss)",
            self.start_delay_s,
            self.interval_s,
        )

    def stop(self) -> None:
        self._stop.set()

    def _loop(self) -> None:
        if self.start_delay_s and self._stop.wait(self.start_delay_s):
            return
        while not self._stop.is_set():
            try:
                results = self.service.run_all()
                logger.info(
                    "Progress cycle finished (%s project(s))",
                    len(results),
                )
            except Exception:
                logger.exception("Progress cycle failed")
            wait = self.interval_s if self.interval_s > 0 else DEFAULT_INTERVAL_S
            if self._stop.wait(wait):
                return

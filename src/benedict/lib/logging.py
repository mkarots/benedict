"""Centralized logging configuration for benedict.

Provides RichHandler-based logging configuration that can be reused
across the entire project.
"""

import logging
import os
from typing import Optional

try:
    from rich.logging import RichHandler

    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False


def setup_logging(
    level: int = logging.DEBUG,
    format_string: Optional[str] = None,
    datefmt: Optional[str] = None,
    rich_tracebacks: bool = True,
) -> None:
    """Configure project-wide logging with RichHandler.

    This function configures the root logger with RichHandler for
    beautiful, formatted console output. It's safe to call multiple times
    (idempotent).

    Args:
        level: Logging level (default: logging.INFO)
        format_string: Custom format string. If None, uses "%(message)s" for RichHandler
        datefmt: Date format string. If None, uses "[%X]" for RichHandler
        rich_tracebacks: Whether to enable rich tracebacks (default: True)

    Example:
        >>> from benedict.lib.logging import setup_logging
        >>> setup_logging()
        >>> import logging
        >>> log = logging.getLogger("app")
        >>> log.info("Something nice happened")
    """
    # Use RichHandler if available, fallback to basic StreamHandler

    if os.environ.get("DEBUG") == "1":
        level = logging.DEBUG
    else:
        level = logging.INFO
    if RICH_AVAILABLE:
        handlers = [RichHandler(rich_tracebacks=rich_tracebacks)]
        # Default format for RichHandler (simple message-only format)
        format_string = format_string or "%(message)s"
        datefmt = datefmt or "[%X]"
    else:
        # Fallback to basic StreamHandler if rich is not available
        handlers = [logging.StreamHandler()]
        format_string = format_string or "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        datefmt = datefmt or None

    logging.basicConfig(
        level=level,
        format=format_string,
        datefmt=datefmt,
        handlers=handlers,
        force=True,  # Override any existing configuration
    )


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance for the given name.

    This is a convenience function that ensures logging is configured
    before returning a logger. If logging hasn't been configured yet,
    it will call setup_logging() with default settings.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Logger instance

    Example:
        >>> from benedict.lib.logging import get_logger
        >>> log = get_logger(__name__)
        >>> log.info("Hello world")
    """
    # Check if root logger has handlers configured
    root_logger = logging.getLogger()
    if not root_logger.handlers:
        setup_logging()

    return logging.getLogger(name)

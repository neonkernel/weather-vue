"""Logging configuration for the Summarizer CLI.

Configures stdlib logging with a consistent format.
Supports a --verbose flag to enable DEBUG-level output.
"""

from __future__ import annotations

import logging
import sys

# Module-level logger for the summarizer package
logger = logging.getLogger("summarizer")

_LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def configure_logging(verbose: bool = False) -> None:
    """Configure the root summarizer logger.

    Args:
        verbose: If True, set the log level to DEBUG; otherwise INFO.
    """
    level = logging.DEBUG if verbose else logging.INFO

    handler = logging.StreamHandler(sys.stderr)
    handler.setLevel(level)

    formatter = logging.Formatter(fmt=_LOG_FORMAT, datefmt=_DATE_FORMAT)
    handler.setFormatter(formatter)

    # Configure the package-level logger so we don't pollute the root logger
    logger.setLevel(level)
    logger.handlers.clear()
    logger.addHandler(handler)
    logger.propagate = False

    logger.debug("Verbose logging enabled.")


def get_logger(name: str | None = None) -> logging.Logger:
    """Return a child logger under the summarizer namespace.

    Args:
        name: Optional sub-name (e.g. 'cli', 'config'). If omitted,
              returns the top-level 'summarizer' logger.

    Returns:
        A :class:`logging.Logger` instance.
    """
    if name:
        return logging.getLogger(f"summarizer.{name}")
    return logger
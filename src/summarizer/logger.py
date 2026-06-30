"""Logging configuration for the summarizer package."""

from __future__ import annotations

import logging
import sys


def setup_logging(level: int = logging.WARNING) -> None:
    """Configure the root logger for the summarizer package.

    Args:
        level: Python logging level constant (e.g. ``logging.DEBUG``).
    """
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S",
        )
    )

    root_logger = logging.getLogger("src.summarizer")
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(level)
    root_logger.propagate = False
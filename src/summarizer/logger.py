"""Logging utilities for the summarizer package."""

import logging
import sys


def get_logger(name: str) -> logging.Logger:
    """Return a logger for *name*, configuring a default handler if needed."""
    logger = logging.getLogger(name)
    if not logger.handlers and not logging.getLogger().handlers:
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(
            logging.Formatter("%(levelname)s %(name)s: %(message)s")
        )
        logger.addHandler(handler)
    return logger
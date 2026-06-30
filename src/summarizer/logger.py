"""Logging utilities for the summarizer package."""

import logging


def get_logger(name: str) -> logging.Logger:
    """Return a logger namespaced under 'summarizer'."""
    # Ensure the root summarizer logger has a handler if running standalone
    root_logger = logging.getLogger("summarizer")
    if not root_logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(
            logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
        )
        root_logger.addHandler(handler)
        root_logger.setLevel(logging.WARNING)

    return logging.getLogger(name)
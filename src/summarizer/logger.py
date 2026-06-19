"""
Logging configuration for the Summarizer CLI.

Provides a consistent log format and helpers to adjust the log level at
runtime (e.g. when the --verbose flag is passed).
"""

from __future__ import annotations

import logging
import sys

# Module-level logger that other modules can import
logger = logging.getLogger("summarizer")

_LOG_FORMAT = "%(asctime)s [%(levelname)-8s] %(name)s: %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

_handler_installed = False


def setup_logging(level: str | int = "INFO", verbose: bool = False) -> None:
    """
    Configure the root *summarizer* logger.

    This function is idempotent — calling it multiple times is safe; the
    handler is only attached once.

    Args:
        level:   Log level string (``"DEBUG"``, ``"INFO"``, …) or an integer
                 constant from the :mod:`logging` module.
        verbose: When *True*, forces the level to ``DEBUG`` regardless of
                 the *level* argument.
    """
    global _handler_installed

    if verbose:
        effective_level = logging.DEBUG
    elif isinstance(level, str):
        effective_level = getattr(logging, level.upper(), logging.INFO)
    else:
        effective_level = level

    logger.setLevel(effective_level)

    if not _handler_installed:
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(logging.Formatter(_LOG_FORMAT, datefmt=_DATE_FORMAT))
        logger.addHandler(handler)
        # Prevent log records from propagating to the root logger
        logger.propagate = False
        _handler_installed = True
    else:
        # Update the level on all existing handlers
        for handler in logger.handlers:
            handler.setLevel(effective_level)


def get_logger(name: str | None = None) -> logging.Logger:
    """
    Return a child logger under the *summarizer* namespace.

    Args:
        name: Sub-namespace, e.g. ``"cli"`` → ``"summarizer.cli"``.
              Pass *None* to get the root summarizer logger.

    Returns:
        A :class:`logging.Logger` instance.
    """
    if name:
        return logging.getLogger(f"summarizer.{name}")
    return logger
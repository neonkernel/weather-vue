"""
Logging configuration for the Summarizer package.

Call `setup_logging(verbose=True)` early in the CLI entry point to
configure a consistent log format across the entire application.
"""

import logging
import sys

_LOG_FORMAT = "%(asctime)s [%(levelname)-8s] %(name)s: %(message)s"
_DATE_FORMAT = "%Y-%m-%dT%H:%M:%S"


def setup_logging(verbose: bool = False) -> None:
    """Configure root logger.

    Args:
        verbose: When *True* set the log level to DEBUG, otherwise INFO.
    """
    level = logging.DEBUG if verbose else logging.INFO

    handler = logging.StreamHandler(sys.stderr)
    handler.setLevel(level)

    formatter = logging.Formatter(fmt=_LOG_FORMAT, datefmt=_DATE_FORMAT)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Avoid adding duplicate handlers when the function is called multiple times
    # (e.g. during testing).
    if not root_logger.handlers:
        root_logger.addHandler(handler)
    else:
        root_logger.handlers.clear()
        root_logger.addHandler(handler)


def get_logger(name: str) -> logging.Logger:
    """Return a named child logger.

    Args:
        name: Typically ``__name__`` of the calling module.

    Returns:
        A :class:`logging.Logger` instance.
    """
    return logging.getLogger(name)
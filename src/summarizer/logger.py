"""
Logging configuration for the Summarizer CLI.

Provides a consistent logging format across the application and supports
toggling between INFO and DEBUG levels via a --verbose flag.
"""

import logging
import sys

# Module-level logger for this package
logger = logging.getLogger("summarizer")

# Prevent log messages from propagating to the root logger if it has handlers
logger.propagate = False

_LOG_FORMAT = "%(asctime)s [%(levelname)-8s] %(name)s: %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup_logging(verbose: bool = False) -> None:
    """
    Configure logging for the application.

    Sets up a StreamHandler writing to stderr with a consistent format.
    When ``verbose`` is True the log level is set to DEBUG; otherwise INFO.

    Args:
        verbose: If True, enable DEBUG-level logging. Defaults to False.
    """
    level = logging.DEBUG if verbose else logging.INFO

    # Remove any handlers already attached (important for test isolation)
    logger.handlers.clear()

    handler = logging.StreamHandler(sys.stderr)
    handler.setLevel(level)

    formatter = logging.Formatter(fmt=_LOG_FORMAT, datefmt=_DATE_FORMAT)
    handler.setFormatter(formatter)

    logger.setLevel(level)
    logger.addHandler(handler)

    logger.debug("Logging initialised at level: %s", logging.getLevelName(level))


def get_logger(name: str | None = None) -> logging.Logger:
    """
    Return a child logger under the ``summarizer`` namespace.

    Args:
        name: Optional sub-name to append, e.g. ``"cli"`` → ``"summarizer.cli"``.

    Returns:
        A :class:`logging.Logger` instance.
    """
    if name:
        return logging.getLogger(f"summarizer.{name}")
    return logger
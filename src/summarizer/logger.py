"""
Logging configuration for the summarizer CLI.

Provides a consistent log format across all modules and supports
enabling DEBUG-level output via a --verbose flag.
"""

import logging
import sys

_LOG_FORMAT = "%(asctime)s [%(levelname)-8s] %(name)s: %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# Top-level logger for the entire package
logger = logging.getLogger("summarizer")


def setup_logging(verbose: bool = False) -> None:
    """
    Configure the root 'summarizer' logger.

    Args:
        verbose: When True, sets the log level to DEBUG.
                 Otherwise INFO is used.
    """
    level = logging.DEBUG if verbose else logging.INFO

    handler = logging.StreamHandler(sys.stderr)
    handler.setLevel(level)

    formatter = logging.Formatter(fmt=_LOG_FORMAT, datefmt=_DATE_FORMAT)
    handler.setFormatter(formatter)

    logger.setLevel(level)
    # Avoid duplicate handlers if setup_logging is called more than once
    logger.handlers.clear()
    logger.addHandler(handler)
    # Prevent log records from propagating to the root logger
    logger.propagate = False

    logger.debug("Logging initialised (level=%s)", logging.getLevelName(level))


def get_logger(name: str) -> logging.Logger:
    """
    Return a child logger under the 'summarizer' namespace.

    Usage::

        from summarizer.logger import get_logger
        log = get_logger(__name__)
        log.info("hello")

    Args:
        name: Typically ``__name__`` of the calling module.

    Returns:
        A :class:`logging.Logger` instance.
    """
    return logging.getLogger(name)
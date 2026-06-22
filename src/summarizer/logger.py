"""
Logging configuration for the summarizer package.

Provides a consistent log format and supports toggling between
INFO (default) and DEBUG (verbose) levels.
"""

import logging
import sys

# Module-level logger for the entire summarizer package
logger = logging.getLogger("summarizer")

_LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup_logging(verbose: bool = False) -> None:
    """
    Configure the root 'summarizer' logger.

    Args:
        verbose: When True, sets the log level to DEBUG.
                 When False (default), sets the log level to INFO.
    """
    level = logging.DEBUG if verbose else logging.INFO

    handler = logging.StreamHandler(sys.stderr)
    handler.setLevel(level)

    formatter = logging.Formatter(fmt=_LOG_FORMAT, datefmt=_DATE_FORMAT)
    handler.setFormatter(formatter)

    logger.setLevel(level)
    # Avoid adding duplicate handlers if setup_logging is called multiple times
    if not logger.handlers:
        logger.addHandler(handler)
    else:
        # Update existing handlers to the new level
        for h in logger.handlers:
            h.setLevel(level)
            h.setFormatter(formatter)

    logger.debug("Logging initialised at level: %s", logging.getLevelName(level))


def get_logger(name: str) -> logging.Logger:
    """
    Return a child logger under the 'summarizer' namespace.

    Args:
        name: Sub-module name (e.g. 'cli', 'config').

    Returns:
        A Logger instance named 'summarizer.<name>'.
    """
    return logging.getLogger(f"summarizer.{name}")
"""
Logging configuration for the Summarizer CLI.

Provides a consistent log format across the application and supports
toggling between INFO and DEBUG levels via a --verbose flag.
"""

import logging
import sys

# Logger name used throughout the application
LOGGER_NAME = "summarizer"

# Log format: timestamp | level | logger name | message
LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def get_logger(name: str | None = None) -> logging.Logger:
    """
    Return a logger under the 'summarizer' namespace.

    Args:
        name: Optional sub-logger name (e.g. 'summarizer.cli').
              If None, returns the root 'summarizer' logger.

    Returns:
        A configured logging.Logger instance.
    """
    logger_name = f"{LOGGER_NAME}.{name}" if name else LOGGER_NAME
    return logging.getLogger(logger_name)


def configure_logging(verbose: bool = False) -> None:
    """
    Configure application-wide logging.

    Sets up a StreamHandler on stdout with a consistent format.
    If verbose is True, the log level is set to DEBUG; otherwise INFO.

    Args:
        verbose: When True, enables DEBUG-level logging.
    """
    level = logging.DEBUG if verbose else logging.INFO

    root_logger = logging.getLogger(LOGGER_NAME)
    root_logger.setLevel(level)

    # Avoid adding duplicate handlers if called more than once
    if root_logger.handlers:
        root_logger.handlers.clear()

    handler = logging.StreamHandler(sys.stderr)
    handler.setLevel(level)

    formatter = logging.Formatter(fmt=LOG_FORMAT, datefmt=DATE_FORMAT)
    handler.setFormatter(formatter)

    root_logger.addHandler(handler)

    # Prevent log records from propagating to the root Python logger
    root_logger.propagate = False

    logger = get_logger()
    logger.debug("Logging configured at level: %s", logging.getLevelName(level))
"""
Logging configuration for the AI summarizer.

Provides a consistent logging format and supports toggling
between INFO and DEBUG level via a verbose flag.
"""

import logging
import sys

# Module-level logger for the summarizer package
logger = logging.getLogger("summarizer")

_HANDLER_CONFIGURED = False


def setup_logging(verbose: bool = False) -> logging.Logger:
    """
    Configure the root summarizer logger.

    Sets up a StreamHandler writing to stderr with a consistent format.
    Call this once at CLI startup before any other logging calls.

    Args:
        verbose: If True, sets the log level to DEBUG; otherwise INFO.

    Returns:
        The configured 'summarizer' logger instance.
    """
    global _HANDLER_CONFIGURED

    level = logging.DEBUG if verbose else logging.INFO

    # Avoid adding duplicate handlers if called multiple times (e.g., in tests)
    if not _HANDLER_CONFIGURED:
        handler = logging.StreamHandler(sys.stderr)
        formatter = logging.Formatter(
            fmt="%(asctime)s [%(levelname)-8s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        _HANDLER_CONFIGURED = True

    logger.setLevel(level)

    logger.debug("Logging initialised at %s level.", logging.getLevelName(level))
    return logger


def get_logger(name: str | None = None) -> logging.Logger:
    """
    Return a child logger under the 'summarizer' namespace.

    Args:
        name: Optional sub-name, e.g. 'cli' → 'summarizer.cli'.
              If None, returns the root 'summarizer' logger.

    Returns:
        A logging.Logger instance.
    """
    if name:
        return logging.getLogger(f"summarizer.{name}")
    return logger
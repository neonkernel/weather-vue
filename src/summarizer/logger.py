"""
Logging configuration for the summarizer package.

Provides a consistent logging format across all modules and supports
a --verbose flag to enable DEBUG-level output.
"""

import logging
import sys

# Module-level logger for the summarizer package
logger = logging.getLogger("summarizer")

_HANDLER_CONFIGURED = False


def configure_logging(verbose: bool = False) -> None:
    """
    Configure the root summarizer logger.

    Sets up a StreamHandler writing to stderr with a consistent format.
    If verbose is True, the log level is set to DEBUG; otherwise INFO.

    Args:
        verbose: If True, enable DEBUG-level logging.
    """
    global _HANDLER_CONFIGURED

    level = logging.DEBUG if verbose else logging.INFO

    # Avoid adding duplicate handlers on repeated calls (e.g., in tests)
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
    logger.debug("Logging configured (level=%s)", logging.getLevelName(level))


def get_logger(name: str) -> logging.Logger:
    """
    Return a child logger under the 'summarizer' namespace.

    Args:
        name: Sub-module or component name (e.g., 'cli', 'config').

    Returns:
        A Logger instance named 'summarizer.<name>'.
    """
    return logging.getLogger(f"summarizer.{name}")
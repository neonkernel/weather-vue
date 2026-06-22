"""
Logging configuration for the summarizer package.

Provides a consistent log format across all modules and supports
a --verbose flag to elevate the log level to DEBUG.
"""

import logging
import sys

# Module-level logger for the package
_LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# Sentinel to ensure we only configure the root logger once
_configured = False


def configure_logging(verbose: bool = False) -> None:
    """
    Configure the root 'summarizer' logger.

    Args:
        verbose: If True, set the log level to DEBUG; otherwise INFO.
    """
    global _configured

    level = logging.DEBUG if verbose else logging.INFO

    logger = logging.getLogger("summarizer")
    logger.setLevel(level)

    # Avoid adding duplicate handlers if called more than once
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stderr)
        handler.setLevel(level)
        formatter = logging.Formatter(fmt=_LOG_FORMAT, datefmt=_DATE_FORMAT)
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    else:
        # Update existing handler levels if reconfigured
        for handler in logger.handlers:
            handler.setLevel(level)

    logger.debug("Logging initialised at %s level.", logging.getLevelName(level))
    _configured = True


def get_logger(name: str) -> logging.Logger:
    """
    Return a child logger under the 'summarizer' namespace.

    Args:
        name: Typically __name__ of the calling module.

    Returns:
        A Logger instance named 'summarizer.<name>'.
    """
    # Strip the package prefix if already present to avoid double-nesting
    if name.startswith("summarizer."):
        return logging.getLogger(name)
    return logging.getLogger(f"summarizer.{name}")
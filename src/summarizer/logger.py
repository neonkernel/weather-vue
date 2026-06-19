"""
Logging configuration for the Summarizer CLI.

Provides a helper that configures the root summarizer logger with a
consistent format and respects a ``--verbose`` flag to enable DEBUG output.
"""

from __future__ import annotations

import logging
import sys

# Module-level logger; child loggers in other modules should use
# ``logging.getLogger(__name__)`` to inherit this configuration.
_LOG_FORMAT = "%(asctime)s [%(levelname)-8s] %(name)s: %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# Package-level logger name — all child loggers share this namespace.
LOGGER_NAME = "summarizer"


def get_logger(name: str | None = None) -> logging.Logger:
    """
    Return a logger namespaced under the ``summarizer`` package.

    Parameters
    ----------
    name:
        Optional sub-name appended to ``"summarizer."``.  Pass ``__name__``
        from the calling module for a per-module logger.

    Returns
    -------
    logging.Logger
    """
    if name and not name.startswith(LOGGER_NAME):
        logger_name = f"{LOGGER_NAME}.{name}"
    else:
        logger_name = name or LOGGER_NAME

    return logging.getLogger(logger_name)


def configure_logging(verbose: bool = False) -> None:
    """
    Configure the ``summarizer`` logger hierarchy.

    This should be called **once** at application startup (i.e., inside the
    Click command callback) before any other logging calls.

    Parameters
    ----------
    verbose:
        When ``True``, sets the log level to ``DEBUG``.
        When ``False`` (default), sets it to ``INFO``.
    """
    level = logging.DEBUG if verbose else logging.INFO

    # Build a handler that writes to stderr so that log output does not
    # pollute stdout (where the actual summary is printed).
    handler = logging.StreamHandler(sys.stderr)
    handler.setLevel(level)

    formatter = logging.Formatter(fmt=_LOG_FORMAT, datefmt=_DATE_FORMAT)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger(LOGGER_NAME)
    root_logger.setLevel(level)

    # Avoid duplicate handlers if configure_logging is called more than once
    # (e.g., in tests).
    if not root_logger.handlers:
        root_logger.addHandler(handler)
    else:
        root_logger.handlers.clear()
        root_logger.addHandler(handler)

    root_logger.debug("Logging initialised at %s level.", logging.getLevelName(level))
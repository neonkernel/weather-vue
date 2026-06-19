"""
CLI entry point for the Summarizer tool.

Defines the ``summarize`` command and all its options using Click.
Input validation is performed here; actual summarization will be added
in a later phase.
"""

from __future__ import annotations

import sys
from pathlib import Path
from urllib.parse import urlparse

import click

from summarizer import __version__
from summarizer.config import Config, ConfigurationError
from summarizer.logger import configure_logging, get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

VALID_STYLES = ("paragraph", "bullet", "tldr")
VALID_FORMATS = ("plain", "markdown", "json")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _is_valid_url(value: str) -> bool:
    """Return True if *value* looks like an http/https URL."""
    try:
        result = urlparse(value)
        return result.scheme in {"http", "https"} and bool(result.netloc)
    except ValueError:
        return False


def _is_readable_file(value: str) -> bool:
    """Return True if *value* is a path to an existing, readable file."""
    path = Path(value)
    return path.is_file() and os.access(path, os.R_OK)


# We need os for os.access — import it here to keep the top-level imports tidy.
import os  # noqa: E402 (needed after helper definition for clarity)


# ---------------------------------------------------------------------------
# Click command
# ---------------------------------------------------------------------------


@click.command("summarize")
@click.version_option(version=__version__, prog_name="summarize")
@click.option(
    "--url",
    "url",
    default=None,
    metavar="URL",
    help="URL of the web page to summarize.",
)
@click.option(
    "--file",
    "file_path",
    default=None,
    metavar="PATH",
    type=click.Path(exists=False),  # We do manual validation for better messages.
    help="Path to a local file to summarize.",
)
@click.option(
    "--style",
    "style",
    default="paragraph",
    show_default=True,
    type=click.Choice(VALID_STYLES, case_sensitive=False),
    help="Style of the generated summary.",
)
@click.option(
    "--format",
    "output_format",
    default="plain",
    show_default=True,
    type=click.Choice(VALID_FORMATS, case_sensitive=False),
    help="Output format for the summary.",
)
@click.option(
    "--verbose",
    "verbose",
    is_flag=True,
    default=False,
    help="Enable debug-level logging.",
)
def main(
    url: str | None,
    file_path: str | None,
    style: str,
    output_format: str,
    verbose: bool,
) -> None:
    """Summarize a web page or local file using an LLM.

    Exactly one of --url or --file must be provided.

    \b
    Examples:
      summarize --url https://example.com/article
      summarize --file ./report.txt --style bullet --format markdown
    """
    # 1. Configure logging as early as possible.
    configure_logging(verbose=verbose)

    logger.debug(
        "summarize called: url=%r file=%r style=%r format=%r verbose=%r",
        url,
        file_path,
        style,
        output_format,
        verbose,
    )

    # 2. Load configuration from environment.
    try:
        config = Config.from_env()
    except ConfigurationError as exc:
        logger.error("Configuration error: %s", exc)
        raise click.ClickException(str(exc)) from exc

    logger.debug("Config loaded: model=%s max_tokens=%d", config.model, config.max_tokens)

    # 3. Validate that exactly one input source is provided.
    if url and file_path:
        raise click.UsageError("Provide either --url or --file, not both.")

    if not url and not file_path:
        raise click.UsageError("You must provide either --url or --file.")

    # 4. Validate the individual input.
    if url:
        if not _is_valid_url(url):
            raise click.BadParameter(
                f"{url!r} is not a valid http/https URL.",
                param_hint="'--url'",
            )
        input_type = "url"
        input_value = url
        logger.info("Input: URL → %s", url)

    else:
        # file_path is set
        path = Path(file_path)
        if not path.exists():
            raise click.BadParameter(
                f"File not found: {file_path!r}",
                param_hint="'--file'",
            )
        if not path.is_file():
            raise click.BadParameter(
                f"Path is not a file: {file_path!r}",
                param_hint="'--file'",
            )
        if not os.access(path, os.R_OK):
            raise click.BadParameter(
                f"File is not readable: {file_path!r}",
                param_hint="'--file'",
            )
        input_type = "file"
        input_value = str(path.resolve())
        logger.info("Input: file → %s", input_value)

    # 5. Placeholder response (LLM integration comes in Phase 2).
    _print_placeholder(
        input_type=input_type,
        input_value=input_value,
        style=style,
        output_format=output_format,
        config=config,
    )


def _print_placeholder(
    input_type: str,
    input_value: str,
    style: str,
    output_format: str,
    config: Config,
) -> None:
    """Print a placeholder summary until LLM integration is implemented."""
    lines = [
        "=" * 60,
        "  SUMMARIZER CLI — Placeholder Response (Phase 1)",
        "=" * 60,
        f"  Input type   : {input_type}",
        f"  Input value  : {input_value}",
        f"  Style        : {style}",
        f"  Format       : {output_format}",
        f"  Model        : {config.model}",
        f"  Max tokens   : {config.max_tokens}",
        "=" * 60,
        "",
        "  ✅ Input validated successfully.",
        "  🔧 LLM summarization will be implemented in Phase 2.",
        "",
    ]
    click.echo("\n".join(lines))
"""
CLI entry point for the Summarizer tool.

Defines the `summarize` command with options for specifying input (--url or
--file), summary style, and output format. In Phase 1 the tool validates the
input and prints a placeholder response instead of calling an LLM.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from urllib.parse import urlparse

import click

from summarizer import __version__
from summarizer.config import ConfigError, load_config
from summarizer.logger import get_logger, setup_logging

logger = get_logger("cli")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

VALID_STYLES = ("brief", "detailed", "bullets")
VALID_FORMATS = ("text", "markdown", "json")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _is_valid_url(value: str) -> bool:
    """Return True if *value* looks like a plausible HTTP/HTTPS URL."""
    try:
        result = urlparse(value)
        return result.scheme in {"http", "https"} and bool(result.netloc)
    except ValueError:
        return False


def _is_readable_file(value: str) -> bool:
    """Return True if *value* points to an existing, readable file."""
    path = Path(value)
    return path.is_file() and os.access(path, os.R_OK)


def _validate_input(url: str | None, file: str | None) -> tuple[str, str]:
    """
    Ensure exactly one of *url* or *file* is provided and that it is valid.

    Returns:
        A ``(input_type, input_value)`` tuple where *input_type* is one of
        ``"url"`` or ``"file"``.

    Raises:
        click.UsageError: On validation failure.
    """
    if url and file:
        raise click.UsageError("Provide either --url or --file, not both.")

    if not url and not file:
        raise click.UsageError("You must provide either --url or --file.")

    if url:
        if not _is_valid_url(url):
            raise click.BadParameter(
                f"{url!r} does not look like a valid HTTP/HTTPS URL.",
                param_hint="'--url'",
            )
        return "url", url

    # file branch
    if not _is_readable_file(file):  # type: ignore[arg-type]
        raise click.BadParameter(
            f"{file!r} is not a readable file.",
            param_hint="'--file'",
        )
    return "file", file  # type: ignore[return-value]


# ---------------------------------------------------------------------------
# CLI definition
# ---------------------------------------------------------------------------


@click.command()
@click.version_option(version=__version__, prog_name="summarize")
@click.option("--url", "-u", default=None, help="URL of the web page to summarize.")
@click.option(
    "--file",
    "-f",
    "file",
    default=None,
    type=click.Path(exists=False),  # We do our own validation for better messages
    help="Path to a local file to summarize.",
)
@click.option(
    "--style",
    "-s",
    default="brief",
    show_default=True,
    type=click.Choice(VALID_STYLES, case_sensitive=False),
    help="Style of the summary.",
)
@click.option(
    "--format",
    "-o",
    "output_format",
    default="text",
    show_default=True,
    type=click.Choice(VALID_FORMATS, case_sensitive=False),
    help="Output format for the summary.",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    default=False,
    help="Enable verbose/debug logging.",
)
def main(
    url: str | None,
    file: str | None,
    style: str,
    output_format: str,
    verbose: bool,
) -> None:
    """Summarize a web page or local file using AI.

    Examples:

    \b
        summarize --url https://example.com/article
        summarize --file ./report.txt --style detailed --format markdown
    """
    # ------------------------------------------------------------------
    # 1. Logging setup (must happen first so everything below is logged)
    # ------------------------------------------------------------------
    try:
        config = load_config()
    except ConfigError as exc:
        # Config errors before logging is set up — write directly to stderr
        click.echo(f"Configuration error: {exc}", err=True)
        sys.exit(1)

    setup_logging(level=config.log_level, verbose=verbose)
    logger.debug("summarize %s starting (verbose=%s)", __version__, verbose)
    logger.debug("Config: model=%s max_tokens=%s", config.model, config.max_tokens)

    # ------------------------------------------------------------------
    # 2. Input validation
    # ------------------------------------------------------------------
    try:
        input_type, input_value = _validate_input(url, file)
    except (click.UsageError, click.BadParameter) as exc:
        logger.debug("Input validation failed: %s", exc)
        raise  # Let Click handle the formatting

    logger.info("Input validated — type=%s value=%r", input_type, input_value)
    logger.debug("Options — style=%s format=%s", style, output_format)

    # ------------------------------------------------------------------
    # 3. Placeholder response (Phase 1 — no LLM yet)
    # ------------------------------------------------------------------
    _print_placeholder(input_type, input_value, style, output_format)


def _print_placeholder(
    input_type: str,
    input_value: str,
    style: str,
    output_format: str,
) -> None:
    """Print a placeholder summary response (Phase 1 stub)."""
    label = "URL" if input_type == "url" else "File"

    if output_format == "json":
        import json

        payload = {
            "input_type": input_type,
            "input": input_value,
            "style": style,
            "summary": (
                f"[Placeholder] Summarization not yet implemented. "
                f"Would summarize {label}: {input_value}"
            ),
        }
        click.echo(json.dumps(payload, indent=2))

    elif output_format == "markdown":
        click.echo(f"## Summary\n")
        click.echo(f"**{label}:** {input_value}\n")
        click.echo(f"**Style:** {style}\n")
        click.echo(
            f"> [Placeholder] Summarization not yet implemented. "
            f"Would summarize {label}: `{input_value}`"
        )

    else:  # text (default)
        click.echo(
            f"[Placeholder] Summarization not yet implemented.\n"
            f"{label}: {input_value}\n"
            f"Style:  {style}\n"
            f"Format: {output_format}"
        )
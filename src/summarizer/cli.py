"""
CLI entry point for the summarizer tool.

Usage examples:
    summarize --url https://example.com/article
    summarize --file path/to/doc.txt --style detailed --format markdown
    summarize --url https://example.com --verbose
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from urllib.parse import urlparse

import click

from summarizer import __version__
from summarizer.logger import setup_logging, get_logger

logger = get_logger("cli")

# ------------------------------------------------------------------ #
# Validation helpers                                                   #
# ------------------------------------------------------------------ #

_VALID_STYLES = ("brief", "detailed", "bullets")
_VALID_FORMATS = ("text", "markdown", "json")


def _is_plausible_url(value: str) -> bool:
    """Return True when *value* looks like an http/https URL."""
    try:
        result = urlparse(value)
        return result.scheme in ("http", "https") and bool(result.netloc)
    except Exception:
        return False


def _validate_file(ctx: click.Context, param: click.Parameter, value: str | None) -> str | None:
    """Click callback — ensure the supplied path points to a readable file."""
    if value is None:
        return None
    path = Path(value)
    if not path.exists():
        raise click.BadParameter(f"File does not exist: {value}")
    if not path.is_file():
        raise click.BadParameter(f"Path is not a file: {value}")
    if not os.access(path, os.R_OK):
        raise click.BadParameter(f"File is not readable: {value}")
    return str(path)


def _validate_url(ctx: click.Context, param: click.Parameter, value: str | None) -> str | None:
    """Click callback — ensure the supplied value looks like a plausible URL."""
    if value is None:
        return None
    if not _is_plausible_url(value):
        raise click.BadParameter(
            f"Value does not look like a valid http/https URL: {value!r}"
        )
    return value


# ------------------------------------------------------------------ #
# CLI definition                                                        #
# ------------------------------------------------------------------ #


@click.command(name="summarize")
@click.version_option(version=__version__, prog_name="summarize")
@click.option(
    "--url",
    "-u",
    default=None,
    metavar="URL",
    callback=_validate_url,
    help="URL of the web page to summarize.",
)
@click.option(
    "--file",
    "-f",
    "file_path",
    default=None,
    metavar="PATH",
    callback=_validate_file,
    help="Path to a local file to summarize.",
)
@click.option(
    "--style",
    "-s",
    default="brief",
    show_default=True,
    type=click.Choice(_VALID_STYLES, case_sensitive=False),
    help="Summary style.",
)
@click.option(
    "--format",
    "output_format",
    default="text",
    show_default=True,
    type=click.Choice(_VALID_FORMATS, case_sensitive=False),
    help="Output format.",
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
    file_path: str | None,
    style: str,
    output_format: str,
    verbose: bool,
) -> None:
    """Summarize a web page or local file using OpenAI.

    Exactly one of --url or --file must be provided.
    """
    # Initialise logging first so all subsequent messages are formatted.
    setup_logging(verbose=verbose)

    logger.debug(
        "CLI invoked — url=%r, file=%r, style=%r, format=%r, verbose=%r",
        url,
        file_path,
        style,
        output_format,
        verbose,
    )

    # ---- Input validation -------------------------------------------- #
    if url is None and file_path is None:
        raise click.UsageError(
            "You must provide either --url <URL> or --file <PATH>."
        )
    if url is not None and file_path is not None:
        raise click.UsageError(
            "Please provide only one of --url or --file, not both."
        )

    # ---- Determine source -------------------------------------------- #
    if url:
        source_label = f"URL: {url}"
        logger.info("Input source: %s", source_label)
    else:
        source_label = f"file: {file_path}"
        logger.info("Input source: %s", source_label)

    # ---- Placeholder output ------------------------------------------ #
    logger.info("Summarization not yet implemented — returning placeholder.")

    placeholder = _build_placeholder(
        source=source_label,
        style=style,
        output_format=output_format,
    )
    click.echo(placeholder)


# ------------------------------------------------------------------ #
# Placeholder builder                                                  #
# ------------------------------------------------------------------ #


def _build_placeholder(source: str, style: str, output_format: str) -> str:
    """Return a placeholder summary string formatted according to *output_format*."""
    message = (
        f"[PLACEHOLDER] Summarization not yet implemented.\n"
        f"  Source : {source}\n"
        f"  Style  : {style}\n"
        f"  Format : {output_format}\n"
    )

    if output_format == "json":
        import json

        return json.dumps(
            {
                "status": "placeholder",
                "source": source,
                "style": style,
                "format": output_format,
                "summary": "Summarization not yet implemented.",
            },
            indent=2,
        )

    if output_format == "markdown":
        return (
            "## Summary *(placeholder)*\n\n"
            f"> Summarization not yet implemented.\n\n"
            f"**Source:** {source}  \n"
            f"**Style:** {style}  \n"
            f"**Format:** {output_format}  \n"
        )

    # Default: plain text
    return message
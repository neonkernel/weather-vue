"""
Click-based CLI entry point for the summarizer tool.

Defines the ``summarize`` command with the following options:

  --url     URL of the web page to summarize
  --file    Path to a local file to summarize
  --style   Summary style  (paragraph | bullet | tldr)
  --format  Output format  (plain | markdown | json)
  --verbose Enable DEBUG-level logging
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import click

from summarizer import __version__
from summarizer.logger import get_logger, setup_logging

log = get_logger(__name__)

# ------------------------------------------------------------------ #
# Constants                                                           #
# ------------------------------------------------------------------ #

STYLE_CHOICES = ("paragraph", "bullet", "tldr")
FORMAT_CHOICES = ("plain", "markdown", "json")

# Loose URL pattern — we just want to reject obviously non-URL strings.
_URL_RE = re.compile(
    r"^(https?|ftp)://"           # scheme
    r"[^\s/$.?#].[^\s]*$",        # host + optional path/query
    re.IGNORECASE,
)


# ------------------------------------------------------------------ #
# Validators                                                          #
# ------------------------------------------------------------------ #


def _validate_input(url: str | None, file: str | None) -> None:
    """
    Ensure exactly one of --url or --file is provided, and that the
    value is usable.

    Raises:
        click.UsageError: on any validation failure.
    """
    if url and file:
        raise click.UsageError("Provide either --url or --file, not both.")

    if not url and not file:
        raise click.UsageError(
            "You must provide an input source. Use --url <URL> or --file <PATH>."
        )

    if url:
        if not _URL_RE.match(url):
            raise click.UsageError(
                f"The value {url!r} does not look like a valid URL. "
                "Make sure it starts with http:// or https://."
            )
        log.debug("Input validated as URL: %s", url)

    if file:
        path = Path(file)
        if not path.exists():
            raise click.UsageError(f"File not found: {file!r}")
        if not path.is_file():
            raise click.UsageError(f"Path is not a regular file: {file!r}")
        if not os.access(path, os.R_OK):
            raise click.UsageError(f"File is not readable: {file!r}")
        log.debug("Input validated as file: %s", path.resolve())


# ------------------------------------------------------------------ #
# CLI command                                                          #
# ------------------------------------------------------------------ #


@click.command()
@click.version_option(version=__version__, prog_name="summarize")
@click.option(
    "--url",
    default=None,
    metavar="URL",
    help="URL of the web page to summarize.",
)
@click.option(
    "--file",
    "file_path",
    default=None,
    metavar="PATH",
    help="Path to a local file to summarize.",
)
@click.option(
    "--style",
    default="paragraph",
    show_default=True,
    type=click.Choice(STYLE_CHOICES, case_sensitive=False),
    help="Style of the generated summary.",
)
@click.option(
    "--format",
    "output_format",
    default="plain",
    show_default=True,
    type=click.Choice(FORMAT_CHOICES, case_sensitive=False),
    help="Output format for the summary.",
)
@click.option(
    "--verbose",
    is_flag=True,
    default=False,
    help="Enable verbose (DEBUG) logging.",
)
def main(
    url: str | None,
    file_path: str | None,
    style: str,
    output_format: str,
    verbose: bool,
) -> None:
    """
    Summarize a web page or local file.

    Provide exactly one of --url or --file as the input source.

    \b
    Examples:
      summarize --url https://example.com/article
      summarize --file report.txt --style bullet --format markdown
    """
    # 1. Configure logging first so all subsequent messages are formatted.
    setup_logging(verbose=verbose)

    log.debug(
        "CLI invoked: url=%r file=%r style=%r format=%r verbose=%r",
        url,
        file_path,
        style,
        output_format,
        verbose,
    )

    # 2. Validate input.
    _validate_input(url, file_path)

    # 3. Determine the source description for the placeholder response.
    source = url if url else file_path

    # 4. Placeholder — real summarization will be added in a later phase.
    _print_placeholder(source=source, style=style, output_format=output_format)


# ------------------------------------------------------------------ #
# Placeholder output                                                  #
# ------------------------------------------------------------------ #


def _print_placeholder(source: str, style: str, output_format: str) -> None:
    """
    Emit a placeholder summary.  Real LLM integration comes in Phase 2.
    """
    log.info("Summarizing: %s  (style=%s, format=%s)", source, style, output_format)

    placeholder_text = (
        f"[Placeholder] Summarization of '{source}' "
        f"with style='{style}' and format='{output_format}' "
        "will appear here once LLM integration is complete."
    )

    if output_format == "json":
        import json

        result = {
            "source": source,
            "style": style,
            "format": output_format,
            "summary": placeholder_text,
        }
        click.echo(json.dumps(result, indent=2))
    elif output_format == "markdown":
        click.echo(f"## Summary\n\n{placeholder_text}\n")
    else:
        click.echo(placeholder_text)


# ------------------------------------------------------------------ #
# Needed for _validate_input file-readability check                  #
# ------------------------------------------------------------------ #
import os  # noqa: E402  (import after function definition is intentional here)
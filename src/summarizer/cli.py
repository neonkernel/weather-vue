"""
CLI entry point for the Summarizer tool.

Defines the `summarize` command using Click.  In Phase 1, no actual
summarization is performed — input is validated and a placeholder
response is printed.
"""

from __future__ import annotations

import sys
from pathlib import Path
from urllib.parse import urlparse

import click

from summarizer import __version__
from summarizer.logger import configure_logging, get_logger

logger = get_logger("cli")

# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------

_SUPPORTED_SCHEMES = {"http", "https", "ftp"}


def _is_valid_url(value: str) -> bool:
    """Return True if *value* looks like a plausible URL."""
    try:
        parsed = urlparse(value)
        return parsed.scheme in _SUPPORTED_SCHEMES and bool(parsed.netloc)
    except Exception:
        return False


def _is_readable_file(value: str) -> bool:
    """Return True if *value* is a path to an existing, readable file."""
    path = Path(value)
    return path.is_file() and os.access(path, os.R_OK)


# ---------------------------------------------------------------------------
# Click command
# ---------------------------------------------------------------------------

STYLE_CHOICES = click.Choice(["paragraph", "bullet", "tldr"], case_sensitive=False)
FORMAT_CHOICES = click.Choice(["plain", "markdown", "json"], case_sensitive=False)


@click.command(name="summarize")
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
    "file",
    default=None,
    metavar="PATH",
    type=click.Path(exists=False, file_okay=True, dir_okay=False),
    help="Path to a local file to summarize.",
)
@click.option(
    "--style",
    "style",
    default="paragraph",
    show_default=True,
    type=STYLE_CHOICES,
    help="Summary style.",
)
@click.option(
    "--format",
    "output_format",
    default="plain",
    show_default=True,
    type=FORMAT_CHOICES,
    help="Output format.",
)
@click.option(
    "--verbose",
    "verbose",
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
    """
    Summarize a web page (--url) or local file (--file) using AI.

    Exactly one of --url or --file must be provided.

    \b
    Examples:
      summarize --url https://example.com/article
      summarize --file ./document.txt --style bullet --format markdown
    """
    # Configure logging as the very first step so all subsequent log calls
    # respect the --verbose flag.
    configure_logging(verbose=verbose)

    logger.debug(
        "summarize called: url=%r, file=%r, style=%r, format=%r, verbose=%r",
        url,
        file,
        style,
        output_format,
        verbose,
    )

    # -----------------------------------------------------------------------
    # Input validation
    # -----------------------------------------------------------------------

    if url is None and file is None:
        raise click.UsageError(
            "You must provide either --url <URL> or --file <PATH>.\n"
            "Run 'summarize --help' for usage information."
        )

    if url is not None and file is not None:
        raise click.UsageError(
            "Provide either --url or --file, not both."
        )

    if url is not None:
        if not _is_valid_url(url):
            raise click.BadParameter(
                f"{url!r} does not look like a valid URL. "
                "Expected a URL starting with http://, https://, or ftp://.",
                param_hint="--url",
            )
        input_type = "url"
        input_value = url
        logger.info("Input validated as URL: %s", url)

    else:  # file is not None
        file_path = Path(file)
        if not file_path.exists():
            raise click.BadParameter(
                f"File not found: {file!r}",
                param_hint="--file",
            )
        if not file_path.is_file():
            raise click.BadParameter(
                f"{file!r} is not a regular file.",
                param_hint="--file",
            )
        if not os.access(file_path, os.R_OK):
            raise click.BadParameter(
                f"File is not readable: {file!r}",
                param_hint="--file",
            )
        input_type = "file"
        input_value = str(file_path.resolve())
        logger.info("Input validated as file: %s", input_value)

    # -----------------------------------------------------------------------
    # Placeholder response (Phase 1 — no LLM integration yet)
    # -----------------------------------------------------------------------

    logger.debug("Producing placeholder summary (LLM integration not yet implemented).")

    _print_placeholder(
        input_type=input_type,
        input_value=input_value,
        style=style,
        output_format=output_format,
    )


def _print_placeholder(
    input_type: str,
    input_value: str,
    style: str,
    output_format: str,
) -> None:
    """Print a placeholder summary response to stdout."""

    placeholder_text = (
        f"[Placeholder] Summarization not yet implemented.\n"
        f"  Input type : {input_type}\n"
        f"  Input value: {input_value}\n"
        f"  Style      : {style}\n"
        f"  Format     : {output_format}"
    )

    if output_format == "json":
        import json

        payload = {
            "status": "placeholder",
            "input_type": input_type,
            "input_value": input_value,
            "style": style,
            "format": output_format,
            "summary": None,
            "message": "Summarization not yet implemented.",
        }
        click.echo(json.dumps(payload, indent=2))

    elif output_format == "markdown":
        click.echo("## Summary (Placeholder)\n")
        click.echo(f"**Input type:** `{input_type}`  ")
        click.echo(f"**Input value:** `{input_value}`  ")
        click.echo(f"**Style:** `{style}`  ")
        click.echo(f"**Format:** `{output_format}`  \n")
        click.echo("> ⚠️  Summarization is not yet implemented.")

    else:  # plain
        click.echo(placeholder_text)


# ---------------------------------------------------------------------------
# Allow running as a module: python -m summarizer.cli
# ---------------------------------------------------------------------------

import os  # noqa: E402  (import after top-level to satisfy linters)

if __name__ == "__main__":
    main()
"""
CLI entry point for the AI summarizer.

Defines the `summarize` command using Click. Validates input (URL or file),
sets up logging, and (in later phases) dispatches to the summarisation pipeline.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import click

from summarizer import __version__
from summarizer.logger import setup_logging, get_logger

# Logger for this module — initialised after setup_logging() is called.
log = get_logger("cli")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

VALID_STYLES = ("brief", "detailed", "bullets")
VALID_FORMATS = ("text", "markdown", "json")

# Very permissive URL pattern — just enough to catch obvious mistakes.
_URL_RE = re.compile(
    r"^(https?|ftp)://"          # scheme
    r"[^\s/$.?#].[^\s]*$",       # host + optional path/query
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _is_valid_url(value: str) -> bool:
    """Return True if *value* looks like a plausible HTTP/HTTPS/FTP URL."""
    return bool(_URL_RE.match(value.strip()))


def _validate_file(path_str: str) -> Path:
    """
    Resolve and validate a file path.

    Raises:
        click.BadParameter: If the path does not exist or is not readable.
    """
    path = Path(path_str).expanduser().resolve()
    if not path.exists():
        raise click.BadParameter(f"File not found: {path}")
    if not path.is_file():
        raise click.BadParameter(f"Path is not a file: {path}")
    if not os.access(path, os.R_OK):
        raise click.BadParameter(f"File is not readable: {path}")
    return path


# ---------------------------------------------------------------------------
# Click command
# ---------------------------------------------------------------------------

@click.command(name="summarize")
@click.version_option(version=__version__, prog_name="summarize")
@click.option(
    "--url", "-u",
    default=None,
    metavar="URL",
    help="URL of the web page to summarize.",
)
@click.option(
    "--file", "-f", "file_path",
    default=None,
    metavar="PATH",
    help="Path to a local file to summarize.",
)
@click.option(
    "--style", "-s",
    default="brief",
    show_default=True,
    type=click.Choice(VALID_STYLES, case_sensitive=False),
    help="Summary style.",
)
@click.option(
    "--format", "-o", "output_format",
    default="text",
    show_default=True,
    type=click.Choice(VALID_FORMATS, case_sensitive=False),
    help="Output format.",
)
@click.option(
    "--verbose", "-v",
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
    """
    Summarize a web page or local file using AI.

    Provide exactly one of --url or --file as the content source.

    \b
    Examples:
        summarize --url https://example.com/article
        summarize --file ./report.txt --style detailed --format markdown
    """
    # ---- Logging ----
    setup_logging(verbose=verbose)
    log.debug("summarize version %s starting.", __version__)
    log.debug("Options: url=%r, file=%r, style=%r, format=%r", url, file_path, style, output_format)

    # ---- Input validation ----
    if url and file_path:
        raise click.UsageError("Provide either --url or --file, not both.")

    if not url and not file_path:
        raise click.UsageError(
            "You must provide an input source. Use --url <URL> or --file <PATH>.\n"
            "Run 'summarize --help' for usage information."
        )

    # ---- Resolve the source ----
    if url:
        url = url.strip()
        if not _is_valid_url(url):
            raise click.BadParameter(
                f"{url!r} does not look like a valid URL. "
                "Make sure it starts with http:// or https://",
                param_hint="--url",
            )
        source_type = "url"
        source = url
        log.info("Source: URL → %s", url)
    else:
        # Inline import to keep top-level imports minimal
        import os  # noqa: PLC0415
        resolved = _validate_file(file_path)
        source_type = "file"
        source = str(resolved)
        log.info("Source: file → %s", source)

    # ---- Placeholder response (Phase 1) ----
    log.debug("Dispatching to summarisation pipeline (placeholder).")

    click.echo(
        f"[PLACEHOLDER] Summarization not yet implemented.\n"
        f"  Source type : {source_type}\n"
        f"  Source      : {source}\n"
        f"  Style       : {style}\n"
        f"  Format      : {output_format}"
    )

    log.debug("Done.")


# ---------------------------------------------------------------------------
# Allow running as `python -m summarizer.cli`
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    main()
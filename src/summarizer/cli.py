"""
CLI entry point for the Summarizer tool.

Defines the ``summarize`` Click command which accepts either a URL or a local
file path, validates the input, and (in Phase 1) prints a placeholder response.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import click

from summarizer import __version__
from summarizer.logger import setup_logging, get_logger

log = get_logger("cli")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

VALID_STYLES = ("bullet", "narrative", "tldr")
VALID_FORMATS = ("plain", "markdown", "json")

_URL_RE = re.compile(
    r"^(https?|ftp)://"          # scheme
    r"(\w+(\-\w+)*\.)+\w{2,}"   # domain
    r"(:\d+)?(/.*)?$",           # optional port + path
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Input validation helpers
# ---------------------------------------------------------------------------


def _is_valid_url(value: str) -> bool:
    """Return True if *value* looks like a plausible HTTP/HTTPS/FTP URL."""
    return bool(_URL_RE.match(value.strip()))


def _is_readable_file(value: str) -> bool:
    """Return True if *value* is a path to an existing, readable file."""
    path = Path(value)
    return path.is_file() and os.access(path, os.R_OK) if path.exists() else False


# Re-import os after the stdlib guard (needed by _is_readable_file)
import os  # noqa: E402  (intentional placement after helper def for clarity)


def _validate_input(url: str | None, file: str | None) -> tuple[str, str]:
    """
    Validate that exactly one of *url* or *file* was provided and is usable.

    Returns:
        A ``(kind, value)`` tuple where ``kind`` is ``"url"`` or ``"file"``.

    Raises:
        click.UsageError: On invalid / missing input.
    """
    if url and file:
        raise click.UsageError(
            "Provide either --url or --file, not both."
        )

    if not url and not file:
        raise click.UsageError(
            "You must provide an input via --url <URL> or --file <PATH>.\n"
            "Run `summarize --help` for usage information."
        )

    if url:
        if not _is_valid_url(url):
            raise click.BadParameter(
                f"{url!r} does not look like a valid URL. "
                "Make sure it starts with http:// or https://",
                param_hint="--url",
            )
        log.debug("Input validated as URL: %s", url)
        return "url", url

    # file branch
    path = Path(file)  # type: ignore[arg-type]
    if not path.exists():
        raise click.BadParameter(
            f"File not found: {file!r}",
            param_hint="--file",
        )
    if not path.is_file():
        raise click.BadParameter(
            f"{file!r} is not a regular file.",
            param_hint="--file",
        )
    if not os.access(path, os.R_OK):
        raise click.BadParameter(
            f"File is not readable (check permissions): {file!r}",
            param_hint="--file",
        )
    log.debug("Input validated as file: %s", path.resolve())
    return "file", str(path.resolve())


# ---------------------------------------------------------------------------
# Click command
# ---------------------------------------------------------------------------


@click.command(name="summarize")
@click.version_option(version=__version__, prog_name="summarize")
@click.option(
    "--url",
    "-u",
    default=None,
    metavar="URL",
    help="URL of the web page to summarize.",
)
@click.option(
    "--file",
    "-f",
    "file",
    default=None,
    metavar="PATH",
    help="Path to a local file to summarize.",
)
@click.option(
    "--style",
    "-s",
    default="narrative",
    show_default=True,
    type=click.Choice(VALID_STYLES, case_sensitive=False),
    help="Summary style.",
)
@click.option(
    "--format",
    "-o",
    "output_format",
    default="plain",
    show_default=True,
    type=click.Choice(VALID_FORMATS, case_sensitive=False),
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
    file: str | None,
    style: str,
    output_format: str,
    verbose: bool,
) -> None:
    """
    Summarize a web page or local file using AI.

    Provide either a --url or a --file as the input source.

    \b
    Examples:
      summarize --url https://example.com/article
      summarize --file ./report.txt --style bullet --format markdown
      summarize --url https://news.site/story --style tldr --verbose
    """
    # Initialise logging first so subsequent log calls are formatted correctly
    setup_logging(verbose=verbose)

    log.debug(
        "summarize v%s | style=%s format=%s verbose=%s",
        __version__,
        style,
        output_format,
        verbose,
    )

    try:
        kind, value = _validate_input(url, file)
    except (click.UsageError, click.BadParameter) as exc:
        # Let Click handle formatting and exit code
        raise

    # ------------------------------------------------------------------
    # Phase 1 placeholder — no LLM integration yet
    # ------------------------------------------------------------------
    log.info("Processing %s: %s", kind, value)
    log.info("Style: %s | Format: %s", style, output_format)

    _print_placeholder(kind=kind, value=value, style=style, output_format=output_format)


def _print_placeholder(
    *,
    kind: str,
    value: str,
    style: str,
    output_format: str,
) -> None:
    """
    Emit a placeholder summary to stdout.

    This will be replaced by real LLM summarization in a later phase.
    """
    placeholder_text = (
        f"[PLACEHOLDER] Summary of {kind}: {value}\n"
        f"Style: {style} | Format: {output_format}\n\n"
        "LLM integration coming in Phase 2."
    )

    if output_format == "json":
        import json

        result = {
            "input_type": kind,
            "input_value": value,
            "style": style,
            "format": output_format,
            "summary": placeholder_text,
            "phase": "1 - placeholder",
        }
        click.echo(json.dumps(result, indent=2))

    elif output_format == "markdown":
        click.echo(f"## Summary\n\n{placeholder_text}\n")

    else:
        # plain
        click.echo(placeholder_text)
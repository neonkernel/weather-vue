"""
CLI entry point for the summarizer tool.

Defines the `summarize` Click command.  Accepts either a URL or a local file
path as input, validates the input, and prints a placeholder summary response.
(Full LLM integration is added in a later phase.)
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

import click

from summarizer import __version__
from summarizer.logger import configure_logging, get_logger

logger = get_logger("cli")

# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------

_URL_RE = re.compile(
    r"^(https?|ftp)://"          # scheme
    r"([A-Za-z0-9\-._~:/?#\[\]@!$&'()*+,;=%]+)"  # rest
    r"$",
    re.IGNORECASE,
)


def _is_plausible_url(value: str) -> bool:
    """Return True if *value* looks like a URL (http/https/ftp scheme)."""
    return bool(_URL_RE.match(value.strip()))


def _is_readable_file(value: str) -> bool:
    """Return True if *value* is an existing, readable file path."""
    p = Path(value)
    return p.is_file() and os.access(p, os.R_OK)


def _validate_input(url: str | None, file: str | None) -> tuple[str, str]:
    """
    Validate that exactly one of *url* or *file* is provided and is usable.

    Returns:
        A (input_type, input_value) tuple where input_type is 'url' or 'file'.

    Raises:
        click.UsageError: If validation fails.
    """
    if url and file:
        raise click.UsageError(
            "Provide either --url or --file, not both."
        )

    if not url and not file:
        raise click.UsageError(
            "You must provide an input via --url <URL> or --file <PATH>."
        )

    if url:
        if not _is_plausible_url(url):
            raise click.BadParameter(
                f"'{url}' does not look like a valid URL. "
                "URLs must start with http://, https://, or ftp://.",
                param_hint="'--url'",
            )
        return "url", url

    # file path
    if not _is_readable_file(file):  # type: ignore[arg-type]
        raise click.BadParameter(
            f"'{file}' is not a readable file. "
            "Please provide a valid path to an existing file.",
            param_hint="'--file'",
        )
    return "file", file  # type: ignore[return-value]


# ---------------------------------------------------------------------------
# CLI definition
# ---------------------------------------------------------------------------

STYLE_CHOICES = click.Choice(["paragraph", "bullet", "tldr"], case_sensitive=False)
FORMAT_CHOICES = click.Choice(["plain", "markdown", "json"], case_sensitive=False)


@click.command("summarize")
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
    default="paragraph",
    show_default=True,
    type=STYLE_CHOICES,
    help="Summary style: paragraph, bullet, or tldr.",
)
@click.option(
    "--format",
    "output_format",
    "-o",
    default="plain",
    show_default=True,
    type=FORMAT_CHOICES,
    help="Output format: plain, markdown, or json.",
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

    Provide either a URL (--url) or a file path (--file) as input.

    \b
    Examples:
      summarize --url https://example.com/article
      summarize --file report.txt --style bullet --format markdown
    """
    configure_logging(verbose=verbose)

    logger.debug(
        "Invoked with url=%r, file=%r, style=%r, format=%r, verbose=%r",
        url,
        file,
        style,
        output_format,
        verbose,
    )

    # Validate input
    try:
        input_type, input_value = _validate_input(url, file)
    except (click.UsageError, click.BadParameter) as exc:
        logger.debug("Input validation failed: %s", exc)
        raise  # Let Click handle the formatting and exit code

    logger.info("Input type : %s", input_type)
    logger.info("Input value: %s", input_value)
    logger.info("Style      : %s", style)
    logger.info("Format     : %s", output_format)

    # ---------------------------------------------------------------------------
    # Placeholder response (LLM integration added in a later phase)
    # ---------------------------------------------------------------------------
    placeholder = _build_placeholder(input_type, input_value, style, output_format)
    click.echo(placeholder)


def _build_placeholder(
    input_type: str,
    input_value: str,
    style: str,
    output_format: str,
) -> str:
    """
    Build a human-readable placeholder message.

    This will be replaced by real LLM output in a later phase.
    """
    description = (
        f"URL: {input_value}" if input_type == "url" else f"File: {input_value}"
    )

    message = (
        f"[PLACEHOLDER] Summarizer received your input.\n"
        f"  {description}\n"
        f"  Style  : {style}\n"
        f"  Format : {output_format}\n\n"
        f"LLM integration is not yet implemented. "
        f"This is Phase 1 — the tool is wired up and ready."
    )

    if output_format == "json":
        import json
        return json.dumps(
            {
                "status": "placeholder",
                "input_type": input_type,
                "input_value": input_value,
                "style": style,
                "format": output_format,
                "summary": "LLM integration not yet implemented (Phase 1).",
            },
            indent=2,
        )

    if output_format == "markdown":
        return (
            f"## Summary *(placeholder)*\n\n"
            f"> **Input ({input_type}):** `{input_value}`  \n"
            f"> **Style:** {style}  \n"
            f"> **Format:** {output_format}\n\n"
            f"_LLM integration is not yet implemented. "
            f"This is Phase 1 — the tool is wired up and ready._"
        )

    # default: plain
    return message
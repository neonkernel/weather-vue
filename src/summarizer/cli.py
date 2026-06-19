"""
CLI entry point for the Summarizer tool.

Usage examples::

    summarize --url https://example.com/article
    summarize --file ./document.txt --style bullet --format markdown
    summarize --url https://example.com --verbose
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

import click

from summarizer import __version__
from summarizer.logger import get_logger, setup_logging

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_URL_RE = re.compile(
    r"^(https?|ftp)://"           # scheme
    r"([A-Za-z0-9\-._~:/?#\[\]@!$&'()*+,;=%]+)"  # rest
    r"$",
    re.IGNORECASE,
)


def _is_valid_url(value: str) -> bool:
    """Return *True* when *value* looks like a plausible HTTP/HTTPS/FTP URL."""
    return bool(_URL_RE.match(value.strip()))


def _is_readable_file(value: str) -> bool:
    """Return *True* when *value* is a path to an existing, readable file."""
    p = Path(value)
    return p.is_file() and os.access(p, os.R_OK)


# ---------------------------------------------------------------------------
# CLI definition
# ---------------------------------------------------------------------------

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
    type=click.Path(exists=False),  # We validate manually for nicer error messages.
    help="Path to a local file to summarize.",
)
@click.option(
    "--style",
    "style",
    default=None,
    type=click.Choice(["paragraph", "bullet", "tldr"], case_sensitive=False),
    show_default=True,
    help="Summary style.  Defaults to the value of SUMMARIZER_DEFAULT_STYLE (.env).",
)
@click.option(
    "--format",
    "output_format",
    default=None,
    type=click.Choice(["plain", "markdown", "json"], case_sensitive=False),
    show_default=True,
    help="Output format.  Defaults to the value of SUMMARIZER_DEFAULT_FORMAT (.env).",
)
@click.option(
    "--verbose",
    is_flag=True,
    default=False,
    help="Enable verbose/debug logging.",
)
def main(
    url: str | None,
    file: str | None,
    style: str | None,
    output_format: str | None,
    verbose: bool,
) -> None:
    """Summarize a web page (--url) or local file (--file) using an LLM.

    Exactly one of --url or --file must be provided.
    """
    # Set up logging as early as possible so all subsequent messages use the
    # chosen verbosity level.
    setup_logging(verbose=verbose)

    logger.debug(
        "summarize called: url=%r file=%r style=%r format=%r verbose=%r",
        url,
        file,
        style,
        output_format,
        verbose,
    )

    # -----------------------------------------------------------------------
    # Input validation — exactly one source must be provided.
    # -----------------------------------------------------------------------
    if url and file:
        raise click.UsageError("Provide either --url or --file, not both.")

    if not url and not file:
        raise click.UsageError("You must provide either --url or --file.")

    # -----------------------------------------------------------------------
    # Validate the specific input type.
    # -----------------------------------------------------------------------
    input_type: str
    input_value: str

    if url:
        if not _is_valid_url(url):
            raise click.BadParameter(
                f"{url!r} does not look like a valid URL (expected http/https/ftp).",
                param_hint="--url",
            )
        input_type = "url"
        input_value = url
        logger.info("Input validated as URL: %s", url)

    else:  # file is set
        assert file is not None  # for type checkers
        if not _is_readable_file(file):
            raise click.BadParameter(
                f"{file!r} is not a readable file.",
                param_hint="--file",
            )
        input_type = "file"
        input_value = file
        logger.info("Input validated as file: %s", file)

    # -----------------------------------------------------------------------
    # Load config (best-effort — skip hard failure in Phase 1 since we don't
    # actually call the LLM yet).
    # -----------------------------------------------------------------------
    effective_style = style or "paragraph"
    effective_format = output_format or "plain"

    try:
        from summarizer.config import load_config  # noqa: PLC0415

        config = load_config()
        effective_style = style or config.default_style
        effective_format = output_format or config.default_format
        logger.debug("Config loaded successfully.")
    except Exception as exc:  # noqa: BLE001
        logger.debug("Could not load config (this is expected without a .env): %s", exc)

    logger.debug("Effective style=%r format=%r", effective_style, effective_format)

    # -----------------------------------------------------------------------
    # Phase 1 placeholder — echo input details back to the user.
    # -----------------------------------------------------------------------
    click.echo(
        f"[Summarizer v{__version__}] Placeholder output\n"
        f"  Input type : {input_type}\n"
        f"  Input value: {input_value}\n"
        f"  Style      : {effective_style}\n"
        f"  Format     : {effective_format}\n"
        "\n"
        "(No summarization yet — LLM integration coming in Phase 2.)"
    )
"""CLI entry point for the Summarizer tool.

Defines the `summarize` command with input options (--url / --file),
output options (--style / --format), and a --verbose flag.

Phase 1: No LLM integration yet — validates input and prints a placeholder.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from urllib.parse import urlparse

import click

from summarizer import __version__
from summarizer.config import VALID_FORMATS, VALID_STYLES, load_config
from summarizer.logger import configure_logging, get_logger

log = get_logger("cli")


def _is_valid_url(value: str) -> bool:
    """Return True if *value* looks like a plausible HTTP/HTTPS URL."""
    try:
        result = urlparse(value)
        return result.scheme in ("http", "https") and bool(result.netloc)
    except Exception:
        return False


def _is_readable_file(value: str) -> bool:
    """Return True if *value* is an existing, readable file path."""
    path = Path(value)
    return path.is_file() and os.access(path, os.R_OK)


# ---------------------------------------------------------------------------
# CLI definition
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
    help="Path to a local file to summarize.",
)
@click.option(
    "--style",
    "style",
    default=None,
    type=click.Choice(VALID_STYLES, case_sensitive=False),
    help=(
        "Summarization style. "
        f"Choices: {', '.join(VALID_STYLES)}. "
        "Defaults to the value of SUMMARIZER_DEFAULT_STYLE (or 'brief')."
    ),
)
@click.option(
    "--format",
    "output_format",
    default=None,
    type=click.Choice(VALID_FORMATS, case_sensitive=False),
    help=(
        "Output format. "
        f"Choices: {', '.join(VALID_FORMATS)}. "
        "Defaults to the value of SUMMARIZER_DEFAULT_FORMAT (or 'text')."
    ),
)
@click.option(
    "--verbose",
    is_flag=True,
    default=False,
    help="Enable verbose (DEBUG) logging output.",
)
def main(
    url: str | None,
    file_path: str | None,
    style: str | None,
    output_format: str | None,
    verbose: bool,
) -> None:
    """Summarize a web page URL or a local file using AI.

    Exactly one of --url or --file must be provided.

    \b
    Examples:
      summarize --url https://example.com/article
      summarize --file ./document.txt --style bullet --format markdown
    """
    # ---- Logging setup ----
    configure_logging(verbose=verbose)
    log.debug("summarize CLI starting (version %s)", __version__)

    # ---- Load config ----
    try:
        config = load_config()
    except ValueError as exc:
        raise click.ClickException(f"Configuration error: {exc}") from exc

    log.debug(
        "Config loaded: model=%s, max_tokens=%d, default_style=%s, default_format=%s",
        config.model,
        config.max_tokens,
        config.default_style,
        config.default_format,
    )

    # ---- Input validation: exactly one of --url / --file ----
    if url is None and file_path is None:
        raise click.UsageError(
            "You must provide either --url <URL> or --file <PATH>."
        )

    if url is not None and file_path is not None:
        raise click.UsageError(
            "Provide only one of --url or --file, not both."
        )

    # ---- Validate the chosen input ----
    if url is not None:
        if not _is_valid_url(url):
            raise click.BadParameter(
                f"'{url}' does not look like a valid HTTP/HTTPS URL.",
                param_hint="--url",
            )
        input_description = f"URL: {url}"
        log.info("Input accepted as URL: %s", url)
    else:
        if not _is_readable_file(file_path):  # type: ignore[arg-type]
            raise click.BadParameter(
                f"'{file_path}' is not a readable file.",
                param_hint="--file",
            )
        input_description = f"File: {file_path}"
        log.info("Input accepted as file: %s", file_path)

    # ---- Resolve style / format (CLI flag overrides config default) ----
    effective_style = style or config.default_style
    effective_format = output_format or config.default_format

    log.debug(
        "Effective style=%s, format=%s", effective_style, effective_format
    )

    # ---- Warn if no API key is configured (won't matter in Phase 1) ----
    if not config.has_api_key:
        log.warning(
            "OPENAI_API_KEY is not set. Summarization will not work until "
            "you add it to your .env file."
        )

    # ---- Placeholder output (Phase 1 — no LLM yet) ----
    click.echo(f"[summarize] Input   : {input_description}")
    click.echo(f"[summarize] Style   : {effective_style}")
    click.echo(f"[summarize] Format  : {effective_format}")
    click.echo(
        "[summarize] Summary : (placeholder) LLM integration coming in Phase 2."
    )
    log.debug("summarize CLI finished successfully.")
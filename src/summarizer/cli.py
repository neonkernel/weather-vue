"""
CLI entry point for the summarizer tool.

Defines the `summarize` command using Click.  In this initial phase
no actual summarization takes place — the tool validates its input
and prints a placeholder response.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from urllib.parse import urlparse

import click

from summarizer import __version__
from summarizer.config import load_config
from summarizer.logger import configure_logging, get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Supported option values
# ---------------------------------------------------------------------------

STYLES = ("brief", "detailed", "bullets")
FORMATS = ("text", "markdown", "json")


# ---------------------------------------------------------------------------
# Input validation helpers
# ---------------------------------------------------------------------------


def _is_valid_url(value: str) -> bool:
    """Return True if *value* looks like a plausible HTTP(S) URL."""
    try:
        parsed = urlparse(value)
        return parsed.scheme in {"http", "https"} and bool(parsed.netloc)
    except Exception:
        return False


def _is_readable_file(value: str) -> bool:
    """Return True if *value* is a path to an existing, readable file."""
    path = Path(value)
    return path.is_file() and os.access(path, os.R_OK)


# ---------------------------------------------------------------------------
# Click command
# ---------------------------------------------------------------------------


@click.command(context_settings={"help_option_names": ["-h", "--help"]})
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
    "file_path",
    default=None,
    metavar="PATH",
    help="Path to a local file to summarize.",
)
@click.option(
    "--style",
    "-s",
    default="brief",
    show_default=True,
    type=click.Choice(STYLES, case_sensitive=False),
    help="Summary style.",
)
@click.option(
    "--format",
    "output_format",
    default="text",
    show_default=True,
    type=click.Choice(FORMATS, case_sensitive=False),
    help="Output format.",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    default=False,
    help="Enable verbose/debug logging.",
)
@click.option(
    "--env-file",
    default=None,
    metavar="PATH",
    help="Path to a .env file (defaults to .env in the current directory).",
)
def main(
    url: str | None,
    file_path: str | None,
    style: str,
    output_format: str,
    verbose: bool,
    env_file: str | None,
) -> None:
    """Summarize a web page or local file using AI.

    Provide exactly one of --url or --file as the input source.

    \b
    Examples:
      summarize --url https://example.com/article
      summarize --file report.txt --style detailed --format markdown
    """
    # 1. Configure logging first so all subsequent messages are formatted.
    configure_logging(verbose=verbose)
    logger.debug("summarize %s starting", __version__)

    # 2. Load configuration (reads .env / env vars).
    try:
        config = load_config(env_file=env_file)
    except ValueError as exc:
        click.echo(f"Configuration error: {exc}", err=True)
        sys.exit(1)

    # 3. Validate that exactly one input source was provided.
    if url and file_path:
        click.echo(
            "Error: Please provide either --url or --file, not both.", err=True
        )
        sys.exit(1)

    if not url and not file_path:
        click.echo(
            "Error: You must provide an input source via --url or --file.\n"
            "Run 'summarize --help' for usage information.",
            err=True,
        )
        sys.exit(1)

    # 4. Validate the individual input source.
    if url:
        if not _is_valid_url(url):
            click.echo(
                f"Error: '{url}' does not look like a valid HTTP/HTTPS URL.",
                err=True,
            )
            sys.exit(1)
        input_type = "url"
        input_value = url
        logger.debug("Input validated as URL: %s", url)

    else:  # file_path is set
        if not _is_readable_file(file_path):
            click.echo(
                f"Error: '{file_path}' is not a readable file.",
                err=True,
            )
            sys.exit(1)
        input_type = "file"
        input_value = file_path
        logger.debug("Input validated as file: %s", file_path)

    # 5. Placeholder response (no LLM integration yet).
    logger.info(
        "Would summarize %s=%r with style=%r, format=%r, model=%s",
        input_type,
        input_value,
        style,
        output_format,
        config.model,
    )

    _print_placeholder(
        input_type=input_type,
        input_value=input_value,
        style=style,
        output_format=output_format,
        config_model=config.model,
    )


def _print_placeholder(
    input_type: str,
    input_value: str,
    style: str,
    output_format: str,
    config_model: str,
) -> None:
    """Emit a placeholder summary response to stdout."""
    lines = [
        "[PLACEHOLDER] Summarization not yet implemented.",
        f"  Input type : {input_type}",
        f"  Input value: {input_value}",
        f"  Style      : {style}",
        f"  Format     : {output_format}",
        f"  Model      : {config_model}",
    ]

    if output_format == "json":
        import json

        payload = {
            "status": "placeholder",
            "input_type": input_type,
            "input_value": input_value,
            "style": style,
            "format": output_format,
            "model": config_model,
            "summary": None,
        }
        click.echo(json.dumps(payload, indent=2))
    elif output_format == "markdown":
        click.echo("## Summary\n")
        click.echo("> **[PLACEHOLDER]** Summarization not yet implemented.\n")
        for line in lines[1:]:
            key, _, val = line.partition(":")
            click.echo(f"- **{key.strip()}**: {val.strip()}")
    else:
        click.echo("\n".join(lines))
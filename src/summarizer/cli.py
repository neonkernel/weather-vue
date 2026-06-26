"""Command-line interface for the article summarizer."""

import sys
from pathlib import Path

import click

from .config import Config
from .exceptions import SummarizerError
from .formatter import Formatter
from .styles import OutputFormat, SummaryStyle
from .summarize import summarize_url


@click.command()
@click.argument("url")
@click.option(
    "--style",
    type=click.Choice([s.value for s in SummaryStyle], case_sensitive=False),
    default=SummaryStyle.BRIEF.value,
    show_default=True,
    help=(
        "Summary style: "
        "'bullets' (key takeaways as bullet points), "
        "'brief' (short executive brief), "
        "'detailed' (comprehensive analysis), "
        "'eli5' (explain like I'm 5), "
        "'tldr' (one-sentence summary)."
    ),
)
@click.option(
    "--format",
    "output_format",
    type=click.Choice([f.value for f in OutputFormat], case_sensitive=False),
    default=OutputFormat.TEXT.value,
    show_default=True,
    help=(
        "Output format: "
        "'text' (plain text), "
        "'markdown' (Markdown with title and metadata), "
        "'json' (full JSON including metadata)."
    ),
)
@click.option(
    "--output",
    "output_file",
    type=click.Path(dir_okay=False, writable=True),
    default=None,
    help="Write output to this file instead of stdout.",
)
@click.option(
    "--model",
    default=None,
    help="Override the LLM model specified in config.",
)
@click.option(
    "--config",
    "config_path",
    type=click.Path(exists=True, dir_okay=False),
    default=None,
    help="Path to a custom configuration file.",
)
@click.option(
    "--verbose",
    is_flag=True,
    default=False,
    help="Enable verbose/debug logging.",
)
@click.version_option()
def main(
    url: str,
    style: str,
    output_format: str,
    output_file: str | None,
    model: str | None,
    config_path: str | None,
    verbose: bool,
) -> None:
    """Summarize the article at URL and print the result.

    Examples:

    \b
    # Brief summary (default) as plain text
    summarizer https://example.com/article

    \b
    # Bullet-point summary in Markdown
    summarizer https://example.com/article --style bullets --format markdown

    \b
    # Detailed summary saved to a file as JSON
    summarizer https://example.com/article --style detailed --format json --output summary.json

    \b
    # ELI5 explanation printed to stdout
    summarizer https://example.com/article --style eli5

    \b
    # One-sentence TL;DR in Markdown
    summarizer https://example.com/article --style tldr --format markdown
    """
    try:
        # Load configuration
        cfg = Config.load(config_path)
        if model:
            cfg.model = model
        if verbose:
            cfg.verbose = True

        # Resolve enums from the CLI string values
        summary_style = SummaryStyle(style)
        fmt = OutputFormat(output_format)

        # Generate the summary
        summary = summarize_url(url, style=summary_style, config=cfg)

        # Format the output
        formatter = Formatter()
        rendered = formatter.format(summary, fmt)

        # Write to file or stdout
        if output_file:
            output_path = Path(output_file)
            output_path.write_text(rendered, encoding="utf-8")
            click.echo(f"Summary written to {output_path}", err=True)
        else:
            click.echo(rendered)

    except SummarizerError as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)
    except KeyboardInterrupt:
        click.echo("\nAborted.", err=True)
        sys.exit(130)
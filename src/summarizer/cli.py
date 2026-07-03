"""Command-line interface for the article summarizer."""
from __future__ import annotations

import sys
import logging
from pathlib import Path
from typing import Optional

import click

from .config import Config
from .exceptions import SummarizerError
from .logger import setup_logging

logger = logging.getLogger(__name__)


def _get_config(ctx: click.Context) -> Config:
    """Retrieve config from Click context."""
    return ctx.ensure_object(Config)


@click.group()
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose/debug logging.")
@click.option("--quiet", "-q", is_flag=True, help="Suppress non-essential output.")
@click.pass_context
def cli(ctx: click.Context, verbose: bool, quiet: bool) -> None:
    """Article summarizer — fetch and summarize articles from URLs or files."""
    ctx.ensure_object(Config)
    cfg: Config = ctx.obj
    cfg.verbose = verbose
    cfg.quiet = quiet
    level = logging.DEBUG if verbose else (logging.WARNING if quiet else logging.INFO)
    setup_logging(level)


@cli.command("summarize")
@click.argument("source")
@click.option("--style", "-s", default="concise", show_default=True,
              help="Summary style: concise, detailed, bullet.")
@click.option("--model", "-m", default=None, help="LLM model to use.")
@click.option("--format", "output_format", default="text", show_default=True,
              help="Output format: text, markdown, json.")
@click.pass_context
def summarize_cmd(
    ctx: click.Context,
    source: str,
    style: str,
    model: Optional[str],
    output_format: str,
) -> None:
    """Summarize a single article from a URL or file path."""
    cfg = _get_config(ctx)
    try:
        from .ingestion import fetch_article
        from .summarize import summarize_article
        from .formatter import format_output

        article = fetch_article(source)
        summary = summarize_article(article, style=style, model=model or cfg.default_model)
        output = format_output(summary, article, fmt=output_format)
        click.echo(output)
    except SummarizerError as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)
    except Exception as exc:
        logger.debug("Unexpected error", exc_info=True)
        click.echo(f"Unexpected error: {exc}", err=True)
        sys.exit(1)


@cli.command("batch")
@click.argument("input_path", metavar="INPUT")
@click.option(
    "--workers", "-w",
    default=4,
    show_default=True,
    type=click.IntRange(1, 32),
    help="Number of concurrent worker threads.",
)
@click.option(
    "--output", "-o",
    default=None,
    help="Output file path for results (CSV or JSON Lines).",
)
@click.option(
    "--format", "output_format",
    default="csv",
    show_default=True,
    type=click.Choice(["csv", "jsonl"], case_sensitive=False),
    help="Output file format when --output is specified.",
)
@click.option(
    "--style", "-s",
    default="concise",
    show_default=True,
    help="Summary style: concise, detailed, bullet.",
)
@click.option(
    "--model", "-m",
    default=None,
    help="LLM model to use for summarization.",
)
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Fetch and validate sources without calling the LLM.",
)
@click.pass_context
def batch_cmd(
    ctx: click.Context,
    input_path: str,
    workers: int,
    output: Optional[str],
    output_format: str,
    style: str,
    model: Optional[str],
    dry_run: bool,
) -> None:
    """
    Summarize multiple articles from a URL list file or directory.

    INPUT can be:

    \b
      - A .txt file with one URL per line
      - A directory of .txt or .html article files

    Examples:

    \b
      summarizer batch urls.txt --workers 8 --output results.csv
      summarizer batch articles/ --dry-run
      summarizer batch urls.txt --output results.jsonl --format jsonl
    """
    cfg = _get_config(ctx)

    try:
        from .batch import BatchProcessor
        from .reporter import generate_rich_table, write_output
    except ImportError as exc:
        click.echo(f"Import error: {exc}", err=True)
        sys.exit(1)

    # Try to import ingestion and summarize; provide helpful errors if missing
    try:
        from .ingestion import fetch_article
    except ImportError:
        click.echo(
            "Error: ingestion module not found. Ensure the package is installed correctly.",
            err=True,
        )
        sys.exit(1)

    summarize_fn = None
    if not dry_run:
        try:
            from .summarize import summarize_article
            summarize_fn = summarize_article
        except ImportError:
            click.echo(
                "Error: summarize module not found. Use --dry-run to skip LLM calls.",
                err=True,
            )
            sys.exit(1)

    # Set up progress display
    try:
        from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
        from rich.console import Console

        console = Console(stderr=True)
        use_rich = True
    except ImportError:
        use_rich = False
        console = None

    if use_rich:
        progress = Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console,
            transient=True,
        )
    else:
        progress = None

    def _progress_callback(result, completed, total):
        status = "✓" if (result.dry_run_success if dry_run else result.success) else "✗"
        source_short = result.source[-50:] if len(result.source) > 50 else result.source
        if use_rich and progress and task_id is not None:
            progress.update(
                task_id,
                completed=completed,
                description=f"[{status}] {source_short}",
            )
        else:
            symbol = "OK" if (result.dry_run_success if dry_run else result.success) else "FAIL"
            click.echo(f"  [{completed}/{total}] {symbol}: {source_short}", err=True)

    task_id = None

    processor = BatchProcessor(
        max_workers=workers,
        dry_run=dry_run,
        progress_callback=_progress_callback,
    )

    # Load sources
    try:
        sources = processor.load_sources(input_path)
    except (FileNotFoundError, ValueError) as exc:
        click.echo(f"Error loading sources: {exc}", err=True)
        sys.exit(1)

    mode_label = "[DRY RUN] " if dry_run else ""
    click.echo(
        f"{mode_label}Processing {len(sources)} source(s) with {workers} worker(s)...",
        err=True,
    )

    # Run batch with optional progress bar
    effective_model = model or cfg.default_model if hasattr(cfg, "default_model") else model

    try:
        if use_rich and progress is not None:
            with progress:
                task_id = progress.add_task("Starting...", total=len(sources))
                results = processor.run(
                    sources,
                    fetch_fn=fetch_article,
                    summarize_fn=summarize_fn,
                    style=style,
                    model=effective_model,
                )
        else:
            results = processor.run(
                sources,
                fetch_fn=fetch_article,
                summarize_fn=summarize_fn,
                style=style,
                model=effective_model,
            )
    except Exception as exc:
        logger.debug("Batch processing error", exc_info=True)
        click.echo(f"Batch processing error: {exc}", err=True)
        sys.exit(1)

    # Display results table
    generate_rich_table(results, dry_run=dry_run)

    # Write output file if requested
    if output:
        try:
            write_output(results, output, fmt=output_format)
            click.echo(f"Results written to: {output}", err=True)
        except Exception as exc:
            click.echo(f"Failed to write output file: {exc}", err=True)
            sys.exit(1)

    # Exit with non-zero code if any failures occurred
    failures = [r for r in results if r.error]
    if failures:
        sys.exit(1)
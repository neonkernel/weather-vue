"""CLI entry point for the summarizer tool."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

import click
from rich.console import Console

from .logger import get_logger
from .config import load_config
from .summarize import summarize_source

console = Console()
logger = get_logger(__name__)


def _build_summarize_fn(style: str, model: Optional[str], config):
    """Build a summarize function that captures style/model context."""
    from .summarize import summarize_source

    def fn(source: str, dry_run: bool) -> tuple:
        return summarize_source(
            source=source,
            style=style,
            model=model,
            config=config,
            dry_run=dry_run,
        )

    return fn


@click.group()
@click.version_option()
def cli():
    """Article summarizer powered by LLMs."""
    pass


@cli.command("summarize")
@click.argument("source")
@click.option("--style", default="default", show_default=True, help="Summary style.")
@click.option("--model", default=None, help="LLM model override.")
@click.option("--output", default=None, type=click.Path(), help="Save summary to file.")
@click.option("--dry-run", is_flag=True, default=False, help="Fetch only, skip LLM call.")
def summarize_cmd(source: str, style: str, model: Optional[str], output: Optional[str], dry_run: bool):
    """Summarize a single article from a URL or file path."""
    try:
        config = load_config()
        article, summary = summarize_source(
            source=source,
            style=style,
            model=model,
            config=config,
            dry_run=dry_run,
        )
        if dry_run:
            console.print(f"[yellow]DRY RUN:[/yellow] Fetched [bold]{article.title!r}[/bold] ({article.word_count} words). LLM not called.")
            return

        console.print(f"\n[bold cyan]{article.title}[/bold cyan]")
        console.print(f"[dim]{article.url}[/dim]\n")
        console.print(summary.text)

        if summary.tokens_used:
            console.print(f"\n[dim]Tokens used: {summary.tokens_used}[/dim]")

        if output:
            out_path = Path(output)
            out_path.write_text(summary.text, encoding="utf-8")
            console.print(f"\n[green]Summary saved to:[/green] {out_path}")

    except Exception as exc:
        console.print(f"[red]Error:[/red] {exc}", err=True)
        logger.exception("summarize command failed")
        sys.exit(1)


@cli.command("batch")
@click.argument("input_path", type=click.Path(exists=True))
@click.option(
    "--workers",
    default=4,
    show_default=True,
    type=int,
    help="Number of concurrent worker threads.",
)
@click.option(
    "--output",
    default=None,
    type=click.Path(),
    help="Output file path for results (CSV, JSON, or JSONL).",
)
@click.option(
    "--format",
    "output_format",
    default="csv",
    show_default=True,
    type=click.Choice(["csv", "json", "jsonl"], case_sensitive=False),
    help="Output file format when --output is specified.",
)
@click.option("--style", default="default", show_default=True, help="Summary style for all items.")
@click.option("--model", default=None, help="LLM model override for all items.")
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Fetch and validate sources without calling the LLM.",
)
def batch_cmd(
    input_path: str,
    workers: int,
    output: Optional[str],
    output_format: str,
    style: str,
    model: Optional[str],
    dry_run: bool,
):
    """
    Summarize multiple articles from a URL list file or directory.

    INPUT_PATH can be:
    \b
      - A .txt file with one URL or file path per line
      - A directory containing .txt or .html files

    Examples:
    \b
      summarizer batch urls.txt --workers 8 --output results.csv
      summarizer batch articles/ --dry-run
      summarizer batch urls.txt --output results.jsonl --format jsonl
    """
    from .batch import BatchProcessor, collect_sources
    from .reporter import print_batch_summary, export_results

    input_path_obj = Path(input_path)

    try:
        config = load_config()
    except Exception as exc:
        console.print(f"[red]Failed to load config:[/red] {exc}", err=True)
        sys.exit(1)

    # Collect sources
    try:
        sources = collect_sources(input_path_obj)
    except Exception as exc:
        console.print(f"[red]Failed to collect sources:[/red] {exc}", err=True)
        sys.exit(1)

    if not sources:
        console.print("[yellow]No sources found. Nothing to process.[/yellow]")
        sys.exit(0)

    console.print(
        f"\n[bold cyan]Batch Processing[/bold cyan] — "
        f"{len(sources)} source(s), {workers} worker(s)"
        + (" [yellow][DRY RUN][/yellow]" if dry_run else "")
    )

    summarize_fn = _build_summarize_fn(style=style, model=model, config=config)

    def progress_callback(source: str, status: str) -> None:
        icon = "[green]✓[/green]" if status == "success" else "[red]✗[/red]"
        short = source if len(source) <= 60 else "..." + source[-57:]
        console.print(f"  {icon} {short} [dim]({status})[/dim]")

    processor = BatchProcessor(
        summarize_fn=summarize_fn,
        workers=workers,
        dry_run=dry_run,
        progress_callback=progress_callback,
    )

    try:
        results = processor.run(sources)
    except KeyboardInterrupt:
        console.print("\n[yellow]Batch interrupted by user.[/yellow]")
        sys.exit(130)

    # Print Rich table summary
    print_batch_summary(results, dry_run=dry_run)

    # Export to file if requested
    if output:
        try:
            export_results(results, Path(output), fmt=output_format)
        except Exception as exc:
            console.print(f"[red]Failed to write output:[/red] {exc}", err=True)
            sys.exit(1)

    # Exit with non-zero if any failures
    failures = [r for r in results if not r.success]
    if failures:
        sys.exit(1)


def main():
    cli()


if __name__ == "__main__":
    main()
"""Command-line interface for the summarizer."""

import sys
import logging
from pathlib import Path
from typing import Optional

import click

logger = logging.getLogger(__name__)


def _setup_logging(verbose: bool = False) -> None:
    """Configure logging based on verbosity."""
    level = logging.DEBUG if verbose else logging.WARNING
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


@click.group()
@click.option("--verbose", "-v", is_flag=True, default=False, help="Enable verbose logging.")
@click.pass_context
def cli(ctx: click.Context, verbose: bool) -> None:
    """
    Summarizer — AI-powered article summarization tool.

    Use one of the subcommands below to get started.
    """
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose
    _setup_logging(verbose)


# ---------------------------------------------------------------------------
# summarize subcommand
# ---------------------------------------------------------------------------

@cli.command("summarize")
@click.argument("source")
@click.option(
    "--style",
    "-s",
    default="default",
    show_default=True,
    help="Summary style (default, brief, detailed, bullet).",
)
@click.option("--model", "-m", default=None, help="LLM model to use.")
@click.option("--output", "-o", default=None, help="Save summary to this file.")
@click.pass_context
def summarize_cmd(
    ctx: click.Context,
    source: str,
    style: str,
    model: Optional[str],
    output: Optional[str],
) -> None:
    """
    Summarize a single article from a URL or local file.

    SOURCE can be a URL (http/https) or a path to a .txt or .html file.
    """
    from .batch import BatchProcessor
    from .reporter import print_rich_table

    processor = BatchProcessor(workers=1, dry_run=False, style=style, model=model)
    results = processor.run([source])
    result = results[0]

    if result.success:
        summary_text = result.summary_text or ""
        click.echo("\n" + "=" * 60)
        if result.article:
            click.echo(f"Title: {result.article.title}")
            click.echo(f"Words: {result.article.word_count:,}")
        click.echo("=" * 60)
        click.echo(summary_text)
        click.echo("=" * 60)

        if result.tokens_used:
            click.echo(f"\nTokens used: {result.tokens_used:,} | Est. cost: ${result.cost_estimate:.4f}")

        if output:
            out_path = Path(output)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(summary_text, encoding="utf-8")
            click.echo(f"\nSummary saved to: {output}")
    else:
        click.echo(f"\n[ERROR] Failed to summarize '{source}':", err=True)
        click.echo(f"  {result.error}", err=True)
        sys.exit(1)


# ---------------------------------------------------------------------------
# batch subcommand
# ---------------------------------------------------------------------------

@cli.command("batch")
@click.argument("source_path")
@click.option(
    "--workers",
    "-w",
    default=4,
    show_default=True,
    type=click.IntRange(1, 32),
    help="Number of parallel worker threads.",
)
@click.option(
    "--output",
    "-o",
    default=None,
    help="Output file path for results (e.g. results.csv or results.jsonl).",
)
@click.option(
    "--format",
    "-f",
    "output_format",
    default=None,
    type=click.Choice(["csv", "jsonl"], case_sensitive=False),
    help="Output format: csv or jsonl. Inferred from --output extension if not set.",
)
@click.option(
    "--style",
    "-s",
    default="default",
    show_default=True,
    help="Summary style (default, brief, detailed, bullet).",
)
@click.option("--model", "-m", default=None, help="LLM model to use.")
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Fetch and validate all sources without calling the LLM.",
)
@click.pass_context
def batch_cmd(
    ctx: click.Context,
    source_path: str,
    workers: int,
    output: Optional[str],
    output_format: Optional[str],
    style: str,
    model: Optional[str],
    dry_run: bool,
) -> None:
    """
    Summarize multiple articles from a URL list file or directory.

    SOURCE_PATH can be:

    \b
    - A .txt file with one URL per line (lines starting with # are ignored)
    - A directory containing .txt or .html article files

    Examples:

    \b
      summarizer batch urls.txt --workers 8
      summarizer batch ./articles/ --dry-run
      summarizer batch urls.txt --output results.csv
      summarizer batch urls.txt --output results.jsonl --format jsonl
    """
    from .batch import BatchProcessor
    from .reporter import print_rich_table, write_results

    # Determine output format
    fmt = output_format
    if fmt is None and output:
        ext = Path(output).suffix.lower()
        if ext in (".jsonl", ".json"):
            fmt = "jsonl"
        else:
            fmt = "csv"

    # Progress callback using Rich if available
    try:
        from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
        from rich.console import Console

        console = Console()

        def make_progress_display(total: int):
            progress = Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
                console=console,
            )
            return progress

        use_rich_progress = True
    except ImportError:
        use_rich_progress = False

    completed_count = [0]
    total_sources = [0]  # will be set after loading

    def _simple_progress_callback(result):
        completed_count[0] += 1
        status = "✓" if result.success else "✗"
        source_label = result.source[:60] + "..." if len(result.source) > 60 else result.source
        click.echo(f"  [{completed_count[0]}/{total_sources[0]}] {status} {source_label}")

    processor = BatchProcessor(
        workers=workers,
        dry_run=dry_run,
        style=style,
        model=model,
    )

    try:
        sources = processor.load_sources(source_path)
    except (FileNotFoundError, ValueError) as exc:
        click.echo(f"\n[ERROR] {exc}", err=True)
        sys.exit(1)

    total_sources[0] = len(sources)

    mode_str = " [DRY RUN]" if dry_run else ""
    click.echo(
        f"\nProcessing {len(sources)} source(s){mode_str} with {workers} worker(s)...\n"
    )

    processor.progress_callback = _simple_progress_callback

    results = processor.run(sources)

    # Display Rich table
    print_rich_table(results, dry_run=dry_run)

    # Write output file if requested
    if output and fmt:
        try:
            write_results(results, output, fmt=fmt)
            click.echo(f"Results written to: {output} (format: {fmt})\n")
        except Exception as exc:
            click.echo(f"\n[ERROR] Failed to write output: {exc}", err=True)
            sys.exit(1)

    # Exit with non-zero code if any failures occurred
    failure_count = sum(1 for r in results if not r.success)
    if failure_count > 0:
        click.echo(
            f"Warning: {failure_count} of {len(results)} sources failed.",
            err=True,
        )
        # Non-zero exit but don't abort — partial success
        sys.exit(2)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    """Main entry point."""
    cli(obj={})


if __name__ == "__main__":
    main()
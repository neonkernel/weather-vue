"""Command-line interface for the summarizer."""

import logging
import sys
from pathlib import Path
from typing import Optional

import click

from .config import Config
from .exceptions import SummarizerError
from .logger import setup_logging

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_ingest_fn(cfg: Config):
    """Return a callable that ingests a single source into an Article."""
    from .ingestion import ingest  # local import to keep startup fast
    return lambda source: ingest(source, cfg)


def _get_summarize_fn(cfg: Config, style: str, model: Optional[str]):
    """Return a callable that summarises an Article into a Summary."""
    from .summarize import summarize_article  # local import
    return lambda article: summarize_article(article, cfg, style=style, model=model)


# ---------------------------------------------------------------------------
# Root group
# ---------------------------------------------------------------------------

@click.group()
@click.option("--debug/--no-debug", default=False, help="Enable debug logging.")
@click.pass_context
def cli(ctx: click.Context, debug: bool):
    """Article summarizer CLI."""
    ctx.ensure_object(dict)
    setup_logging(level=logging.DEBUG if debug else logging.INFO)
    ctx.obj["debug"] = debug
    ctx.obj["config"] = Config()


# ---------------------------------------------------------------------------
# summarize (single-article) subcommand
# ---------------------------------------------------------------------------

@cli.command("summarize")
@click.argument("source")
@click.option(
    "--style",
    default="concise",
    show_default=True,
    help="Summary style (e.g. concise, detailed, bullets).",
)
@click.option("--model", default=None, help="LLM model override.")
@click.option("--output", "-o", default=None, help="Write summary to file.")
@click.pass_context
def summarize_cmd(
    ctx: click.Context,
    source: str,
    style: str,
    model: Optional[str],
    output: Optional[str],
):
    """Summarize a single article from URL or file."""
    cfg: Config = ctx.obj["config"]

    try:
        ingest = _get_ingest_fn(cfg)
        summarize = _get_summarize_fn(cfg, style, model)

        article = ingest(source)
        summary = summarize(article)

        text = summary.text
        if output:
            Path(output).write_text(text, encoding="utf-8")
            click.echo(f"Summary written to {output}")
        else:
            click.echo(text)

        click.echo(
            f"\n[tokens: {summary.tokens_used} | cost: ${summary.cost_estimate:.6f}]",
            err=True,
        )
    except SummarizerError as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)


# ---------------------------------------------------------------------------
# batch subcommand
# ---------------------------------------------------------------------------

@cli.command("batch")
@click.argument("input_path")
@click.option(
    "--workers",
    "-w",
    default=4,
    show_default=True,
    type=click.IntRange(1, 64),
    help="Number of concurrent worker threads.",
)
@click.option(
    "--output",
    "-o",
    default=None,
    help="Output file for results (CSV or JSON Lines, inferred from extension).",
)
@click.option(
    "--format",
    "fmt",
    default="auto",
    type=click.Choice(["auto", "csv", "jsonl"], case_sensitive=False),
    show_default=True,
    help="Output format when --output is specified.",
)
@click.option(
    "--style",
    default="concise",
    show_default=True,
    help="Summary style applied to every article.",
)
@click.option("--model", default=None, help="LLM model override.")
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
    fmt: str,
    style: str,
    model: Optional[str],
    dry_run: bool,
):
    """
    Summarize multiple articles from a URL list file or directory.

    INPUT_PATH can be:

    \b
      - A .txt file with one URL per line
      - A directory containing .txt / .html article files
      - A single URL or file path

    Examples:

    \b
      summarizer batch urls.txt --workers 8 --output results.csv
      summarizer batch articles/ --dry-run
      summarizer batch urls.txt --output results.jsonl --format jsonl
    """
    cfg: Config = ctx.obj["config"]

    try:
        from .batch import BatchProcessor
        from .reporter import BatchReporter

        ingest_fn = _get_ingest_fn(cfg)
        summarize_fn = _get_summarize_fn(cfg, style, model)

        # Rich progress indicator (best-effort)
        try:
            from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
            from rich.console import Console

            console = Console()
            progress_ctx = Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
                console=console,
                transient=True,
            )

            with progress_ctx as progress:
                # We don't know the total until BatchProcessor loads sources, so
                # we start the task lazily.
                task_id = None
                completed = [0]

                def _progress_callback(result):
                    nonlocal task_id
                    if task_id is None:
                        return
                    completed[0] += 1
                    status = "✓" if result.success else "✗"
                    short_src = result.source[-50:] if len(result.source) > 50 else result.source
                    progress.update(task_id, advance=1, description=f"{status} {short_src}")

                processor = BatchProcessor(
                    ingest_fn=ingest_fn,
                    summarize_fn=summarize_fn,
                    workers=workers,
                    dry_run=dry_run,
                    progress_callback=_progress_callback,
                )

                # Load sources first so we can set the total
                sources = processor._load_sources(input_path)
                task_id = progress.add_task("Processing...", total=len(sources))

                results = processor.run(input_path)

        except ImportError:
            # Fallback without Rich progress
            def _plain_callback(result):
                status = "OK" if result.success else "FAIL"
                click.echo(f"[{status}] {result.source} ({result.duration_seconds:.2f}s)")

            processor = BatchProcessor(
                ingest_fn=ingest_fn,
                summarize_fn=summarize_fn,
                workers=workers,
                dry_run=dry_run,
                progress_callback=_plain_callback,
            )
            results = processor.run(input_path)
            console = None

        reporter = BatchReporter(results, console=console if "console" in dir() else None)
        reporter.print_table()

        if output:
            reporter.write_output(output, fmt=fmt)
            click.echo(f"\nResults written to {output}", err=True)

        # Exit with non-zero if any failures
        if reporter.failures:
            sys.exit(1)

    except SummarizerError as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    cli(obj={})


if __name__ == "__main__":
    main()
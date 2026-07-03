"""Command-line interface for the article summarizer."""
from __future__ import annotations

import sys
import logging
from pathlib import Path
from typing import Optional

import click

from .config import Config
from .exceptions import SummarizerError

logger = logging.getLogger(__name__)


def _get_console():
    """Lazily import and return a Rich Console."""
    try:
        from rich.console import Console
        return Console()
    except ImportError:
        return None


@click.group()
@click.option("--debug", is_flag=True, default=False, help="Enable debug logging.")
@click.option(
    "--config",
    "config_path",
    type=click.Path(exists=False),
    default=None,
    help="Path to configuration file.",
)
@click.pass_context
def cli(ctx: click.Context, debug: bool, config_path: Optional[str]) -> None:
    """Article Summarizer CLI – summarize web articles using LLMs."""
    ctx.ensure_object(dict)

    level = logging.DEBUG if debug else logging.WARNING
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    try:
        config = Config.load(config_path)
    except Exception as exc:
        click.echo(f"Warning: Could not load config: {exc}", err=True)
        config = Config()

    ctx.obj["config"] = config
    ctx.obj["debug"] = debug


@cli.command("summarize")
@click.argument("url")
@click.option(
    "--style",
    default="default",
    show_default=True,
    help="Summary style (default, bullets, academic, etc.).",
)
@click.option("--model", default=None, help="LLM model to use.")
@click.option("--no-cache", is_flag=True, default=False, help="Bypass cache.")
@click.pass_context
def summarize_cmd(
    ctx: click.Context,
    url: str,
    style: str,
    model: Optional[str],
    no_cache: bool,
) -> None:
    """Summarize a single article from URL."""
    config: Config = ctx.obj["config"]
    console = _get_console()

    try:
        from .summarize import summarize_article

        if model:
            config.model = model

        summary = summarize_article(url, style=style, config=config, use_cache=not no_cache)

        if console:
            console.print(f"\n[bold]Summary[/bold] ([dim]{summary.model}[/dim])\n")
            console.print(summary.text)
            console.print(
                f"\n[dim]Tokens: {summary.tokens_used} | "
                f"Cost: ${summary.cost_estimate:.4f} | "
                f"Time: {summary.duration_seconds:.1f}s[/dim]"
            )
        else:
            print(f"\nSummary ({summary.model})\n")
            print(summary.text)
            print(
                f"\nTokens: {summary.tokens_used} | "
                f"Cost: ${summary.cost_estimate:.4f} | "
                f"Time: {summary.duration_seconds:.1f}s"
            )
    except SummarizerError as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)
    except Exception as exc:
        logger.debug("Unexpected error", exc_info=True)
        click.echo(f"Unexpected error: {exc}", err=True)
        sys.exit(1)


@cli.command("batch")
@click.argument("source")
@click.option(
    "--workers",
    default=4,
    show_default=True,
    type=click.IntRange(1, 32),
    help="Number of concurrent worker threads.",
)
@click.option(
    "--output",
    default=None,
    type=click.Path(),
    help="Path to write results (CSV or JSON Lines).",
)
@click.option(
    "--format",
    "output_format",
    default="csv",
    show_default=True,
    type=click.Choice(["csv", "jsonl", "json"], case_sensitive=False),
    help="Output file format (csv or jsonl).",
)
@click.option(
    "--style",
    default="default",
    show_default=True,
    help="Summary style for all articles.",
)
@click.option("--model", default=None, help="LLM model to use for all articles.")
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Fetch and validate sources without calling the LLM.",
)
@click.option("--no-cache", is_flag=True, default=False, help="Bypass cache.")
@click.pass_context
def batch_cmd(
    ctx: click.Context,
    source: str,
    workers: int,
    output: Optional[str],
    output_format: str,
    style: str,
    model: Optional[str],
    dry_run: bool,
    no_cache: bool,
) -> None:
    """Summarize multiple articles from a URL list file or directory.

    SOURCE can be:
      - A .txt file with one URL per line
      - A directory containing .txt or .html article files
    """
    config: Config = ctx.obj["config"]
    console = _get_console()

    if model:
        config.model = model

    if dry_run:
        msg = "[yellow]Dry-run mode: sources will be fetched but not summarized.[/yellow]"
        if console:
            console.print(msg)
        else:
            click.echo("Dry-run mode: sources will be fetched but not summarized.")

    try:
        from .summarize import summarize_article, fetch_article
        from .batch import BatchProcessor
        from .reporter import write_report

        # Build callables
        def _summarize(src: str):
            return summarize_article(src, style=style, config=config, use_cache=not no_cache)

        def _fetch(src: str):
            return fetch_article(src, config=config)

        # Set up progress display
        completed = [0]
        total_ref = [0]

        def _progress(result):
            completed[0] += 1
            status = "[green]OK[/green]" if result.success else "[red]FAIL[/red]"
            if console:
                console.print(
                    f"  [{completed[0]}/{total_ref[0]}] {status} "
                    f"[dim]{result.source[:70]}[/dim]"
                )
            else:
                status_plain = "OK" if result.success else "FAIL"
                click.echo(
                    f"  [{completed[0]}/{total_ref[0]}] {status_plain} {result.source[:70]}"
                )

        processor = BatchProcessor(
            summarize_fn=_summarize,
            fetch_fn=_fetch,
            workers=workers,
            dry_run=dry_run,
            progress_callback=_progress,
        )

        # Load sources
        sources = processor.load_sources(source)

        if not sources:
            click.echo("No sources found. Exiting.", err=True)
            sys.exit(1)

        total_ref[0] = len(sources)

        mode_str = "dry-run" if dry_run else f"style={style}"
        if console:
            console.print(
                f"\n[bold]Batch Processing[/bold] – "
                f"{len(sources)} sources, {workers} workers, {mode_str}\n"
            )
        else:
            click.echo(
                f"\nBatch Processing – {len(sources)} sources, {workers} workers, {mode_str}\n"
            )

        # Run batch
        report = processor.run(sources)

        # Display and optionally write report
        write_report(
            report,
            output_path=output,
            output_format=output_format,
            console=console,
        )

        # Exit with non-zero if any failures
        if report.failures > 0 and report.successes == 0:
            sys.exit(1)

    except ValueError as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)
    except SummarizerError as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)
    except Exception as exc:
        logger.debug("Unexpected error in batch", exc_info=True)
        click.echo(f"Unexpected error: {exc}", err=True)
        sys.exit(1)


def main() -> None:
    """Entry point for the CLI."""
    cli(obj={})


if __name__ == "__main__":
    main()
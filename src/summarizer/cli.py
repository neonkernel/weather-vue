"""Command-line interface for the summarizer package."""

from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

from .config import Config
from .exceptions import SummarizerError

app = typer.Typer(
    name="summarize",
    help="AI-powered article summarizer.",
    add_completion=False,
)
console = Console()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_config() -> Config:
    """Load configuration from environment / config file."""
    return Config.load()


def _build_process_fn(cfg: Config):
    """Return a callable that fetches & ingests a single source."""

    def process_fn(source: str):
        from urllib.parse import urlparse
        from .ingestion import ingest_url, ingest_file
        from .models import ArticleContent

        try:
            parsed = urlparse(source)
            if parsed.scheme in ("http", "https"):
                article = ingest_url(source, cfg)
            else:
                article = ingest_file(Path(source), cfg)
            return article, None
        except Exception as exc:  # noqa: BLE001
            return None, str(exc)

    return process_fn


def _build_summarize_fn(cfg: Config, style: str, model: Optional[str]):
    """Return a callable that summarises an ArticleContent."""

    def summarize_fn(article):
        from .summarize import summarize_article

        result = summarize_article(article, cfg, style=style, model=model)
        return result.summary, result.tokens_used

    return summarize_fn


# ---------------------------------------------------------------------------
# `summarize run` — single article
# ---------------------------------------------------------------------------

@app.command("run")
def run_cmd(
    source: str = typer.Argument(..., help="URL or path to an article file."),
    style: str = typer.Option("default", "--style", "-s", help="Summary style."),
    model: Optional[str] = typer.Option(None, "--model", "-m", help="LLM model override."),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Save summary to file."),
) -> None:
    """Summarise a single article from a URL or file."""
    cfg = _get_config()

    process_fn = _build_process_fn(cfg)
    article, error = process_fn(source)

    if error or article is None:
        console.print(f"[red]Error fetching source:[/red] {error}")
        raise typer.Exit(code=1)

    summarize_fn = _build_summarize_fn(cfg, style, model)
    try:
        summary_text, tokens = summarize_fn(article)
    except SummarizerError as exc:
        console.print(f"[red]Summarisation failed:[/red] {exc}")
        raise typer.Exit(code=1)

    console.print()
    console.rule(f"[bold]{article.title or source}")
    console.print(summary_text)
    console.print()
    console.print(f"[dim]Tokens used: {tokens}[/dim]")

    if output:
        output.write_text(summary_text, encoding="utf-8")
        console.print(f"[green]Summary written to:[/green] {output}")


# ---------------------------------------------------------------------------
# `summarize batch` — multiple articles
# ---------------------------------------------------------------------------

@app.command("batch")
def batch_cmd(
    source_path: Path = typer.Argument(
        ...,
        help=(
            "Path to a .txt file containing one URL per line, "
            "or a directory of .txt/.html article files."
        ),
    ),
    workers: int = typer.Option(
        4, "--workers", "-w", min=1, max=32, help="Number of concurrent worker threads."
    ),
    output: Optional[Path] = typer.Option(
        None,
        "--output",
        "-o",
        help="Write results to this file (format determined by --format).",
    ),
    fmt: str = typer.Option(
        "csv",
        "--format",
        "-f",
        help="Output format when --output is specified: csv | jsonl.",
    ),
    style: str = typer.Option("default", "--style", "-s", help="Summary style for all articles."),
    model: Optional[str] = typer.Option(None, "--model", "-m", help="LLM model override."),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Fetch and validate all sources without calling the LLM.",
    ),
) -> None:
    """
    Summarise multiple articles concurrently from a URL list file or directory.

    \b
    Examples:
        summarize batch urls.txt --workers 8 --output results.csv
        summarize batch articles/ --format jsonl --output results.jsonl
        summarize batch urls.txt --dry-run
    """
    from .batch import BatchProcessor, load_sources
    from .reporter import build_report, print_summary_table, write_output

    cfg = _get_config()

    # Load sources ────────────────────────────────────────────────────────────
    try:
        sources = load_sources(source_path)
    except ValueError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(code=1)

    console.print(
        f"[bold cyan]Batch mode:[/bold cyan] {len(sources)} source(s) | "
        f"{workers} worker(s) | dry_run={dry_run}"
    )

    if dry_run:
        console.print("[yellow]Dry-run enabled — LLM calls will be skipped.[/yellow]")

    # Build processor ─────────────────────────────────────────────────────────
    process_fn = _build_process_fn(cfg)
    summarize_fn = None if dry_run else _build_summarize_fn(cfg, style, model)

    processor = BatchProcessor(
        workers=workers,
        dry_run=dry_run,
        process_fn=process_fn,
        summarize_fn=summarize_fn,
    )

    # Run ─────────────────────────────────────────────────────────────────────
    wall_start = time.monotonic()
    results = processor.run(sources)
    wall_duration = time.monotonic() - wall_start

    # Report ──────────────────────────────────────────────────────────────────
    report = build_report(results, wall_duration)
    print_summary_table(report)

    if output:
        write_output(report, output, fmt=fmt)

    # Exit with non-zero code if any item failed
    if report.failures:
        raise typer.Exit(code=1)


# ---------------------------------------------------------------------------
# Entry-point
# ---------------------------------------------------------------------------

def main() -> None:
    app()


if __name__ == "__main__":
    main()
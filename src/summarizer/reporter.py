"""Batch report generation for summarizer results."""
from __future__ import annotations

import csv
import json
import io
import sys
from pathlib import Path
from typing import List, Optional, Sequence

from .models import BatchResult

# Cost estimates per 1K tokens (input + output blended) — rough estimates
COST_PER_1K_TOKENS = {
    "gpt-4o": 0.005,
    "gpt-4o-mini": 0.000165,
    "gpt-4-turbo": 0.015,
    "gpt-3.5-turbo": 0.0015,
    "claude-3-opus": 0.015,
    "claude-3-sonnet": 0.003,
    "claude-3-haiku": 0.00025,
    "claude-3-5-sonnet": 0.003,
    "default": 0.005,
}


def _estimate_cost(tokens: int, model: Optional[str] = None) -> float:
    """Estimate cost in USD for a given token count and model."""
    if tokens <= 0:
        return 0.0
    rate = COST_PER_1K_TOKENS.get(model or "default", COST_PER_1K_TOKENS["default"])
    return (tokens / 1000) * rate


def _truncate(text: str, max_len: int = 60) -> str:
    """Truncate a string for display."""
    if len(text) <= max_len:
        return text
    return text[: max_len - 3] + "..."


def generate_rich_table(results: List[BatchResult], dry_run: bool = False) -> None:
    """Print a Rich-formatted table summarizing batch results to stdout."""
    try:
        from rich.console import Console
        from rich.table import Table
        from rich import box
    except ImportError:
        _fallback_table(results, dry_run)
        return

    console = Console()

    successes = [r for r in results if (r.dry_run_success if dry_run else r.success)]
    failures = [r for r in results if r.error]
    total_tokens = sum(r.tokens_used for r in results)
    total_duration = sum(r.duration_seconds for r in results)

    # Determine the most common model used
    models_used = [
        r.summary.model for r in results if r.summary and r.summary.model
    ]
    primary_model = models_used[0] if models_used else None

    console.print()
    console.rule("[bold cyan]Batch Processing Summary[/bold cyan]")
    console.print()

    # Results table
    table = Table(box=box.ROUNDED, show_header=True, header_style="bold magenta")
    table.add_column("#", style="dim", width=4)
    table.add_column("Source", min_width=30, max_width=60)
    table.add_column("Status", width=10)
    table.add_column("Duration", width=10, justify="right")
    if not dry_run:
        table.add_column("Tokens", width=8, justify="right")
    table.add_column("Details", min_width=20)

    for i, result in enumerate(results, start=1):
        source_display = _truncate(result.source, 58)
        duration_display = f"{result.duration_seconds:.2f}s"

        if result.error:
            status = "[red]✗ FAILED[/red]"
            details = f"[red]{_truncate(result.error, 40)}[/red]"
            tokens_display = "-"
        elif dry_run and result.dry_run_success:
            status = "[green]✓ FETCHED[/green]"
            word_count = result.article.word_count if result.article else 0
            details = f"[dim]{word_count} words[/dim]"
            tokens_display = "-"
        elif result.success:
            status = "[green]✓ OK[/green]"
            preview = _truncate(result.summary.text if result.summary else "", 40)
            details = f"[dim]{preview}[/dim]"
            tokens_display = str(result.tokens_used) if result.tokens_used else "-"
        else:
            status = "[yellow]? UNKNOWN[/yellow]"
            details = ""
            tokens_display = "-"

        if dry_run:
            table.add_row(str(i), source_display, status, duration_display, details)
        else:
            table.add_row(
                str(i), source_display, status, duration_display, tokens_display, details
            )

    console.print(table)
    console.print()

    # Summary statistics
    console.print(f"  [bold]Total items:[/bold]    {len(results)}")
    console.print(f"  [bold]Successful:[/bold]     [green]{len(successes)}[/green]")
    console.print(f"  [bold]Failed:[/bold]         [red]{len(failures)}[/red]")
    console.print(f"  [bold]Total duration:[/bold] {total_duration:.2f}s")

    if not dry_run and total_tokens > 0:
        estimated_cost = _estimate_cost(total_tokens, primary_model)
        console.print(f"  [bold]Total tokens:[/bold]   {total_tokens:,}")
        if primary_model:
            console.print(f"  [bold]Model:[/bold]          {primary_model}")
        console.print(
            f"  [bold]Est. cost:[/bold]      [yellow]${estimated_cost:.4f} USD[/yellow]"
        )

    console.print()


def _fallback_table(results: List[BatchResult], dry_run: bool = False) -> None:
    """Plain-text fallback when Rich is not available."""
    successes = sum(1 for r in results if (r.dry_run_success if dry_run else r.success))
    failures = sum(1 for r in results if r.error)
    total_tokens = sum(r.tokens_used for r in results)
    total_duration = sum(r.duration_seconds for r in results)

    print("\n=== Batch Processing Summary ===")
    print(f"{'#':<4} {'Source':<50} {'Status':<10} {'Duration':<10}")
    print("-" * 80)
    for i, result in enumerate(results, start=1):
        source = _truncate(result.source, 48)
        status = "FAILED" if result.error else ("FETCHED" if dry_run else "OK")
        print(f"{i:<4} {source:<50} {status:<10} {result.duration_seconds:.2f}s")

    print("-" * 80)
    print(f"Total: {len(results)} | OK: {successes} | Failed: {failures}")
    print(f"Total duration: {total_duration:.2f}s")
    if not dry_run and total_tokens > 0:
        print(f"Total tokens: {total_tokens:,}")
    print()


def write_csv(results: List[BatchResult], output_path: str) -> None:
    """Write batch results to a CSV file."""
    path = Path(output_path)
    fieldnames = [
        "source",
        "status",
        "duration_seconds",
        "tokens_used",
        "title",
        "word_count",
        "model",
        "summary_preview",
        "error",
        "timestamp",
    ]

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for result in results:
            writer.writerow({
                "source": result.source,
                "status": "success" if result.success else "failed",
                "duration_seconds": f"{result.duration_seconds:.3f}",
                "tokens_used": result.tokens_used,
                "title": result.article.title if result.article else "",
                "word_count": result.article.word_count if result.article else 0,
                "model": result.summary.model if result.summary else "",
                "summary_preview": _truncate(result.summary.text, 200) if result.summary else "",
                "error": result.error or "",
                "timestamp": result.timestamp.isoformat(),
            })


def write_jsonl(results: List[BatchResult], output_path: str) -> None:
    """Write batch results to a JSON Lines file."""
    path = Path(output_path)
    with open(path, "w", encoding="utf-8") as f:
        for result in results:
            record = {
                "source": result.source,
                "status": "success" if result.success else "failed",
                "duration_seconds": result.duration_seconds,
                "tokens_used": result.tokens_used,
                "timestamp": result.timestamp.isoformat(),
                "article": {
                    "title": result.article.title if result.article else None,
                    "word_count": result.article.word_count if result.article else None,
                } if result.article else None,
                "summary": {
                    "text": result.summary.text if result.summary else None,
                    "model": result.summary.model if result.summary else None,
                    "style": result.summary.style if result.summary else None,
                    "tokens_used": result.summary.tokens_used if result.summary else None,
                } if result.summary else None,
                "error": result.error,
            }
            f.write(json.dumps(record, ensure_ascii=False) + "\n")


def write_output(results: List[BatchResult], output_path: str, fmt: str = "csv") -> None:
    """Write results to an output file in the specified format."""
    fmt = fmt.lower()
    if fmt == "csv":
        write_csv(results, output_path)
    elif fmt in ("jsonl", "json"):
        write_jsonl(results, output_path)
    else:
        raise ValueError(f"Unsupported output format: {fmt!r}. Use 'csv' or 'jsonl'.")
"""Generates batch summary reports in various formats."""
from __future__ import annotations

import csv
import json
import sys
from io import StringIO
from pathlib import Path
from typing import Optional

from .models import BatchReport, BatchResult

try:
    from rich.console import Console
    from rich.table import Table
    from rich import box

    _RICH_AVAILABLE = True
except ImportError:
    _RICH_AVAILABLE = False


# Cost per 1K tokens (approximate defaults, can be overridden)
DEFAULT_COST_PER_1K_TOKENS = 0.002


def _truncate(text: str, max_len: int = 60) -> str:
    """Truncate a string to max_len characters."""
    if len(text) <= max_len:
        return text
    return text[: max_len - 3] + "..."


def format_duration(seconds: float) -> str:
    """Format a duration in seconds to a human-readable string."""
    if seconds < 60:
        return f"{seconds:.1f}s"
    minutes = int(seconds // 60)
    secs = seconds % 60
    return f"{minutes}m {secs:.1f}s"


def print_rich_table(report: BatchReport, console: Optional[object] = None) -> None:
    """Print a Rich table summary of the batch report to stdout."""
    if not _RICH_AVAILABLE:
        print_plain_summary(report)
        return

    if console is None:
        console = Console()

    # Results table
    table = Table(
        title="Batch Processing Results",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold cyan",
        show_lines=True,
    )

    table.add_column("#", style="dim", width=4, justify="right")
    table.add_column("Source", style="white", min_width=30, max_width=60)
    table.add_column("Status", justify="center", width=10)
    table.add_column("Duration", justify="right", width=10)
    table.add_column("Tokens", justify="right", width=8)
    table.add_column("Cost", justify="right", width=10)
    table.add_column("Error", style="red", max_width=40)

    for i, result in enumerate(report.results, start=1):
        status = "[green]✓ OK[/green]" if result.success else "[red]✗ FAIL[/red]"
        tokens_str = str(result.tokens_used) if result.tokens_used else "-"
        cost_str = f"${result.cost_estimate:.4f}" if result.cost_estimate else "-"
        error_str = _truncate(result.error or "", 40)
        duration_str = format_duration(result.duration_seconds)

        table.add_row(
            str(i),
            _truncate(result.source, 58),
            status,
            duration_str,
            tokens_str,
            cost_str,
            error_str,
        )

    console.print(table)

    # Summary panel
    console.print()
    console.print(f"[bold]Batch Summary[/bold]")
    console.print(f"  Total items  : [cyan]{report.total}[/cyan]")
    console.print(
        f"  Successes    : [green]{report.successes}[/green]"
    )
    console.print(
        f"  Failures     : [red]{report.failures}[/red]"
    )
    console.print(
        f"  Success rate : [yellow]{report.success_rate:.1f}%[/yellow]"
    )
    console.print(
        f"  Total time   : [cyan]{format_duration(report.total_duration_seconds)}[/cyan]"
    )
    console.print(f"  Total tokens : [cyan]{report.total_tokens}[/cyan]")
    console.print(f"  Total cost   : [cyan]${report.total_cost:.4f}[/cyan]")


def print_plain_summary(report: BatchReport) -> None:
    """Print a plain-text summary when Rich is not available."""
    print("\n=== Batch Processing Results ===")
    print(f"{'#':<4} {'Source':<60} {'Status':<8} {'Duration':<10} {'Tokens':<8} {'Cost':<10}")
    print("-" * 110)

    for i, result in enumerate(report.results, start=1):
        status = "OK" if result.success else "FAIL"
        tokens_str = str(result.tokens_used) if result.tokens_used else "-"
        cost_str = f"${result.cost_estimate:.4f}" if result.cost_estimate else "-"
        print(
            f"{i:<4} {_truncate(result.source, 58):<60} {status:<8} "
            f"{format_duration(result.duration_seconds):<10} {tokens_str:<8} {cost_str:<10}"
        )

    print("\n=== Summary ===")
    print(f"Total    : {report.total}")
    print(f"Success  : {report.successes}")
    print(f"Failures : {report.failures}")
    print(f"Rate     : {report.success_rate:.1f}%")
    print(f"Duration : {format_duration(report.total_duration_seconds)}")
    print(f"Tokens   : {report.total_tokens}")
    print(f"Cost     : ${report.total_cost:.4f}")


def write_csv(report: BatchReport, output_path: Path) -> None:
    """Write batch results to a CSV file."""
    fieldnames = [
        "index",
        "source",
        "success",
        "duration_seconds",
        "tokens_used",
        "cost_estimate",
        "error",
        "summary_text",
        "article_title",
        "article_word_count",
    ]

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for i, result in enumerate(report.results, start=1):
            row = {
                "index": i,
                "source": result.source,
                "success": result.success,
                "duration_seconds": round(result.duration_seconds, 3),
                "tokens_used": result.tokens_used,
                "cost_estimate": round(result.cost_estimate, 6),
                "error": result.error or "",
                "summary_text": result.summary.text if result.summary else "",
                "article_title": result.article.title if result.article else "",
                "article_word_count": result.article.word_count if result.article else 0,
            }
            writer.writerow(row)


def write_jsonlines(report: BatchReport, output_path: Path) -> None:
    """Write batch results to a JSON Lines file."""
    with open(output_path, "w", encoding="utf-8") as f:
        for i, result in enumerate(report.results, start=1):
            record = {
                "index": i,
                "source": result.source,
                "success": result.success,
                "duration_seconds": round(result.duration_seconds, 3),
                "tokens_used": result.tokens_used,
                "cost_estimate": round(result.cost_estimate, 6),
                "error": result.error,
                "summary": result.summary.text if result.summary else None,
                "article": {
                    "title": result.article.title,
                    "word_count": result.article.word_count,
                    "url": result.article.url,
                }
                if result.article
                else None,
            }
            f.write(json.dumps(record) + "\n")


def write_report(
    report: BatchReport,
    output_path: Optional[str] = None,
    output_format: str = "csv",
    console: Optional[object] = None,
) -> None:
    """
    Display the batch report and optionally write to a file.

    Args:
        report: The BatchReport to render.
        output_path: Optional path for file output.
        output_format: 'csv' or 'jsonl' / 'json'.
        console: Optional Rich Console instance.
    """
    print_rich_table(report, console=console)

    if output_path:
        path = Path(output_path)
        fmt = output_format.lower().strip()

        if fmt in ("jsonl", "json", "jsonlines"):
            write_jsonlines(report, path)
            _info(f"Results written to {path} (JSON Lines)", console)
        else:
            write_csv(report, path)
            _info(f"Results written to {path} (CSV)", console)


def _info(message: str, console: Optional[object] = None) -> None:
    """Print an info message."""
    if _RICH_AVAILABLE and console is not None:
        console.print(f"[dim]{message}[/dim]")
    else:
        print(message)
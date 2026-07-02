"""Batch summary reporting: Rich tables, CSV, and JSON Lines output."""

import csv
import json
import sys
import logging
from pathlib import Path
from typing import List, Optional
from datetime import datetime, timezone

from .models import BatchResult

logger = logging.getLogger(__name__)

# Cost per 1K tokens (approximate defaults — override via config if needed)
DEFAULT_COST_PER_1K_TOKENS = 0.002


def _format_duration(seconds: float) -> str:
    """Format duration in human-readable form."""
    if seconds < 60:
        return f"{seconds:.1f}s"
    minutes = int(seconds // 60)
    secs = seconds % 60
    return f"{minutes}m {secs:.0f}s"


def _truncate(text: str, max_len: int = 60) -> str:
    """Truncate text to max_len characters."""
    if len(text) <= max_len:
        return text
    return text[: max_len - 3] + "..."


def compute_batch_stats(results: List[BatchResult]) -> dict:
    """
    Compute aggregate statistics from a list of BatchResults.

    Returns:
        Dictionary with keys: total, success_count, failure_count,
        total_duration_seconds, total_tokens, total_cost, avg_duration_seconds.
    """
    total = len(results)
    successes = [r for r in results if r.success]
    failures = [r for r in results if not r.success]
    total_tokens = sum(r.tokens_used for r in results)
    total_cost = sum(r.cost_estimate for r in results)
    total_duration = sum(r.duration_seconds for r in results)
    avg_duration = total_duration / total if total > 0 else 0.0

    return {
        "total": total,
        "success_count": len(successes),
        "failure_count": len(failures),
        "total_duration_seconds": total_duration,
        "avg_duration_seconds": avg_duration,
        "total_tokens": total_tokens,
        "total_cost": total_cost,
    }


def print_rich_table(results: List[BatchResult], dry_run: bool = False) -> None:
    """
    Print a Rich-formatted table summarizing batch results.

    Args:
        results: List of BatchResult objects.
        dry_run: Whether this was a dry-run batch.
    """
    try:
        from rich.console import Console
        from rich.table import Table
        from rich import box
        from rich.text import Text

        console = Console()
        stats = compute_batch_stats(results)

        mode_label = "[DRY RUN] " if dry_run else ""
        console.print(
            f"\n[bold cyan]{mode_label}Batch Processing Results[/bold cyan]",
            justify="center",
        )

        table = Table(
            box=box.ROUNDED,
            show_header=True,
            header_style="bold magenta",
            expand=True,
        )

        table.add_column("#", style="dim", width=4, justify="right")
        table.add_column("Source", min_width=30)
        table.add_column("Status", width=10, justify="center")
        table.add_column("Duration", width=10, justify="right")
        table.add_column("Tokens", width=8, justify="right")
        table.add_column("Cost", width=10, justify="right")
        table.add_column("Title / Error", min_width=30)

        # Sort results: successes first, then failures
        sorted_results = sorted(results, key=lambda r: (not r.success, r.source))

        for idx, result in enumerate(sorted_results, start=1):
            status_text = (
                Text("✓ OK", style="green bold")
                if result.success
                else Text("✗ FAIL", style="red bold")
            )

            duration_str = _format_duration(result.duration_seconds)
            tokens_str = str(result.tokens_used) if result.tokens_used else "-"
            cost_str = f"${result.cost_estimate:.4f}" if result.cost_estimate else "-"

            if result.success:
                title_or_error = _truncate(
                    result.article.title if result.article else result.source
                )
                title_cell = Text(title_or_error, style="white")
            else:
                title_cell = Text(_truncate(result.error or "Unknown error"), style="red")

            source_display = _truncate(result.source, 55)

            table.add_row(
                str(idx),
                source_display,
                status_text,
                duration_str,
                tokens_str,
                cost_str,
                title_cell,
            )

        console.print(table)

        # Summary stats footer
        console.print()
        console.print(
            f"[bold]Summary:[/bold] "
            f"[green]{stats['success_count']} succeeded[/green] | "
            f"[red]{stats['failure_count']} failed[/red] | "
            f"[cyan]{stats['total']} total[/cyan]"
        )
        console.print(
            f"[bold]Tokens:[/bold] {stats['total_tokens']:,} total | "
            f"[bold]Est. Cost:[/bold] ${stats['total_cost']:.4f} | "
            f"[bold]Avg Duration:[/bold] {_format_duration(stats['avg_duration_seconds'])}"
        )
        console.print()

    except ImportError:
        # Fallback to plain-text output if Rich is not available
        _print_plain_table(results, dry_run)


def _print_plain_table(results: List[BatchResult], dry_run: bool = False) -> None:
    """Plain-text fallback for environments without Rich."""
    stats = compute_batch_stats(results)
    mode = "[DRY RUN] " if dry_run else ""
    print(f"\n{mode}Batch Processing Results")
    print("=" * 80)
    print(f"{'#':<4} {'Status':<8} {'Duration':<10} {'Tokens':<8} {'Source'}")
    print("-" * 80)

    for idx, result in enumerate(results, start=1):
        status = "OK" if result.success else "FAIL"
        print(
            f"{idx:<4} {status:<8} {_format_duration(result.duration_seconds):<10} "
            f"{result.tokens_used:<8} {_truncate(result.source, 50)}"
        )
        if not result.success:
            print(f"     ERROR: {result.error}")

    print("=" * 80)
    print(
        f"Total: {stats['total']} | "
        f"Success: {stats['success_count']} | "
        f"Failed: {stats['failure_count']}"
    )
    print(
        f"Tokens: {stats['total_tokens']:,} | "
        f"Est. Cost: ${stats['total_cost']:.4f} | "
        f"Avg Duration: {_format_duration(stats['avg_duration_seconds'])}"
    )
    print()


def write_csv(results: List[BatchResult], output_path: str) -> None:
    """
    Write batch results to a CSV file.

    Args:
        results: List of BatchResult objects.
        output_path: Path to write the CSV file.
    """
    fieldnames = [
        "source",
        "status",
        "title",
        "duration_seconds",
        "tokens_used",
        "cost_estimate",
        "error",
        "summary_excerpt",
        "timestamp",
        "dry_run",
    ]

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for result in results:
            summary_text = result.summary_text or ""
            summary_excerpt = summary_text[:200] + "..." if len(summary_text) > 200 else summary_text

            writer.writerow({
                "source": result.source,
                "status": "success" if result.success else "failure",
                "title": result.article.title if result.article else "",
                "duration_seconds": round(result.duration_seconds, 3),
                "tokens_used": result.tokens_used,
                "cost_estimate": round(result.cost_estimate, 6),
                "error": result.error or "",
                "summary_excerpt": summary_excerpt,
                "timestamp": result.timestamp.isoformat(),
                "dry_run": result.dry_run,
            })

    logger.info(f"CSV results written to: {output_path}")


def write_jsonl(results: List[BatchResult], output_path: str) -> None:
    """
    Write batch results to a JSON Lines file.

    Args:
        results: List of BatchResult objects.
        output_path: Path to write the JSONL file.
    """
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "w", encoding="utf-8") as f:
        for result in results:
            record = {
                "source": result.source,
                "status": "success" if result.success else "failure",
                "title": result.article.title if result.article else None,
                "word_count": result.article.word_count if result.article else None,
                "duration_seconds": round(result.duration_seconds, 3),
                "tokens_used": result.tokens_used,
                "cost_estimate": round(result.cost_estimate, 6),
                "error": result.error,
                "summary": result.summary_text,
                "timestamp": result.timestamp.isoformat(),
                "dry_run": result.dry_run,
            }
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    logger.info(f"JSON Lines results written to: {output_path}")


def write_results(results: List[BatchResult], output_path: str, fmt: str = "csv") -> None:
    """
    Write batch results to a file in the specified format.

    Args:
        results: List of BatchResult objects.
        output_path: Destination file path.
        fmt: Output format — "csv" or "jsonl" / "json".
    """
    fmt = fmt.lower().strip()

    if fmt == "csv":
        write_csv(results, output_path)
    elif fmt in ("jsonl", "json", "json-lines"):
        write_jsonl(results, output_path)
    else:
        raise ValueError(f"Unsupported output format: '{fmt}'. Choose 'csv' or 'jsonl'.")
"""Batch report generation: Rich table, CSV, and JSON Lines output."""

from __future__ import annotations

import csv
import json
import time
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.table import Table
from rich import box

from .models import BatchResult, BatchReport

console = Console()

# Very rough cost estimate: $0.002 per 1 000 tokens (GPT-3.5 ballpark)
_COST_PER_1K_TOKENS: float = 0.002


def _estimate_cost(tokens: int) -> float:
    """Return a rough USD cost estimate for the given token count."""
    return tokens / 1000 * _COST_PER_1K_TOKENS


def build_report(results: list[BatchResult], total_duration: float) -> BatchReport:
    """Construct a BatchReport from a list of results."""
    report = BatchReport(results=results, total_duration_seconds=total_duration)
    return report


def print_summary_table(report: BatchReport) -> None:
    """Print a Rich table summarising the batch run to stdout."""

    # ── Per-item table ──────────────────────────────────────────────────────
    item_table = Table(
        title="Batch Processing Results",
        box=box.ROUNDED,
        show_lines=True,
        expand=True,
    )
    item_table.add_column("#", style="dim", width=4, justify="right")
    item_table.add_column("Source", style="cyan", no_wrap=False, ratio=4)
    item_table.add_column("Title", ratio=3)
    item_table.add_column("Status", justify="center", width=10)
    item_table.add_column("Tokens", justify="right", width=8)
    item_table.add_column("Duration", justify="right", width=10)

    for idx, result in enumerate(report.results, start=1):
        if result.succeeded:
            status = "[green]✓ OK[/green]"
            tokens_str = str(result.tokens_used) if result.tokens_used else "—"
        else:
            status = "[red]✗ FAIL[/red]"
            tokens_str = "—"

        duration_str = f"{result.duration_seconds:.2f}s"
        title_str = result.title[:60] if result.title != result.source else "—"
        source_display = result.source if len(result.source) <= 70 else result.source[:67] + "…"

        item_table.add_row(
            str(idx),
            source_display,
            title_str,
            status,
            tokens_str,
            duration_str,
        )

    console.print()
    console.print(item_table)

    # ── Aggregate stats ─────────────────────────────────────────────────────
    stats_table = Table(box=box.SIMPLE, show_header=False, padding=(0, 2))
    stats_table.add_column("Metric", style="bold")
    stats_table.add_column("Value", justify="right")

    stats_table.add_row("Total sources", str(report.total))
    stats_table.add_row(
        "Succeeded",
        f"[green]{report.successes}[/green]",
    )
    stats_table.add_row(
        "Failed",
        f"[red]{report.failures}[/red]" if report.failures else "0",
    )
    stats_table.add_row("Success rate", f"{report.success_rate:.1f}%")
    stats_table.add_row("Total tokens used", str(report.total_tokens))
    stats_table.add_row(
        "Estimated cost",
        f"${_estimate_cost(report.total_tokens):.4f}",
    )
    stats_table.add_row("Wall-clock time", f"{report.total_duration_seconds:.2f}s")

    console.print()
    console.rule("[bold]Aggregate Statistics")
    console.print(stats_table)
    console.print()

    # Print failures detail if any
    failures = [r for r in report.results if not r.succeeded]
    if failures:
        console.rule("[bold red]Failures")
        for result in failures:
            console.print(f"  [red]•[/red] [cyan]{result.source}[/cyan]")
            console.print(f"    [dim]{result.error}[/dim]")
        console.print()


def write_csv(report: BatchReport, output_path: Path) -> None:
    """Write batch results to a CSV file."""
    fieldnames = [
        "source",
        "title",
        "status",
        "error",
        "tokens_used",
        "duration_seconds",
        "summary",
    ]

    with output_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for result in report.results:
            writer.writerow(
                {
                    "source": result.source,
                    "title": result.title if result.article else "",
                    "status": "success" if result.succeeded else "failure",
                    "error": result.error or "",
                    "tokens_used": result.tokens_used,
                    "duration_seconds": f"{result.duration_seconds:.3f}",
                    "summary": (result.summary or "").replace("\n", " "),
                }
            )

    console.print(f"[green]CSV written to:[/green] {output_path}")


def write_jsonl(report: BatchReport, output_path: Path) -> None:
    """Write batch results to a JSON Lines file."""
    with output_path.open("w", encoding="utf-8") as fh:
        for result in report.results:
            record = {
                "source": result.source,
                "title": result.title if result.article else None,
                "status": "success" if result.succeeded else "failure",
                "error": result.error,
                "tokens_used": result.tokens_used,
                "duration_seconds": round(result.duration_seconds, 3),
                "summary": result.summary,
            }
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")

    console.print(f"[green]JSON Lines written to:[/green] {output_path}")


def write_output(report: BatchReport, output_path: Path, fmt: str = "csv") -> None:
    """
    Write the batch report to a file.

    Args:
        report: The BatchReport to serialise.
        output_path: Destination file path.
        fmt: Output format — ``"csv"`` or ``"jsonl"`` / ``"json"``.
    """
    fmt = fmt.lower().strip()
    if fmt in ("jsonl", "json", "json-lines"):
        write_jsonl(report, output_path)
    else:
        write_csv(report, output_path)
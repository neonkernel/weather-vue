"""Batch summary reporting: Rich table, CSV, and JSON Lines output."""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.table import Table
from rich import box

from .models import BatchResult

console = Console()

# Rough cost estimate per 1k tokens (GPT-3.5-turbo default)
DEFAULT_COST_PER_1K_TOKENS = 0.002


def _estimate_cost(tokens: int, cost_per_1k: float = DEFAULT_COST_PER_1K_TOKENS) -> float:
    return (tokens / 1000) * cost_per_1k


def print_batch_summary(results: list[BatchResult], dry_run: bool = False) -> None:
    """Print a Rich table summary of batch results to stdout."""
    successes = [r for r in results if r.success]
    failures = [r for r in results if not r.success]
    total_tokens = sum(r.tokens_used for r in results if r.tokens_used is not None)
    total_cost = sum(r.cost_estimate for r in results if r.cost_estimate is not None)
    if total_cost == 0.0 and total_tokens > 0:
        total_cost = _estimate_cost(total_tokens)
    total_duration = sum(r.duration_seconds for r in results)

    # Results table
    table = Table(
        title="Batch Processing Results",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold cyan",
    )
    table.add_column("#", style="dim", width=4)
    table.add_column("Source", style="white", max_width=50, no_wrap=False)
    table.add_column("Status", width=10)
    table.add_column("Duration", width=10, justify="right")
    table.add_column("Tokens", width=8, justify="right")
    table.add_column("Error", style="red", max_width=40, no_wrap=False)

    for i, result in enumerate(results, start=1):
        status = "[green]✓ OK[/green]" if result.success else "[red]✗ FAIL[/red]"
        duration_str = f"{result.duration_seconds:.2f}s"
        tokens_str = str(result.tokens_used) if result.tokens_used is not None else "-"
        error_str = result.error or ""
        # Truncate source for display
        source_display = result.source
        if len(source_display) > 50:
            source_display = source_display[:47] + "..."
        table.add_row(
            str(i),
            source_display,
            status,
            duration_str,
            tokens_str,
            error_str,
        )

    console.print()
    console.print(table)

    # Aggregate summary panel
    console.print()
    console.rule("[bold cyan]Batch Summary[/bold cyan]")
    console.print(f"  [bold]Total items:[/bold]    {len(results)}")
    console.print(f"  [bold]Successes:[/bold]      [green]{len(successes)}[/green]")
    console.print(f"  [bold]Failures:[/bold]       [red]{len(failures)}[/red]")
    console.print(f"  [bold]Total duration:[/bold] {total_duration:.2f}s")
    if dry_run:
        console.print("  [bold]Mode:[/bold]           [yellow]DRY RUN (LLM not called)[/yellow]")
    if total_tokens > 0:
        console.print(f"  [bold]Total tokens:[/bold]   {total_tokens:,}")
        console.print(f"  [bold]Est. cost:[/bold]      ${total_cost:.4f}")
    console.print()

    if failures:
        console.rule("[bold red]Failed Items[/bold red]")
        for result in failures:
            console.print(f"  [red]✗[/red] {result.source}")
            console.print(f"    [dim]{result.error}[/dim]")
        console.print()


def write_csv(results: list[BatchResult], output_path: Path) -> None:
    """Write batch results to a CSV file."""
    fieldnames = [
        "source",
        "title",
        "status",
        "duration_seconds",
        "tokens_used",
        "cost_estimate",
        "summary",
        "error",
    ]
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for result in results:
            writer.writerow(
                {
                    "source": result.source,
                    "title": result.title,
                    "status": "success" if result.success else "error",
                    "duration_seconds": f"{result.duration_seconds:.3f}",
                    "tokens_used": result.tokens_used or "",
                    "cost_estimate": f"{result.cost_estimate:.6f}" if result.cost_estimate else "",
                    "summary": result.summary.text if result.summary else "",
                    "error": result.error or "",
                }
            )
    console.print(f"[green]Results written to CSV:[/green] {output_path}")


def write_jsonl(results: list[BatchResult], output_path: Path) -> None:
    """Write batch results to a JSON Lines file."""
    with open(output_path, "w", encoding="utf-8") as f:
        for result in results:
            record = {
                "source": result.source,
                "title": result.title,
                "status": "success" if result.success else "error",
                "duration_seconds": result.duration_seconds,
                "tokens_used": result.tokens_used,
                "cost_estimate": result.cost_estimate,
                "summary": result.summary.text if result.summary else None,
                "error": result.error,
            }
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    console.print(f"[green]Results written to JSONL:[/green] {output_path}")


def write_json(results: list[BatchResult], output_path: Path) -> None:
    """Write batch results to a JSON array file."""
    records = []
    for result in results:
        records.append(
            {
                "source": result.source,
                "title": result.title,
                "status": "success" if result.success else "error",
                "duration_seconds": result.duration_seconds,
                "tokens_used": result.tokens_used,
                "cost_estimate": result.cost_estimate,
                "summary": result.summary.text if result.summary else None,
                "error": result.error,
            }
        )
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)
    console.print(f"[green]Results written to JSON:[/green] {output_path}")


def export_results(
    results: list[BatchResult],
    output_path: Path,
    fmt: str = "csv",
) -> None:
    """Export results in the specified format (csv, jsonl, json)."""
    fmt = fmt.lower()
    if fmt == "csv":
        write_csv(results, output_path)
    elif fmt in ("jsonl", "jsonlines"):
        write_jsonl(results, output_path)
    elif fmt == "json":
        write_json(results, output_path)
    else:
        raise ValueError(f"Unsupported export format: {fmt!r}. Use csv, jsonl, or json.")
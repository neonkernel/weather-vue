"""Generate batch summary reports as Rich table, CSV, or JSON Lines."""

import csv
import json
import sys
from pathlib import Path
from typing import List, Optional

from .models import BatchResult

try:
    from rich.console import Console
    from rich.table import Table
    from rich import box
    _RICH_AVAILABLE = True
except ImportError:  # pragma: no cover
    _RICH_AVAILABLE = False


# Cost per 1 000 tokens (rough defaults; override via config if needed)
_COST_PER_1K_TOKENS = 0.002


def _estimate_cost(tokens: int) -> float:
    return round(tokens / 1000 * _COST_PER_1K_TOKENS, 6)


class BatchReporter:
    """
    Produces human-readable and machine-readable summaries of batch runs.

    Parameters
    ----------
    results:
        The list of :class:`BatchResult` objects from a batch run.
    console:
        Optional Rich Console instance (created automatically if not given).
    """

    def __init__(
        self,
        results: List[BatchResult],
        console: Optional["Console"] = None,
    ):
        self.results = results
        self._console = console

    @property
    def console(self) -> "Console":
        if self._console is None:
            if _RICH_AVAILABLE:
                from rich.console import Console as _Console
                self._console = _Console()
            else:
                raise RuntimeError("rich is not installed")
        return self._console

    # ------------------------------------------------------------------
    # Aggregate stats
    # ------------------------------------------------------------------

    @property
    def total(self) -> int:
        return len(self.results)

    @property
    def successes(self) -> int:
        return sum(1 for r in self.results if r.success)

    @property
    def failures(self) -> int:
        return sum(1 for r in self.results if not r.success)

    @property
    def total_tokens(self) -> int:
        return sum(r.tokens_used for r in self.results)

    @property
    def total_cost(self) -> float:
        total = sum(r.cost_estimate for r in self.results)
        if total == 0 and self.total_tokens:
            total = _estimate_cost(self.total_tokens)
        return round(total, 6)

    @property
    def total_duration(self) -> float:
        return round(sum(r.duration_seconds for r in self.results), 2)

    # ------------------------------------------------------------------
    # Rich table
    # ------------------------------------------------------------------

    def print_table(self) -> None:
        """Print a Rich table to stdout."""
        if not _RICH_AVAILABLE:
            self._print_plain()
            return

        table = Table(
            title="Batch Processing Results",
            box=box.ROUNDED,
            show_lines=True,
        )
        table.add_column("#", style="dim", width=4)
        table.add_column("Source", style="cyan", no_wrap=False, max_width=60)
        table.add_column("Status", width=9)
        table.add_column("Tokens", justify="right", width=8)
        table.add_column("Cost ($)", justify="right", width=10)
        table.add_column("Duration (s)", justify="right", width=12)
        table.add_column("Error", style="red", no_wrap=False, max_width=40)

        for idx, result in enumerate(self.results, start=1):
            status = "[green]✓ OK[/green]" if result.success else "[red]✗ FAIL[/red]"
            cost = (
                f"{result.cost_estimate:.6f}"
                if result.cost_estimate
                else f"{_estimate_cost(result.tokens_used):.6f}"
            )
            table.add_row(
                str(idx),
                result.source,
                status,
                str(result.tokens_used) if result.tokens_used else "-",
                cost if result.tokens_used else "-",
                f"{result.duration_seconds:.2f}",
                result.error or "",
            )

        self.console.print(table)
        self.console.print(
            f"\n[bold]Summary:[/bold] {self.total} items | "
            f"[green]{self.successes} succeeded[/green] | "
            f"[red]{self.failures} failed[/red] | "
            f"Total tokens: {self.total_tokens} | "
            f"Est. cost: ${self.total_cost:.6f} | "
            f"Wall time: {self.total_duration}s"
        )

    def _print_plain(self) -> None:
        """Fallback plain-text summary when Rich is not available."""
        print("=" * 60)
        print("Batch Processing Results")
        print("=" * 60)
        for idx, r in enumerate(self.results, start=1):
            status = "OK" if r.success else "FAIL"
            print(
                f"{idx:3}. [{status}] {r.source} "
                f"| {r.duration_seconds:.2f}s "
                f"| tokens={r.tokens_used}"
            )
            if r.error:
                print(f"     Error: {r.error}")
        print("-" * 60)
        print(
            f"Total: {self.total} | Succeeded: {self.successes} | "
            f"Failed: {self.failures} | Tokens: {self.total_tokens} | "
            f"Cost: ${self.total_cost:.6f} | Duration: {self.total_duration}s"
        )

    # ------------------------------------------------------------------
    # CSV export
    # ------------------------------------------------------------------

    def write_csv(self, output_path: str) -> None:
        """Write results to a CSV file."""
        fieldnames = [
            "source",
            "success",
            "tokens_used",
            "cost_estimate",
            "duration_seconds",
            "error",
            "summary_text",
        ]
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for r in self.results:
                writer.writerow(
                    {
                        "source": r.source,
                        "success": r.success,
                        "tokens_used": r.tokens_used,
                        "cost_estimate": r.cost_estimate or _estimate_cost(r.tokens_used),
                        "duration_seconds": round(r.duration_seconds, 4),
                        "error": r.error or "",
                        "summary_text": r.summary.text if r.summary else "",
                    }
                )

    # ------------------------------------------------------------------
    # JSON Lines export
    # ------------------------------------------------------------------

    def write_jsonl(self, output_path: str) -> None:
        """Write results to a JSON Lines file."""
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, "w", encoding="utf-8") as f:
            for r in self.results:
                record = {
                    "source": r.source,
                    "success": r.success,
                    "tokens_used": r.tokens_used,
                    "cost_estimate": r.cost_estimate or _estimate_cost(r.tokens_used),
                    "duration_seconds": round(r.duration_seconds, 4),
                    "error": r.error,
                    "summary_text": r.summary.text if r.summary else None,
                    "article_title": r.article.title if r.article else None,
                    "article_word_count": r.article.word_count if r.article else None,
                }
                f.write(json.dumps(record, ensure_ascii=False) + "\n")

    # ------------------------------------------------------------------
    # Convenience dispatcher
    # ------------------------------------------------------------------

    def write_output(self, output_path: str, fmt: str = "auto") -> None:
        """
        Write results to *output_path* in the given format.

        Parameters
        ----------
        output_path:
            Destination file path.
        fmt:
            One of ``"csv"``, ``"jsonl"``, or ``"auto"`` (inferred from
            the file extension).
        """
        if fmt == "auto":
            ext = Path(output_path).suffix.lower()
            if ext == ".csv":
                fmt = "csv"
            elif ext in (".jsonl", ".json"):
                fmt = "jsonl"
            else:
                fmt = "jsonl"  # safe default

        if fmt == "csv":
            self.write_csv(output_path)
        elif fmt in ("jsonl", "json"):
            self.write_jsonl(output_path)
        else:
            raise ValueError(f"Unknown output format: {fmt!r}")
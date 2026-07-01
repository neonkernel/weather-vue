"""
Rich-based UI helpers: spinner, chunked progress bar, and summary display panel.
"""
from __future__ import annotations

import contextlib
import sys
from typing import Generator, Iterable, Iterator, Optional, TypeVar

T = TypeVar("T")

try:
    from rich.console import Console
    from rich.live import Live
    from rich.panel import Panel
    from rich.progress import (
        BarColumn,
        MofNCompleteColumn,
        Progress,
        SpinnerColumn,
        TaskID,
        TextColumn,
        TimeElapsedColumn,
    )
    from rich.spinner import Spinner
    from rich.text import Text
    RICH_AVAILABLE = True
except ImportError:  # pragma: no cover
    RICH_AVAILABLE = False

from .models import Summary

# ---------------------------------------------------------------------------
# Module-level console (stderr so it doesn't pollute piped stdout)
# ---------------------------------------------------------------------------

_console: Optional["Console"] = None  # type: ignore[name-defined]


def get_console() -> "Console":  # type: ignore[name-defined]
    global _console
    if _console is None:
        if RICH_AVAILABLE:
            _console = Console(stderr=True)
        else:
            raise RuntimeError("rich is not installed. Install it with: pip install rich")
    return _console


# ---------------------------------------------------------------------------
# Quiet-mode flag
# ---------------------------------------------------------------------------

_quiet: bool = False


def set_quiet(value: bool) -> None:
    """Enable or disable all Rich UI output."""
    global _quiet
    _quiet = value


def is_quiet() -> bool:
    return _quiet


# ---------------------------------------------------------------------------
# Spinner context manager
# ---------------------------------------------------------------------------

@contextlib.contextmanager
def spinner(message: str = "Working…") -> Generator[None, None, None]:
    """
    Display a Rich spinner while the body executes.

    In quiet mode the spinner is suppressed entirely.
    """
    if _quiet or not RICH_AVAILABLE:
        yield
        return

    console = get_console()
    with console.status(f"[bold green]{message}[/bold green]", spinner="dots"):
        yield


# ---------------------------------------------------------------------------
# Chunked-summarization progress bar
# ---------------------------------------------------------------------------

@contextlib.contextmanager
def chunk_progress(
    total: int,
    description: str = "Summarising chunks",
) -> Generator["_ChunkProgressUpdater", None, None]:
    """
    Context manager that yields a callable ``advance()`` used to increment a
    Rich progress bar for chunked summarisation.

    Usage::

        with chunk_progress(total=len(chunks)) as advance:
            for chunk in chunks:
                result = llm.complete(chunk)
                advance()
    """
    if _quiet or not RICH_AVAILABLE:
        yield _ChunkProgressUpdater(None, None)
        return

    progress = Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        MofNCompleteColumn(),
        TimeElapsedColumn(),
        console=get_console(),
        transient=True,
    )
    task_id: TaskID = progress.add_task(description, total=total)
    updater = _ChunkProgressUpdater(progress, task_id)

    with progress:
        yield updater


class _ChunkProgressUpdater:
    """Internal helper returned by :func:`chunk_progress`."""

    def __init__(
        self,
        progress: Optional["Progress"],  # type: ignore[name-defined]
        task_id: Optional["TaskID"],  # type: ignore[name-defined]
    ) -> None:
        self._progress = progress
        self._task_id = task_id

    def advance(self, amount: int = 1) -> None:
        if self._progress is not None and self._task_id is not None:
            self._progress.advance(self._task_id, amount)

    def __call__(self, amount: int = 1) -> None:
        self.advance(amount)


# ---------------------------------------------------------------------------
# Summary display panel
# ---------------------------------------------------------------------------

def print_summary(summary: Summary, from_cache: bool = False) -> None:
    """
    Render a :class:`~summarizer.models.Summary` as a Rich panel to the console.

    In quiet mode only the plain text summary is written to stdout.
    """
    if _quiet:
        print(summary.text)
        return

    if not RICH_AVAILABLE:
        # Fallback plain output
        print(f"\n{'='*60}")
        print(f"Title   : {summary.title or 'N/A'}")
        print(f"URL     : {summary.url or 'N/A'}")
        print(f"Provider: {summary.provider} / {summary.model}")
        print(f"Style   : {summary.style}")
        if from_cache:
            print("[from cache]")
        print(f"\n{summary.text}\n")
        return

    console = get_console()

    cache_label = "[dim](from cache)[/dim] " if from_cache else ""
    title_line = Text()
    title_line.append("📰 ", style="bold yellow")
    title_line.append(summary.title or "Summary", style="bold white")

    meta_lines: list[str] = []
    if summary.url:
        meta_lines.append(f"[dim]URL:[/dim] [cyan]{summary.url}[/cyan]")
    meta_lines.append(
        f"[dim]Provider:[/dim] [green]{summary.provider}[/green] "
        f"[dim]Model:[/dim] [green]{summary.model}[/green]"
    )
    meta_lines.append(f"[dim]Style:[/dim] [yellow]{summary.style}[/yellow]  {cache_label}")

    meta_block = "\n".join(meta_lines)
    body = f"{meta_block}\n\n{summary.text}"

    panel = Panel(
        body,
        title=title_line,
        border_style="blue",
        padding=(1, 2),
    )
    console.print(panel)


# ---------------------------------------------------------------------------
# Generic status / error helpers
# ---------------------------------------------------------------------------

def print_status(message: str, style: str = "bold green") -> None:
    """Print a status line (suppressed in quiet mode)."""
    if _quiet:
        return
    if RICH_AVAILABLE:
        get_console().print(f"[{style}]{message}[/{style}]")
    else:
        print(message, file=sys.stderr)


def print_error(message: str) -> None:
    """Always print errors, even in quiet mode (to stderr)."""
    if RICH_AVAILABLE:
        get_console().print(f"[bold red]Error:[/bold red] {message}")
    else:
        print(f"Error: {message}", file=sys.stderr)
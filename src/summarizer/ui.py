"""Rich-based UI helpers for the summarizer CLI."""

from __future__ import annotations

import contextlib
from contextlib import contextmanager
from typing import Generator, Optional

try:
    from rich.console import Console
    from rich.live import Live
    from rich.panel import Panel
    from rich.progress import (
        BarColumn,
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

# Module-level console (can be replaced in tests)
console: "Console" = None  # type: ignore


def _get_console(quiet: bool = False) -> "Console":
    """Return the module console, creating it on first use."""
    global console  # noqa: PLW0603
    if console is None:
        if RICH_AVAILABLE:
            from rich.console import Console as _Console

            console = _Console(stderr=False)
        else:
            console = _FallbackConsole()  # type: ignore
    return console


# ---------------------------------------------------------------------------
# Fallback when rich is not installed
# ---------------------------------------------------------------------------


class _FallbackConsole:
    """Minimal console replacement used when rich is unavailable."""

    def print(self, *args: object, **kwargs: object) -> None:  # noqa: A003
        print(*args)

    def log(self, *args: object, **kwargs: object) -> None:
        print(*args)


# ---------------------------------------------------------------------------
# Context managers
# ---------------------------------------------------------------------------


@contextmanager
def spinner(message: str, quiet: bool = False) -> Generator[None, None, None]:
    """Display a spinner while the wrapped block executes."""
    if quiet or not RICH_AVAILABLE:
        yield
        return

    con = _get_console()
    with con.status(f"[bold cyan]{message}[/bold cyan]", spinner="dots"):
        yield


@contextmanager
def chunk_progress(
    total: int, description: str = "Summarizing", quiet: bool = False
) -> Generator["_ProgressProxy", None, None]:
    """Context manager yielding a progress-bar proxy for chunked work."""
    if quiet or not RICH_AVAILABLE:
        yield _NoopProgress(total)  # type: ignore
        return

    from rich.progress import Progress as _Progress

    progress = _Progress(
        SpinnerColumn(),
        TextColumn("[bold cyan]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TextColumn("({task.completed}/{task.total} chunks)"),
        TimeElapsedColumn(),
    )
    with progress:
        task_id = progress.add_task(description, total=total)
        yield _ProgressProxy(progress, task_id)


class _ProgressProxy:
    """Thin wrapper so callers don't import rich types directly."""

    def __init__(self, progress: "Progress", task_id: "TaskID") -> None:
        self._progress = progress
        self._task_id = task_id

    def advance(self, steps: int = 1) -> None:
        self._progress.advance(self._task_id, steps)

    def update(self, **kwargs: object) -> None:
        self._progress.update(self._task_id, **kwargs)


class _NoopProgress:
    """Silent progress proxy used in quiet mode or when rich is unavailable."""

    def __init__(self, total: int) -> None:
        self.total = total

    def advance(self, steps: int = 1) -> None:
        pass

    def update(self, **kwargs: object) -> None:
        pass


# ---------------------------------------------------------------------------
# Display helpers
# ---------------------------------------------------------------------------


def display_summary(summary: Summary, quiet: bool = False, cached: bool = False) -> None:
    """Render a Summary to the terminal using a rich Panel."""
    if quiet:
        # Minimal output for scripting
        print(summary.summary)
        return

    con = _get_console()

    if not RICH_AVAILABLE:
        con.print(f"\n=== {summary.title or summary.url} ===")
        con.print(summary.summary)
        _print_meta(summary, cached, con)
        return

    from rich.panel import Panel
    from rich.text import Text

    title_text = summary.title or summary.url
    cache_badge = " [bold green][cached][/bold green]" if cached else ""

    body = Text(summary.summary)

    meta_parts = [
        f"Style: {summary.style}",
        f"Provider: {summary.provider} / {summary.model}",
        f"Words: {summary.word_count}",
        f"Chunks: {summary.chunk_count}",
        f"Time: {summary.elapsed_seconds:.1f}s",
    ]
    meta_line = "  •  ".join(meta_parts)

    from rich.console import Group
    from rich.rule import Rule

    renderable = Group(
        body,
        Rule(style="dim"),
        Text(meta_line, style="dim"),
    )

    panel = Panel(
        renderable,
        title=f"[bold]{title_text}[/bold]{cache_badge}",
        border_style="blue",
        padding=(1, 2),
    )
    con.print(panel)


def display_cache_cleared(count: int, quiet: bool = False) -> None:
    if quiet:
        return
    con = _get_console()
    con.print(f"[green]Cache cleared: {count} entries removed.[/green]")


def display_error(message: str, quiet: bool = False) -> None:
    if quiet:
        return
    con = _get_console()
    if RICH_AVAILABLE:
        con.print(f"[bold red]Error:[/bold red] {message}")
    else:
        con.print(f"Error: {message}")


def display_warning(message: str, quiet: bool = False) -> None:
    if quiet:
        return
    con = _get_console()
    if RICH_AVAILABLE:
        con.print(f"[yellow]Warning:[/yellow] {message}")
    else:
        con.print(f"Warning: {message}")


def _print_meta(summary: Summary, cached: bool, con: object) -> None:
    cached_str = " (cached)" if cached else ""
    con.print(  # type: ignore[union-attr]
        f"[{summary.provider}/{summary.model}] "
        f"style={summary.style} words={summary.word_count} "
        f"chunks={summary.chunk_count} time={summary.elapsed_seconds:.1f}s{cached_str}"
    )
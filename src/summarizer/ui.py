"""
Rich-based UI helpers for the summarizer CLI.
Provides spinner context manager, progress bar, and summary display panel.
"""

import contextlib
import logging
import sys
from contextlib import contextmanager
from typing import Generator, Optional

logger = logging.getLogger(__name__)

# Try to import rich; fall back to plain output if unavailable
try:
    from rich.console import Console
    from rich.live import Live
    from rich.panel import Panel
    from rich.progress import (
        BarColumn,
        MofNCompleteColumn,
        Progress,
        SpinnerColumn,
        TaskProgressColumn,
        TextColumn,
        TimeElapsedColumn,
        TimeRemainingColumn,
    )
    from rich.spinner import Spinner
    from rich.status import Status
    from rich.table import Table
    from rich.text import Text
    from rich import box
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

# Module-level console — can be replaced for testing
_console: Optional["Console"] = None


def get_console(quiet: bool = False) -> "Console":
    """Get the shared Rich console, creating it if needed."""
    global _console
    if _console is None:
        if RICH_AVAILABLE:
            _console = Console(stderr=False, quiet=quiet)
        else:
            _console = None  # type: ignore
    return _console  # type: ignore


def set_quiet(quiet: bool) -> None:
    """Configure quiet mode — replaces the global console."""
    global _console
    if RICH_AVAILABLE:
        _console = Console(quiet=quiet)


def _plain_print(msg: str, quiet: bool = False) -> None:
    """Fallback plain print when Rich is unavailable."""
    if not quiet:
        print(msg, file=sys.stderr)


# ---------------------------------------------------------------------------
# Spinner context manager
# ---------------------------------------------------------------------------

@contextmanager
def spinner(message: str, quiet: bool = False) -> Generator[None, None, None]:
    """
    Context manager that shows a spinner with `message` while the body executes.

    Usage::

        with spinner("Fetching article..."):
            content = fetch(url)
    """
    if quiet or not RICH_AVAILABLE:
        if not quiet:
            _plain_print(f"... {message}")
        yield
        return

    console = get_console(quiet=quiet)
    with console.status(f"[bold cyan]{message}[/bold cyan]", spinner="dots") as _status:
        yield


# ---------------------------------------------------------------------------
# Chunked progress bar context manager
# ---------------------------------------------------------------------------

@contextmanager
def chunked_progress(
    total: int,
    description: str = "Summarizing",
    quiet: bool = False,
) -> Generator["ProgressHandle", None, None]:
    """
    Context manager for a progress bar over N chunks.

    Usage::

        with chunked_progress(total=len(chunks), description="Summarizing") as progress:
            for chunk in chunks:
                result = process(chunk)
                progress.advance()
    """
    if quiet or not RICH_AVAILABLE:
        yield _PlainProgressHandle(total, quiet)
        return

    progress = Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]{task.description}"),
        BarColumn(),
        MofNCompleteColumn(),
        TaskProgressColumn(),
        TimeElapsedColumn(),
        TimeRemainingColumn(),
        console=get_console(quiet=quiet),
        transient=True,
    )
    task_id = progress.add_task(description, total=total)

    with progress:
        yield _RichProgressHandle(progress, task_id)


class _RichProgressHandle:
    """Handle returned from `chunked_progress` when Rich is available."""

    def __init__(self, progress: "Progress", task_id) -> None:
        self._progress = progress
        self._task_id = task_id

    def advance(self, amount: int = 1) -> None:
        self._progress.advance(self._task_id, amount)

    def update(self, **kwargs) -> None:
        self._progress.update(self._task_id, **kwargs)


class _PlainProgressHandle:
    """Fallback progress handle when Rich is unavailable or quiet mode is on."""

    def __init__(self, total: int, quiet: bool = False) -> None:
        self._total = total
        self._current = 0
        self._quiet = quiet

    def advance(self, amount: int = 1) -> None:
        self._current += amount
        if not self._quiet:
            pct = int(100 * self._current / max(self._total, 1))
            print(f"  Progress: {self._current}/{self._total} ({pct}%)", file=sys.stderr)

    def update(self, **kwargs) -> None:
        pass


# ---------------------------------------------------------------------------
# Summary display panel
# ---------------------------------------------------------------------------

def display_summary(
    summary,  # summarizer.models.Summary
    quiet: bool = False,
    show_metadata: bool = True,
) -> None:
    """
    Render a Summary object as a rich Panel (or plain text if Rich is unavailable).

    Args:
        summary: A Summary dataclass instance.
        quiet: If True, suppress all output.
        show_metadata: Whether to display metadata (model, provider, tokens, etc.)
    """
    if quiet:
        return

    if not RICH_AVAILABLE:
        _display_plain(summary, show_metadata)
        return

    console = get_console(quiet=quiet)

    # Build content
    content_lines = []

    # Title / URL
    url_display = getattr(summary, "url", None) or getattr(summary, "source_url", None) or ""
    title = getattr(summary, "title", None) or ""
    if title:
        content_lines.append(f"[bold]{title}[/bold]")
        if url_display:
            content_lines.append(f"[dim]{url_display}[/dim]")
    elif url_display:
        content_lines.append(f"[bold blue]{url_display}[/bold blue]")

    if content_lines:
        content_lines.append("")

    # Summary text
    summary_text = getattr(summary, "text", None) or getattr(summary, "summary", None) or str(summary)
    content_lines.append(summary_text)

    # Metadata footer
    if show_metadata:
        meta_parts = []
        provider = getattr(summary, "provider", None)
        model = getattr(summary, "model", None)
        style = getattr(summary, "style", None)
        tokens_used = getattr(summary, "tokens_used", None)
        cached = getattr(summary, "cached", False)

        if provider:
            meta_parts.append(f"provider=[cyan]{provider}[/cyan]")
        if model:
            meta_parts.append(f"model=[cyan]{model}[/cyan]")
        if style:
            meta_parts.append(f"style=[cyan]{style}[/cyan]")
        if tokens_used:
            meta_parts.append(f"tokens=[yellow]{tokens_used:,}[/yellow]")
        if cached:
            meta_parts.append("[green]● cached[/green]")

        if meta_parts:
            content_lines.append("")
            content_lines.append("[dim]" + "  •  ".join(meta_parts) + "[/dim]")

    panel = Panel(
        "\n".join(content_lines),
        title="[bold green]Summary[/bold green]",
        border_style="green",
        padding=(1, 2),
    )
    console.print(panel)


def _display_plain(summary, show_metadata: bool = True) -> None:
    """Plain-text fallback for displaying a summary."""
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    title = getattr(summary, "title", None) or ""
    url_display = getattr(summary, "url", None) or getattr(summary, "source_url", None) or ""
    if title:
        print(f"Title: {title}")
    if url_display:
        print(f"URL: {url_display}")

    summary_text = getattr(summary, "text", None) or getattr(summary, "summary", None) or str(summary)
    print()
    print(summary_text)

    if show_metadata:
        provider = getattr(summary, "provider", None)
        model = getattr(summary, "model", None)
        style = getattr(summary, "style", None)
        tokens_used = getattr(summary, "tokens_used", None)
        cached = getattr(summary, "cached", False)

        meta = []
        if provider:
            meta.append(f"Provider: {provider}")
        if model:
            meta.append(f"Model: {model}")
        if style:
            meta.append(f"Style: {style}")
        if tokens_used:
            meta.append(f"Tokens: {tokens_used:,}")
        if cached:
            meta.append("(from cache)")
        if meta:
            print()
            print("  |  ".join(meta))

    print("=" * 60 + "\n")


# ---------------------------------------------------------------------------
# Error / warning helpers
# ---------------------------------------------------------------------------

def print_error(message: str, quiet: bool = False) -> None:
    """Print an error message to stderr."""
    if quiet:
        return
    if RICH_AVAILABLE:
        console = Console(stderr=True)
        console.print(f"[bold red]Error:[/bold red] {message}")
    else:
        print(f"Error: {message}", file=sys.stderr)


def print_warning(message: str, quiet: bool = False) -> None:
    """Print a warning message to stderr."""
    if quiet:
        return
    if RICH_AVAILABLE:
        console = Console(stderr=True)
        console.print(f"[bold yellow]Warning:[/bold yellow] {message}")
    else:
        print(f"Warning: {message}", file=sys.stderr)


def print_success(message: str, quiet: bool = False) -> None:
    """Print a success message."""
    if quiet:
        return
    if RICH_AVAILABLE:
        console = get_console(quiet=quiet)
        console.print(f"[bold green]✓[/bold green] {message}")
    else:
        print(f"✓ {message}")


def print_info(message: str, quiet: bool = False) -> None:
    """Print an informational message."""
    if quiet:
        return
    if RICH_AVAILABLE:
        console = get_console(quiet=quiet)
        console.print(f"[dim]{message}[/dim]")
    else:
        print(message)
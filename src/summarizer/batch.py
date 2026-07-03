"""Batch processing for multiple articles."""

from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Callable, Optional
from urllib.parse import urlparse

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn

from .models import BatchResult, ArticleContent
from .exceptions import SummarizerError

console = Console()


def _is_url(source: str) -> bool:
    """Check if a string looks like a URL."""
    try:
        result = urlparse(source)
        return result.scheme in ("http", "https")
    except Exception:
        return False


def load_sources(source_path: Path) -> list[str]:
    """
    Load sources from a .txt file of URLs or a directory of .txt/.html files.

    Args:
        source_path: Path to a URL list file or directory of article files.

    Returns:
        List of source identifiers (URLs or file paths as strings).

    Raises:
        ValueError: If the path doesn't exist or no sources are found.
    """
    if not source_path.exists():
        raise ValueError(f"Source path does not exist: {source_path}")

    sources: list[str] = []

    if source_path.is_file():
        # Treat as a list of URLs / file paths, one per line
        lines = source_path.read_text(encoding="utf-8").splitlines()
        for line in lines:
            stripped = line.strip()
            if stripped and not stripped.startswith("#"):
                sources.append(stripped)
    elif source_path.is_dir():
        # Collect all .txt and .html files in the directory
        for ext in ("*.txt", "*.html"):
            for file_path in sorted(source_path.glob(ext)):
                sources.append(str(file_path))
    else:
        raise ValueError(f"Source path must be a file or directory: {source_path}")

    if not sources:
        raise ValueError(f"No sources found in: {source_path}")

    return sources


class BatchProcessor:
    """
    Processes multiple article sources concurrently and collects results.
    """

    def __init__(
        self,
        workers: int = 4,
        dry_run: bool = False,
        process_fn: Optional[Callable[[str], tuple[Optional[ArticleContent], Optional[str]]]] = None,
        summarize_fn: Optional[Callable[[ArticleContent], tuple[str, int]]] = None,
    ):
        """
        Initialize the BatchProcessor.

        Args:
            workers: Number of concurrent worker threads.
            dry_run: If True, fetch/validate sources without calling the LLM.
            process_fn: Function that takes a source string and returns
                        (ArticleContent | None, error_message | None).
            summarize_fn: Function that takes an ArticleContent and returns
                          (summary_text, tokens_used).
        """
        self.workers = workers
        self.dry_run = dry_run
        self.process_fn = process_fn
        self.summarize_fn = summarize_fn

    def _process_single(self, source: str) -> BatchResult:
        """
        Process a single source, returning a BatchResult.
        Errors are isolated — exceptions do not propagate.
        """
        start_time = time.monotonic()

        try:
            # --- Fetch / ingest phase ---
            if self.process_fn is None:
                raise SummarizerError("No process_fn provided to BatchProcessor.")

            article, fetch_error = self.process_fn(source)

            if fetch_error or article is None:
                duration = time.monotonic() - start_time
                return BatchResult(
                    source=source,
                    article=None,
                    summary=None,
                    error=fetch_error or "Failed to load article (unknown reason).",
                    duration_seconds=duration,
                    tokens_used=0,
                )

            # --- Dry-run: skip LLM ---
            if self.dry_run:
                duration = time.monotonic() - start_time
                return BatchResult(
                    source=source,
                    article=article,
                    summary="[dry-run: LLM skipped]",
                    error=None,
                    duration_seconds=duration,
                    tokens_used=0,
                )

            # --- Summarise phase ---
            if self.summarize_fn is None:
                raise SummarizerError("No summarize_fn provided to BatchProcessor.")

            summary_text, tokens = self.summarize_fn(article)
            duration = time.monotonic() - start_time

            return BatchResult(
                source=source,
                article=article,
                summary=summary_text,
                error=None,
                duration_seconds=duration,
                tokens_used=tokens,
            )

        except Exception as exc:  # noqa: BLE001
            duration = time.monotonic() - start_time
            return BatchResult(
                source=source,
                article=None,
                summary=None,
                error=str(exc),
                duration_seconds=duration,
                tokens_used=0,
            )

    def run(self, sources: list[str]) -> list[BatchResult]:
        """
        Run batch processing over a list of sources.

        Args:
            sources: List of source identifiers (URLs or file paths).

        Returns:
            List of BatchResult objects (one per source, in completion order).
        """
        results: list[BatchResult] = []

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console,
            transient=True,
        ) as progress:
            task = progress.add_task(
                f"[cyan]Processing {len(sources)} source(s) with {self.workers} worker(s)…",
                total=len(sources),
            )

            with ThreadPoolExecutor(max_workers=self.workers) as executor:
                future_to_source = {
                    executor.submit(self._process_single, src): src for src in sources
                }

                for future in as_completed(future_to_source):
                    result = future.result()
                    results.append(result)
                    status = "✓" if result.error is None else "✗"
                    progress.advance(task)
                    progress.console.log(
                        f"[{'green' if result.error is None else 'red'}]{status}[/] {result.source[:80]}"
                    )

        return results
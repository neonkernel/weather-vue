"""Batch processing for multiple articles."""
from __future__ import annotations

import os
import time
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Callable, Optional

from .models import Article, BatchReport, BatchResult, Summary

logger = logging.getLogger(__name__)


class BatchProcessor:
    """Processes multiple article sources concurrently."""

    def __init__(
        self,
        summarize_fn: Callable[[str], Summary],
        fetch_fn: Callable[[str], Article],
        workers: int = 4,
        dry_run: bool = False,
        progress_callback: Optional[Callable[[BatchResult], None]] = None,
    ):
        """
        Initialize the BatchProcessor.

        Args:
            summarize_fn: Function that takes a source URL/path and returns a Summary.
            fetch_fn: Function that takes a source URL/path and returns an Article.
            workers: Number of concurrent worker threads.
            dry_run: If True, fetch and validate sources without calling the LLM.
            progress_callback: Optional callback invoked after each item completes.
        """
        self.summarize_fn = summarize_fn
        self.fetch_fn = fetch_fn
        self.workers = workers
        self.dry_run = dry_run
        self.progress_callback = progress_callback

    def load_sources_from_file(self, file_path: Path) -> list[str]:
        """Load URLs or paths from a text file (one per line)."""
        sources = []
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    sources.append(line)
        logger.info(f"Loaded {len(sources)} sources from {file_path}")
        return sources

    def load_sources_from_directory(self, dir_path: Path) -> list[str]:
        """Load all .txt and .html files from a directory."""
        sources = []
        for ext in ("*.txt", "*.html"):
            for file_path in sorted(dir_path.glob(ext)):
                sources.append(str(file_path))
        logger.info(f"Loaded {len(sources)} sources from directory {dir_path}")
        return sources

    def load_sources(self, source: str) -> list[str]:
        """
        Load sources from a file of URLs or a directory of documents.

        Args:
            source: Path to a .txt file of URLs or a directory.

        Returns:
            List of source strings (URLs or file paths).
        """
        path = Path(source)

        if path.is_dir():
            return self.load_sources_from_directory(path)
        elif path.is_file():
            return self.load_sources_from_file(path)
        else:
            raise ValueError(f"Source '{source}' is neither a file nor a directory.")

    def _process_single(self, source: str) -> BatchResult:
        """Process a single source, returning a BatchResult."""
        start = time.monotonic()
        try:
            if self.dry_run:
                article = self.fetch_fn(source)
                duration = time.monotonic() - start
                result = BatchResult(
                    source=source,
                    article=article,
                    summary=None,
                    error=None,
                    duration_seconds=duration,
                    tokens_used=0,
                    cost_estimate=0.0,
                    success=True,
                )
            else:
                summary = self.summarize_fn(source)
                duration = time.monotonic() - start
                result = BatchResult(
                    source=source,
                    article=summary.article,
                    summary=summary,
                    error=None,
                    duration_seconds=duration,
                    tokens_used=summary.tokens_used,
                    cost_estimate=summary.cost_estimate,
                    success=True,
                )
        except Exception as exc:
            duration = time.monotonic() - start
            logger.error(f"Failed to process '{source}': {exc}")
            result = BatchResult(
                source=source,
                article=None,
                summary=None,
                error=str(exc),
                duration_seconds=duration,
                tokens_used=0,
                cost_estimate=0.0,
                success=False,
            )

        if self.progress_callback:
            try:
                self.progress_callback(result)
            except Exception:
                pass  # Don't let callback errors affect processing

        return result

    def run(self, sources: list[str]) -> BatchReport:
        """
        Process all sources concurrently.

        Args:
            sources: List of URLs or file paths to process.

        Returns:
            BatchReport with all results and aggregate statistics.
        """
        report = BatchReport()
        report.start_time = time.time()
        wall_start = time.monotonic()

        results: list[BatchResult] = []

        with ThreadPoolExecutor(max_workers=self.workers) as executor:
            future_to_source = {
                executor.submit(self._process_single, source): source
                for source in sources
            }

            for future in as_completed(future_to_source):
                source = future_to_source[future]
                try:
                    result = future.result()
                except Exception as exc:
                    # This should rarely happen since _process_single catches exceptions,
                    # but guard against it anyway.
                    logger.error(f"Unexpected error for '{source}': {exc}")
                    result = BatchResult(
                        source=source,
                        error=f"Unexpected error: {exc}",
                        success=False,
                    )
                results.append(result)

        report.end_time = time.time()
        report.total_duration_seconds = time.monotonic() - wall_start
        report.results = results

        return report
"""Batch processing module for summarizing multiple articles concurrently."""

from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional
from urllib.parse import urlparse

from .models import Article, BatchResult, Summary
from .logger import get_logger

logger = get_logger(__name__)


def is_url(source: str) -> bool:
    """Check if a string is a URL."""
    try:
        result = urlparse(source.strip())
        return result.scheme in ("http", "https")
    except Exception:
        return False


def load_sources_from_file(path: Path) -> list[str]:
    """Load URLs or file paths from a .txt list file (one per line)."""
    sources = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                sources.append(line)
    return sources


def load_sources_from_directory(directory: Path) -> list[Path]:
    """Load all .txt and .html files from a directory."""
    sources = []
    for ext in ("*.txt", "*.html"):
        sources.extend(sorted(directory.glob(ext)))
    return sources


def collect_sources(input_path: Path) -> list[str]:
    """
    Collect all sources from a file list or directory.
    Returns a list of URLs or file path strings.
    """
    if input_path.is_dir():
        file_paths = load_sources_from_directory(input_path)
        return [str(p) for p in file_paths]
    elif input_path.suffix == ".txt":
        # Could be a URL list or a single text file
        # Try to detect if it's a list of URLs/paths
        sources = load_sources_from_file(input_path)
        if sources:
            return sources
        # Fall back to treating it as a single file
        return [str(input_path)]
    else:
        return [str(input_path)]


@dataclass
class BatchProcessor:
    """Processes multiple articles concurrently using a thread pool."""

    summarize_fn: Callable[[str, bool], tuple[Article, Summary]]
    workers: int = 4
    dry_run: bool = False
    progress_callback: Optional[Callable[[str, str], None]] = None

    def process_source(self, source: str) -> BatchResult:
        """Process a single source and return a BatchResult."""
        start_time = time.monotonic()
        try:
            logger.info(f"Processing source: {source}")
            article, summary = self.summarize_fn(source, self.dry_run)
            duration = time.monotonic() - start_time
            tokens_used = getattr(summary, "tokens_used", None)
            cost_estimate = getattr(summary, "cost_estimate", None)
            result = BatchResult(
                source=source,
                article=article,
                summary=summary,
                error=None,
                duration_seconds=duration,
                tokens_used=tokens_used,
                cost_estimate=cost_estimate,
            )
            logger.info(f"Successfully processed: {source} in {duration:.2f}s")
            if self.progress_callback:
                self.progress_callback(source, "success")
            return result
        except Exception as exc:
            duration = time.monotonic() - start_time
            logger.error(f"Failed to process {source}: {exc}")
            if self.progress_callback:
                self.progress_callback(source, f"error: {exc}")
            return BatchResult(
                source=source,
                article=None,
                summary=None,
                error=str(exc),
                duration_seconds=duration,
                tokens_used=None,
                cost_estimate=None,
            )

    def run(self, sources: list[str]) -> list[BatchResult]:
        """
        Process all sources concurrently and return results.
        Per-item errors are isolated; one failure does not abort the batch.
        """
        results: list[BatchResult] = []
        total = len(sources)
        logger.info(f"Starting batch of {total} sources with {self.workers} workers")

        with ThreadPoolExecutor(max_workers=self.workers) as executor:
            future_to_source = {
                executor.submit(self.process_source, source): source
                for source in sources
            }
            for i, future in enumerate(as_completed(future_to_source), start=1):
                source = future_to_source[future]
                try:
                    result = future.result()
                except Exception as exc:
                    # Shouldn't happen since process_source catches exceptions,
                    # but handle just in case
                    result = BatchResult(
                        source=source,
                        article=None,
                        summary=None,
                        error=f"Unexpected executor error: {exc}",
                        duration_seconds=0.0,
                        tokens_used=None,
                        cost_estimate=None,
                    )
                results.append(result)
                logger.info(f"Completed {i}/{total}: {source}")

        return results
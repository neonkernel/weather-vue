"""Batch processing for multiple articles."""
from __future__ import annotations

import os
import time
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import List, Optional, Callable
from datetime import datetime

from .models import BatchResult, Article, Summary

logger = logging.getLogger(__name__)


def _load_urls_from_file(path: Path) -> List[str]:
    """Load URLs from a text file (one per line), skipping blanks and comments."""
    urls = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                urls.append(line)
    return urls


def _load_sources_from_directory(directory: Path) -> List[str]:
    """Load all .txt and .html file paths from a directory."""
    sources = []
    for ext in ("*.txt", "*.html"):
        for file_path in sorted(directory.glob(ext)):
            sources.append(str(file_path))
    return sources


def _detect_source_type(source: str) -> str:
    """Detect whether a source is a URL or a file path."""
    if source.startswith("http://") or source.startswith("https://"):
        return "url"
    return "file"


class BatchProcessor:
    """
    Processes multiple articles concurrently.

    Supports loading sources from:
    - A .txt file containing URLs (one per line)
    - A directory of .txt or .html files
    - A list of URLs/file paths passed directly
    """

    def __init__(
        self,
        max_workers: int = 4,
        dry_run: bool = False,
        progress_callback: Optional[Callable[[BatchResult, int, int], None]] = None,
    ):
        self.max_workers = max_workers
        self.dry_run = dry_run
        self.progress_callback = progress_callback

    def load_sources(self, input_path: str) -> List[str]:
        """
        Load sources from a file or directory.

        If input_path is a .txt file, read URLs from it.
        If input_path is a directory, load .txt and .html files from it.
        """
        path = Path(input_path)
        if not path.exists():
            raise FileNotFoundError(f"Input path does not exist: {input_path}")

        if path.is_dir():
            sources = _load_sources_from_directory(path)
            if not sources:
                raise ValueError(f"No .txt or .html files found in directory: {input_path}")
            return sources
        elif path.is_file():
            if path.suffix.lower() == ".txt":
                urls = _load_urls_from_file(path)
                if not urls:
                    raise ValueError(f"No URLs found in file: {input_path}")
                return urls
            else:
                raise ValueError(
                    f"Input file must be a .txt file containing URLs, got: {path.suffix}"
                )
        else:
            raise ValueError(f"Input path is neither a file nor a directory: {input_path}")

    def _process_single(
        self,
        source: str,
        fetch_fn: Callable,
        summarize_fn: Optional[Callable] = None,
        **summarize_kwargs,
    ) -> BatchResult:
        """Process a single source, isolating errors."""
        start_time = time.monotonic()
        result = BatchResult(source=source, timestamp=datetime.utcnow())

        try:
            # Fetch the article
            source_type = _detect_source_type(source)
            if source_type == "url":
                article = fetch_fn(source)
            else:
                article = fetch_fn(source)

            result.article = article

            if self.dry_run:
                # Dry-run: validate fetch only, no LLM call
                result.duration_seconds = time.monotonic() - start_time
                logger.debug(f"[dry-run] Fetched '{source}' successfully.")
                return result

            # Summarize the article
            if summarize_fn is None:
                raise ValueError("summarize_fn is required when not in dry-run mode")

            summary = summarize_fn(article, **summarize_kwargs)
            result.summary = summary
            result.tokens_used = summary.tokens_used if summary else 0

        except Exception as exc:
            result.error = str(exc)
            logger.warning(f"Failed to process '{source}': {exc}")
        finally:
            result.duration_seconds = time.monotonic() - start_time

        return result

    def run(
        self,
        sources: List[str],
        fetch_fn: Callable,
        summarize_fn: Optional[Callable] = None,
        **summarize_kwargs,
    ) -> List[BatchResult]:
        """
        Run batch processing over a list of sources.

        Args:
            sources: List of URLs or file paths.
            fetch_fn: Callable that takes a source string and returns an Article.
            summarize_fn: Callable that takes an Article and returns a Summary.
                          Not required in dry-run mode.
            **summarize_kwargs: Additional keyword arguments passed to summarize_fn.

        Returns:
            List of BatchResult objects (one per source).
        """
        if not sources:
            return []

        results: List[BatchResult] = [None] * len(sources)  # type: ignore
        total = len(sources)

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_index = {
                executor.submit(
                    self._process_single,
                    source,
                    fetch_fn,
                    summarize_fn,
                    **summarize_kwargs,
                ): idx
                for idx, source in enumerate(sources)
            }

            completed = 0
            for future in as_completed(future_to_index):
                idx = future_to_index[future]
                completed += 1
                try:
                    result = future.result()
                except Exception as exc:
                    # Catch any unexpected exception from the future itself
                    result = BatchResult(
                        source=sources[idx],
                        error=f"Unexpected error: {exc}",
                        duration_seconds=0.0,
                    )

                results[idx] = result

                if self.progress_callback:
                    self.progress_callback(result, completed, total)

        return results
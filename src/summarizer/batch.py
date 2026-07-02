"""Batch processing for summarizing multiple articles concurrently."""

import os
import time
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import List, Optional, Callable

from .models import BatchResult, Article, Summary
from .exceptions import SummarizerError

logger = logging.getLogger(__name__)


def _load_urls_from_file(file_path: Path) -> List[str]:
    """Load URLs from a text file (one per line)."""
    urls = []
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                urls.append(line)
    return urls


def _load_sources_from_directory(dir_path: Path) -> List[str]:
    """Load file paths from a directory of .txt and .html files."""
    sources = []
    for ext in ("*.txt", "*.html"):
        for p in sorted(dir_path.glob(ext)):
            sources.append(str(p))
    return sources


def _is_url(source: str) -> bool:
    return source.startswith("http://") or source.startswith("https://")


class BatchProcessor:
    """
    Processes multiple articles concurrently using a ThreadPoolExecutor.

    Parameters
    ----------
    ingest_fn:
        Callable that accepts a source string (URL or file path) and returns
        an :class:`Article`.
    summarize_fn:
        Callable that accepts an :class:`Article` and returns a
        :class:`Summary`.
    workers:
        Number of parallel workers (default: 4).
    dry_run:
        If True, fetch and validate sources but skip the LLM call.
    progress_callback:
        Optional callable invoked after each item completes with the
        :class:`BatchResult`.
    """

    def __init__(
        self,
        ingest_fn: Callable[[str], Article],
        summarize_fn: Callable[[Article], Summary],
        workers: int = 4,
        dry_run: bool = False,
        progress_callback: Optional[Callable[[BatchResult], None]] = None,
    ):
        self.ingest_fn = ingest_fn
        self.summarize_fn = summarize_fn
        self.workers = workers
        self.dry_run = dry_run
        self.progress_callback = progress_callback

    def _load_sources(self, input_path: str) -> List[str]:
        """
        Resolve the input to a list of sources.

        Accepts:
        - A .txt file of URLs (one per line)
        - A directory of .txt / .html files
        - A single URL or file path
        """
        path = Path(input_path)

        if path.is_dir():
            return _load_sources_from_directory(path)

        if path.is_file() and path.suffix.lower() == ".txt":
            # Peek at first non-comment line to decide if it's a URL list
            urls = _load_urls_from_file(path)
            if urls and _is_url(urls[0]):
                return urls
            # Otherwise treat each line as a file path
            return [u for u in urls if u]

        # Single source
        return [input_path]

    def _process_one(self, source: str) -> BatchResult:
        """Fetch and (optionally) summarise a single source."""
        start = time.monotonic()
        result = BatchResult(source=source, dry_run=self.dry_run)

        try:
            article = self.ingest_fn(source)
            result.article = article

            if not self.dry_run:
                summary = self.summarize_fn(article)
                result.summary = summary
                result.tokens_used = summary.tokens_used
                result.cost_estimate = summary.cost_estimate

            result.success = True
        except Exception as exc:  # pylint: disable=broad-except
            logger.warning("Failed to process %s: %s", source, exc)
            result.error = str(exc)
            result.success = False
        finally:
            result.duration_seconds = time.monotonic() - start

        return result

    def run(self, input_path: str) -> List[BatchResult]:
        """
        Run the batch job.

        Parameters
        ----------
        input_path:
            A URL list file, directory, single URL, or single file path.

        Returns
        -------
        List[BatchResult]
            One result per source, in completion order.
        """
        sources = self._load_sources(input_path)
        if not sources:
            logger.warning("No sources found in %s", input_path)
            return []

        logger.info(
            "Starting batch: %d sources, %d workers, dry_run=%s",
            len(sources),
            self.workers,
            self.dry_run,
        )

        results: List[BatchResult] = []

        with ThreadPoolExecutor(max_workers=self.workers) as executor:
            future_to_source = {
                executor.submit(self._process_one, src): src for src in sources
            }
            for future in as_completed(future_to_source):
                result = future.result()
                results.append(result)
                if self.progress_callback:
                    self.progress_callback(result)

        return results
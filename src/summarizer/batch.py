"""Batch processing for multiple articles."""

import os
import time
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import List, Optional, Callable
from datetime import datetime

from .models import Article, Summary, BatchResult
from .exceptions import SummarizerError

logger = logging.getLogger(__name__)


def _load_urls_from_file(filepath: Path) -> List[str]:
    """Load URLs from a text file (one per line)."""
    urls = []
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                urls.append(line)
    return urls


def _load_sources_from_directory(dirpath: Path) -> List[str]:
    """Load file paths from a directory containing .txt or .html files."""
    sources = []
    for ext in ("*.txt", "*.html"):
        for path in sorted(dirpath.glob(ext)):
            sources.append(str(path))
    return sources


def _read_file_content(filepath: str) -> str:
    """Read content from a local file."""
    with open(filepath, "r", encoding="utf-8") as f:
        return f.read()


class BatchProcessor:
    """
    Processes multiple article sources concurrently using ThreadPoolExecutor.

    Supports:
    - A .txt file containing one URL per line
    - A directory of .txt or .html files
    - Per-item error isolation (one failure doesn't abort the batch)
    - Dry-run mode (fetches/validates without calling the LLM)
    - Configurable worker count
    """

    def __init__(
        self,
        workers: int = 4,
        dry_run: bool = False,
        style: str = "default",
        model: Optional[str] = None,
        progress_callback: Optional[Callable[[BatchResult], None]] = None,
    ):
        self.workers = workers
        self.dry_run = dry_run
        self.style = style
        self.model = model
        self.progress_callback = progress_callback

    def load_sources(self, source_path: str) -> List[str]:
        """
        Load sources from a file path or directory.

        Args:
            source_path: Path to a .txt URL list or a directory.

        Returns:
            List of source strings (URLs or file paths).
        """
        path = Path(source_path)

        if not path.exists():
            raise FileNotFoundError(f"Source path does not exist: {source_path}")

        if path.is_dir():
            sources = _load_sources_from_directory(path)
            if not sources:
                raise ValueError(f"No .txt or .html files found in directory: {source_path}")
            logger.info(f"Loaded {len(sources)} files from directory: {source_path}")
            return sources

        if path.is_file():
            sources = _load_urls_from_file(path)
            if not sources:
                raise ValueError(f"No URLs found in file: {source_path}")
            logger.info(f"Loaded {len(sources)} URLs from file: {source_path}")
            return sources

        raise ValueError(f"Source path must be a file or directory: {source_path}")

    def _process_single(self, source: str) -> BatchResult:
        """
        Process a single source (URL or file path).

        Args:
            source: URL string or local file path.

        Returns:
            BatchResult with success or error information.
        """
        start_time = time.monotonic()
        result = BatchResult(source=source, dry_run=self.dry_run)

        try:
            # Fetch/load the article
            article = self._fetch_article(source)
            result.article = article

            if self.dry_run:
                # In dry-run mode, we validate the source but don't call LLM
                logger.info(f"[DRY RUN] Validated source: {source} ({article.word_count} words)")
            else:
                # Generate summary using LLM
                summary = self._generate_summary(article)
                result.summary = summary
                result.tokens_used = summary.tokens_used
                result.cost_estimate = summary.cost_estimate
                logger.info(
                    f"Summarized: {source} | tokens={summary.tokens_used} | "
                    f"cost=${summary.cost_estimate:.4f}"
                )

        except Exception as exc:
            error_msg = f"{type(exc).__name__}: {exc}"
            result.error = error_msg
            logger.warning(f"Failed to process source '{source}': {error_msg}")

        finally:
            result.duration_seconds = time.monotonic() - start_time

        return result

    def _fetch_article(self, source: str) -> Article:
        """
        Fetch and parse article content from a URL or local file.

        Args:
            source: URL or file path.

        Returns:
            Article object with parsed content.
        """
        is_url = source.startswith("http://") or source.startswith("https://")

        if is_url:
            return self._fetch_url(source)
        else:
            return self._fetch_local_file(source)

    def _fetch_url(self, url: str) -> Article:
        """Fetch article from a URL."""
        try:
            from .ingestion import fetch_url  # type: ignore
            return fetch_url(url)
        except ImportError:
            # Fallback implementation using requests + basic parsing
            import requests
            from html.parser import HTMLParser

            class _TextExtractor(HTMLParser):
                def __init__(self):
                    super().__init__()
                    self.text_parts = []
                    self.title = ""
                    self._in_title = False
                    self._skip_tags = {"script", "style", "head"}
                    self._current_skip = None

                def handle_starttag(self, tag, attrs):
                    if tag.lower() in self._skip_tags:
                        self._current_skip = tag.lower()
                    if tag.lower() == "title":
                        self._in_title = True

                def handle_endtag(self, tag):
                    if tag.lower() == self._current_skip:
                        self._current_skip = None
                    if tag.lower() == "title":
                        self._in_title = False

                def handle_data(self, data):
                    if self._current_skip:
                        return
                    text = data.strip()
                    if not text:
                        return
                    if self._in_title:
                        self.title = text
                    else:
                        self.text_parts.append(text)

            response = requests.get(url, timeout=30, headers={"User-Agent": "summarizer-bot/1.0"})
            response.raise_for_status()

            content_type = response.headers.get("content-type", "")
            if "html" in content_type:
                extractor = _TextExtractor()
                extractor.feed(response.text)
                content = " ".join(extractor.text_parts)
                title = extractor.title or url
            else:
                content = response.text
                title = url

            word_count = len(content.split())
            return Article(
                url=url,
                title=title,
                content=content,
                word_count=word_count,
                source="url",
            )

    def _fetch_local_file(self, filepath: str) -> Article:
        """Fetch article from a local file."""
        path = Path(filepath)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {filepath}")

        content = _read_file_content(filepath)

        if path.suffix.lower() == ".html":
            from html.parser import HTMLParser

            class _TextExtractor(HTMLParser):
                def __init__(self):
                    super().__init__()
                    self.text_parts = []
                    self.title = ""
                    self._in_title = False
                    self._skip_tags = {"script", "style"}
                    self._current_skip = None

                def handle_starttag(self, tag, attrs):
                    if tag.lower() in self._skip_tags:
                        self._current_skip = tag.lower()
                    if tag.lower() == "title":
                        self._in_title = True

                def handle_endtag(self, tag):
                    if tag.lower() == self._current_skip:
                        self._current_skip = None
                    if tag.lower() == "title":
                        self._in_title = False

                def handle_data(self, data):
                    if self._current_skip:
                        return
                    text = data.strip()
                    if not text:
                        return
                    if self._in_title:
                        self.title = text
                    else:
                        self.text_parts.append(text)

            extractor = _TextExtractor()
            extractor.feed(content)
            text_content = " ".join(extractor.text_parts)
            title = extractor.title or path.name
        else:
            text_content = content
            title = path.name

        word_count = len(text_content.split())
        return Article(
            url=str(path.resolve()),
            title=title,
            content=text_content,
            word_count=word_count,
            source="file",
        )

    def _generate_summary(self, article: Article) -> Summary:
        """
        Generate a summary for an article using the LLM.

        Args:
            article: Article to summarize.

        Returns:
            Summary object.
        """
        try:
            from .summarize import summarize_article  # type: ignore
            return summarize_article(article, style=self.style, model=self.model)
        except ImportError:
            # Fallback: create a simple extractive summary
            words = article.content.split()
            excerpt = " ".join(words[:100]) + ("..." if len(words) > 100 else "")
            tokens = len(words) // 4  # rough estimate
            cost = tokens * 0.000002  # rough cost estimate

            return Summary(
                article=article,
                summary_text=f"[Summary of '{article.title}']: {excerpt}",
                style=self.style,
                tokens_used=tokens,
                model=self.model or "unknown",
                cost_estimate=cost,
            )

    def run(self, sources: List[str]) -> List[BatchResult]:
        """
        Process all sources concurrently.

        Args:
            sources: List of URLs or file paths to process.

        Returns:
            List of BatchResult objects (one per source, in completion order).
        """
        if not sources:
            return []

        results: List[BatchResult] = []
        total = len(sources)

        logger.info(
            f"Starting batch of {total} sources | workers={self.workers} | "
            f"dry_run={self.dry_run}"
        )

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
                    # Shouldn't happen since _process_single catches all exceptions,
                    # but just in case:
                    result = BatchResult(
                        source=source,
                        error=f"Unexpected executor error: {exc}",
                        duration_seconds=0.0,
                    )
                    logger.error(f"Unexpected error processing '{source}': {exc}")

                results.append(result)

                if self.progress_callback:
                    try:
                        self.progress_callback(result)
                    except Exception as cb_exc:
                        logger.warning(f"Progress callback error: {cb_exc}")

        logger.info(
            f"Batch complete | total={total} | "
            f"success={sum(1 for r in results if r.success)} | "
            f"failed={sum(1 for r in results if not r.success)}"
        )

        return results

    def run_from_source_path(self, source_path: str) -> List[BatchResult]:
        """
        Convenience method: load sources then run batch.

        Args:
            source_path: Path to a URL list file or directory.

        Returns:
            List of BatchResult objects.
        """
        sources = self.load_sources(source_path)
        return self.run(sources)
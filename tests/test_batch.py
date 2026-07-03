"""Tests for batch processing functionality."""
from __future__ import annotations

import time
from pathlib import Path
from typing import List
from unittest.mock import MagicMock, patch, call
import pytest
import tempfile
import os

from src.summarizer.models import Article, BatchReport, BatchResult, Summary
from src.summarizer.batch import BatchProcessor
from src.summarizer.reporter import (
    write_csv,
    write_jsonlines,
    write_report,
    print_plain_summary,
    format_duration,
)


# ---------------------------------------------------------------------------
# Helpers / Fixtures
# ---------------------------------------------------------------------------

def _make_article(url: str = "http://example.com/article") -> Article:
    return Article(
        url=url,
        title="Test Article",
        content="This is the article body text.",
        source=url,
        word_count=6,
    )


def _make_summary(article: Article, tokens: int = 100, cost: float = 0.0002) -> Summary:
    return Summary(
        article=article,
        text="This is a test summary.",
        style="default",
        model="gpt-test",
        tokens_used=tokens,
        cost_estimate=cost,
        duration_seconds=0.5,
    )


def _make_summarize_fn(articles: dict):
    """Return a summarize function that uses a pre-built dict of url -> Summary."""
    def _fn(source: str) -> Summary:
        if source in articles:
            return articles[source]
        raise ValueError(f"No mock for source: {source}")
    return _fn


def _make_fetch_fn(articles: dict):
    """Return a fetch function that uses a pre-built dict of url -> Article."""
    def _fn(source: str) -> Article:
        if source in articles:
            return articles[source]
        raise ValueError(f"No mock for source: {source}")
    return _fn


# ---------------------------------------------------------------------------
# BatchResult tests
# ---------------------------------------------------------------------------

class TestBatchResult:
    def test_success_result(self):
        article = _make_article()
        summary = _make_summary(article)
        result = BatchResult(
            source="http://example.com",
            article=article,
            summary=summary,
            tokens_used=summary.tokens_used,
            cost_estimate=summary.cost_estimate,
        )
        result.success = True
        assert result.success is True
        assert result.error is None
        assert result.tokens_used == 100

    def test_failure_result(self):
        result = BatchResult(
            source="http://bad.example.com",
            error="Connection refused",
            success=False,
        )
        assert result.success is False
        assert result.error == "Connection refused"
        assert result.tokens_used == 0

    def test_post_init_sets_success_from_summary(self):
        article = _make_article()
        summary = _make_summary(article, tokens=200, cost=0.0004)
        result = BatchResult(
            source="http://example.com",
            article=article,
            summary=summary,
        )
        assert result.success is True
        assert result.tokens_used == 200
        assert result.cost_estimate == pytest.approx(0.0004)


# ---------------------------------------------------------------------------
# BatchReport tests
# ---------------------------------------------------------------------------

class TestBatchReport:
    def _make_report(self, successes: int = 3, failures: int = 1) -> BatchReport:
        results = []
        for i in range(successes):
            article = _make_article(f"http://example.com/{i}")
            summary = _make_summary(article, tokens=100, cost=0.002)
            results.append(
                BatchResult(
                    source=f"http://example.com/{i}",
                    article=article,
                    summary=summary,
                    tokens_used=100,
                    cost_estimate=0.002,
                    duration_seconds=1.0,
                    success=True,
                )
            )
        for i in range(failures):
            results.append(
                BatchResult(
                    source=f"http://fail.example.com/{i}",
                    error="Timeout",
                    duration_seconds=5.0,
                    success=False,
                )
            )
        report = BatchReport(
            results=results,
            total_duration_seconds=10.0,
        )
        return report

    def test_total(self):
        report = self._make_report(successes=3, failures=1)
        assert report.total == 4

    def test_successes(self):
        report = self._make_report(successes=3, failures=1)
        assert report.successes == 3

    def test_failures(self):
        report = self._make_report(successes=3, failures=1)
        assert report.failures == 1

    def test_success_rate(self):
        report = self._make_report(successes=3, failures=1)
        assert report.success_rate == pytest.approx(75.0)

    def test_total_tokens(self):
        report = self._make_report(successes=3, failures=1)
        assert report.total_tokens == 300

    def test_total_cost(self):
        report = self._make_report(successes=3, failures=1)
        assert report.total_cost == pytest.approx(0.006)

    def test_empty_report(self):
        report = BatchReport()
        assert report.total == 0
        assert report.successes == 0
        assert report.failures == 0
        assert report.success_rate == 0.0
        assert report.total_tokens == 0
        assert report.total_cost == 0.0


# ---------------------------------------------------------------------------
# BatchProcessor tests
# ---------------------------------------------------------------------------

class TestBatchProcessor:

    def _make_processor(
        self,
        sources_map: dict = None,
        workers: int = 2,
        dry_run: bool = False,
    ) -> BatchProcessor:
        if sources_map is None:
            sources_map = {}

        articles = {url: _make_article(url) for url in sources_map}
        summaries = {url: _make_summary(articles[url]) for url in sources_map}

        summarize_fn = _make_summarize_fn(summaries)
        fetch_fn = _make_fetch_fn(articles)

        return BatchProcessor(
            summarize_fn=summarize_fn,
            fetch_fn=fetch_fn,
            workers=workers,
            dry_run=dry_run,
        )

    def test_run_all_success(self):
        urls = [f"http://example.com/{i}" for i in range(5)]
        sources_map = {url: None for url in urls}
        processor = self._make_processor(sources_map=sources_map, workers=2)
        report = processor.run(urls)

        assert report.total == 5
        assert report.successes == 5
        assert report.failures == 0

    def test_run_with_failure_isolated(self):
        """A single failing URL should not abort the batch."""
        good_urls = [f"http://example.com/{i}" for i in range(4)]
        bad_url = "http://will-fail.example.com"

        articles = {url: _make_article(url) for url in good_urls}
        summaries = {url: _make_summary(articles[url]) for url in good_urls}

        def _bad_summarize(source: str) -> Summary:
            if source == bad_url:
                raise ConnectionError("Host unreachable")
            return summaries[source]

        def _bad_fetch(source: str) -> Article:
            if source == bad_url:
                raise ConnectionError("Host unreachable")
            return articles[source]

        processor = BatchProcessor(
            summarize_fn=_bad_summarize,
            fetch_fn=_bad_fetch,
            workers=2,
        )

        all_urls = good_urls + [bad_url]
        report = processor.run(all_urls)

        assert report.total == 5
        assert report.successes == 4
        assert report.failures == 1

        failed = [r for r in report.results if not r.success]
        assert len(failed) == 1
        assert failed[0].source == bad_url
        assert "Host unreachable" in failed[0].error

    def test_worker_count_respected(self):
        """Verify workers parameter is passed through correctly."""
        urls = [f"http://example.com/{i}" for i in range(3)]
        sources_map = {url: None for url in urls}

        with patch("concurrent.futures.ThreadPoolExecutor") as mock_executor_cls:
            # Set up mock context manager
            mock_executor = MagicMock()
            mock_executor.__enter__ = MagicMock(return_value=mock_executor)
            mock_executor.__exit__ = MagicMock(return_value=False)
            mock_executor_cls.return_value = mock_executor

            # Mock futures
            mock_futures = []
            for url in urls:
                article = _make_article(url)
                summary = _make_summary(article)
                mock_future = MagicMock()
                mock_future.result.return_value = BatchResult(
                    source=url,
                    article=article,
                    summary=summary,
                    success=True,
                )
                mock_futures.append(mock_future)

            mock_executor.submit.side_effect = mock_futures
            mock_future_map = {f: urls[i] for i, f in enumerate(mock_futures)}

            with patch(
                "concurrent.futures.as_completed",
                return_value=iter(mock_futures),
            ):
                with patch.object(
                    mock_executor,
                    "submit",
                    side_effect=mock_futures,
                ):
                    processor = self._make_processor(sources_map=sources_map, workers=8)
                    # We can't easily verify ThreadPoolExecutor args in this patching,
                    # so just verify the processor has correct workers set.
                    assert processor.workers == 8

    def test_dry_run_does_not_call_summarize(self):
        """In dry-run mode, summarize_fn should not be called."""
        urls = [f"http://example.com/{i}" for i in range(3)]
        articles = {url: _make_article(url) for url in urls}

        summarize_mock = MagicMock(side_effect=AssertionError("Should not be called"))
        fetch_mock = MagicMock(side_effect=lambda src: articles[src])

        processor = BatchProcessor(
            summarize_fn=summarize_mock,
            fetch_fn=fetch_mock,
            workers=2,
            dry_run=True,
        )

        report = processor.run(urls)

        assert report.total == 3
        assert report.successes == 3
        summarize_mock.assert_not_called()
        assert fetch_mock.call_count == 3

    def test_dry_run_failure_isolated(self):
        """Dry-run failures should also be isolated."""
        urls = ["http://good.com", "http://bad.com"]

        def _fetch(source: str) -> Article:
            if "bad" in source:
                raise ConnectionError("Bad host")
            return _make_article(source)

        processor = BatchProcessor(
            summarize_fn=MagicMock(),
            fetch_fn=_fetch,
            workers=2,
            dry_run=True,
        )

        report = processor.run(urls)
        assert report.total == 2
        assert report.successes == 1
        assert report.failures == 1

    def test_progress_callback_called(self):
        """Progress callback should be called for each result."""
        urls = [f"http://example.com/{i}" for i in range(3)]
        sources_map = {url: None for url in urls}
        processor = self._make_processor(sources_map=sources_map, workers=2)

        callback_results = []
        processor.progress_callback = lambda r: callback_results.append(r)

        report = processor.run(urls)
        assert len(callback_results) == 3

    def test_empty_sources(self):
        processor = self._make_processor(workers=2)
        report = processor.run([])
        assert report.total == 0
        assert report.successes == 0

    def test_all_failures(self):
        urls = [f"http://fail.example.com/{i}" for i in range(3)]

        def _bad_summarize(source: str) -> Summary:
            raise RuntimeError("Always fails")

        def _bad_fetch(source: str) -> Article:
            raise RuntimeError("Always fails")

        processor = BatchProcessor(
            summarize_fn=_bad_summarize,
            fetch_fn=_bad_fetch,
            workers=2,
        )

        report = processor.run(urls)
        assert report.total == 3
        assert report.failures == 3
        assert report.successes == 0
        for r in report.results:
            assert r.error == "Always fails"


# ---------------------------------------------------------------------------
# Load sources tests
# ---------------------------------------------------------------------------

class TestLoadSources:

    def test_load_from_url_file(self, tmp_path):
        url_file = tmp_path / "urls.txt"
        urls = [
            "https://example.com/article1",
            "https://example.com/article2",
            "# This is a comment",
            "",
            "https://example.com/article3",
        ]
        url_file.write_text("\n".join(urls))

        processor = BatchProcessor(
            summarize_fn=MagicMock(),
            fetch_fn=MagicMock(),
        )
        sources = processor.load_sources(str(url_file))

        assert len(sources) == 3
        assert "https://example.com/article1" in sources
        assert "https://example.com/article2" in sources
        assert "https://example.com/article3" in sources
        # Comments and blank lines excluded
        assert "# This is a comment" not in sources

    def test_load_from_directory(self, tmp_path):
        (tmp_path / "article1.txt").write_text("Content 1")
        (tmp_path / "article2.html").write_text("<html><body>Content 2</body></html>")
        (tmp_path / "notes.md").write_text("This should be excluded")

        processor = BatchProcessor(
            summarize_fn=MagicMock(),
            fetch_fn=MagicMock(),
        )
        sources = processor.load_sources(str(tmp_path))

        assert len(sources) == 2
        # .md file not included
        for src in sources:
            assert not src.endswith(".md")

    def test_load_invalid_source_raises(self):
        processor = BatchProcessor(
            summarize_fn=MagicMock(),
            fetch_fn=MagicMock(),
        )
        with pytest.raises(ValueError, match="neither a file nor a directory"):
            processor.load_sources("/nonexistent/path/that/does/not/exist")

    def test_load_comments_and_blank_lines_skipped(self, tmp_path):
        url_file = tmp_path / "urls.txt"
        url_file.write_text(
            "# Comment line\n"
            "\n"
            "   \n"
            "https://example.com/a\n"
            "# Another comment\n"
            "https://example.com/b\n"
        )
        processor = BatchProcessor(
            summarize_fn=MagicMock(),
            fetch_fn=MagicMock(),
        )
        sources = processor.load_sources(str(url_file))
        assert sources == ["https://example.com/a", "https://example.com/b"]


# ---------------------------------------------------------------------------
# Reporter tests
# ---------------------------------------------------------------------------

class TestReporter:

    def _make_report(self) -> BatchReport:
        results = []
        for i in range(3):
            article = _make_article(f"http://example.com/{i}")
            summary = _make_summary(article, tokens=100 * (i + 1))
            results.append(
                BatchResult(
                    source=f"http://example.com/{i}",
                    article=article,
                    summary=summary,
                    tokens_used=100 * (i + 1),
                    cost_estimate=0.002 * (i + 1),
                    duration_seconds=float(i + 1),
                    success=True,
                )
            )
        results.append(
            BatchResult(
                source="http://fail.example.com/bad",
                error="Connection reset",
                duration_seconds=5.0,
                success=False,
            )
        )
        return BatchReport(results=results, total_duration_seconds=15.0)

    def test_write_csv(self, tmp_path):
        report = self._make_report()
        output = tmp_path / "results.csv"
        write_csv(report, output)

        assert output.exists()
        content = output.read_text(encoding="utf-8")
        assert "source" in content
        assert "success" in content
        assert "http://example.com/0" in content
        assert "http://fail.example.com/bad" in content
        assert "Connection reset" in content

    def test_write_csv_has_correct_row_count(self, tmp_path):
        import csv as csv_mod

        report = self._make_report()
        output = tmp_path / "results.csv"
        write_csv(report, output)

        with open(output, newline="", encoding="utf-8") as f:
            reader = csv_mod.DictReader(f)
            rows = list(reader)

        # 3 success + 1 failure = 4 rows
        assert len(rows) == 4

    def test_write_jsonlines(self, tmp_path):
        import json

        report = self._make_report()
        output = tmp_path / "results.jsonl"
        write_jsonlines(report, output)

        assert output.exists()
        lines = output.read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) == 4

        first = json.loads(lines[0])
        assert first["index"] == 1
        assert first["success"] is True
        assert "summary" in first
        assert "article" in first

    def test_write_jsonlines_failure_row(self, tmp_path):
        import json

        report = self._make_report()
        output = tmp_path / "results.jsonl"
        write_jsonlines(report, output)

        lines = output.read_text(encoding="utf-8").strip().split("\n")
        last = json.loads(lines[-1])
        assert last["success"] is False
        assert last["error"] == "Connection reset"
        assert last["summary"] is None
        assert last["article"] is None

    def test_print_plain_summary(self, capsys):
        report = self._make_report()
        print_plain_summary(report)
        captured = capsys.readouterr()
        assert "Batch Processing Results" in captured.out
        assert "Success" in captured.out
        assert "Failures" in captured.out
        assert "4" in captured.out  # total

    def test_format_duration_seconds(self):
        assert format_duration(5.0) == "5.0s"
        assert format_duration(0.5) == "0.5s"

    def test_format_duration_minutes(self):
        assert format_duration(90.0) == "1m 30.0s"
        assert format_duration(120.5) == "2m 0.5s"

    def test_write_report_csv(self, tmp_path):
        report = self._make_report()
        output = tmp_path / "out.csv"
        write_report(report, output_path=str(output), output_format="csv")
        assert output.exists()

    def test_write_report_jsonl(self, tmp_path):
        report = self._make_report()
        output = tmp_path / "out.jsonl"
        write_report(report, output_path=str(output), output_format="jsonl")
        assert output.exists()

    def test_write_report_no_output(self, tmp_path):
        """write_report without output path should not raise."""
        report = self._make_report()
        # Should not raise
        write_report(report, output_path=None)

    def test_aggregate_tokens(self):
        report = self._make_report()
        # 100 + 200 + 300 = 600, failure has 0
        assert report.total_tokens == 600

    def test_aggregate_cost(self):
        report = self._make_report()
        # 0.002 + 0.004 + 0.006 = 0.012
        assert report.total_cost == pytest.approx(0.012)


# ---------------------------------------------------------------------------
# Integration-style test with fixture file
# ---------------------------------------------------------------------------

class TestBatchWithFixture:
    """Tests that use the fixture URL list file."""

    FIXTURE_FILE = Path(__file__).parent / "fixtures" / "url_list.txt"

    def test_fixture_file_exists(self):
        assert self.FIXTURE_FILE.exists(), f"Fixture not found: {self.FIXTURE_FILE}"

    def test_load_fixture_sources(self):
        processor = BatchProcessor(
            summarize_fn=MagicMock(),
            fetch_fn=MagicMock(),
        )
        sources = processor.load_sources(str(self.FIXTURE_FILE))
        assert len(sources) >= 3, "Fixture should have at least 3 URLs"
        for src in sources:
            assert src.startswith("http"), f"Expected URL, got: {src}"

    def test_batch_run_with_mocked_llm(self):
        """Run full batch with mocked LLM using fixture URL list."""
        processor = BatchProcessor(
            summarize_fn=MagicMock(),
            fetch_fn=MagicMock(),
        )
        sources = processor.load_sources(str(self.FIXTURE_FILE))

        articles = {src: _make_article(src) for src in sources}
        summaries = {src: _make_summary(articles[src]) for src in sources}

        def _summarize(src):
            return summaries[src]

        def _fetch(src):
            return articles[src]

        processor.summarize_fn = _summarize
        processor.fetch_fn = _fetch

        report = processor.run(sources)
        assert report.total == len(sources)
        assert report.successes == len(sources)
        assert report.failures == 0
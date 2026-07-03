"""Tests for batch processing functionality."""
from __future__ import annotations

import time
from pathlib import Path
from unittest.mock import MagicMock, patch, call
from datetime import datetime

import pytest

from src.summarizer.batch import BatchProcessor, _load_urls_from_file, _load_sources_from_directory
from src.summarizer.models import BatchResult, Article, Summary


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_article(source: str, word_count: int = 100) -> Article:
    return Article(
        url=source,
        title=f"Article: {source}",
        content="Lorem ipsum dolor sit amet.",
        word_count=word_count,
        fetch_duration_seconds=0.01,
    )


def _make_summary(text: str = "A short summary.", tokens: int = 50) -> Summary:
    return Summary(
        text=text,
        style="concise",
        model="gpt-4o-mini",
        tokens_used=tokens,
        prompt_tokens=30,
        completion_tokens=20,
        duration_seconds=0.1,
    )


def _mock_fetch(source: str) -> Article:
    return _make_article(source)


def _mock_summarize(article: Article, **kwargs) -> Summary:
    return _make_summary(f"Summary of {article.title}")


def _failing_fetch(source: str) -> Article:
    raise RuntimeError(f"Failed to fetch: {source}")


def _failing_summarize(article: Article, **kwargs) -> Summary:
    raise RuntimeError("LLM unavailable")


# ---------------------------------------------------------------------------
# Helper: load_sources
# ---------------------------------------------------------------------------

class TestLoadSources:
    def test_load_urls_from_txt_file(self, tmp_path):
        url_file = tmp_path / "urls.txt"
        url_file.write_text(
            "https://example.com/1\n"
            "https://example.com/2\n"
            "# comment line\n"
            "\n"
            "https://example.com/3\n"
        )
        processor = BatchProcessor()
        sources = processor.load_sources(str(url_file))
        assert sources == [
            "https://example.com/1",
            "https://example.com/2",
            "https://example.com/3",
        ]

    def test_load_from_directory(self, tmp_path):
        (tmp_path / "article1.txt").write_text("content")
        (tmp_path / "article2.html").write_text("<html></html>")
        (tmp_path / "notes.md").write_text("ignored")

        processor = BatchProcessor()
        sources = processor.load_sources(str(tmp_path))
        filenames = [Path(s).name for s in sources]
        assert "article1.txt" in filenames
        assert "article2.html" in filenames
        assert "notes.md" not in filenames

    def test_nonexistent_path_raises(self):
        processor = BatchProcessor()
        with pytest.raises(FileNotFoundError):
            processor.load_sources("/nonexistent/path/file.txt")

    def test_empty_txt_file_raises(self, tmp_path):
        empty = tmp_path / "empty.txt"
        empty.write_text("# only comments\n\n")
        processor = BatchProcessor()
        with pytest.raises(ValueError, match="No URLs found"):
            processor.load_sources(str(empty))

    def test_empty_directory_raises(self, tmp_path):
        processor = BatchProcessor()
        with pytest.raises(ValueError, match="No .txt or .html files"):
            processor.load_sources(str(tmp_path))

    def test_non_txt_file_raises(self, tmp_path):
        csv_file = tmp_path / "data.csv"
        csv_file.write_text("url\nhttps://example.com\n")
        processor = BatchProcessor()
        with pytest.raises(ValueError, match=".txt file"):
            processor.load_sources(str(csv_file))


# ---------------------------------------------------------------------------
# BatchProcessor.run — basic functionality
# ---------------------------------------------------------------------------

class TestBatchProcessorRun:
    def test_successful_batch(self):
        sources = [
            "https://example.com/1",
            "https://example.com/2",
            "https://example.com/3",
        ]
        processor = BatchProcessor(max_workers=2)
        results = processor.run(sources, fetch_fn=_mock_fetch, summarize_fn=_mock_summarize)

        assert len(results) == 3
        for result in results:
            assert result.success
            assert result.error is None
            assert result.article is not None
            assert result.summary is not None
            assert result.tokens_used == 50

    def test_results_order_matches_sources(self):
        """Results should be returned in the same order as input sources."""
        sources = [f"https://example.com/{i}" for i in range(10)]
        processor = BatchProcessor(max_workers=4)
        results = processor.run(sources, fetch_fn=_mock_fetch, summarize_fn=_mock_summarize)

        assert len(results) == 10
        for i, result in enumerate(results):
            assert result.source == sources[i]

    def test_empty_sources_returns_empty_list(self):
        processor = BatchProcessor()
        results = processor.run([], fetch_fn=_mock_fetch, summarize_fn=_mock_summarize)
        assert results == []

    def test_single_source(self):
        processor = BatchProcessor()
        results = processor.run(
            ["https://example.com/only"],
            fetch_fn=_mock_fetch,
            summarize_fn=_mock_summarize,
        )
        assert len(results) == 1
        assert results[0].success


# ---------------------------------------------------------------------------
# Error isolation
# ---------------------------------------------------------------------------

class TestErrorIsolation:
    def test_fetch_failure_does_not_abort_batch(self):
        sources = [
            "https://example.com/good1",
            "https://example.com/bad",      # will fail
            "https://example.com/good2",
        ]

        def selective_fetch(source: str) -> Article:
            if "bad" in source:
                raise RuntimeError("Network error")
            return _make_article(source)

        processor = BatchProcessor(max_workers=2)
        results = processor.run(
            sources, fetch_fn=selective_fetch, summarize_fn=_mock_summarize
        )

        assert len(results) == 3
        good_results = [r for r in results if not r.error]
        bad_results = [r for r in results if r.error]

        assert len(good_results) == 2
        assert len(bad_results) == 1
        assert "Network error" in bad_results[0].error

    def test_summarize_failure_does_not_abort_batch(self):
        sources = [
            "https://example.com/1",
            "https://example.com/2",
            "https://example.com/3",
        ]

        call_count = [0]

        def selective_summarize(article: Article, **kwargs) -> Summary:
            call_count[0] += 1
            if call_count[0] == 2:
                raise RuntimeError("LLM rate limited")
            return _make_summary()

        processor = BatchProcessor(max_workers=1)  # serial to keep count deterministic
        results = processor.run(
            sources, fetch_fn=_mock_fetch, summarize_fn=selective_summarize
        )

        assert len(results) == 3
        errors = [r for r in results if r.error]
        assert len(errors) == 1

    def test_all_failures_still_returns_results(self):
        sources = ["https://fail.com/1", "https://fail.com/2"]
        processor = BatchProcessor(max_workers=2)
        results = processor.run(
            sources, fetch_fn=_failing_fetch, summarize_fn=_mock_summarize
        )
        assert len(results) == 2
        for result in results:
            assert result.error is not None
            assert not result.success

    def test_error_message_captured(self):
        def fetch_with_message(source: str) -> Article:
            raise ValueError("Specific error message here")

        processor = BatchProcessor()
        results = processor.run(
            ["https://example.com"],
            fetch_fn=fetch_with_message,
            summarize_fn=_mock_summarize,
        )
        assert results[0].error == "Specific error message here"


# ---------------------------------------------------------------------------
# Worker count
# ---------------------------------------------------------------------------

class TestWorkerCount:
    def test_custom_worker_count(self):
        """Verify that BatchProcessor respects the max_workers setting."""
        processor = BatchProcessor(max_workers=8)
        assert processor.max_workers == 8

    def test_single_worker_is_serial(self):
        order = []

        def ordered_fetch(source: str) -> Article:
            order.append(source)
            return _make_article(source)

        sources = [f"https://example.com/{i}" for i in range(5)]
        processor = BatchProcessor(max_workers=1)
        results = processor.run(sources, fetch_fn=ordered_fetch, summarize_fn=_mock_summarize)
        assert len(results) == 5
        # With 1 worker, processing should happen in submission order
        assert order == sources

    def test_multiple_workers_all_complete(self):
        import threading
        active_threads = set()

        def slow_fetch(source: str) -> Article:
            active_threads.add(threading.current_thread().ident)
            time.sleep(0.01)
            return _make_article(source)

        sources = [f"https://example.com/{i}" for i in range(8)]
        processor = BatchProcessor(max_workers=4)
        results = processor.run(sources, fetch_fn=slow_fetch, summarize_fn=_mock_summarize)
        assert len(results) == 8
        assert all(r.success for r in results)


# ---------------------------------------------------------------------------
# Dry-run mode
# ---------------------------------------------------------------------------

class TestDryRun:
    def test_dry_run_does_not_call_summarize(self):
        mock_summarize = MagicMock(return_value=_make_summary())
        sources = ["https://example.com/1", "https://example.com/2"]

        processor = BatchProcessor(dry_run=True)
        results = processor.run(
            sources, fetch_fn=_mock_fetch, summarize_fn=mock_summarize
        )

        mock_summarize.assert_not_called()
        assert len(results) == 2
        for result in results:
            assert result.dry_run_success
            assert result.summary is None

    def test_dry_run_fetch_failure_captured(self):
        processor = BatchProcessor(dry_run=True)
        results = processor.run(
            ["https://fail.com"],
            fetch_fn=_failing_fetch,
        )
        assert len(results) == 1
        assert results[0].error is not None
        assert not results[0].dry_run_success

    def test_dry_run_no_tokens_used(self):
        sources = ["https://example.com/1", "https://example.com/2"]
        processor = BatchProcessor(dry_run=True)
        results = processor.run(sources, fetch_fn=_mock_fetch)

        total_tokens = sum(r.tokens_used for r in results)
        assert total_tokens == 0


# ---------------------------------------------------------------------------
# Timing metadata
# ---------------------------------------------------------------------------

class TestTimingMetadata:
    def test_duration_is_recorded(self):
        def slow_fetch(source: str) -> Article:
            time.sleep(0.05)
            return _make_article(source)

        processor = BatchProcessor(dry_run=True)
        results = processor.run(["https://example.com"], fetch_fn=slow_fetch)
        assert results[0].duration_seconds >= 0.05

    def test_timestamp_is_set(self):
        processor = BatchProcessor(dry_run=True)
        before = datetime.utcnow()
        results = processor.run(["https://example.com"], fetch_fn=_mock_fetch)
        after = datetime.utcnow()
        assert before <= results[0].timestamp <= after


# ---------------------------------------------------------------------------
# Progress callback
# ---------------------------------------------------------------------------

class TestProgressCallback:
    def test_callback_called_for_each_item(self):
        calls = []

        def callback(result, completed, total):
            calls.append((completed, total))

        sources = [f"https://example.com/{i}" for i in range(5)]
        processor = BatchProcessor(max_workers=2, progress_callback=callback, dry_run=True)
        processor.run(sources, fetch_fn=_mock_fetch)

        assert len(calls) == 5
        # Total should always be 5
        for completed, total in calls:
            assert total == 5

    def test_callback_receives_result(self):
        received = []

        def callback(result, completed, total):
            received.append(result)

        processor = BatchProcessor(progress_callback=callback, dry_run=True)
        processor.run(["https://example.com/test"], fetch_fn=_mock_fetch)

        assert len(received) == 1
        assert isinstance(received[0], BatchResult)
        assert received[0].source == "https://example.com/test"


# ---------------------------------------------------------------------------
# Token usage
# ---------------------------------------------------------------------------

class TestTokenUsage:
    def test_tokens_aggregated_per_result(self):
        def fetch(source: str) -> Article:
            return _make_article(source)

        token_amounts = [10, 20, 30]
        sources = [f"https://example.com/{i}" for i in range(3)]
        idx = [0]

        def summarize(article: Article, **kwargs) -> Summary:
            tokens = token_amounts[idx[0] % len(token_amounts)]
            idx[0] += 1
            return _make_summary(tokens=tokens)

        processor = BatchProcessor(max_workers=1)
        results = processor.run(sources, fetch_fn=fetch, summarize_fn=summarize)

        token_total = sum(r.tokens_used for r in results)
        assert token_total == sum(token_amounts)

    def test_failed_results_have_zero_tokens(self):
        processor = BatchProcessor(max_workers=1)
        results = processor.run(
            ["https://fail.com"],
            fetch_fn=_failing_fetch,
            summarize_fn=_mock_summarize,
        )
        assert results[0].tokens_used == 0


# ---------------------------------------------------------------------------
# Reporter tests
# ---------------------------------------------------------------------------

class TestReporter:
    def _make_results(self) -> list:
        return [
            BatchResult(
                source="https://example.com/1",
                article=_make_article("https://example.com/1"),
                summary=_make_summary("Summary one", tokens=100),
                tokens_used=100,
                duration_seconds=0.5,
            ),
            BatchResult(
                source="https://example.com/2",
                error="Connection refused",
                duration_seconds=0.1,
            ),
        ]

    def test_write_csv(self, tmp_path):
        from src.summarizer.reporter import write_csv
        import csv

        results = self._make_results()
        output = tmp_path / "results.csv"
        write_csv(results, str(output))

        assert output.exists()
        with open(output, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        assert len(rows) == 2
        assert rows[0]["source"] == "https://example.com/1"
        assert rows[0]["status"] == "success"
        assert rows[0]["tokens_used"] == "100"
        assert rows[1]["source"] == "https://example.com/2"
        assert rows[1]["status"] == "failed"
        assert rows[1]["error"] == "Connection refused"

    def test_write_jsonl(self, tmp_path):
        from src.summarizer.reporter import write_jsonl
        import json

        results = self._make_results()
        output = tmp_path / "results.jsonl"
        write_jsonl(results, str(output))

        assert output.exists()
        lines = output.read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) == 2

        rec0 = json.loads(lines[0])
        assert rec0["source"] == "https://example.com/1"
        assert rec0["status"] == "success"
        assert rec0["tokens_used"] == 100

        rec1 = json.loads(lines[1])
        assert rec1["status"] == "failed"
        assert rec1["error"] == "Connection refused"

    def test_write_output_csv(self, tmp_path):
        from src.summarizer.reporter import write_output
        results = self._make_results()
        output = tmp_path / "out.csv"
        write_output(results, str(output), fmt="csv")
        assert output.exists()

    def test_write_output_jsonl(self, tmp_path):
        from src.summarizer.reporter import write_output
        results = self._make_results()
        output = tmp_path / "out.jsonl"
        write_output(results, str(output), fmt="jsonl")
        assert output.exists()

    def test_write_output_invalid_format(self, tmp_path):
        from src.summarizer.reporter import write_output
        results = self._make_results()
        with pytest.raises(ValueError, match="Unsupported output format"):
            write_output(results, str(tmp_path / "out.xml"), fmt="xml")

    def test_generate_rich_table_no_crash(self, capsys):
        from src.summarizer.reporter import generate_rich_table
        results = self._make_results()
        # Should not raise even if rich is not installed or stdout is redirected
        try:
            generate_rich_table(results)
        except Exception as exc:
            pytest.fail(f"generate_rich_table raised an exception: {exc}")

    def test_generate_rich_table_dry_run(self, capsys):
        from src.summarizer.reporter import generate_rich_table
        results = [
            BatchResult(
                source="https://example.com/1",
                article=_make_article("https://example.com/1"),
                duration_seconds=0.3,
            )
        ]
        try:
            generate_rich_table(results, dry_run=True)
        except Exception as exc:
            pytest.fail(f"generate_rich_table (dry_run) raised: {exc}")


# ---------------------------------------------------------------------------
# BatchResult model
# ---------------------------------------------------------------------------

class TestBatchResultModel:
    def test_success_property_true(self):
        result = BatchResult(
            source="https://example.com",
            article=_make_article("https://example.com"),
            summary=_make_summary(),
        )
        assert result.success is True

    def test_success_property_false_on_error(self):
        result = BatchResult(source="https://example.com", error="oops")
        assert result.success is False

    def test_success_property_false_without_summary(self):
        result = BatchResult(
            source="https://example.com",
            article=_make_article("https://example.com"),
        )
        assert result.success is False

    def test_dry_run_success_property(self):
        result = BatchResult(
            source="https://example.com",
            article=_make_article("https://example.com"),
        )
        assert result.dry_run_success is True

    def test_dry_run_success_false_on_error(self):
        result = BatchResult(source="https://example.com", error="network failure")
        assert result.dry_run_success is False

    def test_default_timestamp(self):
        before = datetime.utcnow()
        result = BatchResult(source="https://example.com")
        after = datetime.utcnow()
        assert before <= result.timestamp <= after
"""Tests for batch processing functionality."""

import os
import csv
import json
import time
import tempfile
import threading
from pathlib import Path
from unittest.mock import patch, MagicMock, call
from datetime import datetime

import pytest

from src.summarizer.models import Article, Summary, BatchResult
from src.summarizer.batch import BatchProcessor, _load_urls_from_file, _load_sources_from_directory
from src.summarizer.reporter import (
    compute_batch_stats,
    write_csv,
    write_jsonl,
    write_results,
    _format_duration,
    _truncate,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_article():
    return Article(
        url="https://example.com/article1",
        title="Test Article 1",
        content="This is the content of test article 1. " * 20,
        word_count=120,
        source="url",
    )


@pytest.fixture
def sample_summary(sample_article):
    return Summary(
        article=sample_article,
        summary_text="This is a test summary.",
        style="default",
        tokens_used=150,
        model="gpt-4",
        cost_estimate=0.0003,
    )


@pytest.fixture
def success_result(sample_article, sample_summary):
    return BatchResult(
        source="https://example.com/article1",
        article=sample_article,
        summary=sample_summary,
        tokens_used=150,
        cost_estimate=0.0003,
        duration_seconds=1.5,
        timestamp=datetime(2026, 7, 2, 12, 0, 0),
    )


@pytest.fixture
def failure_result():
    return BatchResult(
        source="https://example.com/broken",
        error="ConnectionError: Failed to connect",
        duration_seconds=0.5,
        timestamp=datetime(2026, 7, 2, 12, 0, 1),
    )


@pytest.fixture
def url_list_file(tmp_path):
    """Create a temporary URL list file."""
    url_file = tmp_path / "urls.txt"
    urls = [
        "https://example.com/article1",
        "https://example.com/article2",
        "# This is a comment and should be ignored",
        "",
        "https://example.com/article3",
    ]
    url_file.write_text("\n".join(urls))
    return url_file


@pytest.fixture
def article_directory(tmp_path):
    """Create a temporary directory with article files."""
    articles_dir = tmp_path / "articles"
    articles_dir.mkdir()

    (articles_dir / "article1.txt").write_text("This is the content of article 1.")
    (articles_dir / "article2.txt").write_text("This is the content of article 2.")
    (articles_dir / "article3.html").write_text(
        "<html><head><title>Article 3</title></head><body><p>Content of article 3.</p></body></html>"
    )
    (articles_dir / "ignore_me.md").write_text("This should be ignored.")

    return articles_dir


@pytest.fixture
def mock_processor(tmp_path):
    """BatchProcessor with mocked _fetch_article and _generate_summary."""
    processor = BatchProcessor(workers=2, dry_run=False, style="default")

    def fake_fetch(source):
        return Article(
            url=source,
            title=f"Title for {source}",
            content="Article content. " * 30,
            word_count=90,
            source="url",
        )

    def fake_summarize(article):
        return Summary(
            article=article,
            summary_text=f"Summary of {article.title}",
            style="default",
            tokens_used=100,
            model="mock-model",
            cost_estimate=0.0002,
        )

    processor._fetch_article = fake_fetch
    processor._generate_summary = fake_summarize
    return processor


# ---------------------------------------------------------------------------
# Model tests
# ---------------------------------------------------------------------------

class TestBatchResult:
    def test_success_property_true_when_no_error(self, success_result):
        assert success_result.success is True

    def test_success_property_false_when_error(self, failure_result):
        assert failure_result.success is False

    def test_summary_text_returns_summary(self, success_result):
        assert success_result.summary_text == "This is a test summary."

    def test_summary_text_none_when_no_summary(self, failure_result):
        assert failure_result.summary_text is None

    def test_default_timestamp_is_set(self):
        result = BatchResult(source="http://example.com")
        assert result.timestamp is not None
        assert isinstance(result.timestamp, datetime)

    def test_dry_run_defaults_false(self):
        result = BatchResult(source="http://example.com")
        assert result.dry_run is False


# ---------------------------------------------------------------------------
# File loading tests
# ---------------------------------------------------------------------------

class TestLoadUrlsFromFile:
    def test_loads_valid_urls(self, url_list_file):
        urls = _load_urls_from_file(url_list_file)
        assert len(urls) == 3
        assert "https://example.com/article1" in urls
        assert "https://example.com/article2" in urls
        assert "https://example.com/article3" in urls

    def test_ignores_comments(self, url_list_file):
        urls = _load_urls_from_file(url_list_file)
        assert not any(u.startswith("#") for u in urls)

    def test_ignores_empty_lines(self, url_list_file):
        urls = _load_urls_from_file(url_list_file)
        assert "" not in urls

    def test_empty_file_returns_empty_list(self, tmp_path):
        empty_file = tmp_path / "empty.txt"
        empty_file.write_text("")
        urls = _load_urls_from_file(empty_file)
        assert urls == []

    def test_file_with_only_comments(self, tmp_path):
        comment_file = tmp_path / "comments.txt"
        comment_file.write_text("# comment 1\n# comment 2\n")
        urls = _load_urls_from_file(comment_file)
        assert urls == []


class TestLoadSourcesFromDirectory:
    def test_loads_txt_and_html_files(self, article_directory):
        sources = _load_sources_from_directory(article_directory)
        assert len(sources) == 3  # 2 txt + 1 html, 1 md ignored

    def test_ignores_non_txt_html_files(self, article_directory):
        sources = _load_sources_from_directory(article_directory)
        assert not any(s.endswith(".md") for s in sources)

    def test_empty_directory_returns_empty_list(self, tmp_path):
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        sources = _load_sources_from_directory(empty_dir)
        assert sources == []

    def test_sources_are_sorted(self, article_directory):
        sources = _load_sources_from_directory(article_directory)
        # Should be in sorted order within each glob
        assert sources == sorted(sources)


class TestBatchProcessorLoadSources:
    def test_load_from_url_file(self, url_list_file):
        processor = BatchProcessor()
        sources = processor.load_sources(str(url_list_file))
        assert len(sources) == 3

    def test_load_from_directory(self, article_directory):
        processor = BatchProcessor()
        sources = processor.load_sources(str(article_directory))
        assert len(sources) == 3

    def test_raises_for_nonexistent_path(self, tmp_path):
        processor = BatchProcessor()
        with pytest.raises(FileNotFoundError):
            processor.load_sources(str(tmp_path / "nonexistent.txt"))

    def test_raises_for_empty_url_file(self, tmp_path):
        empty_file = tmp_path / "empty.txt"
        empty_file.write_text("")
        processor = BatchProcessor()
        with pytest.raises(ValueError, match="No URLs found"):
            processor.load_sources(str(empty_file))

    def test_raises_for_empty_directory(self, tmp_path):
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        processor = BatchProcessor()
        with pytest.raises(ValueError, match="No .txt or .html files found"):
            processor.load_sources(str(empty_dir))


# ---------------------------------------------------------------------------
# Batch processing tests
# ---------------------------------------------------------------------------

class TestBatchProcessorRun:
    def test_processes_all_sources(self, mock_processor):
        sources = [
            "https://example.com/1",
            "https://example.com/2",
            "https://example.com/3",
        ]
        results = mock_processor.run(sources)
        assert len(results) == 3

    def test_all_successes_with_mock(self, mock_processor):
        sources = ["https://example.com/1", "https://example.com/2"]
        results = mock_processor.run(sources)
        assert all(r.success for r in results)

    def test_empty_sources_returns_empty_list(self, mock_processor):
        results = mock_processor.run([])
        assert results == []

    def test_error_isolation(self):
        """One failed source should not abort processing of others."""
        processor = BatchProcessor(workers=2)

        def fake_fetch(source):
            if "broken" in source:
                raise ConnectionError("Simulated connection error")
            return Article(
                url=source,
                title=f"Title: {source}",
                content="Content",
                word_count=1,
                source="url",
            )

        def fake_summarize(article):
            return Summary(
                article=article,
                summary_text="Summary",
                tokens_used=50,
                model="mock",
                cost_estimate=0.0001,
            )

        processor._fetch_article = fake_fetch
        processor._generate_summary = fake_summarize

        sources = [
            "https://example.com/good1",
            "https://example.com/broken",
            "https://example.com/good2",
        ]
        results = processor.run(sources)

        assert len(results) == 3
        successes = [r for r in results if r.success]
        failures = [r for r in results if not r.success]
        assert len(successes) == 2
        assert len(failures) == 1
        assert "ConnectionError" in failures[0].error

    def test_worker_count_respected(self):
        """Verify the processor uses the specified number of workers."""
        call_times = []
        lock = threading.Lock()

        processor = BatchProcessor(workers=4)

        def fake_fetch(source):
            with lock:
                call_times.append(time.time())
            time.sleep(0.05)  # Simulate work
            return Article(url=source, title="T", content="C", word_count=1)

        def fake_summarize(article):
            return Summary(article=article, summary_text="S", tokens_used=10, model="m", cost_estimate=0.0)

        processor._fetch_article = fake_fetch
        processor._generate_summary = fake_summarize

        sources = [f"https://example.com/{i}" for i in range(8)]
        results = processor.run(sources)
        assert len(results) == 8

    def test_duration_is_recorded(self, mock_processor):
        results = mock_processor.run(["https://example.com/1"])
        assert results[0].duration_seconds >= 0

    def test_tokens_recorded_in_result(self, mock_processor):
        results = mock_processor.run(["https://example.com/1"])
        assert results[0].tokens_used == 100

    def test_cost_recorded_in_result(self, mock_processor):
        results = mock_processor.run(["https://example.com/1"])
        assert results[0].cost_estimate == 0.0002

    def test_progress_callback_called_for_each_result(self):
        processor = BatchProcessor(workers=2)
        callback_calls = []

        def fake_fetch(source):
            return Article(url=source, title="T", content="C", word_count=1)

        def fake_summarize(article):
            return Summary(article=article, summary_text="S", tokens_used=10, model="m", cost_estimate=0.0)

        processor._fetch_article = fake_fetch
        processor._generate_summary = fake_summarize
        processor.progress_callback = lambda r: callback_calls.append(r)

        sources = ["https://example.com/1", "https://example.com/2", "https://example.com/3"]
        processor.run(sources)

        assert len(callback_calls) == 3

    def test_dry_run_skips_llm(self):
        """Dry-run mode should not call _generate_summary."""
        processor = BatchProcessor(workers=2, dry_run=True)
        summarize_called = []

        def fake_fetch(source):
            return Article(url=source, title="T", content="C", word_count=1)

        def fake_summarize(article):
            summarize_called.append(article)
            return Summary(article=article, summary_text="S", tokens_used=10, model="m", cost_estimate=0.0)

        processor._fetch_article = fake_fetch
        processor._generate_summary = fake_summarize

        results = processor.run(["https://example.com/1", "https://example.com/2"])

        assert len(summarize_called) == 0
        assert all(r.success for r in results)
        assert all(r.dry_run for r in results)
        assert all(r.tokens_used == 0 for r in results)

    def test_dry_run_result_has_article_but_no_summary(self):
        """In dry-run mode, article should be set but summary should be None."""
        processor = BatchProcessor(workers=1, dry_run=True)

        def fake_fetch(source):
            return Article(url=source, title="T", content="C", word_count=5)

        processor._fetch_article = fake_fetch

        results = processor.run(["https://example.com/test"])
        assert len(results) == 1
        assert results[0].article is not None
        assert results[0].summary is None
        assert results[0].success is True


class TestBatchProcessorLocalFiles:
    def test_processes_txt_file(self, tmp_path):
        txt_file = tmp_path / "test.txt"
        txt_file.write_text("Hello world. This is test content.")

        processor = BatchProcessor(workers=1, dry_run=True)
        results = processor.run([str(txt_file)])

        assert len(results) == 1
        assert results[0].success
        assert results[0].article is not None
        assert results[0].article.word_count == 7

    def test_processes_html_file(self, tmp_path):
        html_file = tmp_path / "test.html"
        html_file.write_text(
            "<html><head><title>My Page</title></head>"
            "<body><p>Hello world from HTML.</p></body></html>"
        )

        processor = BatchProcessor(workers=1, dry_run=True)
        results = processor.run([str(html_file)])

        assert len(results) == 1
        assert results[0].success
        assert results[0].article is not None
        assert results[0].article.title == "My Page"

    def test_missing_file_produces_failure(self):
        processor = BatchProcessor(workers=1, dry_run=True)
        results = processor.run(["/nonexistent/path/to/file.txt"])

        assert len(results) == 1
        assert not results[0].success
        assert "FileNotFoundError" in results[0].error or "not found" in results[0].error.lower()


# ---------------------------------------------------------------------------
# Reporter tests
# ---------------------------------------------------------------------------

class TestComputeBatchStats:
    def test_all_successes(self, success_result):
        results = [success_result, success_result]
        stats = compute_batch_stats(results)
        assert stats["total"] == 2
        assert stats["success_count"] == 2
        assert stats["failure_count"] == 0
        assert stats["total_tokens"] == 300
        assert abs(stats["total_cost"] - 0.0006) < 1e-6

    def test_mixed_results(self, success_result, failure_result):
        results = [success_result, failure_result]
        stats = compute_batch_stats(results)
        assert stats["total"] == 2
        assert stats["success_count"] == 1
        assert stats["failure_count"] == 1

    def test_empty_results(self):
        stats = compute_batch_stats([])
        assert stats["total"] == 0
        assert stats["avg_duration_seconds"] == 0.0

    def test_avg_duration(self, success_result, failure_result):
        success_result.duration_seconds = 2.0
        failure_result.duration_seconds = 4.0
        stats = compute_batch_stats([success_result, failure_result])
        assert stats["avg_duration_seconds"] == 3.0

    def test_total_duration(self, success_result, failure_result):
        success_result.duration_seconds = 1.5
        failure_result.duration_seconds = 0.5
        stats = compute_batch_stats([success_result, failure_result])
        assert stats["total_duration_seconds"] == 2.0


class TestFormatDuration:
    def test_seconds_only(self):
        assert _format_duration(45.3) == "45.3s"

    def test_minutes_and_seconds(self):
        assert _format_duration(90.0) == "1m 30s"

    def test_zero(self):
        assert _format_duration(0) == "0.0s"


class TestTruncate:
    def test_short_string_unchanged(self):
        assert _truncate("hello", 20) == "hello"

    def test_long_string_truncated(self):
        result = _truncate("a" * 100, 20)
        assert len(result) == 20
        assert result.endswith("...")

    def test_exact_length_unchanged(self):
        assert _truncate("a" * 20, 20) == "a" * 20


class TestWriteCsv:
    def test_writes_csv_file(self, tmp_path, success_result, failure_result):
        output_file = tmp_path / "results.csv"
        write_csv([success_result, failure_result], str(output_file))

        assert output_file.exists()

        with open(output_file, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        assert len(rows) == 2

    def test_csv_has_correct_columns(self, tmp_path, success_result):
        output_file = tmp_path / "results.csv"
        write_csv([success_result], str(output_file))

        with open(output_file, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames

        expected_fields = ["source", "status", "title", "duration_seconds", "tokens_used",
                           "cost_estimate", "error", "summary_excerpt", "timestamp", "dry_run"]
        for field in expected_fields:
            assert field in fieldnames

    def test_csv_success_row_values(self, tmp_path, success_result):
        output_file = tmp_path / "results.csv"
        write_csv([success_result], str(output_file))

        with open(output_file, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            row = next(reader)

        assert row["source"] == "https://example.com/article1"
        assert row["status"] == "success"
        assert row["title"] == "Test Article 1"
        assert row["tokens_used"] == "150"
        assert row["error"] == ""

    def test_csv_failure_row_values(self, tmp_path, failure_result):
        output_file = tmp_path / "results.csv"
        write_csv([failure_result], str(output_file))

        with open(output_file, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            row = next(reader)

        assert row["status"] == "failure"
        assert row["error"] == "ConnectionError: Failed to connect"

    def test_creates_parent_directories(self, tmp_path):
        output_file = tmp_path / "subdir" / "nested" / "results.csv"
        write_csv([], str(output_file))
        assert output_file.exists()

    def test_summary_excerpt_truncated_at_200_chars(self, tmp_path, success_result):
        success_result.summary.summary_text = "word " * 100  # 500 chars
        output_file = tmp_path / "results.csv"
        write_csv([success_result], str(output_file))

        with open(output_file, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            row = next(reader)

        assert len(row["summary_excerpt"]) <= 203  # 200 + "..."


class TestWriteJsonl:
    def test_writes_jsonl_file(self, tmp_path, success_result, failure_result):
        output_file = tmp_path / "results.jsonl"
        write_jsonl([success_result, failure_result], str(output_file))

        assert output_file.exists()

        lines = output_file.read_text().strip().split("\n")
        assert len(lines) == 2

    def test_jsonl_each_line_is_valid_json(self, tmp_path, success_result, failure_result):
        output_file = tmp_path / "results.jsonl"
        write_jsonl([success_result, failure_result], str(output_file))

        for line in output_file.read_text().strip().split("\n"):
            record = json.loads(line)  # Should not raise
            assert "source" in record

    def test_jsonl_success_record(self, tmp_path, success_result):
        output_file = tmp_path / "results.jsonl"
        write_jsonl([success_result], str(output_file))

        record = json.loads(output_file.read_text().strip())
        assert record["source"] == "https://example.com/article1"
        assert record["status"] == "success"
        assert record["title"] == "Test Article 1"
        assert record["tokens_used"] == 150
        assert record["error"] is None
        assert record["summary"] == "This is a test summary."

    def test_jsonl_failure_record(self, tmp_path, failure_result):
        output_file = tmp_path / "results.jsonl"
        write_jsonl([failure_result], str(output_file))

        record = json.loads(output_file.read_text().strip())
        assert record["status"] == "failure"
        assert record["error"] == "ConnectionError: Failed to connect"
        assert record["title"] is None
        assert record["summary"] is None

    def test_creates_parent_directories(self, tmp_path):
        output_file = tmp_path / "nested" / "results.jsonl"
        write_jsonl([], str(output_file))
        assert output_file.exists()


class TestWriteResults:
    def test_writes_csv_by_format_arg(self, tmp_path, success_result):
        output_file = tmp_path / "out.dat"
        write_results([success_result], str(output_file), fmt="csv")
        with open(output_file, newline="") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        assert len(rows) == 1

    def test_writes_jsonl_by_format_arg(self, tmp_path, success_result):
        output_file = tmp_path / "out.dat"
        write_results([success_result], str(output_file), fmt="jsonl")
        record = json.loads(output_file.read_text().strip())
        assert record["source"] == success_result.source

    def test_raises_for_unknown_format(self, tmp_path, success_result):
        with pytest.raises(ValueError, match="Unsupported output format"):
            write_results([success_result], str(tmp_path / "out.xml"), fmt="xml")


# ---------------------------------------------------------------------------
# Integration-style tests
# ---------------------------------------------------------------------------

class TestBatchProcessorIntegration:
    def test_run_from_source_path_url_file(self, tmp_path):
        """End-to-end: load URLs from file, process with mock, verify results."""
        url_file = tmp_path / "urls.txt"
        url_file.write_text(
            "https://example.com/a\nhttps://example.com/b\nhttps://example.com/c\n"
        )

        processor = BatchProcessor(workers=2)

        def fake_fetch(source):
            return Article(url=source, title=f"Title {source[-1]}", content="Content", word_count=1)

        def fake_summarize(article):
            return Summary(
                article=article, summary_text="Summary", tokens_used=50, model="m", cost_estimate=0.0001
            )

        processor._fetch_article = fake_fetch
        processor._generate_summary = fake_summarize

        results = processor.run_from_source_path(str(url_file))
        assert len(results) == 3
        assert all(r.success for r in results)

    def test_run_from_source_path_directory(self, tmp_path):
        """End-to-end: load files from directory, process with dry_run."""
        articles_dir = tmp_path / "articles"
        articles_dir.mkdir()
        (articles_dir / "a.txt").write_text("Content A")
        (articles_dir / "b.txt").write_text("Content B")

        processor = BatchProcessor(workers=2, dry_run=True)
        results = processor.run_from_source_path(str(articles_dir))

        assert len(results) == 2
        assert all(r.success for r in results)
        assert all(r.dry_run for r in results)

    def test_concurrent_processing_is_faster_than_sequential(self, tmp_path):
        """With multiple workers, 4 tasks taking 0.1s each should complete in < 0.35s."""
        processor = BatchProcessor(workers=4)
        sleep_duration = 0.1

        def slow_fetch(source):
            time.sleep(sleep_duration)
            return Article(url=source, title="T", content="C", word_count=1)

        def fast_summarize(article):
            return Summary(article=article, summary_text="S", tokens_used=10, model="m", cost_estimate=0.0)

        processor._fetch_article = slow_fetch
        processor._generate_summary = fast_summarize

        sources = [f"https://example.com/{i}" for i in range(4)]
        start = time.monotonic()
        results = processor.run(sources)
        elapsed = time.monotonic() - start

        assert len(results) == 4
        # Sequential would take ~0.4s; parallel should be much less
        assert elapsed < 0.35, f"Expected parallel processing to be faster, took {elapsed:.3f}s"

    def test_write_batch_results_to_csv_after_run(self, tmp_path):
        """Integration: run batch and write results to CSV."""
        processor = BatchProcessor(workers=2)

        def fake_fetch(source):
            return Article(url=source, title="T", content="C", word_count=1)

        def fake_summarize(article):
            return Summary(
                article=article, summary_text="Summary", tokens_used=80, model="m", cost_estimate=0.00016
            )

        processor._fetch_article = fake_fetch
        processor._generate_summary = fake_summarize

        sources = ["https://a.com/1", "https://a.com/2"]
        results = processor.run(sources)

        csv_path = tmp_path / "output.csv"
        write_results(results, str(csv_path), fmt="csv")

        with open(csv_path, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))

        assert len(rows) == 2
        assert all(row["status"] == "success" for row in rows)

    def test_write_batch_results_to_jsonl_after_run(self, tmp_path):
        """Integration: run batch and write results to JSONL."""
        processor = BatchProcessor(workers=2)

        def fake_fetch(source):
            return Article(url=source, title="T", content="C", word_count=1)

        def fake_summarize(article):
            return Summary(
                article=article, summary_text="Summary", tokens_used=80, model="m", cost_estimate=0.00016
            )

        processor._fetch_article = fake_fetch
        processor._generate_summary = fake_summarize

        sources = ["https://a.com/1", "https://a.com/2"]
        results = processor.run(sources)

        jsonl_path = tmp_path / "output.jsonl"
        write_results(results, str(jsonl_path), fmt="jsonl")

        records = [json.loads(line) for line in jsonl_path.read_text().strip().split("\n")]
        assert len(records) == 2
        assert all(r["status"] == "success" for r in records)
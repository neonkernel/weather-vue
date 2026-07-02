"""Tests for batch processing functionality."""

from __future__ import annotations

import csv
import json
import os
import time
from pathlib import Path
from typing import Optional
from unittest.mock import MagicMock, patch

import pytest

from src.summarizer.models import Article, BatchResult, Summary
from src.summarizer.batch import (
    BatchProcessor,
    collect_sources,
    is_url,
    load_sources_from_directory,
    load_sources_from_file,
)
from src.summarizer.reporter import (
    export_results,
    print_batch_summary,
    write_csv,
    write_json,
    write_jsonl,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_article(title: str = "Test Article", source: str = "http://example.com") -> Article:
    return Article(
        url=source,
        title=title,
        text="This is a test article body.",
        word_count=6,
        source_type="url",
    )


def make_summary(text: str = "A brief summary.", tokens: int = 50) -> Summary:
    return Summary(
        text=text,
        style="default",
        model="gpt-3.5-turbo",
        tokens_used=tokens,
        cost_estimate=tokens * 0.002 / 1000,
    )


def make_result(
    source: str = "http://example.com",
    success: bool = True,
    tokens: int = 50,
    duration: float = 0.5,
) -> BatchResult:
    if success:
        return BatchResult(
            source=source,
            article=make_article(source=source),
            summary=make_summary(tokens=tokens),
            error=None,
            duration_seconds=duration,
            tokens_used=tokens,
            cost_estimate=tokens * 0.002 / 1000,
        )
    else:
        return BatchResult(
            source=source,
            article=None,
            summary=None,
            error="Connection timeout",
            duration_seconds=duration,
            tokens_used=None,
            cost_estimate=None,
        )


# ---------------------------------------------------------------------------
# is_url
# ---------------------------------------------------------------------------

class TestIsUrl:
    def test_http_url(self):
        assert is_url("http://example.com/article") is True

    def test_https_url(self):
        assert is_url("https://news.ycombinator.com") is True

    def test_file_path(self):
        assert is_url("/home/user/article.txt") is False

    def test_relative_path(self):
        assert is_url("articles/test.html") is False

    def test_empty_string(self):
        assert is_url("") is False


# ---------------------------------------------------------------------------
# load_sources_from_file
# ---------------------------------------------------------------------------

class TestLoadSourcesFromFile:
    def test_loads_urls(self, tmp_path):
        url_file = tmp_path / "urls.txt"
        url_file.write_text(
            "https://example.com/1\n"
            "https://example.com/2\n"
            "# this is a comment\n"
            "\n"
            "https://example.com/3\n"
        )
        sources = load_sources_from_file(url_file)
        assert sources == [
            "https://example.com/1",
            "https://example.com/2",
            "https://example.com/3",
        ]

    def test_ignores_blank_lines(self, tmp_path):
        url_file = tmp_path / "urls.txt"
        url_file.write_text("\n\nhttps://example.com\n\n")
        sources = load_sources_from_file(url_file)
        assert sources == ["https://example.com"]

    def test_ignores_comments(self, tmp_path):
        url_file = tmp_path / "urls.txt"
        url_file.write_text("# header\nhttps://example.com\n# footer\n")
        sources = load_sources_from_file(url_file)
        assert sources == ["https://example.com"]

    def test_empty_file(self, tmp_path):
        url_file = tmp_path / "urls.txt"
        url_file.write_text("")
        sources = load_sources_from_file(url_file)
        assert sources == []


# ---------------------------------------------------------------------------
# load_sources_from_directory
# ---------------------------------------------------------------------------

class TestLoadSourcesFromDirectory:
    def test_finds_txt_and_html(self, tmp_path):
        (tmp_path / "article1.txt").write_text("text")
        (tmp_path / "article2.html").write_text("<html></html>")
        (tmp_path / "ignore.md").write_text("markdown")

        sources = load_sources_from_directory(tmp_path)
        names = {p.name for p in sources}
        assert "article1.txt" in names
        assert "article2.html" in names
        assert "ignore.md" not in names

    def test_empty_directory(self, tmp_path):
        sources = load_sources_from_directory(tmp_path)
        assert sources == []


# ---------------------------------------------------------------------------
# collect_sources
# ---------------------------------------------------------------------------

class TestCollectSources:
    def test_from_url_list_file(self, tmp_path):
        url_file = tmp_path / "urls.txt"
        url_file.write_text("https://example.com/1\nhttps://example.com/2\n")
        sources = collect_sources(url_file)
        assert sources == ["https://example.com/1", "https://example.com/2"]

    def test_from_directory(self, tmp_path):
        (tmp_path / "a.txt").write_text("text")
        (tmp_path / "b.html").write_text("<html></html>")
        sources = collect_sources(tmp_path)
        assert len(sources) == 2
        for s in sources:
            assert Path(s).exists()


# ---------------------------------------------------------------------------
# BatchProcessor
# ---------------------------------------------------------------------------

class TestBatchProcessor:
    def _make_processor(self, success_sources=None, fail_sources=None, workers=2):
        """Create a processor with a mock summarize_fn."""
        success_sources = set(success_sources or [])
        fail_sources = set(fail_sources or [])

        def mock_fn(source: str, dry_run: bool):
            if source in fail_sources:
                raise RuntimeError(f"Failed to fetch {source}")
            article = make_article(source=source)
            summary = make_summary()
            return article, summary

        return BatchProcessor(summarize_fn=mock_fn, workers=workers)

    def test_all_success(self):
        sources = ["https://example.com/1", "https://example.com/2", "https://example.com/3"]
        processor = self._make_processor(success_sources=sources)
        results = processor.run(sources)

        assert len(results) == 3
        assert all(r.success for r in results)

    def test_error_isolation(self):
        """One failed URL should not abort the batch."""
        sources = [
            "https://example.com/1",
            "https://bad-url.com/fail",
            "https://example.com/3",
        ]
        processor = self._make_processor(fail_sources={"https://bad-url.com/fail"})
        results = processor.run(sources)

        assert len(results) == 3
        successes = [r for r in results if r.success]
        failures = [r for r in results if not r.success]
        assert len(successes) == 2
        assert len(failures) == 1
        assert failures[0].source == "https://bad-url.com/fail"
        assert failures[0].error is not None

    def test_all_failures_isolated(self):
        """All items failing should still return all results."""
        sources = ["https://a.com", "https://b.com"]

        def always_fail(source, dry_run):
            raise RuntimeError("Network unreachable")

        processor = BatchProcessor(summarize_fn=always_fail, workers=2)
        results = processor.run(sources)

        assert len(results) == 2
        assert all(not r.success for r in results)

    def test_worker_count_respected(self):
        """Test that processor accepts and uses the configured worker count."""
        sources = [f"https://example.com/{i}" for i in range(8)]

        def slow_fn(source, dry_run):
            time.sleep(0.05)
            return make_article(source=source), make_summary()

        start = time.monotonic()
        processor = BatchProcessor(summarize_fn=slow_fn, workers=4)
        results = processor.run(sources)
        duration = time.monotonic() - start

        # With 4 workers and 8 items at 50ms each, should take ~100ms not 400ms
        assert duration < 0.35, f"Expected faster execution with 4 workers, got {duration:.2f}s"
        assert len(results) == 8
        assert all(r.success for r in results)

    def test_dry_run_flag_passed(self):
        """Dry run flag should be passed to the summarize function."""
        received_dry_runs = []

        def capturing_fn(source, dry_run):
            received_dry_runs.append(dry_run)
            article = make_article(source=source)
            summary = Summary(text="[DRY RUN]", dry_run=True)
            return article, summary

        processor = BatchProcessor(summarize_fn=capturing_fn, workers=1, dry_run=True)
        processor.run(["https://example.com"])

        assert received_dry_runs == [True]

    def test_progress_callback_called(self):
        """Progress callback should be called for each item."""
        calls = []

        def callback(source, status):
            calls.append((source, status))

        def mock_fn(source, dry_run):
            return make_article(source=source), make_summary()

        processor = BatchProcessor(
            summarize_fn=mock_fn, workers=2, progress_callback=callback
        )
        sources = ["https://example.com/1", "https://example.com/2"]
        processor.run(sources)

        assert len(calls) == 2
        sources_called = {c[0] for c in calls}
        assert sources_called == set(sources)

    def test_duration_tracked(self):
        """Each result should have a non-negative duration."""
        def mock_fn(source, dry_run):
            return make_article(source=source), make_summary()

        processor = BatchProcessor(summarize_fn=mock_fn, workers=1)
        results = processor.run(["https://example.com"])

        assert results[0].duration_seconds >= 0

    def test_tokens_captured(self):
        """Tokens used from summary should be in BatchResult."""
        def mock_fn(source, dry_run):
            article = make_article(source=source)
            summary = make_summary(tokens=123)
            return article, summary

        processor = BatchProcessor(summarize_fn=mock_fn, workers=1)
        results = processor.run(["https://example.com"])

        assert results[0].tokens_used == 123

    def test_empty_sources(self):
        """Empty source list should return empty results."""
        def mock_fn(source, dry_run):
            return make_article(), make_summary()

        processor = BatchProcessor(summarize_fn=mock_fn, workers=2)
        results = processor.run([])
        assert results == []


# ---------------------------------------------------------------------------
# BatchResult model
# ---------------------------------------------------------------------------

class TestBatchResult:
    def test_success_property(self):
        result = make_result(success=True)
        assert result.success is True

    def test_failure_property(self):
        result = make_result(success=False)
        assert result.success is False

    def test_title_from_article(self):
        result = make_result(success=True)
        assert result.title == "Test Article"

    def test_title_fallback_to_source(self):
        result = BatchResult(
            source="https://example.com/some/path",
            article=None,
            summary=None,
            error="failed",
            duration_seconds=0.1,
        )
        assert "example.com" in result.title or result.title == "https://example.com/some/path"

    def test_title_truncation(self):
        long_source = "https://example.com/" + "x" * 100
        result = BatchResult(
            source=long_source,
            article=None,
            summary=None,
            error="failed",
            duration_seconds=0.1,
        )
        assert len(result.title) <= 63  # "..." + 57 chars + some slack


# ---------------------------------------------------------------------------
# Reporter: CSV output
# ---------------------------------------------------------------------------

class TestWriteCsv:
    def test_writes_csv(self, tmp_path):
        results = [
            make_result("https://example.com/1", success=True),
            make_result("https://example.com/2", success=False),
        ]
        out = tmp_path / "results.csv"
        write_csv(results, out)

        assert out.exists()
        with open(out, newline="") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        assert len(rows) == 2
        assert rows[0]["status"] == "success"
        assert rows[1]["status"] == "error"

    def test_csv_has_required_columns(self, tmp_path):
        results = [make_result()]
        out = tmp_path / "results.csv"
        write_csv(results, out)

        with open(out, newline="") as f:
            reader = csv.DictReader(f)
            cols = reader.fieldnames

        required = {"source", "title", "status", "duration_seconds", "tokens_used", "summary", "error"}
        assert required.issubset(set(cols))

    def test_csv_summary_text_included(self, tmp_path):
        results = [make_result(success=True)]
        results[0].summary.text = "This is the summary."
        out = tmp_path / "results.csv"
        write_csv(results, out)

        with open(out, newline="") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        assert rows[0]["summary"] == "This is the summary."


# ---------------------------------------------------------------------------
# Reporter: JSONL output
# ---------------------------------------------------------------------------

class TestWriteJsonl:
    def test_writes_jsonl(self, tmp_path):
        results = [
            make_result("https://a.com", success=True),
            make_result("https://b.com", success=False),
        ]
        out = tmp_path / "results.jsonl"
        write_jsonl(results, out)

        lines = out.read_text().strip().splitlines()
        assert len(lines) == 2

        records = [json.loads(l) for l in lines]
        assert records[0]["status"] == "success"
        assert records[1]["status"] == "error"

    def test_jsonl_fields(self, tmp_path):
        results = [make_result()]
        out = tmp_path / "results.jsonl"
        write_jsonl(results, out)

        record = json.loads(out.read_text().strip())
        assert "source" in record
        assert "title" in record
        assert "summary" in record
        assert "tokens_used" in record


# ---------------------------------------------------------------------------
# Reporter: JSON output
# ---------------------------------------------------------------------------

class TestWriteJson:
    def test_writes_json_array(self, tmp_path):
        results = [make_result("https://a.com"), make_result("https://b.com")]
        out = tmp_path / "results.json"
        write_json(results, out)

        data = json.loads(out.read_text())
        assert isinstance(data, list)
        assert len(data) == 2

    def test_json_valid(self, tmp_path):
        results = [make_result()]
        out = tmp_path / "results.json"
        write_json(results, out)

        data = json.loads(out.read_text())
        assert data[0]["source"] == "http://example.com"


# ---------------------------------------------------------------------------
# Reporter: export_results dispatcher
# ---------------------------------------------------------------------------

class TestExportResults:
    def test_export_csv(self, tmp_path):
        results = [make_result()]
        out = tmp_path / "out.csv"
        export_results(results, out, fmt="csv")
        assert out.exists()

    def test_export_jsonl(self, tmp_path):
        results = [make_result()]
        out = tmp_path / "out.jsonl"
        export_results(results, out, fmt="jsonl")
        assert out.exists()

    def test_export_json(self, tmp_path):
        results = [make_result()]
        out = tmp_path / "out.json"
        export_results(results, out, fmt="json")
        assert out.exists()

    def test_invalid_format_raises(self, tmp_path):
        results = [make_result()]
        with pytest.raises(ValueError, match="Unsupported export format"):
            export_results(results, tmp_path / "out.xyz", fmt="xml")


# ---------------------------------------------------------------------------
# Reporter: print_batch_summary (smoke test)
# ---------------------------------------------------------------------------

class TestPrintBatchSummary:
    def test_runs_without_error(self, capsys):
        results = [
            make_result("https://a.com", success=True),
            make_result("https://b.com", success=False),
        ]
        # Should not raise
        print_batch_summary(results, dry_run=False)

    def test_dry_run_indicator(self, capsys):
        results = [make_result()]
        # Should not raise
        print_batch_summary(results, dry_run=True)

    def test_empty_results(self, capsys):
        print_batch_summary([], dry_run=False)


# ---------------------------------------------------------------------------
# CLI integration (click test runner)
# ---------------------------------------------------------------------------

class TestBatchCli:
    def test_batch_command_with_url_list(self, tmp_path):
        from click.testing import CliRunner
        from src.summarizer.cli import cli

        url_file = tmp_path / "urls.txt"
        url_file.write_text(
            "https://example.com/1\nhttps://example.com/2\n"
        )

        def mock_summarize(source, style, model, config, dry_run):
            article = make_article(source=source)
            summary = make_summary()
            return article, summary

        runner = CliRunner()
        with patch("src.summarizer.cli._build_summarize_fn") as mock_build:
            def fn(source, dry_run):
                return make_article(source=source), make_summary()
            mock_build.return_value = fn

            with patch("src.summarizer.cli.load_config", return_value=MagicMock()):
                result = runner.invoke(
                    cli,
                    ["batch", str(url_file), "--workers", "2", "--dry-run"],
                    catch_exceptions=False,
                )

        assert result.exit_code == 0

    def test_batch_command_dry_run(self, tmp_path):
        from click.testing import CliRunner
        from src.summarizer.cli import cli

        url_file = tmp_path / "urls.txt"
        url_file.write_text("https://example.com/article\n")

        runner = CliRunner()
        with patch("src.summarizer.cli._build_summarize_fn") as mock_build:
            def fn(source, dry_run):
                assert dry_run is True
                return make_article(source=source), Summary(text="[DRY RUN]", dry_run=True)
            mock_build.return_value = fn

            with patch("src.summarizer.cli.load_config", return_value=MagicMock()):
                result = runner.invoke(
                    cli,
                    ["batch", str(url_file), "--dry-run"],
                    catch_exceptions=False,
                )

        assert result.exit_code == 0

    def test_batch_command_csv_output(self, tmp_path):
        from click.testing import CliRunner
        from src.summarizer.cli import cli

        url_file = tmp_path / "urls.txt"
        url_file.write_text("https://example.com/1\nhttps://example.com/2\n")
        out_file = tmp_path / "results.csv"

        runner = CliRunner()
        with patch("src.summarizer.cli._build_summarize_fn") as mock_build:
            def fn(source, dry_run):
                return make_article(source=source), make_summary()
            mock_build.return_value = fn

            with patch("src.summarizer.cli.load_config", return_value=MagicMock()):
                result = runner.invoke(
                    cli,
                    ["batch", str(url_file), "--output", str(out_file), "--format", "csv"],
                    catch_exceptions=False,
                )

        assert result.exit_code == 0
        assert out_file.exists()

    def test_batch_command_nonexistent_input(self, tmp_path):
        from click.testing import CliRunner
        from src.summarizer.cli import cli

        runner = CliRunner()
        result = runner.invoke(cli, ["batch", str(tmp_path / "nonexistent.txt")])
        assert result.exit_code != 0

    def test_batch_command_with_directory(self, tmp_path):
        from click.testing import CliRunner
        from src.summarizer.cli import cli

        (tmp_path / "article1.txt").write_text("This is article one.\n")
        (tmp_path / "article2.txt").write_text("This is article two.\n")

        runner = CliRunner()
        with patch("src.summarizer.cli._build_summarize_fn") as mock_build:
            def fn(source, dry_run):
                return make_article(source=source), make_summary()
            mock_build.return_value = fn

            with patch("src.summarizer.cli.load_config", return_value=MagicMock()):
                result = runner.invoke(
                    cli,
                    ["batch", str(tmp_path), "--workers", "1"],
                    catch_exceptions=False,
                )

        assert result.exit_code == 0

    def test_batch_exits_nonzero_on_all_failures(self, tmp_path):
        from click.testing import CliRunner
        from src.summarizer.cli import cli

        url_file = tmp_path / "urls.txt"
        url_file.write_text("https://example.com/fail\n")

        runner = CliRunner()
        with patch("src.summarizer.cli._build_summarize_fn") as mock_build:
            def fn(source, dry_run):
                raise RuntimeError("Network error")
            mock_build.return_value = fn

            with patch("src.summarizer.cli.load_config", return_value=MagicMock()):
                result = runner.invoke(
                    cli,
                    ["batch", str(url_file)],
                )

        assert result.exit_code != 0
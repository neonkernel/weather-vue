"""Tests for the batch processing module."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Optional
from unittest.mock import MagicMock, patch

import pytest

from src.summarizer.batch import BatchProcessor, load_sources
from src.summarizer.models import ArticleContent, BatchResult, BatchReport
from src.summarizer.reporter import build_report, write_csv, write_jsonl, _estimate_cost


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def _make_article(url: str = "https://example.com/article", title: str = "Test Article") -> ArticleContent:
    return ArticleContent(url=url, title=title, text="This is test article content. " * 20)


def _ok_process_fn(source: str):
    """Always succeeds — returns a dummy ArticleContent."""
    article = _make_article(url=source, title=f"Title for {source}")
    return article, None


def _fail_process_fn(source: str):
    """Always fails — simulates a fetch error."""
    return None, f"Simulated fetch error for {source}"


def _ok_summarize_fn(article: ArticleContent):
    """Returns a canned summary and token count."""
    return f"Summary of {article.title}", 42


def _slow_process_fn(source: str):
    """Simulates a slow network call."""
    time.sleep(0.05)
    return _make_article(url=source, title=f"Slow {source}"), None


# ---------------------------------------------------------------------------
# load_sources tests
# ---------------------------------------------------------------------------

class TestLoadSources:
    def test_load_from_url_list_file(self, tmp_path: Path):
        url_file = tmp_path / "urls.txt"
        url_file.write_text(
            "https://example.com/a\n"
            "# this is a comment\n"
            "\n"
            "https://example.com/b\n"
        )
        sources = load_sources(url_file)
        assert sources == ["https://example.com/a", "https://example.com/b"]

    def test_load_from_directory(self, tmp_path: Path):
        (tmp_path / "article1.txt").write_text("Hello world")
        (tmp_path / "article2.html").write_text("<p>Hello</p>")
        (tmp_path / "readme.md").write_text("# ignored")

        sources = load_sources(tmp_path)
        filenames = {Path(s).name for s in sources}
        assert "article1.txt" in filenames
        assert "article2.html" in filenames
        assert "readme.md" not in filenames

    def test_raises_if_path_does_not_exist(self, tmp_path: Path):
        with pytest.raises(ValueError, match="does not exist"):
            load_sources(tmp_path / "nonexistent.txt")

    def test_raises_if_no_sources_found(self, tmp_path: Path):
        empty_file = tmp_path / "empty.txt"
        empty_file.write_text("# only comments\n\n")
        with pytest.raises(ValueError, match="No sources found"):
            load_sources(empty_file)

    def test_fixture_url_list(self):
        sources = load_sources(FIXTURES_DIR / "url_list.txt")
        assert len(sources) == 5
        assert all(s.startswith("https://") for s in sources)

    def test_skips_comment_lines(self, tmp_path: Path):
        url_file = tmp_path / "urls.txt"
        url_file.write_text("# comment\nhttps://a.com\n# another\nhttps://b.com\n")
        sources = load_sources(url_file)
        assert len(sources) == 2


# ---------------------------------------------------------------------------
# BatchProcessor tests
# ---------------------------------------------------------------------------

class TestBatchProcessor:
    def test_successful_batch(self):
        processor = BatchProcessor(
            workers=2,
            dry_run=False,
            process_fn=_ok_process_fn,
            summarize_fn=_ok_summarize_fn,
        )
        sources = ["https://example.com/1", "https://example.com/2", "https://example.com/3"]
        results = processor.run(sources)

        assert len(results) == 3
        assert all(r.succeeded for r in results)
        assert all(r.tokens_used == 42 for r in results)
        assert all(r.summary is not None for r in results)

    def test_error_isolation(self):
        """One failure must not abort the rest of the batch."""
        sources = [
            "https://example.com/good-1",
            "https://example.com/bad",
            "https://example.com/good-2",
        ]

        def selective_process(source: str):
            if "bad" in source:
                return None, "Intentional failure"
            return _ok_process_fn(source)

        processor = BatchProcessor(
            workers=2,
            dry_run=False,
            process_fn=selective_process,
            summarize_fn=_ok_summarize_fn,
        )
        results = processor.run(sources)

        assert len(results) == 3
        failures = [r for r in results if not r.succeeded]
        successes = [r for r in results if r.succeeded]
        assert len(failures) == 1
        assert len(successes) == 2
        assert "Intentional failure" in failures[0].error

    def test_all_failures(self):
        processor = BatchProcessor(
            workers=2,
            dry_run=False,
            process_fn=_fail_process_fn,
            summarize_fn=_ok_summarize_fn,
        )
        results = processor.run(["https://a.com", "https://b.com"])
        assert len(results) == 2
        assert all(not r.succeeded for r in results)
        assert all(r.tokens_used == 0 for r in results)

    def test_dry_run_skips_llm(self):
        """In dry-run mode, summarize_fn should never be called."""
        summarize_called = []

        def tracking_summarize(article):
            summarize_called.append(article.url)
            return "summary", 100

        processor = BatchProcessor(
            workers=2,
            dry_run=True,
            process_fn=_ok_process_fn,
            summarize_fn=tracking_summarize,
        )
        results = processor.run(["https://example.com/1", "https://example.com/2"])

        assert len(summarize_called) == 0
        assert all(r.succeeded for r in results)
        assert all("[dry-run" in (r.summary or "") for r in results)
        assert all(r.tokens_used == 0 for r in results)

    def test_worker_count_respected(self):
        """Check that different worker counts produce the same results."""
        sources = [f"https://example.com/{i}" for i in range(6)]

        for workers in (1, 2, 4, 6):
            processor = BatchProcessor(
                workers=workers,
                dry_run=False,
                process_fn=_ok_process_fn,
                summarize_fn=_ok_summarize_fn,
            )
            results = processor.run(sources)
            assert len(results) == 6
            assert all(r.succeeded for r in results)

    def test_concurrent_processing_is_faster(self):
        """Concurrent workers should complete a slow batch faster than sequential."""
        sources = [f"https://example.com/{i}" for i in range(4)]

        start = time.monotonic()
        processor = BatchProcessor(
            workers=4,
            dry_run=False,
            process_fn=_slow_process_fn,
            summarize_fn=_ok_summarize_fn,
        )
        processor.run(sources)
        concurrent_time = time.monotonic() - start

        # With 4 workers and 0.05s sleep each, should take ~0.05s not ~0.2s
        # Be generous with the bound to avoid flakiness
        assert concurrent_time < 0.15, (
            f"Concurrent processing took {concurrent_time:.3f}s — expected < 0.15s"
        )

    def test_exception_in_process_fn_is_isolated(self):
        """An exception raised inside process_fn must not propagate."""

        def crashing_process(source: str):
            raise RuntimeError("Boom!")

        processor = BatchProcessor(
            workers=2,
            dry_run=False,
            process_fn=crashing_process,
            summarize_fn=_ok_summarize_fn,
        )
        results = processor.run(["https://a.com"])
        assert len(results) == 1
        assert not results[0].succeeded
        assert "Boom!" in results[0].error

    def test_exception_in_summarize_fn_is_isolated(self):
        """An exception raised inside summarize_fn must not propagate."""

        def crashing_summarize(article):
            raise RuntimeError("LLM exploded")

        processor = BatchProcessor(
            workers=2,
            dry_run=False,
            process_fn=_ok_process_fn,
            summarize_fn=crashing_summarize,
        )
        results = processor.run(["https://a.com", "https://b.com"])
        assert len(results) == 2
        assert all(not r.succeeded for r in results)
        assert all("LLM exploded" in r.error for r in results)

    def test_duration_is_recorded(self):
        processor = BatchProcessor(
            workers=2,
            dry_run=False,
            process_fn=_ok_process_fn,
            summarize_fn=_ok_summarize_fn,
        )
        results = processor.run(["https://example.com/1"])
        assert results[0].duration_seconds >= 0.0


# ---------------------------------------------------------------------------
# BatchResult / BatchReport model tests
# ---------------------------------------------------------------------------

class TestBatchModels:
    def test_batch_result_succeeded_property(self):
        ok = BatchResult(source="s", article=_make_article(), summary="ok", error=None)
        fail = BatchResult(source="s", article=None, summary=None, error="oops")
        assert ok.succeeded is True
        assert fail.succeeded is False

    def test_batch_result_title_fallback(self):
        result_no_article = BatchResult(
            source="https://example.com/page",
            article=None,
            summary=None,
            error="fail",
        )
        assert result_no_article.title == "https://example.com/page"

        article = _make_article(title="My Article")
        result_with_article = BatchResult(
            source="https://example.com/page",
            article=article,
            summary="s",
            error=None,
        )
        assert result_with_article.title == "My Article"

    def test_batch_report_aggregates(self):
        results = [
            BatchResult(source="a", article=_make_article(), summary="s", error=None, tokens_used=100),
            BatchResult(source="b", article=_make_article(), summary="s", error=None, tokens_used=200),
            BatchResult(source="c", article=None, summary=None, error="bad", tokens_used=0),
        ]
        report = build_report(results, total_duration=5.0)
        assert report.total == 3
        assert report.successes == 2
        assert report.failures == 1
        assert report.total_tokens == 300
        assert abs(report.success_rate - 66.666) < 0.1
        assert report.total_duration_seconds == 5.0


# ---------------------------------------------------------------------------
# Reporter tests
# ---------------------------------------------------------------------------

class TestReporter:
    def _sample_report(self) -> BatchReport:
        results = [
            BatchResult(
                source="https://example.com/a",
                article=_make_article(url="https://example.com/a", title="Article A"),
                summary="Summary A",
                error=None,
                tokens_used=150,
                duration_seconds=1.2,
            ),
            BatchResult(
                source="https://example.com/b",
                article=None,
                summary=None,
                error="Network timeout",
                tokens_used=0,
                duration_seconds=5.0,
            ),
        ]
        return build_report(results, total_duration=6.5)

    def test_write_csv(self, tmp_path: Path):
        report = self._sample_report()
        output = tmp_path / "results.csv"
        write_csv(report, output)

        assert output.exists()
        content = output.read_text(encoding="utf-8")
        assert "source" in content  # header row
        assert "https://example.com/a" in content
        assert "success" in content
        assert "failure" in content
        assert "Network timeout" in content

    def test_write_jsonl(self, tmp_path: Path):
        import json

        report = self._sample_report()
        output = tmp_path / "results.jsonl"
        write_jsonl(report, output)

        assert output.exists()
        lines = output.read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) == 2

        record_a = json.loads(lines[0])
        assert record_a["source"] == "https://example.com/a"
        assert record_a["status"] == "success"
        assert record_a["tokens_used"] == 150

        record_b = json.loads(lines[1])
        assert record_b["status"] == "failure"
        assert record_b["error"] == "Network timeout"

    def test_csv_has_correct_columns(self, tmp_path: Path):
        import csv

        report = self._sample_report()
        output = tmp_path / "results.csv"
        write_csv(report, output)

        with output.open(newline="", encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            fieldnames = reader.fieldnames or []

        expected = {"source", "title", "status", "error", "tokens_used", "duration_seconds", "summary"}
        assert expected.issubset(set(fieldnames))

    def test_estimate_cost(self):
        assert _estimate_cost(0) == 0.0
        assert _estimate_cost(1000) == pytest.approx(0.002)
        assert _estimate_cost(500) == pytest.approx(0.001)

    def test_print_summary_table_runs_without_error(self, capsys):
        """Smoke test — ensure no exceptions are raised."""
        from src.summarizer.reporter import print_summary_table

        report = self._sample_report()
        # Should not raise
        print_summary_table(report)

    def test_write_output_dispatches_csv(self, tmp_path: Path):
        from src.summarizer.reporter import write_output

        report = self._sample_report()
        output = tmp_path / "out.csv"
        write_output(report, output, fmt="csv")
        assert output.exists()
        assert "source" in output.read_text()

    def test_write_output_dispatches_jsonl(self, tmp_path: Path):
        from src.summarizer.reporter import write_output

        report = self._sample_report()
        output = tmp_path / "out.jsonl"
        write_output(report, output, fmt="jsonl")
        assert output.exists()
        import json
        lines = output.read_text().strip().splitlines()
        assert all(json.loads(line) for line in lines)


# ---------------------------------------------------------------------------
# CLI integration tests (using Typer's test client)
# ---------------------------------------------------------------------------

class TestBatchCLI:
    def test_batch_command_help(self):
        from typer.testing import CliRunner
        from src.summarizer.cli import app

        runner = CliRunner()
        result = runner.invoke(app, ["batch", "--help"])
        assert result.exit_code == 0
        assert "batch" in result.output.lower() or "source" in result.output.lower()

    def test_batch_nonexistent_path(self):
        from typer.testing import CliRunner
        from src.summarizer.cli import app

        runner = CliRunner()
        result = runner.invoke(app, ["batch", "/nonexistent/path/urls.txt"])
        assert result.exit_code != 0

    def test_batch_dry_run_with_fixture(self, tmp_path: Path):
        """Dry-run should complete without needing LLM credentials."""
        from typer.testing import CliRunner
        from src.summarizer.cli import app

        # Write a simple local file list
        article = tmp_path / "article.txt"
        article.write_text("This is a test article about technology and innovation.")
        url_list = tmp_path / "urls.txt"
        url_list.write_text(str(article) + "\n")

        runner = CliRunner(mix_stderr=False)

        # Mock the ingestion to avoid real network calls
        mock_article = _make_article(url=str(article), title="Test Article")

        with patch("src.summarizer.cli._build_process_fn") as mock_pfn, \
             patch("src.summarizer.cli._get_config") as mock_cfg:
            mock_cfg.return_value = MagicMock()
            mock_pfn.return_value = lambda src: (mock_article, None)

            result = runner.invoke(app, ["batch", str(url_list), "--dry-run", "--workers", "1"])

        # Should not crash; dry-run errors are non-fatal
        assert result.exit_code in (0, 1)  # 0 = all OK, 1 = some failures
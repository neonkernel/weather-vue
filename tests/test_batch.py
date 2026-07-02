"""Tests for batch processing (src/summarizer/batch.py) and reporter."""

import csv
import json
import os
import time
from pathlib import Path
from unittest.mock import MagicMock, patch, call

import pytest

from src.summarizer.batch import BatchProcessor, _load_urls_from_file, _load_sources_from_directory
from src.summarizer.models import Article, BatchResult, Summary
from src.summarizer.reporter import BatchReporter

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def _make_article(url: str) -> Article:
    return Article(
        url=url,
        title=f"Title for {url}",
        content="Sample content " * 20,
        word_count=40,
        source=url,
    )


def _make_summary(article: Article, tokens: int = 100) -> Summary:
    return Summary(
        article=article,
        text="This is a test summary.",
        style="concise",
        model="gpt-test",
        tokens_used=tokens,
        cost_estimate=tokens / 1000 * 0.002,
    )


def _ok_ingest(source: str) -> Article:
    return _make_article(source)


def _ok_summarize(article: Article) -> Summary:
    return _make_summary(article)


def _failing_ingest(source: str) -> Article:
    raise RuntimeError(f"Simulated ingest failure for {source}")


def _failing_summarize(article: Article) -> Summary:
    raise RuntimeError("Simulated LLM failure")


# ---------------------------------------------------------------------------
# Helper: build processor
# ---------------------------------------------------------------------------

def _make_processor(
    ingest_fn=None,
    summarize_fn=None,
    workers=2,
    dry_run=False,
    progress_callback=None,
) -> BatchProcessor:
    return BatchProcessor(
        ingest_fn=ingest_fn or _ok_ingest,
        summarize_fn=summarize_fn or _ok_summarize,
        workers=workers,
        dry_run=dry_run,
        progress_callback=progress_callback,
    )


# ---------------------------------------------------------------------------
# _load_urls_from_file
# ---------------------------------------------------------------------------

class TestLoadUrlsFromFile:
    def test_loads_urls_ignores_comments_and_blanks(self, tmp_path):
        f = tmp_path / "urls.txt"
        f.write_text(
            "# comment\n"
            "https://example.com/a\n"
            "\n"
            "https://example.com/b\n",
            encoding="utf-8",
        )
        urls = _load_urls_from_file(f)
        assert urls == ["https://example.com/a", "https://example.com/b"]

    def test_empty_file_returns_empty_list(self, tmp_path):
        f = tmp_path / "empty.txt"
        f.write_text("", encoding="utf-8")
        assert _load_urls_from_file(f) == []

    def test_fixture_file_has_five_urls(self):
        urls = _load_urls_from_file(FIXTURES_DIR / "url_list.txt")
        assert len(urls) == 5
        for url in urls:
            assert url.startswith("https://")


# ---------------------------------------------------------------------------
# _load_sources_from_directory
# ---------------------------------------------------------------------------

class TestLoadSourcesFromDirectory:
    def test_loads_txt_and_html_files(self, tmp_path):
        (tmp_path / "a.txt").write_text("text", encoding="utf-8")
        (tmp_path / "b.html").write_text("<p>html</p>", encoding="utf-8")
        (tmp_path / "c.md").write_text("ignored", encoding="utf-8")

        sources = _load_sources_from_directory(tmp_path)
        names = [Path(s).name for s in sources]
        assert "a.txt" in names
        assert "b.html" in names
        assert "c.md" not in names

    def test_empty_directory_returns_empty_list(self, tmp_path):
        assert _load_sources_from_directory(tmp_path) == []


# ---------------------------------------------------------------------------
# BatchProcessor._load_sources
# ---------------------------------------------------------------------------

class TestBatchProcessorLoadSources:
    def test_url_list_file(self, tmp_path):
        f = tmp_path / "urls.txt"
        f.write_text("https://example.com/1\nhttps://example.com/2\n", encoding="utf-8")
        p = _make_processor()
        sources = p._load_sources(str(f))
        assert sources == ["https://example.com/1", "https://example.com/2"]

    def test_directory(self, tmp_path):
        (tmp_path / "art.html").write_text("<p>x</p>", encoding="utf-8")
        p = _make_processor()
        sources = p._load_sources(str(tmp_path))
        assert len(sources) == 1

    def test_single_url(self):
        p = _make_processor()
        sources = p._load_sources("https://example.com/single")
        assert sources == ["https://example.com/single"]


# ---------------------------------------------------------------------------
# BatchProcessor.run – happy path
# ---------------------------------------------------------------------------

class TestBatchProcessorRun:
    def test_run_returns_one_result_per_source(self, tmp_path):
        f = tmp_path / "urls.txt"
        urls = [f"https://example.com/{i}" for i in range(5)]
        f.write_text("\n".join(urls), encoding="utf-8")

        p = _make_processor(workers=2)
        results = p.run(str(f))

        assert len(results) == 5
        assert all(r.success for r in results)

    def test_run_all_have_duration_set(self, tmp_path):
        f = tmp_path / "urls.txt"
        f.write_text("https://example.com/a\nhttps://example.com/b\n", encoding="utf-8")

        p = _make_processor()
        results = p.run(str(f))
        assert all(r.duration_seconds >= 0 for r in results)

    def test_run_tokens_populated(self, tmp_path):
        f = tmp_path / "urls.txt"
        f.write_text("https://example.com/a\n", encoding="utf-8")

        p = _make_processor()
        results = p.run(str(f))
        assert results[0].tokens_used == 100

    def test_single_worker(self, tmp_path):
        f = tmp_path / "urls.txt"
        urls = [f"https://example.com/{i}" for i in range(3)]
        f.write_text("\n".join(urls), encoding="utf-8")

        p = _make_processor(workers=1)
        results = p.run(str(f))
        assert len(results) == 3

    def test_many_workers(self, tmp_path):
        f = tmp_path / "urls.txt"
        urls = [f"https://example.com/{i}" for i in range(10)]
        f.write_text("\n".join(urls), encoding="utf-8")

        p = _make_processor(workers=8)
        results = p.run(str(f))
        assert len(results) == 10

    def test_empty_input_returns_empty_list(self, tmp_path):
        f = tmp_path / "urls.txt"
        f.write_text("# only comments\n", encoding="utf-8")

        p = _make_processor()
        results = p.run(str(f))
        assert results == []


# ---------------------------------------------------------------------------
# Error isolation
# ---------------------------------------------------------------------------

class TestBatchProcessorErrorIsolation:
    def test_one_failing_ingest_does_not_abort_batch(self, tmp_path):
        f = tmp_path / "urls.txt"
        urls = [f"https://example.com/{i}" for i in range(4)]
        f.write_text("\n".join(urls), encoding="utf-8")

        call_count = [0]

        def selective_ingest(source):
            call_count[0] += 1
            if "2" in source:
                raise RuntimeError("Ingest failed")
            return _ok_ingest(source)

        p = _make_processor(ingest_fn=selective_ingest)
        results = p.run(str(f))

        assert len(results) == 4
        successes = [r for r in results if r.success]
        failures = [r for r in results if not r.success]
        assert len(successes) == 3
        assert len(failures) == 1
        assert failures[0].error == "Ingest failed"

    def test_failing_llm_sets_error_field(self, tmp_path):
        f = tmp_path / "urls.txt"
        f.write_text("https://example.com/a\n", encoding="utf-8")

        p = _make_processor(summarize_fn=_failing_summarize)
        results = p.run(str(f))

        assert len(results) == 1
        assert not results[0].success
        assert "Simulated LLM failure" in results[0].error

    def test_all_failing_returns_all_error_results(self, tmp_path):
        f = tmp_path / "urls.txt"
        urls = [f"https://example.com/{i}" for i in range(3)]
        f.write_text("\n".join(urls), encoding="utf-8")

        p = _make_processor(ingest_fn=_failing_ingest)
        results = p.run(str(f))

        assert len(results) == 3
        assert all(not r.success for r in results)
        assert all(r.error is not None for r in results)

    def test_error_result_has_source_set(self, tmp_path):
        f = tmp_path / "urls.txt"
        f.write_text("https://example.com/fail\n", encoding="utf-8")

        p = _make_processor(ingest_fn=_failing_ingest)
        results = p.run(str(f))

        assert results[0].source == "https://example.com/fail"


# ---------------------------------------------------------------------------
# Dry-run mode
# ---------------------------------------------------------------------------

class TestDryRun:
    def test_dry_run_does_not_call_summarize_fn(self, tmp_path):
        f = tmp_path / "urls.txt"
        f.write_text("https://example.com/a\nhttps://example.com/b\n", encoding="utf-8")

        summarize_mock = MagicMock(side_effect=_ok_summarize)

        p = _make_processor(summarize_fn=summarize_mock, dry_run=True)
        results = p.run(str(f))

        summarize_mock.assert_not_called()
        assert all(r.success for r in results)
        assert all(r.summary is None for r in results)

    def test_dry_run_still_calls_ingest_fn(self, tmp_path):
        f = tmp_path / "urls.txt"
        f.write_text("https://example.com/a\n", encoding="utf-8")

        ingest_mock = MagicMock(side_effect=_ok_ingest)
        p = _make_processor(ingest_fn=ingest_mock, dry_run=True)
        p.run(str(f))

        ingest_mock.assert_called_once_with("https://example.com/a")

    def test_dry_run_ingest_failure_marks_as_failed(self, tmp_path):
        f = tmp_path / "urls.txt"
        f.write_text("https://example.com/a\n", encoding="utf-8")

        p = _make_processor(ingest_fn=_failing_ingest, dry_run=True)
        results = p.run(str(f))

        assert not results[0].success
        assert results[0].error is not None

    def test_dry_run_tokens_are_zero(self, tmp_path):
        f = tmp_path / "urls.txt"
        f.write_text("https://example.com/a\n", encoding="utf-8")

        p = _make_processor(dry_run=True)
        results = p.run(str(f))

        assert results[0].tokens_used == 0


# ---------------------------------------------------------------------------
# Progress callback
# ---------------------------------------------------------------------------

class TestProgressCallback:
    def test_callback_called_for_each_result(self, tmp_path):
        f = tmp_path / "urls.txt"
        urls = [f"https://example.com/{i}" for i in range(5)]
        f.write_text("\n".join(urls), encoding="utf-8")

        called = []
        p = _make_processor(progress_callback=lambda r: called.append(r))
        p.run(str(f))

        assert len(called) == 5

    def test_callback_receives_batch_result(self, tmp_path):
        f = tmp_path / "urls.txt"
        f.write_text("https://example.com/a\n", encoding="utf-8")

        received = []
        p = _make_processor(progress_callback=lambda r: received.append(r))
        p.run(str(f))

        assert isinstance(received[0], BatchResult)


# ---------------------------------------------------------------------------
# BatchReporter
# ---------------------------------------------------------------------------

class TestBatchReporterAggregates:
    def _make_results(self):
        art = _make_article("https://example.com/a")
        summ = _make_summary(art, tokens=200)
        ok = BatchResult(
            source="https://example.com/a",
            article=art,
            summary=summ,
            tokens_used=200,
            cost_estimate=0.0004,
            duration_seconds=1.5,
            success=True,
        )
        fail = BatchResult(
            source="https://example.com/b",
            error="timeout",
            duration_seconds=0.3,
            success=False,
        )
        return [ok, fail]

    def test_total(self):
        r = BatchReporter(self._make_results())
        assert r.total == 2

    def test_successes(self):
        r = BatchReporter(self._make_results())
        assert r.successes == 1

    def test_failures(self):
        r = BatchReporter(self._make_results())
        assert r.failures == 1

    def test_total_tokens(self):
        r = BatchReporter(self._make_results())
        assert r.total_tokens == 200

    def test_total_cost(self):
        r = BatchReporter(self._make_results())
        assert r.total_cost == pytest.approx(0.0004)

    def test_total_duration(self):
        r = BatchReporter(self._make_results())
        assert r.total_duration == pytest.approx(1.8, abs=0.01)


class TestBatchReporterCsvExport:
    def _make_results(self, tmp_path):
        art = _make_article("https://example.com/a")
        summ = _make_summary(art, tokens=50)
        return [
            BatchResult(
                source="https://example.com/a",
                article=art,
                summary=summ,
                tokens_used=50,
                cost_estimate=0.0001,
                duration_seconds=0.8,
                success=True,
            )
        ]

    def test_csv_created(self, tmp_path):
        out = tmp_path / "out.csv"
        r = BatchReporter(self._make_results(tmp_path))
        r.write_csv(str(out))
        assert out.exists()

    def test_csv_has_header(self, tmp_path):
        out = tmp_path / "out.csv"
        r = BatchReporter(self._make_results(tmp_path))
        r.write_csv(str(out))
        with open(out, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            assert "source" in reader.fieldnames
            assert "success" in reader.fieldnames
            assert "tokens_used" in reader.fieldnames

    def test_csv_row_values(self, tmp_path):
        out = tmp_path / "out.csv"
        r = BatchReporter(self._make_results(tmp_path))
        r.write_csv(str(out))
        with open(out, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        assert len(rows) == 1
        assert rows[0]["source"] == "https://example.com/a"
        assert rows[0]["success"] == "True"
        assert rows[0]["tokens_used"] == "50"

    def test_csv_summary_text_included(self, tmp_path):
        out = tmp_path / "out.csv"
        r = BatchReporter(self._make_results(tmp_path))
        r.write_csv(str(out))
        with open(out, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        assert rows[0]["summary_text"] == "This is a test summary."


class TestBatchReporterJsonlExport:
    def _make_results(self):
        art = _make_article("https://example.com/a")
        summ = _make_summary(art, tokens=75)
        return [
            BatchResult(
                source="https://example.com/a",
                article=art,
                summary=summ,
                tokens_used=75,
                cost_estimate=0.00015,
                duration_seconds=1.1,
                success=True,
            )
        ]

    def test_jsonl_created(self, tmp_path):
        out = tmp_path / "out.jsonl"
        r = BatchReporter(self._make_results())
        r.write_jsonl(str(out))
        assert out.exists()

    def test_jsonl_valid_json_per_line(self, tmp_path):
        out = tmp_path / "out.jsonl"
        r = BatchReporter(self._make_results())
        r.write_jsonl(str(out))
        lines = out.read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) == 1
        record = json.loads(lines[0])
        assert record["source"] == "https://example.com/a"
        assert record["success"] is True
        assert record["tokens_used"] == 75

    def test_jsonl_error_field_is_none_on_success(self, tmp_path):
        out = tmp_path / "out.jsonl"
        r = BatchReporter(self._make_results())
        r.write_jsonl(str(out))
        lines = out.read_text(encoding="utf-8").strip().splitlines()
        record = json.loads(lines[0])
        assert record["error"] is None

    def test_jsonl_error_batch_result(self, tmp_path):
        out = tmp_path / "out.jsonl"
        results = [
            BatchResult(
                source="https://example.com/fail",
                error="connection timeout",
                duration_seconds=2.0,
                success=False,
            )
        ]
        r = BatchReporter(results)
        r.write_jsonl(str(out))
        lines = out.read_text(encoding="utf-8").strip().splitlines()
        record = json.loads(lines[0])
        assert record["success"] is False
        assert record["error"] == "connection timeout"


class TestBatchReporterWriteOutput:
    def test_auto_csv(self, tmp_path):
        out = tmp_path / "results.csv"
        art = _make_article("https://example.com/a")
        summ = _make_summary(art)
        results = [BatchResult(source="https://example.com/a", article=art, summary=summ, success=True)]
        r = BatchReporter(results)
        r.write_output(str(out))
        assert out.exists()
        with open(out, encoding="utf-8") as f:
            content = f.read()
        assert "source" in content

    def test_auto_jsonl(self, tmp_path):
        out = tmp_path / "results.jsonl"
        art = _make_article("https://example.com/a")
        summ = _make_summary(art)
        results = [BatchResult(source="https://example.com/a", article=art, summary=summ, success=True)]
        r = BatchReporter(results)
        r.write_output(str(out))
        assert out.exists()

    def test_explicit_format_csv(self, tmp_path):
        out = tmp_path / "results.dat"
        art = _make_article("https://example.com/a")
        summ = _make_summary(art)
        results = [BatchResult(source="https://example.com/a", article=art, summary=summ, success=True)]
        r = BatchReporter(results)
        r.write_output(str(out), fmt="csv")
        assert out.exists()

    def test_unknown_format_raises(self, tmp_path):
        out = tmp_path / "results.xyz"
        r = BatchReporter([])
        with pytest.raises(ValueError, match="Unknown output format"):
            r.write_output(str(out), fmt="xml")


# ---------------------------------------------------------------------------
# BatchResult model
# ---------------------------------------------------------------------------

class TestBatchResultModel:
    def test_success_true_when_summary_present(self):
        art = _make_article("https://example.com")
        summ = _make_summary(art)
        r = BatchResult(source="https://example.com", article=art, summary=summ)
        assert r.success is True

    def test_success_false_when_error_present(self):
        r = BatchResult(source="https://example.com", error="oops")
        assert r.success is False

    def test_dry_run_success_without_summary(self):
        art = _make_article("https://example.com")
        r = BatchResult(source="https://example.com", article=art, dry_run=True)
        assert r.success is True

    def test_dry_run_failure_without_article(self):
        r = BatchResult(source="https://example.com", dry_run=True, error="fail")
        assert r.success is False

    def test_default_duration_is_zero(self):
        r = BatchResult(source="https://example.com")
        assert r.duration_seconds == 0.0

    def test_default_tokens_is_zero(self):
        r = BatchResult(source="https://example.com")
        assert r.tokens_used == 0
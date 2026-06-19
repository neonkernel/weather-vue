"""
Smoke tests for the Summarizer CLI (Phase 1).

Uses Click's CliRunner to invoke the CLI in-process without spawning a
subprocess, which keeps tests fast and avoids requiring a real network or
filesystem beyond controlled fixtures.
"""

from __future__ import annotations

import json
import os
import textwrap
from pathlib import Path

import pytest
from click.testing import CliRunner

# ---------------------------------------------------------------------------
# Import guards — the package must be importable
# ---------------------------------------------------------------------------


def test_package_is_importable() -> None:
    """The summarizer package must be importable."""
    import summarizer  # noqa: F401


def test_version_string_is_defined() -> None:
    """__version__ must be a non-empty string."""
    from summarizer import __version__

    assert isinstance(__version__, str)
    assert len(__version__) > 0


def test_cli_module_is_importable() -> None:
    """The cli module and main entry point must be importable."""
    from summarizer.cli import main  # noqa: F401


# ---------------------------------------------------------------------------
# --help
# ---------------------------------------------------------------------------


def test_help_exits_zero() -> None:
    """``summarize --help`` should exit with code 0."""
    from summarizer.cli import main

    runner = CliRunner()
    result = runner.invoke(main, ["--help"])
    assert result.exit_code == 0


def test_help_output_contains_key_options() -> None:
    """Help text should mention core options."""
    from summarizer.cli import main

    runner = CliRunner()
    result = runner.invoke(main, ["--help"])
    output = result.output

    assert "--url" in output
    assert "--file" in output
    assert "--style" in output
    assert "--format" in output
    assert "--verbose" in output


# ---------------------------------------------------------------------------
# --version
# ---------------------------------------------------------------------------


def test_version_flag() -> None:
    """``summarize --version`` should print the version and exit 0."""
    from summarizer.cli import main
    from summarizer import __version__

    runner = CliRunner()
    result = runner.invoke(main, ["--version"])
    assert result.exit_code == 0
    assert __version__ in result.output


# ---------------------------------------------------------------------------
# Missing / invalid input
# ---------------------------------------------------------------------------


def test_no_input_shows_error() -> None:
    """Invoking without --url or --file should exit non-zero with a usage error."""
    from summarizer.cli import main

    runner = CliRunner()
    result = runner.invoke(main, [])
    assert result.exit_code != 0


def test_both_url_and_file_shows_error() -> None:
    """Providing both --url and --file should exit non-zero."""
    from summarizer.cli import main

    runner = CliRunner()
    result = runner.invoke(main, ["--url", "https://example.com", "--file", "foo.txt"])
    assert result.exit_code != 0


def test_invalid_url_shows_error() -> None:
    """A malformed URL should produce a non-zero exit and an error message."""
    from summarizer.cli import main

    runner = CliRunner()
    result = runner.invoke(main, ["--url", "not-a-url"])
    assert result.exit_code != 0


def test_nonexistent_file_shows_error() -> None:
    """A file path that does not exist should produce a non-zero exit."""
    from summarizer.cli import main

    runner = CliRunner()
    result = runner.invoke(main, ["--file", "/nonexistent/path/to/file.txt"])
    assert result.exit_code != 0


# ---------------------------------------------------------------------------
# Valid URL input (placeholder output)
# ---------------------------------------------------------------------------


def test_valid_url_exits_zero() -> None:
    """A valid URL should result in a zero exit code."""
    from summarizer.cli import main

    runner = CliRunner()
    result = runner.invoke(main, ["--url", "https://example.com"])
    assert result.exit_code == 0, result.output


def test_valid_url_output_contains_placeholder() -> None:
    """Placeholder text should appear in the output for a valid URL."""
    from summarizer.cli import main

    runner = CliRunner()
    result = runner.invoke(main, ["--url", "https://example.com"])
    assert "PLACEHOLDER" in result.output
    assert "https://example.com" in result.output


# ---------------------------------------------------------------------------
# Valid FILE input (placeholder output)
# ---------------------------------------------------------------------------


def test_valid_file_exits_zero(tmp_path: Path) -> None:
    """A valid, readable file should result in a zero exit code."""
    from summarizer.cli import main

    sample = tmp_path / "sample.txt"
    sample.write_text("Hello, world!")

    runner = CliRunner()
    result = runner.invoke(main, ["--file", str(sample)])
    assert result.exit_code == 0, result.output


def test_valid_file_output_contains_placeholder(tmp_path: Path) -> None:
    """Placeholder text should appear in the output for a valid file."""
    from summarizer.cli import main

    sample = tmp_path / "sample.txt"
    sample.write_text("Some content to summarize.")

    runner = CliRunner()
    result = runner.invoke(main, ["--file", str(sample)])
    assert "PLACEHOLDER" in result.output


# ---------------------------------------------------------------------------
# --style and --format options
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("style", ["bullet", "narrative", "tldr"])
def test_valid_styles(style: str) -> None:
    """All valid --style values should be accepted."""
    from summarizer.cli import main

    runner = CliRunner()
    result = runner.invoke(main, ["--url", "https://example.com", "--style", style])
    assert result.exit_code == 0, result.output


def test_invalid_style_shows_error() -> None:
    """An unrecognised --style value should produce a non-zero exit."""
    from summarizer.cli import main

    runner = CliRunner()
    result = runner.invoke(
        main, ["--url", "https://example.com", "--style", "haiku"]
    )
    assert result.exit_code != 0


@pytest.mark.parametrize("fmt", ["plain", "markdown", "json"])
def test_valid_formats(fmt: str) -> None:
    """All valid --format values should be accepted."""
    from summarizer.cli import main

    runner = CliRunner()
    result = runner.invoke(
        main, ["--url", "https://example.com", "--format", fmt]
    )
    assert result.exit_code == 0, result.output


def test_invalid_format_shows_error() -> None:
    """An unrecognised --format value should produce a non-zero exit."""
    from summarizer.cli import main

    runner = CliRunner()
    result = runner.invoke(
        main, ["--url", "https://example.com", "--format", "xml"]
    )
    assert result.exit_code != 0


# ---------------------------------------------------------------------------
# JSON output format
# ---------------------------------------------------------------------------


def test_json_output_is_valid_json() -> None:
    """With --format json the output must be valid JSON."""
    from summarizer.cli import main

    runner = CliRunner()
    result = runner.invoke(
        main, ["--url", "https://example.com", "--format", "json"]
    )
    assert result.exit_code == 0, result.output
    parsed = json.loads(result.output)
    assert "summary" in parsed
    assert "input_type" in parsed


def test_json_output_contains_expected_keys() -> None:
    """JSON output should contain all expected metadata keys."""
    from summarizer.cli import main

    runner = CliRunner()
    result = runner.invoke(
        main,
        ["--url", "https://example.com", "--style", "bullet", "--format", "json"],
    )
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["input_type"] == "url"
    assert parsed["style"] == "bullet"
    assert parsed["format"] == "json"


# ---------------------------------------------------------------------------
# Markdown output format
# ---------------------------------------------------------------------------


def test_markdown_output_contains_heading() -> None:
    """Markdown output should start with a heading."""
    from summarizer.cli import main

    runner = CliRunner()
    result = runner.invoke(
        main, ["--url", "https://example.com", "--format", "markdown"]
    )
    assert result.exit_code == 0
    assert "## Summary" in result.output


# ---------------------------------------------------------------------------
# --verbose flag (smoke test — just ensure it doesn't crash)
# ---------------------------------------------------------------------------


def test_verbose_flag_does_not_crash() -> None:
    """--verbose should not cause a crash."""
    from summarizer.cli import main

    runner = CliRunner()
    result = runner.invoke(main, ["--url", "https://example.com", "--verbose"])
    assert result.exit_code == 0, result.output
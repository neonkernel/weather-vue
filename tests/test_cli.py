"""
Smoke tests for the Summarizer CLI.

These tests use Click's CliRunner so no real HTTP requests or LLM calls are
made.  They exercise:

  1. The package is importable and exposes a version string.
  2. ``--help`` exits cleanly.
  3. Missing input shows a usage error.
  4. A valid URL is accepted and echoed back.
  5. An invalid URL is rejected with a clear message.
  6. A valid file path is accepted and echoed back.
  7. An unreadable / non-existent file path is rejected.
  8. Providing both --url and --file at the same time is rejected.
"""

from __future__ import annotations

import tempfile
import os
from pathlib import Path

import pytest
from click.testing import CliRunner

from summarizer import __version__
from summarizer.cli import main


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

@pytest.fixture()
def runner() -> CliRunner:
    return CliRunner()


# ---------------------------------------------------------------------------
# Package-level smoke tests
# ---------------------------------------------------------------------------

def test_version_string_is_defined() -> None:
    """The package must expose a non-empty version string."""
    assert isinstance(__version__, str)
    assert __version__  # non-empty


# ---------------------------------------------------------------------------
# --help
# ---------------------------------------------------------------------------

def test_help_exits_cleanly(runner: CliRunner) -> None:
    result = runner.invoke(main, ["--help"])
    assert result.exit_code == 0
    assert "Usage" in result.output
    assert "--url" in result.output
    assert "--file" in result.output


def test_version_flag(runner: CliRunner) -> None:
    result = runner.invoke(main, ["--version"])
    assert result.exit_code == 0
    assert __version__ in result.output


# ---------------------------------------------------------------------------
# Missing / conflicting input
# ---------------------------------------------------------------------------

def test_no_input_shows_usage_error(runner: CliRunner) -> None:
    """Running without --url or --file must exit with a non-zero code."""
    result = runner.invoke(main, [])
    assert result.exit_code != 0
    output = result.output + (str(result.exception) if result.exception else "")
    assert "url" in output.lower() or "file" in output.lower() or "error" in output.lower()


def test_both_url_and_file_rejected(runner: CliRunner) -> None:
    """Providing both --url and --file must exit with an error."""
    with runner.isolated_filesystem():
        # Create a temporary file so --file validation passes before the
        # mutual-exclusion check (order doesn't actually matter here, but it's
        # good practice to provide a valid file).
        Path("dummy.txt").write_text("hello")
        result = runner.invoke(main, ["--url", "https://example.com", "--file", "dummy.txt"])
    assert result.exit_code != 0


# ---------------------------------------------------------------------------
# URL input
# ---------------------------------------------------------------------------

def test_valid_url_accepted(runner: CliRunner) -> None:
    result = runner.invoke(main, ["--url", "https://example.com/article"])
    assert result.exit_code == 0
    assert "url" in result.output.lower()
    assert "https://example.com/article" in result.output


def test_invalid_url_rejected(runner: CliRunner) -> None:
    result = runner.invoke(main, ["--url", "not-a-url"])
    assert result.exit_code != 0
    assert "url" in result.output.lower() or "invalid" in result.output.lower() or "error" in result.output.lower()


def test_http_url_accepted(runner: CliRunner) -> None:
    result = runner.invoke(main, ["--url", "http://example.com"])
    assert result.exit_code == 0


# ---------------------------------------------------------------------------
# File input
# ---------------------------------------------------------------------------

def test_valid_file_accepted(runner: CliRunner) -> None:
    with runner.isolated_filesystem():
        Path("document.txt").write_text("Some content to summarize.")
        result = runner.invoke(main, ["--file", "document.txt"])
    assert result.exit_code == 0
    assert "file" in result.output.lower()
    assert "document.txt" in result.output


def test_nonexistent_file_rejected(runner: CliRunner) -> None:
    result = runner.invoke(main, ["--file", "/nonexistent/path/file.txt"])
    assert result.exit_code != 0


# ---------------------------------------------------------------------------
# Style / format options
# ---------------------------------------------------------------------------

def test_style_option_reflected_in_output(runner: CliRunner) -> None:
    result = runner.invoke(main, ["--url", "https://example.com", "--style", "bullet"])
    assert result.exit_code == 0
    assert "bullet" in result.output.lower()


def test_format_option_reflected_in_output(runner: CliRunner) -> None:
    result = runner.invoke(main, ["--url", "https://example.com", "--format", "markdown"])
    assert result.exit_code == 0
    assert "markdown" in result.output.lower()


def test_invalid_style_rejected(runner: CliRunner) -> None:
    result = runner.invoke(main, ["--url", "https://example.com", "--style", "badstyle"])
    assert result.exit_code != 0


def test_invalid_format_rejected(runner: CliRunner) -> None:
    result = runner.invoke(main, ["--url", "https://example.com", "--format", "badformat"])
    assert result.exit_code != 0


# ---------------------------------------------------------------------------
# Verbose flag
# ---------------------------------------------------------------------------

def test_verbose_flag_does_not_crash(runner: CliRunner) -> None:
    result = runner.invoke(main, ["--url", "https://example.com", "--verbose"])
    assert result.exit_code == 0
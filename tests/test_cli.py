"""
Smoke tests for the summarizer CLI.

Uses Click's CliRunner to invoke the command in-process without spawning a
subprocess, making tests fast and easy to debug.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

import pytest
from click.testing import CliRunner

from summarizer.cli import main
from summarizer import __version__


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_runner() -> CliRunner:
    """Return a CliRunner that mixes stdout/stderr so we capture everything."""
    return CliRunner(mix_stderr=False)


# ---------------------------------------------------------------------------
# Importability
# ---------------------------------------------------------------------------

def test_package_importable() -> None:
    """The summarizer package must be importable."""
    import summarizer  # noqa: F401


def test_version_string() -> None:
    """The package must expose a non-empty __version__ string."""
    assert isinstance(__version__, str)
    assert len(__version__) > 0


def test_cli_importable() -> None:
    """The CLI entry point must be importable."""
    from summarizer.cli import main  # noqa: F401


# ---------------------------------------------------------------------------
# --help
# ---------------------------------------------------------------------------

def test_help_exits_zero() -> None:
    """--help must exit with code 0."""
    runner = make_runner()
    result = runner.invoke(main, ["--help"])
    assert result.exit_code == 0


def test_help_contains_usage() -> None:
    """--help output must mention the command name and key options."""
    runner = make_runner()
    result = runner.invoke(main, ["--help"])
    output = result.output
    assert "summarize" in output.lower() or "usage" in output.lower()
    assert "--url" in output
    assert "--file" in output
    assert "--style" in output
    assert "--format" in output
    assert "--verbose" in output


def test_version_flag() -> None:
    """--version must print the version and exit 0."""
    runner = make_runner()
    result = runner.invoke(main, ["--version"])
    assert result.exit_code == 0
    assert __version__ in result.output


# ---------------------------------------------------------------------------
# Missing / invalid input
# ---------------------------------------------------------------------------

def test_no_input_shows_error() -> None:
    """Invoking with no options must exit non-zero and show an error."""
    runner = make_runner()
    result = runner.invoke(main, [])
    assert result.exit_code != 0
    # Error message should mention how to provide input
    combined = (result.output or "") + (result.stderr or "")
    assert "url" in combined.lower() or "file" in combined.lower() or "error" in combined.lower()


def test_both_url_and_file_shows_error() -> None:
    """Providing both --url and --file must exit non-zero."""
    runner = make_runner()
    with runner.isolated_filesystem():
        # Create a temporary file so the file path itself is valid
        tmp = Path("sample.txt")
        tmp.write_text("hello world")
        result = runner.invoke(main, ["--url", "https://example.com", "--file", str(tmp)])
    assert result.exit_code != 0


def test_invalid_url_shows_error() -> None:
    """An input that doesn't look like a URL must exit non-zero."""
    runner = make_runner()
    result = runner.invoke(main, ["--url", "not-a-url"])
    assert result.exit_code != 0
    combined = (result.output or "") + (result.stderr or "")
    assert "url" in combined.lower() or "valid" in combined.lower() or "error" in combined.lower()


def test_nonexistent_file_shows_error() -> None:
    """A file path that doesn't exist must exit non-zero."""
    runner = make_runner()
    result = runner.invoke(main, ["--file", "/this/path/does/not/exist.txt"])
    assert result.exit_code != 0


# ---------------------------------------------------------------------------
# Valid URL input
# ---------------------------------------------------------------------------

def test_valid_url_exits_zero() -> None:
    """A valid URL must result in exit code 0 and print placeholder output."""
    runner = make_runner()
    result = runner.invoke(main, ["--url", "https://example.com/article"])
    assert result.exit_code == 0
    assert "placeholder" in result.output.lower() or "example.com" in result.output


def test_valid_url_with_style() -> None:
    """--style option must be accepted and echoed in placeholder output."""
    runner = make_runner()
    result = runner.invoke(main, ["--url", "https://example.com", "--style", "bullet"])
    assert result.exit_code == 0
    assert "bullet" in result.output.lower()


def test_valid_url_format_json() -> None:
    """--format json must produce valid JSON output."""
    runner = make_runner()
    result = runner.invoke(
        main, ["--url", "https://example.com", "--format", "json"]
    )
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["input_type"] == "url"
    assert data["input_value"] == "https://example.com"
    assert "summary" in data


def test_valid_url_format_markdown() -> None:
    """--format markdown must produce output containing markdown markers."""
    runner = make_runner()
    result = runner.invoke(
        main, ["--url", "https://example.com", "--format", "markdown"]
    )
    assert result.exit_code == 0
    # Markdown output contains a heading marker
    assert "#" in result.output


# ---------------------------------------------------------------------------
# Valid file input
# ---------------------------------------------------------------------------

def test_valid_file_exits_zero() -> None:
    """A valid, readable file path must result in exit code 0."""
    runner = make_runner()
    with runner.isolated_filesystem():
        tmp = Path("document.txt")
        tmp.write_text("This is a test document.")
        result = runner.invoke(main, ["--file", str(tmp)])
    assert result.exit_code == 0
    assert "placeholder" in result.output.lower() or "document.txt" in result.output


def test_valid_file_format_json() -> None:
    """--format json with a file input must produce valid JSON."""
    runner = make_runner()
    with runner.isolated_filesystem():
        tmp = Path("report.txt")
        tmp.write_text("Report content here.")
        result = runner.invoke(main, ["--file", str(tmp), "--format", "json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["input_type"] == "file"
    assert "summary" in data


# ---------------------------------------------------------------------------
# Verbose flag
# ---------------------------------------------------------------------------

def test_verbose_flag_accepted() -> None:
    """--verbose must be accepted without raising an error."""
    runner = make_runner()
    result = runner.invoke(main, ["--url", "https://example.com", "--verbose"])
    assert result.exit_code == 0


# ---------------------------------------------------------------------------
# Invalid option values
# ---------------------------------------------------------------------------

def test_invalid_style_shows_error() -> None:
    """An unrecognised --style value must exit non-zero."""
    runner = make_runner()
    result = runner.invoke(
        main, ["--url", "https://example.com", "--style", "invalid_style"]
    )
    assert result.exit_code != 0


def test_invalid_format_shows_error() -> None:
    """An unrecognised --format value must exit non-zero."""
    runner = make_runner()
    result = runner.invoke(
        main, ["--url", "https://example.com", "--format", "xml"]
    )
    assert result.exit_code != 0
"""
Smoke tests for the Summarizer CLI.

Uses Click's CliRunner so no actual network or filesystem I/O is required
for the basic contract tests.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

import pytest
from click.testing import CliRunner

from summarizer import __version__
from summarizer.cli import main


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_runner() -> CliRunner:
    """Return a CliRunner that mixes stderr into the result output."""
    return CliRunner(mix_stderr=False)


# ---------------------------------------------------------------------------
# Import / version tests
# ---------------------------------------------------------------------------


class TestImports:
    """Ensure the package is importable and version is set."""

    def test_package_importable(self) -> None:
        import summarizer  # noqa: F401 — just checking importability

    def test_version_is_string(self) -> None:
        assert isinstance(__version__, str)

    def test_version_not_empty(self) -> None:
        assert __version__.strip() != ""

    def test_cli_importable(self) -> None:
        from summarizer.cli import main as _main  # noqa: F401

    def test_config_importable(self) -> None:
        from summarizer.config import Config, load_config  # noqa: F401

    def test_logger_importable(self) -> None:
        from summarizer.logger import configure_logging, get_logger  # noqa: F401


# ---------------------------------------------------------------------------
# --help
# ---------------------------------------------------------------------------


class TestHelp:
    """--help should exit 0 and display usage information."""

    def test_help_exits_zero(self) -> None:
        runner = make_runner()
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0, result.output

    def test_help_contains_usage(self) -> None:
        runner = make_runner()
        result = runner.invoke(main, ["--help"])
        assert "Usage:" in result.output

    def test_help_mentions_url_option(self) -> None:
        runner = make_runner()
        result = runner.invoke(main, ["--help"])
        assert "--url" in result.output

    def test_help_mentions_file_option(self) -> None:
        runner = make_runner()
        result = runner.invoke(main, ["--help"])
        assert "--file" in result.output

    def test_help_mentions_style_option(self) -> None:
        runner = make_runner()
        result = runner.invoke(main, ["--help"])
        assert "--style" in result.output

    def test_help_mentions_format_option(self) -> None:
        runner = make_runner()
        result = runner.invoke(main, ["--help"])
        assert "--format" in result.output

    def test_version_flag(self) -> None:
        runner = make_runner()
        result = runner.invoke(main, ["--version"])
        assert result.exit_code == 0
        assert __version__ in result.output


# ---------------------------------------------------------------------------
# Missing / invalid input errors
# ---------------------------------------------------------------------------


class TestInputValidation:
    """Missing or invalid inputs should produce a non-zero exit code."""

    def test_no_input_exits_nonzero(self) -> None:
        runner = make_runner()
        result = runner.invoke(main, [])
        assert result.exit_code != 0

    def test_no_input_shows_error_message(self) -> None:
        runner = make_runner()
        result = runner.invoke(main, [])
        combined = result.output + (result.stderr or "")
        assert "url" in combined.lower() or "file" in combined.lower() or "error" in combined.lower()

    def test_both_url_and_file_exits_nonzero(self) -> None:
        runner = make_runner()
        with runner.isolated_filesystem():
            Path("doc.txt").write_text("hello")
            result = runner.invoke(main, ["--url", "https://example.com", "--file", "doc.txt"])
        assert result.exit_code != 0

    def test_invalid_url_exits_nonzero(self) -> None:
        runner = make_runner()
        result = runner.invoke(main, ["--url", "not-a-valid-url"])
        assert result.exit_code != 0

    def test_invalid_url_scheme_exits_nonzero(self) -> None:
        runner = make_runner()
        result = runner.invoke(main, ["--url", "ftp-ish://bad"])
        assert result.exit_code != 0

    def test_nonexistent_file_exits_nonzero(self) -> None:
        runner = make_runner()
        result = runner.invoke(main, ["--file", "/nonexistent/path/document.txt"])
        assert result.exit_code != 0

    def test_invalid_style_choice_exits_nonzero(self) -> None:
        runner = make_runner()
        result = runner.invoke(main, ["--url", "https://example.com", "--style", "haiku"])
        assert result.exit_code != 0

    def test_invalid_format_choice_exits_nonzero(self) -> None:
        runner = make_runner()
        result = runner.invoke(main, ["--url", "https://example.com", "--format", "xml"])
        assert result.exit_code != 0


# ---------------------------------------------------------------------------
# Valid URL input — placeholder output
# ---------------------------------------------------------------------------


class TestValidUrl:
    """A valid URL should produce exit code 0 and a placeholder response."""

    def test_valid_http_url_exits_zero(self) -> None:
        runner = make_runner()
        result = runner.invoke(main, ["--url", "https://example.com"])
        assert result.exit_code == 0, result.output

    def test_valid_url_output_contains_placeholder(self) -> None:
        runner = make_runner()
        result = runner.invoke(main, ["--url", "https://example.com"])
        assert "placeholder" in result.output.lower() or "not yet implemented" in result.output.lower()

    def test_valid_url_output_contains_url(self) -> None:
        runner = make_runner()
        result = runner.invoke(main, ["--url", "https://example.com"])
        assert "https://example.com" in result.output

    def test_json_format_is_valid_json(self) -> None:
        runner = make_runner()
        result = runner.invoke(main, ["--url", "https://example.com", "--format", "json"])
        assert result.exit_code == 0, result.output
        # The output should be parseable JSON
        data = json.loads(result.output)
        assert isinstance(data, dict)

    def test_json_format_has_expected_keys(self) -> None:
        runner = make_runner()
        result = runner.invoke(main, ["--url", "https://example.com", "--format", "json"])
        data = json.loads(result.output)
        assert "status" in data
        assert "input_type" in data
        assert "input_value" in data

    def test_markdown_format_output(self) -> None:
        runner = make_runner()
        result = runner.invoke(main, ["--url", "https://example.com", "--format", "markdown"])
        assert result.exit_code == 0
        assert "#" in result.output  # markdown heading

    def test_bullet_style_accepted(self) -> None:
        runner = make_runner()
        result = runner.invoke(main, ["--url", "https://example.com", "--style", "bullet"])
        assert result.exit_code == 0

    def test_tldr_style_accepted(self) -> None:
        runner = make_runner()
        result = runner.invoke(main, ["--url", "https://example.com", "--style", "tldr"])
        assert result.exit_code == 0


# ---------------------------------------------------------------------------
# Valid file input — placeholder output
# ---------------------------------------------------------------------------


class TestValidFile:
    """A valid readable file should produce exit code 0 and a placeholder response."""

    def test_valid_file_exits_zero(self) -> None:
        runner = make_runner()
        with runner.isolated_filesystem():
            Path("sample.txt").write_text("This is a test document.")
            result = runner.invoke(main, ["--file", "sample.txt"])
        assert result.exit_code == 0, result.output

    def test_valid_file_output_contains_placeholder(self) -> None:
        runner = make_runner()
        with runner.isolated_filesystem():
            Path("sample.txt").write_text("This is a test document.")
            result = runner.invoke(main, ["--file", "sample.txt"])
        assert "placeholder" in result.output.lower() or "not yet implemented" in result.output.lower()

    def test_valid_file_json_output(self) -> None:
        runner = make_runner()
        with runner.isolated_filesystem():
            Path("doc.txt").write_text("Content here.")
            result = runner.invoke(main, ["--file", "doc.txt", "--format", "json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["input_type"] == "file"


# ---------------------------------------------------------------------------
# Verbose flag
# ---------------------------------------------------------------------------


class TestVerboseFlag:
    """--verbose should not cause the command to fail."""

    def test_verbose_flag_with_url(self) -> None:
        runner = make_runner()
        result = runner.invoke(main, ["--url", "https://example.com", "--verbose"])
        assert result.exit_code == 0, result.output

    def test_verbose_flag_with_file(self) -> None:
        runner = make_runner()
        with runner.isolated_filesystem():
            Path("doc.txt").write_text("hello world")
            result = runner.invoke(main, ["--file", "doc.txt", "--verbose"])
        assert result.exit_code == 0, result.output
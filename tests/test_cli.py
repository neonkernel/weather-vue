"""
Smoke tests for the summarizer CLI.

Uses Click's CliRunner so no real HTTP requests or file I/O are needed
for the basic validation scenarios.
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


def invoke(*args: str, env: dict | None = None):
    """Invoke the CLI with the given arguments and return the result."""
    runner = CliRunner(mix_stderr=False)
    # Provide a dummy API key so config loading doesn't warn during tests
    default_env = {"OPENAI_API_KEY": "test-key-placeholder"}
    if env:
        default_env.update(env)
    return runner.invoke(main, list(args), env=default_env, catch_exceptions=False)


# ---------------------------------------------------------------------------
# Basic importability
# ---------------------------------------------------------------------------


class TestImportability:
    def test_package_importable(self):
        """The summarizer package should be importable."""
        import summarizer  # noqa: F401

    def test_version_is_string(self):
        """__version__ should be a non-empty string."""
        assert isinstance(__version__, str)
        assert __version__

    def test_cli_importable(self):
        """The cli module should be importable."""
        from summarizer import cli  # noqa: F401


# ---------------------------------------------------------------------------
# --help
# ---------------------------------------------------------------------------


class TestHelp:
    def test_help_exits_zero(self):
        result = invoke("--help")
        assert result.exit_code == 0

    def test_help_contains_usage(self):
        result = invoke("--help")
        assert "Usage:" in result.output

    def test_help_lists_url_option(self):
        result = invoke("--help")
        assert "--url" in result.output

    def test_help_lists_file_option(self):
        result = invoke("--help")
        assert "--file" in result.output

    def test_help_lists_style_option(self):
        result = invoke("--help")
        assert "--style" in result.output

    def test_help_lists_format_option(self):
        result = invoke("--help")
        assert "--format" in result.output

    def test_short_help_flag(self):
        result = invoke("-h")
        assert result.exit_code == 0

    def test_version_flag(self):
        result = invoke("--version")
        assert result.exit_code == 0
        assert __version__ in result.output


# ---------------------------------------------------------------------------
# Missing / invalid input
# ---------------------------------------------------------------------------


class TestMissingInput:
    def test_no_input_exits_nonzero(self):
        result = invoke()
        assert result.exit_code != 0

    def test_no_input_shows_error(self):
        result = invoke()
        # Error message should appear on stderr
        assert "Error" in (result.stderr or result.output)

    def test_both_url_and_file_exits_nonzero(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("hello world")
            tmp_path = f.name
        try:
            result = invoke("--url", "https://example.com", "--file", tmp_path)
            assert result.exit_code != 0
        finally:
            os.unlink(tmp_path)

    def test_invalid_url_exits_nonzero(self):
        result = invoke("--url", "not-a-url")
        assert result.exit_code != 0

    def test_invalid_url_shows_error(self):
        result = invoke("--url", "not-a-url")
        assert "Error" in (result.stderr or result.output)

    def test_nonexistent_file_exits_nonzero(self):
        result = invoke("--file", "/nonexistent/path/that/does/not/exist.txt")
        assert result.exit_code != 0

    def test_nonexistent_file_shows_error(self):
        result = invoke("--file", "/nonexistent/path/that/does/not/exist.txt")
        assert "Error" in (result.stderr or result.output)


# ---------------------------------------------------------------------------
# Valid URL input
# ---------------------------------------------------------------------------


class TestValidUrl:
    def test_valid_url_exits_zero(self):
        result = invoke("--url", "https://example.com")
        assert result.exit_code == 0

    def test_valid_url_shows_placeholder(self):
        result = invoke("--url", "https://example.com")
        assert "PLACEHOLDER" in result.output

    def test_valid_url_echoes_url(self):
        url = "https://example.com/article"
        result = invoke("--url", url)
        assert url in result.output

    def test_http_url_accepted(self):
        result = invoke("--url", "http://example.com")
        assert result.exit_code == 0


# ---------------------------------------------------------------------------
# Valid file input
# ---------------------------------------------------------------------------


class TestValidFile:
    def test_valid_file_exits_zero(self, tmp_path: Path):
        doc = tmp_path / "doc.txt"
        doc.write_text("Some content here.")
        result = invoke("--file", str(doc))
        assert result.exit_code == 0

    def test_valid_file_shows_placeholder(self, tmp_path: Path):
        doc = tmp_path / "doc.txt"
        doc.write_text("Some content here.")
        result = invoke("--file", str(doc))
        assert "PLACEHOLDER" in result.output

    def test_valid_file_echoes_path(self, tmp_path: Path):
        doc = tmp_path / "report.txt"
        doc.write_text("Report content.")
        result = invoke("--file", str(doc))
        assert str(doc) in result.output


# ---------------------------------------------------------------------------
# Style and format options
# ---------------------------------------------------------------------------


class TestStyleAndFormat:
    @pytest.mark.parametrize("style", ["brief", "detailed", "bullets"])
    def test_valid_styles_accepted(self, style: str):
        result = invoke("--url", "https://example.com", "--style", style)
        assert result.exit_code == 0

    def test_invalid_style_exits_nonzero(self):
        result = invoke("--url", "https://example.com", "--style", "nonsense")
        assert result.exit_code != 0

    @pytest.mark.parametrize("fmt", ["text", "markdown", "json"])
    def test_valid_formats_accepted(self, fmt: str):
        result = invoke("--url", "https://example.com", "--format", fmt)
        assert result.exit_code == 0

    def test_invalid_format_exits_nonzero(self):
        result = invoke("--url", "https://example.com", "--format", "xml")
        assert result.exit_code != 0

    def test_json_output_is_valid_json(self):
        result = invoke("--url", "https://example.com", "--format", "json")
        assert result.exit_code == 0
        payload = json.loads(result.output)
        assert payload["status"] == "placeholder"
        assert payload["input_type"] == "url"

    def test_markdown_output_contains_heading(self):
        result = invoke("--url", "https://example.com", "--format", "markdown")
        assert result.exit_code == 0
        assert "## Summary" in result.output


# ---------------------------------------------------------------------------
# Config / env
# ---------------------------------------------------------------------------


class TestConfig:
    def test_runs_without_api_key(self):
        """The tool should still run (placeholder) even without an API key."""
        runner = CliRunner(mix_stderr=False)
        result = runner.invoke(
            main,
            ["--url", "https://example.com"],
            env={},
            catch_exceptions=False,
        )
        assert result.exit_code == 0
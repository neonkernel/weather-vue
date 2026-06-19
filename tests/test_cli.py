"""
Smoke tests for the Summarizer CLI (Phase 1).

Uses Click's CliRunner to invoke the CLI in-process without spawning a
subprocess, making tests fast and easy to debug.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from summarizer import __version__
from summarizer.cli import main


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def runner() -> CliRunner:
    """Return a Click CliRunner with isolated filesystem support."""
    return CliRunner()


@pytest.fixture()
def tmp_text_file(tmp_path: Path) -> Path:
    """Create a temporary text file with some content."""
    file = tmp_path / "sample.txt"
    file.write_text("This is a sample document for testing.", encoding="utf-8")
    return file


# ---------------------------------------------------------------------------
# Import / package smoke tests
# ---------------------------------------------------------------------------


class TestImports:
    def test_package_is_importable(self) -> None:
        """The summarizer package should be importable."""
        import summarizer  # noqa: F401

    def test_version_string_exists(self) -> None:
        """__version__ should be a non-empty string."""
        assert isinstance(__version__, str)
        assert __version__

    def test_cli_main_is_callable(self) -> None:
        """The main click command should be a callable."""
        assert callable(main)


# ---------------------------------------------------------------------------
# --help
# ---------------------------------------------------------------------------


class TestHelp:
    def test_help_exits_zero(self, runner: CliRunner) -> None:
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0

    def test_help_mentions_url_option(self, runner: CliRunner) -> None:
        result = runner.invoke(main, ["--help"])
        assert "--url" in result.output

    def test_help_mentions_file_option(self, runner: CliRunner) -> None:
        result = runner.invoke(main, ["--help"])
        assert "--file" in result.output

    def test_help_mentions_style_option(self, runner: CliRunner) -> None:
        result = runner.invoke(main, ["--help"])
        assert "--style" in result.output

    def test_help_mentions_format_option(self, runner: CliRunner) -> None:
        result = runner.invoke(main, ["--help"])
        assert "--format" in result.output

    def test_help_mentions_verbose_option(self, runner: CliRunner) -> None:
        result = runner.invoke(main, ["--help"])
        assert "--verbose" in result.output


# ---------------------------------------------------------------------------
# --version
# ---------------------------------------------------------------------------


class TestVersion:
    def test_version_flag_exits_zero(self, runner: CliRunner) -> None:
        result = runner.invoke(main, ["--version"])
        assert result.exit_code == 0

    def test_version_output_contains_version_string(self, runner: CliRunner) -> None:
        result = runner.invoke(main, ["--version"])
        assert __version__ in result.output


# ---------------------------------------------------------------------------
# Input validation — missing input
# ---------------------------------------------------------------------------


class TestMissingInput:
    def test_no_args_exits_nonzero(self, runner: CliRunner) -> None:
        result = runner.invoke(main, [])
        assert result.exit_code != 0

    def test_no_args_shows_error(self, runner: CliRunner) -> None:
        result = runner.invoke(main, [])
        combined = result.output + (result.exception.__str__() if result.exception else "")
        # Click prints UsageError to output; check output or the exception message
        assert "url" in result.output.lower() or "file" in result.output.lower()

    def test_both_url_and_file_exits_nonzero(
        self, runner: CliRunner, tmp_text_file: Path
    ) -> None:
        result = runner.invoke(
            main, ["--url", "https://example.com", "--file", str(tmp_text_file)]
        )
        assert result.exit_code != 0

    def test_both_url_and_file_shows_error(
        self, runner: CliRunner, tmp_text_file: Path
    ) -> None:
        result = runner.invoke(
            main, ["--url", "https://example.com", "--file", str(tmp_text_file)]
        )
        assert "both" in result.output.lower() or "either" in result.output.lower()


# ---------------------------------------------------------------------------
# Input validation — invalid URL
# ---------------------------------------------------------------------------


class TestInvalidUrl:
    @pytest.mark.parametrize(
        "bad_url",
        [
            "not-a-url",
            "ftp://example.com",
            "example.com",
            "",
            "javascript:alert(1)",
        ],
    )
    def test_bad_url_exits_nonzero(self, runner: CliRunner, bad_url: str) -> None:
        if bad_url == "":
            # Empty string: click will see --url with no value
            result = runner.invoke(main, ["--url"])
        else:
            result = runner.invoke(main, ["--url", bad_url])
        assert result.exit_code != 0

    def test_bad_url_shows_error(self, runner: CliRunner) -> None:
        result = runner.invoke(main, ["--url", "not-a-url"])
        assert result.exit_code != 0


# ---------------------------------------------------------------------------
# Input validation — invalid file
# ---------------------------------------------------------------------------


class TestInvalidFile:
    def test_nonexistent_file_exits_nonzero(self, runner: CliRunner) -> None:
        result = runner.invoke(main, ["--file", "/nonexistent/path/file.txt"])
        assert result.exit_code != 0

    def test_nonexistent_file_shows_error(self, runner: CliRunner) -> None:
        result = runner.invoke(main, ["--file", "/nonexistent/path/file.txt"])
        assert result.exit_code != 0


# ---------------------------------------------------------------------------
# Happy path — URL
# ---------------------------------------------------------------------------


class TestUrlHappyPath:
    def test_valid_url_exits_zero(self, runner: CliRunner) -> None:
        result = runner.invoke(main, ["--url", "https://example.com"])
        assert result.exit_code == 0

    def test_valid_url_prints_placeholder(self, runner: CliRunner) -> None:
        result = runner.invoke(main, ["--url", "https://example.com"])
        assert "placeholder" in result.output.lower()

    def test_valid_url_echoes_url(self, runner: CliRunner) -> None:
        result = runner.invoke(main, ["--url", "https://example.com"])
        assert "https://example.com" in result.output

    def test_http_url_is_accepted(self, runner: CliRunner) -> None:
        result = runner.invoke(main, ["--url", "http://example.com/page"])
        assert result.exit_code == 0


# ---------------------------------------------------------------------------
# Happy path — file
# ---------------------------------------------------------------------------


class TestFileHappyPath:
    def test_valid_file_exits_zero(self, runner: CliRunner, tmp_text_file: Path) -> None:
        result = runner.invoke(main, ["--file", str(tmp_text_file)])
        assert result.exit_code == 0

    def test_valid_file_prints_placeholder(
        self, runner: CliRunner, tmp_text_file: Path
    ) -> None:
        result = runner.invoke(main, ["--file", str(tmp_text_file)])
        assert "placeholder" in result.output.lower()

    def test_valid_file_echoes_path(self, runner: CliRunner, tmp_text_file: Path) -> None:
        result = runner.invoke(main, ["--file", str(tmp_text_file)])
        assert str(tmp_text_file) in result.output


# ---------------------------------------------------------------------------
# Style option
# ---------------------------------------------------------------------------


class TestStyleOption:
    @pytest.mark.parametrize("style", ["brief", "detailed", "bullets"])
    def test_valid_style_exits_zero(self, runner: CliRunner, style: str) -> None:
        result = runner.invoke(main, ["--url", "https://example.com", "--style", style])
        assert result.exit_code == 0

    def test_invalid_style_exits_nonzero(self, runner: CliRunner) -> None:
        result = runner.invoke(
            main, ["--url", "https://example.com", "--style", "haiku"]
        )
        assert result.exit_code != 0

    def test_default_style_is_brief(self, runner: CliRunner) -> None:
        result = runner.invoke(main, ["--url", "https://example.com"])
        assert "brief" in result.output.lower()


# ---------------------------------------------------------------------------
# Format option
# ---------------------------------------------------------------------------


class TestFormatOption:
    def test_text_format_exits_zero(self, runner: CliRunner) -> None:
        result = runner.invoke(
            main, ["--url", "https://example.com", "--format", "text"]
        )
        assert result.exit_code == 0

    def test_markdown_format_exits_zero(self, runner: CliRunner) -> None:
        result = runner.invoke(
            main, ["--url", "https://example.com", "--format", "markdown"]
        )
        assert result.exit_code == 0

    def test_markdown_format_contains_heading(self, runner: CliRunner) -> None:
        result = runner.invoke(
            main, ["--url", "https://example.com", "--format", "markdown"]
        )
        assert "##" in result.output

    def test_json_format_exits_zero(self, runner: CliRunner) -> None:
        result = runner.invoke(
            main, ["--url", "https://example.com", "--format", "json"]
        )
        assert result.exit_code == 0

    def test_json_format_is_valid_json(self, runner: CliRunner) -> None:
        result = runner.invoke(
            main, ["--url", "https://example.com", "--format", "json"]
        )
        assert result.exit_code == 0
        parsed = json.loads(result.output)
        assert "summary" in parsed
        assert "input" in parsed

    def test_json_format_contains_input_value(self, runner: CliRunner) -> None:
        result = runner.invoke(
            main, ["--url", "https://example.com", "--format", "json"]
        )
        parsed = json.loads(result.output)
        assert parsed["input"] == "https://example.com"

    def test_invalid_format_exits_nonzero(self, runner: CliRunner) -> None:
        result = runner.invoke(
            main, ["--url", "https://example.com", "--format", "xml"]
        )
        assert result.exit_code != 0


# ---------------------------------------------------------------------------
# Verbose flag
# ---------------------------------------------------------------------------


class TestVerboseFlag:
    def test_verbose_flag_exits_zero(self, runner: CliRunner) -> None:
        result = runner.invoke(main, ["--url", "https://example.com", "--verbose"])
        assert result.exit_code == 0

    def test_short_verbose_flag_exits_zero(self, runner: CliRunner) -> None:
        result = runner.invoke(main, ["--url", "https://example.com", "-v"])
        assert result.exit_code == 0
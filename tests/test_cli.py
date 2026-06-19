"""
Smoke tests for the Summarizer CLI.

Uses Click's CliRunner so no real HTTP requests or filesystem side-effects
are made.  These tests verify:

  1. The package is importable and exposes a version string.
  2. ``summarize --help`` exits 0 and prints usage information.
  3. Calling ``summarize`` without any input flags prints a usage error.
  4. Providing both --url and --file at the same time is rejected.
  5. An invalid URL is rejected with a meaningful error.
  6. A non-existent file path is rejected with a meaningful error.
  7. A valid URL produces the placeholder output.
  8. A valid file path produces the placeholder output.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest
from click.testing import CliRunner

# ---------------------------------------------------------------------------
# Package importability
# ---------------------------------------------------------------------------


def test_package_is_importable() -> None:
    """The summarizer package must be importable."""
    import summarizer  # noqa: F401


def test_version_string_is_defined() -> None:
    """The package must expose a __version__ string."""
    from summarizer import __version__

    assert isinstance(__version__, str)
    assert len(__version__) > 0


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def runner() -> CliRunner:
    """Return a Click CliRunner instance."""
    return CliRunner()


@pytest.fixture()
def cli():
    """Return the main Click command."""
    from summarizer.cli import main

    return main


@pytest.fixture()
def tmp_text_file(tmp_path: Path) -> Path:
    """Create a temporary text file and return its path."""
    f = tmp_path / "sample.txt"
    f.write_text("This is a sample document for testing.")
    return f


# ---------------------------------------------------------------------------
# --help
# ---------------------------------------------------------------------------


def test_help_exits_zero(runner: CliRunner, cli) -> None:
    """``summarize --help`` should exit with code 0."""
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0


def test_help_contains_usage(runner: CliRunner, cli) -> None:
    """``summarize --help`` output should contain 'Usage'."""
    result = runner.invoke(cli, ["--help"])
    assert "Usage" in result.output or "usage" in result.output.lower()


def test_help_mentions_url_option(runner: CliRunner, cli) -> None:
    """--help output should mention the --url option."""
    result = runner.invoke(cli, ["--help"])
    assert "--url" in result.output


def test_help_mentions_file_option(runner: CliRunner, cli) -> None:
    """--help output should mention the --file option."""
    result = runner.invoke(cli, ["--help"])
    assert "--file" in result.output


# ---------------------------------------------------------------------------
# Missing input
# ---------------------------------------------------------------------------


def test_no_input_shows_error(runner: CliRunner, cli) -> None:
    """Running without --url or --file should produce a usage error."""
    result = runner.invoke(cli, [])
    # Click UsageError exits with code 2.
    assert result.exit_code != 0
    combined = result.output + (result.stderr if hasattr(result, "stderr") else "")
    assert "url" in combined.lower() or "file" in combined.lower() or "error" in combined.lower()


# ---------------------------------------------------------------------------
# Mutually exclusive inputs
# ---------------------------------------------------------------------------


def test_both_url_and_file_rejected(
    runner: CliRunner, cli, tmp_text_file: Path
) -> None:
    """Providing both --url and --file should be rejected."""
    result = runner.invoke(
        cli,
        ["--url", "https://example.com", "--file", str(tmp_text_file)],
    )
    assert result.exit_code != 0


# ---------------------------------------------------------------------------
# URL validation
# ---------------------------------------------------------------------------


def test_invalid_url_rejected(runner: CliRunner, cli) -> None:
    """A string that is not a valid http/https URL should be rejected."""
    result = runner.invoke(cli, ["--url", "not-a-url"])
    assert result.exit_code != 0
    combined = result.output + (result.stderr if hasattr(result, "stderr") else "")
    assert "url" in combined.lower() or "invalid" in combined.lower() or "error" in combined.lower()


def test_ftp_url_rejected(runner: CliRunner, cli) -> None:
    """An ftp:// URL should be rejected (only http/https are allowed)."""
    result = runner.invoke(cli, ["--url", "ftp://example.com/file.txt"])
    assert result.exit_code != 0


def test_valid_url_succeeds(runner: CliRunner, cli) -> None:
    """A valid https URL should produce the placeholder output."""
    result = runner.invoke(cli, ["--url", "https://example.com/article"])
    assert result.exit_code == 0
    assert "placeholder" in result.output.lower() or "phase" in result.output.lower()


def test_valid_http_url_succeeds(runner: CliRunner, cli) -> None:
    """A valid http URL should also be accepted."""
    result = runner.invoke(cli, ["--url", "http://example.com"])
    assert result.exit_code == 0


# ---------------------------------------------------------------------------
# File validation
# ---------------------------------------------------------------------------


def test_nonexistent_file_rejected(runner: CliRunner, cli) -> None:
    """A path that does not exist should be rejected."""
    result = runner.invoke(cli, ["--file", "/nonexistent/path/to/file.txt"])
    assert result.exit_code != 0
    combined = result.output + (result.stderr if hasattr(result, "stderr") else "")
    assert "file" in combined.lower() or "error" in combined.lower() or "not found" in combined.lower()


def test_valid_file_succeeds(runner: CliRunner, cli, tmp_text_file: Path) -> None:
    """An existing, readable file should produce the placeholder output."""
    result = runner.invoke(cli, ["--file", str(tmp_text_file)])
    assert result.exit_code == 0
    assert "placeholder" in result.output.lower() or "phase" in result.output.lower()


# ---------------------------------------------------------------------------
# Style and format options
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("style", ["paragraph", "bullet", "tldr"])
def test_valid_styles_accepted(
    runner: CliRunner, cli, style: str, tmp_text_file: Path
) -> None:
    """All valid --style values should be accepted."""
    result = runner.invoke(cli, ["--file", str(tmp_text_file), "--style", style])
    assert result.exit_code == 0


def test_invalid_style_rejected(
    runner: CliRunner, cli, tmp_text_file: Path
) -> None:
    """An unknown --style value should be rejected."""
    result = runner.invoke(cli, ["--file", str(tmp_text_file), "--style", "haiku"])
    assert result.exit_code != 0


@pytest.mark.parametrize("fmt", ["plain", "markdown", "json"])
def test_valid_formats_accepted(
    runner: CliRunner, cli, fmt: str, tmp_text_file: Path
) -> None:
    """All valid --format values should be accepted."""
    result = runner.invoke(cli, ["--file", str(tmp_text_file), "--format", fmt])
    assert result.exit_code == 0


def test_invalid_format_rejected(
    runner: CliRunner, cli, tmp_text_file: Path
) -> None:
    """An unknown --format value should be rejected."""
    result = runner.invoke(cli, ["--file", str(tmp_text_file), "--format", "xml"])
    assert result.exit_code != 0


# ---------------------------------------------------------------------------
# Verbose flag
# ---------------------------------------------------------------------------


def test_verbose_flag_accepted(
    runner: CliRunner, cli, tmp_text_file: Path
) -> None:
    """The --verbose flag should not cause an error."""
    result = runner.invoke(cli, ["--file", str(tmp_text_file), "--verbose"])
    assert result.exit_code == 0


# ---------------------------------------------------------------------------
# Version flag
# ---------------------------------------------------------------------------


def test_version_flag(runner: CliRunner, cli) -> None:
    """``summarize --version`` should exit 0 and print the version."""
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    from summarizer import __version__

    assert __version__ in result.output
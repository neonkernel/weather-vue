"""
Smoke tests for the summarizer CLI.

Uses Click's CliRunner so no real network calls or file-system side-effects
are produced during the test run.
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


# ------------------------------------------------------------------ #
# Fixtures                                                             #
# ------------------------------------------------------------------ #


@pytest.fixture()
def runner() -> CliRunner:
    """Return a Click CliRunner that mixes stderr into stdout."""
    return CliRunner(mix_stderr=False)


@pytest.fixture()
def tmp_text_file(tmp_path: Path) -> Path:
    """Create a small temporary text file for --file tests."""
    p = tmp_path / "sample.txt"
    p.write_text("Hello, this is a sample document for testing.\n")
    return p


# ------------------------------------------------------------------ #
# Importability                                                        #
# ------------------------------------------------------------------ #


def test_package_is_importable() -> None:
    """The summarizer package must be importable and expose a version string."""
    import summarizer  # noqa: F401

    assert isinstance(__version__, str)
    assert len(__version__) > 0


def test_cli_is_importable() -> None:
    """The CLI entry point must be importable."""
    from summarizer.cli import main as cli_main  # noqa: F401


# ------------------------------------------------------------------ #
# --help                                                               #
# ------------------------------------------------------------------ #


def test_help_exits_zero(runner: CliRunner) -> None:
    """Running `summarize --help` should exit with code 0."""
    result = runner.invoke(main, ["--help"])
    assert result.exit_code == 0


def test_help_contains_expected_options(runner: CliRunner) -> None:
    """Help text should mention key options."""
    result = runner.invoke(main, ["--help"])
    output = result.output
    assert "--url" in output
    assert "--file" in output
    assert "--style" in output
    assert "--format" in output
    assert "--verbose" in output


# ------------------------------------------------------------------ #
# --version                                                            #
# ------------------------------------------------------------------ #


def test_version_flag(runner: CliRunner) -> None:
    """--version should print the current version and exit 0."""
    result = runner.invoke(main, ["--version"])
    assert result.exit_code == 0
    assert __version__ in result.output


# ------------------------------------------------------------------ #
# Missing / conflicting input                                          #
# ------------------------------------------------------------------ #


def test_missing_input_shows_error(runner: CliRunner) -> None:
    """Invoking without --url or --file should exit with a non-zero code."""
    result = runner.invoke(main, [])
    assert result.exit_code != 0


def test_missing_input_error_message(runner: CliRunner) -> None:
    """Error message should guide the user toward --url or --file."""
    result = runner.invoke(main, [])
    combined = (result.output or "") + (result.stderr or "")
    assert "--url" in combined or "--file" in combined or "Usage" in combined


def test_both_url_and_file_shows_error(runner: CliRunner, tmp_text_file: Path) -> None:
    """Providing both --url and --file should be rejected."""
    result = runner.invoke(
        main,
        ["--url", "https://example.com", "--file", str(tmp_text_file)],
    )
    assert result.exit_code != 0


# ------------------------------------------------------------------ #
# --url validation                                                     #
# ------------------------------------------------------------------ #


def test_invalid_url_shows_error(runner: CliRunner) -> None:
    """A non-URL string passed to --url should produce an error."""
    result = runner.invoke(main, ["--url", "not-a-url"])
    assert result.exit_code != 0


def test_valid_url_exits_zero(runner: CliRunner) -> None:
    """A valid https URL should be accepted and produce a placeholder output."""
    result = runner.invoke(main, ["--url", "https://example.com/article"])
    assert result.exit_code == 0
    assert "PLACEHOLDER" in result.output or "placeholder" in result.output.lower()


def test_http_url_is_accepted(runner: CliRunner) -> None:
    """http:// URLs should also be accepted (not just https://)."""
    result = runner.invoke(main, ["--url", "http://example.com"])
    assert result.exit_code == 0


# ------------------------------------------------------------------ #
# --file validation                                                    #
# ------------------------------------------------------------------ #


def test_nonexistent_file_shows_error(runner: CliRunner) -> None:
    """A path that does not exist should be rejected."""
    result = runner.invoke(main, ["--file", "/nonexistent/path/to/file.txt"])
    assert result.exit_code != 0


def test_valid_file_exits_zero(runner: CliRunner, tmp_text_file: Path) -> None:
    """A readable file should be accepted and produce a placeholder output."""
    result = runner.invoke(main, ["--file", str(tmp_text_file)])
    assert result.exit_code == 0
    assert "PLACEHOLDER" in result.output or "placeholder" in result.output.lower()


# ------------------------------------------------------------------ #
# --style and --format options                                         #
# ------------------------------------------------------------------ #


@pytest.mark.parametrize("style", ["brief", "detailed", "bullets"])
def test_valid_styles(runner: CliRunner, style: str) -> None:
    """All documented style values should be accepted."""
    result = runner.invoke(main, ["--url", "https://example.com", "--style", style])
    assert result.exit_code == 0


def test_invalid_style_shows_error(runner: CliRunner) -> None:
    """An unrecognised style value should be rejected."""
    result = runner.invoke(main, ["--url", "https://example.com", "--style", "unknown"])
    assert result.exit_code != 0


@pytest.mark.parametrize("fmt", ["text", "markdown", "json"])
def test_valid_formats(runner: CliRunner, fmt: str) -> None:
    """All documented output format values should be accepted."""
    result = runner.invoke(main, ["--url", "https://example.com", "--format", fmt])
    assert result.exit_code == 0


def test_invalid_format_shows_error(runner: CliRunner) -> None:
    """An unrecognised format value should be rejected."""
    result = runner.invoke(main, ["--url", "https://example.com", "--format", "xml"])
    assert result.exit_code != 0


# ------------------------------------------------------------------ #
# JSON output format                                                   #
# ------------------------------------------------------------------ #


def test_json_output_is_valid_json(runner: CliRunner) -> None:
    """When --format json is used the output must be valid JSON."""
    result = runner.invoke(
        main, ["--url", "https://example.com", "--format", "json"]
    )
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert "status" in parsed
    assert "summary" in parsed


# ------------------------------------------------------------------ #
# --verbose flag                                                       #
# ------------------------------------------------------------------ #


def test_verbose_flag_accepted(runner: CliRunner) -> None:
    """The --verbose flag should be accepted without error."""
    result = runner.invoke(main, ["--url", "https://example.com", "--verbose"])
    assert result.exit_code == 0
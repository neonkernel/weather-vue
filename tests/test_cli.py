"""
Smoke tests for the summarizer CLI.

Covers:
- Package importability
- --version flag
- --help flag
- Missing input shows a clear error
- --url with a valid URL returns a placeholder
- --file with a valid file returns a placeholder
- Providing both --url and --file is rejected
- Invalid URL is rejected
- Non-existent file is rejected
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

import pytest
from click.testing import CliRunner

# --------------------------------------------------------------------------- #
# Importability                                                                #
# --------------------------------------------------------------------------- #


def test_package_is_importable() -> None:
    """The summarizer package must be importable without errors."""
    import summarizer  # noqa: F401

    assert summarizer.__version__, "Package should expose a non-empty __version__"


def test_cli_is_importable() -> None:
    """The CLI module and main command must be importable."""
    from summarizer.cli import main  # noqa: F401

    assert callable(main)


# --------------------------------------------------------------------------- #
# Fixtures                                                                     #
# --------------------------------------------------------------------------- #


@pytest.fixture()
def runner() -> CliRunner:
    """Return a Click test runner that mixes stdout/stderr."""
    return CliRunner(mix_stderr=False)


@pytest.fixture()
def tmp_text_file(tmp_path: Path) -> str:
    """Create a temporary text file and return its path as a string."""
    p = tmp_path / "sample.txt"
    p.write_text("Hello, summarizer!")
    return str(p)


# --------------------------------------------------------------------------- #
# --help / --version                                                           #
# --------------------------------------------------------------------------- #


def test_help_flag(runner: CliRunner) -> None:
    """--help should exit 0 and print usage information."""
    from summarizer.cli import main

    result = runner.invoke(main, ["--help"])
    assert result.exit_code == 0, result.output
    assert "Usage:" in result.output
    assert "--url" in result.output
    assert "--file" in result.output


def test_version_flag(runner: CliRunner) -> None:
    """--version should exit 0 and print the package version."""
    from summarizer.cli import main
    from summarizer import __version__

    result = runner.invoke(main, ["--version"])
    assert result.exit_code == 0, result.output
    assert __version__ in result.output


# --------------------------------------------------------------------------- #
# Input validation — missing / conflicting inputs                              #
# --------------------------------------------------------------------------- #


def test_no_input_shows_error(runner: CliRunner) -> None:
    """Invoking with no --url or --file should exit non-zero with a helpful message."""
    from summarizer.cli import main

    result = runner.invoke(main, [])
    assert result.exit_code != 0
    output = result.output + (result.stderr or "")
    assert "--url" in output or "input" in output.lower() or "Usage" in output


def test_both_url_and_file_rejected(runner: CliRunner, tmp_text_file: str) -> None:
    """Providing both --url and --file should be rejected."""
    from summarizer.cli import main

    result = runner.invoke(
        main,
        ["--url", "https://example.com", "--file", tmp_text_file],
    )
    assert result.exit_code != 0
    combined = result.output + (result.stderr or "")
    assert "both" in combined.lower() or "either" in combined.lower()


# --------------------------------------------------------------------------- #
# Input validation — URL                                                       #
# --------------------------------------------------------------------------- #


def test_valid_url_returns_placeholder(runner: CliRunner) -> None:
    """A valid URL should produce a placeholder summary and exit 0."""
    from summarizer.cli import main

    result = runner.invoke(main, ["--url", "https://example.com/article"])
    assert result.exit_code == 0, result.output
    assert "Placeholder" in result.output or "placeholder" in result.output.lower()
    assert "https://example.com/article" in result.output


def test_invalid_url_rejected(runner: CliRunner) -> None:
    """A string that doesn't look like a URL should be rejected."""
    from summarizer.cli import main

    result = runner.invoke(main, ["--url", "not-a-url"])
    assert result.exit_code != 0
    combined = result.output + (result.stderr or "")
    assert "url" in combined.lower() or "http" in combined.lower()


def test_url_without_scheme_rejected(runner: CliRunner) -> None:
    """A URL missing the scheme (http/https) should be rejected."""
    from summarizer.cli import main

    result = runner.invoke(main, ["--url", "example.com/article"])
    assert result.exit_code != 0


# --------------------------------------------------------------------------- #
# Input validation — file                                                      #
# --------------------------------------------------------------------------- #


def test_valid_file_returns_placeholder(runner: CliRunner, tmp_text_file: str) -> None:
    """A readable file path should produce a placeholder summary and exit 0."""
    from summarizer.cli import main

    result = runner.invoke(main, ["--file", tmp_text_file])
    assert result.exit_code == 0, result.output
    assert "Placeholder" in result.output or "placeholder" in result.output.lower()
    assert tmp_text_file in result.output


def test_nonexistent_file_rejected(runner: CliRunner) -> None:
    """A path that doesn't exist should be rejected."""
    from summarizer.cli import main

    result = runner.invoke(main, ["--file", "/tmp/does_not_exist_xyz.txt"])
    assert result.exit_code != 0
    combined = result.output + (result.stderr or "")
    assert "not found" in combined.lower() or "file" in combined.lower()


# --------------------------------------------------------------------------- #
# Output format options                                                        #
# --------------------------------------------------------------------------- #


def test_json_output_is_valid_json(runner: CliRunner) -> None:
    """--format json should produce parseable JSON."""
    from summarizer.cli import main

    result = runner.invoke(
        main,
        ["--url", "https://example.com", "--format", "json"],
    )
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert "summary" in data
    assert data["source"] == "https://example.com"
    assert data["format"] == "json"


def test_markdown_output_contains_heading(runner: CliRunner) -> None:
    """--format markdown should include a Markdown heading."""
    from summarizer.cli import main

    result = runner.invoke(
        main,
        ["--url", "https://example.com", "--format", "markdown"],
    )
    assert result.exit_code == 0, result.output
    assert "##" in result.output


# --------------------------------------------------------------------------- #
# --style option                                                               #
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("style", ["paragraph", "bullet", "tldr"])
def test_valid_styles_accepted(runner: CliRunner, style: str) -> None:
    """All documented --style values should be accepted."""
    from summarizer.cli import main

    result = runner.invoke(
        main,
        ["--url", "https://example.com", "--style", style],
    )
    assert result.exit_code == 0, result.output


def test_invalid_style_rejected(runner: CliRunner) -> None:
    """An unknown --style value should be rejected by Click."""
    from summarizer.cli import main

    result = runner.invoke(main, ["--url", "https://example.com", "--style", "essay"])
    assert result.exit_code != 0


# --------------------------------------------------------------------------- #
# --verbose flag                                                               #
# --------------------------------------------------------------------------- #


def test_verbose_flag_accepted(runner: CliRunner) -> None:
    """--verbose should not cause an error."""
    from summarizer.cli import main

    result = runner.invoke(
        main,
        ["--url", "https://example.com", "--verbose"],
    )
    assert result.exit_code == 0, result.output
"""Smoke tests for the Summarizer CLI (Phase 1).

Uses Click's CliRunner for isolated, in-process invocation of the CLI.
"""

from __future__ import annotations

import os
import tempfile

import pytest
from click.testing import CliRunner

from summarizer import __version__
from summarizer.cli import main


@pytest.fixture()
def runner() -> CliRunner:
    """Return a Click CliRunner with a clean environment."""
    return CliRunner(mix_stderr=False)


@pytest.fixture()
def clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Remove OpenAI-related env vars so tests are hermetic."""
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("SUMMARIZER_MODEL", "gpt-4o-mini")
    monkeypatch.setenv("SUMMARIZER_MAX_TOKENS", "512")
    monkeypatch.setenv("SUMMARIZER_DEFAULT_STYLE", "brief")
    monkeypatch.setenv("SUMMARIZER_DEFAULT_FORMAT", "text")


# ---------------------------------------------------------------------------
# Basic importability
# ---------------------------------------------------------------------------


class TestImportability:
    def test_package_importable(self) -> None:
        """The summarizer package must be importable."""
        import summarizer  # noqa: F401

    def test_version_string_exists(self) -> None:
        """__version__ must be a non-empty string."""
        assert isinstance(__version__, str)
        assert len(__version__) > 0

    def test_cli_importable(self) -> None:
        """The CLI module must be importable."""
        from summarizer.cli import main  # noqa: F401

    def test_config_importable(self) -> None:
        """The config module must be importable."""
        from summarizer.config import load_config  # noqa: F401

    def test_logger_importable(self) -> None:
        """The logger module must be importable."""
        from summarizer.logger import configure_logging, get_logger  # noqa: F401


# ---------------------------------------------------------------------------
# --help
# ---------------------------------------------------------------------------


class TestHelpOption:
    def test_help_exits_zero(self, runner: CliRunner) -> None:
        """--help should exit with code 0."""
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0, result.output

    def test_help_contains_usage(self, runner: CliRunner) -> None:
        """--help output should contain 'Usage:'."""
        result = runner.invoke(main, ["--help"])
        assert "Usage:" in result.output

    def test_help_mentions_url_option(self, runner: CliRunner) -> None:
        """--help output should document the --url option."""
        result = runner.invoke(main, ["--help"])
        assert "--url" in result.output

    def test_help_mentions_file_option(self, runner: CliRunner) -> None:
        """--help output should document the --file option."""
        result = runner.invoke(main, ["--help"])
        assert "--file" in result.output

    def test_help_mentions_style_option(self, runner: CliRunner) -> None:
        """--help output should document the --style option."""
        result = runner.invoke(main, ["--help"])
        assert "--style" in result.output

    def test_help_mentions_format_option(self, runner: CliRunner) -> None:
        """--help output should document the --format option."""
        result = runner.invoke(main, ["--help"])
        assert "--format" in result.output

    def test_version_flag(self, runner: CliRunner) -> None:
        """--version should print the version string and exit 0."""
        result = runner.invoke(main, ["--version"])
        assert result.exit_code == 0
        assert __version__ in result.output


# ---------------------------------------------------------------------------
# Missing / conflicting input
# ---------------------------------------------------------------------------


class TestInputValidation:
    def test_no_input_shows_error(self, runner: CliRunner, clean_env: None) -> None:
        """Invoking with neither --url nor --file should show a usage error."""
        result = runner.invoke(main, [])
        assert result.exit_code != 0
        combined = result.output + (result.stderr or "")
        assert "url" in combined.lower() or "file" in combined.lower() or "error" in combined.lower()

    def test_both_url_and_file_shows_error(
        self, runner: CliRunner, clean_env: None
    ) -> None:
        """Providing both --url and --file should show a usage error."""
        with runner.isolated_filesystem():
            # Create a temporary file so --file validation passes first
            Path = __import__("pathlib").Path
            tmp = Path("sample.txt")
            tmp.write_text("hello")
            result = runner.invoke(
                main, ["--url", "https://example.com", "--file", str(tmp)]
            )
        assert result.exit_code != 0
        combined = result.output + (result.stderr or "")
        assert "error" in combined.lower() or "not both" in combined.lower()

    def test_invalid_url_shows_error(
        self, runner: CliRunner, clean_env: None
    ) -> None:
        """A malformed URL should produce a non-zero exit and an error message."""
        result = runner.invoke(main, ["--url", "not-a-url"])
        assert result.exit_code != 0
        combined = result.output + (result.stderr or "")
        assert "error" in combined.lower() or "url" in combined.lower()

    def test_nonexistent_file_shows_error(
        self, runner: CliRunner, clean_env: None
    ) -> None:
        """A file path that does not exist should produce a non-zero exit."""
        result = runner.invoke(main, ["--file", "/nonexistent/path/file.txt"])
        assert result.exit_code != 0
        combined = result.output + (result.stderr or "")
        assert "error" in combined.lower() or "file" in combined.lower()

    def test_invalid_style_shows_error(
        self, runner: CliRunner, clean_env: None
    ) -> None:
        """An invalid --style value should produce a non-zero exit."""
        result = runner.invoke(
            main, ["--url", "https://example.com", "--style", "nonsense"]
        )
        assert result.exit_code != 0

    def test_invalid_format_shows_error(
        self, runner: CliRunner, clean_env: None
    ) -> None:
        """An invalid --format value should produce a non-zero exit."""
        result = runner.invoke(
            main, ["--url", "https://example.com", "--format", "xml"]
        )
        assert result.exit_code != 0


# ---------------------------------------------------------------------------
# Happy-path placeholder output
# ---------------------------------------------------------------------------


class TestHappyPath:
    def test_valid_url_exits_zero(
        self, runner: CliRunner, clean_env: None
    ) -> None:
        """A valid URL should exit with code 0."""
        result = runner.invoke(main, ["--url", "https://example.com"])
        assert result.exit_code == 0, result.output

    def test_valid_url_shows_placeholder(
        self, runner: CliRunner, clean_env: None
    ) -> None:
        """A valid URL run should print the placeholder summary line."""
        result = runner.invoke(main, ["--url", "https://example.com"])
        assert "placeholder" in result.output.lower()

    def test_valid_url_echoes_url(
        self, runner: CliRunner, clean_env: None
    ) -> None:
        """The output should echo back the provided URL."""
        result = runner.invoke(main, ["--url", "https://example.com"])
        assert "https://example.com" in result.output

    def test_valid_file_exits_zero(
        self, runner: CliRunner, clean_env: None
    ) -> None:
        """A valid readable file should exit with code 0."""
        with runner.isolated_filesystem():
            from pathlib import Path

            tmp = Path("sample.txt")
            tmp.write_text("Some content here.")
            result = runner.invoke(main, ["--file", str(tmp)])
        assert result.exit_code == 0, result.output

    def test_valid_file_shows_placeholder(
        self, runner: CliRunner, clean_env: None
    ) -> None:
        """A valid file run should print the placeholder summary line."""
        with runner.isolated_filesystem():
            from pathlib import Path

            tmp = Path("sample.txt")
            tmp.write_text("Some content here.")
            result = runner.invoke(main, ["--file", str(tmp)])
        assert "placeholder" in result.output.lower()

    def test_style_option_reflected_in_output(
        self, runner: CliRunner, clean_env: None
    ) -> None:
        """The chosen --style should appear in the placeholder output."""
        result = runner.invoke(
            main, ["--url", "https://example.com", "--style", "detailed"]
        )
        assert "detailed" in result.output

    def test_format_option_reflected_in_output(
        self, runner: CliRunner, clean_env: None
    ) -> None:
        """The chosen --format should appear in the placeholder output."""
        result = runner.invoke(
            main, ["--url", "https://example.com", "--format", "markdown"]
        )
        assert "markdown" in result.output

    def test_verbose_flag_does_not_break_output(
        self, runner: CliRunner, clean_env: None
    ) -> None:
        """Running with --verbose should still exit 0 and produce placeholder output."""
        result = runner.invoke(
            main, ["--url", "https://example.com", "--verbose"]
        )
        assert result.exit_code == 0, result.output
        assert "placeholder" in result.output.lower()


# ---------------------------------------------------------------------------
# Config loading
# ---------------------------------------------------------------------------


class TestConfig:
    def test_load_config_returns_defaults(self, clean_env: None) -> None:
        """load_config() should return sensible defaults when env vars are set."""
        from summarizer.config import load_config

        cfg = load_config()
        assert cfg.model == "gpt-4o-mini"
        assert cfg.max_tokens == 512
        assert cfg.default_style == "brief"
        assert cfg.default_format == "text"

    def test_load_config_respects_env_vars(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """load_config() should pick up custom env var values."""
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key")
        monkeypatch.setenv("SUMMARIZER_MODEL", "gpt-4o")
        monkeypatch.setenv("SUMMARIZER_MAX_TOKENS", "1024")
        monkeypatch.setenv("SUMMARIZER_DEFAULT_STYLE", "bullet")
        monkeypatch.setenv("SUMMARIZER_DEFAULT_FORMAT", "json")

        from summarizer.config import load_config

        cfg = load_config()
        assert cfg.api_key == "sk-test-key"
        assert cfg.model == "gpt-4o"
        assert cfg.max_tokens == 1024
        assert cfg.default_style == "bullet"
        assert cfg.default_format == "json"

    def test_has_api_key_false_when_missing(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """has_api_key should be False when OPENAI_API_KEY is not set."""
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.setenv("SUMMARIZER_DEFAULT_STYLE", "brief")
        monkeypatch.setenv("SUMMARIZER_DEFAULT_FORMAT", "text")
        monkeypatch.setenv("SUMMARIZER_MAX_TOKENS", "512")

        from summarizer.config import load_config

        cfg = load_config()
        assert cfg.has_api_key is False

    def test_has_api_key_true_when_set(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """has_api_key should be True when OPENAI_API_KEY is set."""
        monkeypatch.setenv("OPENAI_API_KEY", "sk-real-key")
        monkeypatch.setenv("SUMMARIZER_DEFAULT_STYLE", "brief")
        monkeypatch.setenv("SUMMARIZER_DEFAULT_FORMAT", "text")
        monkeypatch.setenv("SUMMARIZER_MAX_TOKENS", "512")

        from summarizer.config import load_config

        cfg = load_config()
        assert cfg.has_api_key is True

    def test_invalid_max_tokens_raises(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """load_config() should raise ValueError for a non-integer SUMMARIZER_MAX_TOKENS."""
        monkeypatch.setenv("SUMMARIZER_MAX_TOKENS", "not-a-number")
        monkeypatch.setenv("SUMMARIZER_DEFAULT_STYLE", "brief")
        monkeypatch.setenv("SUMMARIZER_DEFAULT_FORMAT", "text")

        from summarizer.config import load_config

        with pytest.raises(ValueError, match="integer"):
            load_config()
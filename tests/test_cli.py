"""
Smoke tests for the summarize CLI.

Uses Click's CliRunner to invoke the command in-process without spawning
a subprocess, so tests run fast and produce clean output.
"""

from __future__ import annotations

import pytest
from click.testing import CliRunner

from summarizer.cli import main
from summarizer import __version__


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def runner() -> CliRunner:
    """Return a Click test runner that mixes stdout/stderr."""
    return CliRunner(mix_stderr=False)


# ---------------------------------------------------------------------------
# Basic importability & metadata
# ---------------------------------------------------------------------------

class TestImportability:
    def test_package_is_importable(self):
        """The summarizer package must be importable without side-effects."""
        import summarizer  # noqa: F401

    def test_version_string_is_defined(self):
        assert isinstance(__version__, str)
        assert len(__version__) > 0

    def test_cli_module_is_importable(self):
        from summarizer import cli  # noqa: F401

    def test_config_module_is_importable(self):
        from summarizer import config  # noqa: F401

    def test_logger_module_is_importable(self):
        from summarizer import logger  # noqa: F401


# ---------------------------------------------------------------------------
# --help
# ---------------------------------------------------------------------------

class TestHelp:
    def test_help_exits_zero(self, runner: CliRunner):
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0, result.output

    def test_help_mentions_url_option(self, runner: CliRunner):
        result = runner.invoke(main, ["--help"])
        assert "--url" in result.output

    def test_help_mentions_file_option(self, runner: CliRunner):
        result = runner.invoke(main, ["--help"])
        assert "--file" in result.output

    def test_help_mentions_style_option(self, runner: CliRunner):
        result = runner.invoke(main, ["--help"])
        assert "--style" in result.output

    def test_help_mentions_format_option(self, runner: CliRunner):
        result = runner.invoke(main, ["--help"])
        assert "--format" in result.output

    def test_version_flag(self, runner: CliRunner):
        result = runner.invoke(main, ["--version"])
        assert result.exit_code == 0
        assert __version__ in result.output


# ---------------------------------------------------------------------------
# Missing / invalid input
# ---------------------------------------------------------------------------

class TestInputValidation:
    def test_no_args_shows_error(self, runner: CliRunner):
        """Invoking without --url or --file must fail with a usage error."""
        result = runner.invoke(main, [])
        assert result.exit_code != 0

    def test_no_args_error_message(self, runner: CliRunner):
        result = runner.invoke(main, [])
        combined = (result.output or "") + (result.stderr or "")
        assert "url" in combined.lower() or "file" in combined.lower() or "input" in combined.lower()

    def test_both_url_and_file_shows_error(self, runner: CliRunner, tmp_path):
        dummy = tmp_path / "dummy.txt"
        dummy.write_text("hello")
        result = runner.invoke(main, ["--url", "https://example.com", "--file", str(dummy)])
        assert result.exit_code != 0

    def test_invalid_url_shows_error(self, runner: CliRunner):
        result = runner.invoke(main, ["--url", "not-a-url"])
        assert result.exit_code != 0

    def test_nonexistent_file_shows_error(self, runner: CliRunner):
        result = runner.invoke(main, ["--file", "/nonexistent/path/file.txt"])
        assert result.exit_code != 0

    def test_invalid_style_shows_error(self, runner: CliRunner):
        result = runner.invoke(main, ["--url", "https://example.com", "--style", "invalid"])
        assert result.exit_code != 0

    def test_invalid_format_shows_error(self, runner: CliRunner):
        result = runner.invoke(main, ["--url", "https://example.com", "--format", "xml"])
        assert result.exit_code != 0


# ---------------------------------------------------------------------------
# Happy-path placeholder output
# ---------------------------------------------------------------------------

class TestPlaceholderOutput:
    def test_url_input_exits_zero(self, runner: CliRunner):
        result = runner.invoke(main, ["--url", "https://example.com/article"])
        assert result.exit_code == 0, result.output

    def test_url_input_shows_placeholder(self, runner: CliRunner):
        result = runner.invoke(main, ["--url", "https://example.com/article"])
        assert "PLACEHOLDER" in result.output

    def test_url_input_echoes_source(self, runner: CliRunner):
        url = "https://example.com/article"
        result = runner.invoke(main, ["--url", url])
        assert url in result.output

    def test_file_input_exits_zero(self, runner: CliRunner, tmp_path):
        f = tmp_path / "sample.txt"
        f.write_text("Sample content for testing.")
        result = runner.invoke(main, ["--file", str(f)])
        assert result.exit_code == 0, result.output

    def test_file_input_shows_placeholder(self, runner: CliRunner, tmp_path):
        f = tmp_path / "sample.txt"
        f.write_text("Sample content for testing.")
        result = runner.invoke(main, ["--file", str(f)])
        assert "PLACEHOLDER" in result.output

    def test_style_echoed_in_output(self, runner: CliRunner):
        result = runner.invoke(main, ["--url", "https://example.com", "--style", "detailed"])
        assert "detailed" in result.output

    def test_format_echoed_in_output(self, runner: CliRunner):
        result = runner.invoke(main, ["--url", "https://example.com", "--format", "markdown"])
        assert "markdown" in result.output

    def test_default_style_is_brief(self, runner: CliRunner):
        result = runner.invoke(main, ["--url", "https://example.com"])
        assert "brief" in result.output

    def test_default_format_is_text(self, runner: CliRunner):
        result = runner.invoke(main, ["--url", "https://example.com"])
        assert "text" in result.output

    def test_verbose_flag_is_accepted(self, runner: CliRunner):
        result = runner.invoke(main, ["--url", "https://example.com", "--verbose"])
        assert result.exit_code == 0, result.output


# ---------------------------------------------------------------------------
# Config module (unit tests — no real API key required)
# ---------------------------------------------------------------------------

class TestConfig:
    def test_config_raises_without_api_key(self, monkeypatch):
        """Config.from_env() must raise ValueError when OPENAI_API_KEY is absent."""
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        from summarizer.config import Config
        with pytest.raises(ValueError, match="OPENAI_API_KEY"):
            Config.from_env()

    def test_config_loads_with_api_key(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test-1234567890abcdef")
        from summarizer.config import Config
        cfg = Config.from_env()
        assert cfg.api_key == "sk-test-1234567890abcdef"

    def test_config_defaults(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key")
        monkeypatch.delenv("SUMMARIZER_MODEL", raising=False)
        monkeypatch.delenv("SUMMARIZER_MAX_TOKENS", raising=False)
        monkeypatch.delenv("SUMMARIZER_TEMPERATURE", raising=False)
        from summarizer.config import Config
        cfg = Config.from_env()
        assert cfg.model == "gpt-4o-mini"
        assert cfg.max_tokens == 1024
        assert pytest.approx(cfg.temperature) == 0.7

    def test_config_masked_api_key(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test-1234567890abcdef")
        from summarizer.config import Config
        cfg = Config.from_env()
        masked = cfg.masked_api_key()
        assert masked.endswith("cdef")
        assert "sk-test" not in masked

    def test_config_invalid_max_tokens(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key")
        monkeypatch.setenv("SUMMARIZER_MAX_TOKENS", "not-a-number")
        from summarizer.config import Config
        with pytest.raises(ValueError, match="SUMMARIZER_MAX_TOKENS"):
            Config.from_env()

    def test_config_invalid_temperature(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key")
        monkeypatch.setenv("SUMMARIZER_TEMPERATURE", "5.0")
        from summarizer.config import Config
        with pytest.raises(ValueError, match="SUMMARIZER_TEMPERATURE"):
            Config.from_env()
"""
Tests for ConfigResolver: merge priority, profile switching, and validation.
"""
from __future__ import annotations

import os
import pytest
from pathlib import Path
from unittest.mock import patch

from src.summarizer.config import ConfigResolver, ResolvedConfig, BUILTIN_DEFAULTS
from src.summarizer.profile import ProfileManager
from src.summarizer.exceptions import ConfigError
from src.summarizer.schemas import ConfigFile, DefaultConfig, ProfileConfig


@pytest.fixture
def tmp_config_dir(tmp_path: Path) -> Path:
    """Return a temporary config directory."""
    config_dir = tmp_path / "summarizer"
    config_dir.mkdir(parents=True)
    return config_dir


@pytest.fixture
def pm(tmp_config_dir: Path) -> ProfileManager:
    """Return a ProfileManager with a temp config directory."""
    return ProfileManager(config_dir=tmp_config_dir)


@pytest.fixture
def resolver(pm: ProfileManager) -> ConfigResolver:
    """Return a ConfigResolver backed by a temp ProfileManager."""
    return ConfigResolver(profile_manager=pm)


class TestBuiltinDefaults:
    """ConfigResolver should start with built-in defaults."""

    def test_all_builtin_defaults_present(self, resolver: ConfigResolver) -> None:
        config = resolver.resolve()
        assert config.provider == "openai"
        assert config.model == "gpt-3.5-turbo"
        assert config.style == "concise"
        assert config.format == "text"
        assert config.max_length == 500
        assert config.temperature == 0.7

    def test_default_profile_is_default(self, resolver: ConfigResolver) -> None:
        config = resolver.resolve()
        assert config.profile == "default"

    def test_cache_defaults(self, resolver: ConfigResolver) -> None:
        config = resolver.resolve()
        assert config.cache_enabled is True
        assert config.cache_ttl_hours == 24
        assert config.cache_max_size_mb == 100

    def test_rate_limit_defaults(self, resolver: ConfigResolver) -> None:
        config = resolver.resolve()
        assert config.rate_limit_requests_per_minute == 60
        assert config.rate_limit_retry_attempts == 3


class TestConfigFileProfile:
    """Config file profile settings should override built-in defaults."""

    def test_profile_overrides_defaults(self, pm: ProfileManager, resolver: ConfigResolver) -> None:
        pm.create_profile("work", provider="anthropic", model="claude-3-sonnet-20240229")
        pm.use_profile("work")

        config = resolver.resolve()
        assert config.provider == "anthropic"
        assert config.model == "claude-3-sonnet-20240229"

    def test_profile_partial_override(self, pm: ProfileManager, resolver: ConfigResolver) -> None:
        pm.create_profile("partial", provider="ollama")
        pm.use_profile("partial")

        config = resolver.resolve()
        assert config.provider == "ollama"
        # Other fields should still be defaults
        assert config.style == "concise"
        assert config.format == "text"

    def test_explicit_profile_name(self, pm: ProfileManager, resolver: ConfigResolver) -> None:
        pm.create_profile("research", provider="anthropic", style="detailed")
        pm.create_profile("quick", provider="openai", style="concise")
        pm.use_profile("quick")

        # Explicitly request research profile
        config = resolver.resolve(profile_name="research")
        assert config.provider == "anthropic"
        assert config.style == "detailed"

    def test_cli_profile_flag_overrides_active(
        self, pm: ProfileManager, resolver: ConfigResolver
    ) -> None:
        pm.create_profile("work", provider="openai", style="bullet")
        pm.create_profile("personal", provider="ollama", style="casual")
        pm.use_profile("work")

        config = resolver.resolve(cli_flags={"profile": "personal"})
        assert config.provider == "ollama"
        assert config.style == "casual"

    def test_nonexistent_profile_warns(
        self, pm: ProfileManager, resolver: ConfigResolver
    ) -> None:
        pm.use_profile("default")
        # Manually set the active profile to a nonexistent one
        config_file = pm.load_config()
        config_file.default.profile = "ghost"
        # Bypass validation to set an invalid profile
        from src.summarizer.profile import _dump_toml
        data = config_file.to_toml_dict()
        data["default"]["profile"] = "ghost"
        _dump_toml(data, pm.config_path)
        pm._invalidate_cache()

        import warnings
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            config = resolver.resolve()
            assert len(w) == 1
            assert "ghost" in str(w[0].message)

        # Should fall back to built-in defaults
        assert config.provider == "openai"


class TestEnvironmentVariables:
    """Environment variables should override config file but not CLI flags."""

    def test_env_var_overrides_default(self, resolver: ConfigResolver) -> None:
        with patch.dict(os.environ, {"SUMMARIZER_PROVIDER": "anthropic"}):
            config = resolver.resolve()
            assert config.provider == "anthropic"

    def test_env_var_overrides_profile(
        self, pm: ProfileManager, resolver: ConfigResolver
    ) -> None:
        pm.create_profile("work", provider="openai")
        pm.use_profile("work")

        with patch.dict(os.environ, {"SUMMARIZER_PROVIDER": "ollama"}):
            config = resolver.resolve()
            assert config.provider == "ollama"

    def test_multiple_env_vars(self, resolver: ConfigResolver) -> None:
        env = {
            "SUMMARIZER_PROVIDER": "anthropic",
            "SUMMARIZER_STYLE": "detailed",
            "SUMMARIZER_MAX_LENGTH": "1000",
        }
        with patch.dict(os.environ, env):
            config = resolver.resolve()
            assert config.provider == "anthropic"
            assert config.style == "detailed"
            assert config.max_length == 1000

    def test_env_var_int_coercion(self, resolver: ConfigResolver) -> None:
        with patch.dict(os.environ, {"SUMMARIZER_MAX_LENGTH": "300"}):
            config = resolver.resolve()
            assert config.max_length == 300
            assert isinstance(config.max_length, int)

    def test_env_var_float_coercion(self, resolver: ConfigResolver) -> None:
        with patch.dict(os.environ, {"SUMMARIZER_TEMPERATURE": "0.5"}):
            config = resolver.resolve()
            assert config.temperature == 0.5
            assert isinstance(config.temperature, float)

    def test_env_var_bool_coercion(self, resolver: ConfigResolver) -> None:
        with patch.dict(os.environ, {"SUMMARIZER_CACHE_ENABLED": "false"}):
            config = resolver.resolve()
            assert config.cache_enabled is False

    def test_invalid_env_var_raises(self, resolver: ConfigResolver) -> None:
        with patch.dict(os.environ, {"SUMMARIZER_MAX_LENGTH": "not_a_number"}):
            with pytest.raises(ConfigError, match="SUMMARIZER_MAX_LENGTH"):
                resolver.resolve()


class TestCLIFlags:
    """CLI flags should have highest priority."""

    def test_cli_overrides_env_and_profile(
        self, pm: ProfileManager, resolver: ConfigResolver
    ) -> None:
        pm.create_profile("work", provider="anthropic")
        pm.use_profile("work")

        with patch.dict(os.environ, {"SUMMARIZER_PROVIDER": "ollama"}):
            config = resolver.resolve(cli_flags={"provider": "openrouter"})
            assert config.provider == "openrouter"

    def test_cli_overrides_default(self, resolver: ConfigResolver) -> None:
        config = resolver.resolve(cli_flags={"provider": "anthropic", "style": "detailed"})
        assert config.provider == "anthropic"
        assert config.style == "detailed"

    def test_none_cli_flags_ignored(self, resolver: ConfigResolver) -> None:
        config = resolver.resolve(cli_flags={"provider": None, "style": None})
        # Should use built-in defaults
        assert config.provider == "openai"
        assert config.style == "concise"

    def test_cli_max_length(self, resolver: ConfigResolver) -> None:
        config = resolver.resolve(cli_flags={"max_length": 250})
        assert config.max_length == 250

    def test_cli_temperature(self, resolver: ConfigResolver) -> None:
        config = resolver.resolve(cli_flags={"temperature": 0.3})
        assert config.temperature == 0.3


class TestMergePriority:
    """Full priority chain: defaults < profile < env < cli."""

    def test_full_priority_chain(
        self, pm: ProfileManager, resolver: ConfigResolver
    ) -> None:
        # Set up profile
        pm.create_profile("chain", provider="anthropic", model="claude-3-haiku", style="bullet")
        pm.use_profile("chain")

        # Env overrides style from profile
        # CLI overrides model from both profile and env
        with patch.dict(os.environ, {
            "SUMMARIZER_STYLE": "academic",
            "SUMMARIZER_MODEL": "env-model",
        }):
            config = resolver.resolve(cli_flags={"model": "cli-model"})

        # provider from profile (anthropic)
        assert config.provider == "anthropic"
        # style from env (overrides profile's bullet)
        assert config.style == "academic"
        # model from cli (overrides env's env-model)
        assert config.model == "cli-model"

    def test_source_tracking(
        self, pm: ProfileManager, resolver: ConfigResolver
    ) -> None:
        pm.create_profile("track", provider="anthropic")
        pm.use_profile("track")

        with patch.dict(os.environ, {"SUMMARIZER_STYLE": "detailed"}):
            config = resolver.resolve(cli_flags={"format": "markdown"})

        assert "config:profile:track" in config._sources.get("provider", "")
        assert "env:" in config._sources.get("style", "")
        assert config._sources.get("format") == "cli"
        assert config._sources.get("max_length") == "default"


class TestExplain:
    """ConfigResolver.explain() should return a readable string."""

    def test_explain_returns_string(self, resolver: ConfigResolver) -> None:
        explanation = resolver.explain()
        assert isinstance(explanation, str)
        assert "provider" in explanation
        assert "model" in explanation

    def test_explain_with_cli_flags(self, resolver: ConfigResolver) -> None:
        explanation = resolver.explain(cli_flags={"provider": "anthropic"})
        assert "anthropic" in explanation
        assert "cli" in explanation


class TestResolvedConfigAsDict:
    """ResolvedConfig.as_dict() should work correctly."""

    def test_as_dict(self, resolver: ConfigResolver) -> None:
        config = resolver.resolve()
        d = config.as_dict()
        assert isinstance(d, dict)
        assert "provider" in d
        assert "_sources" not in d

    def test_as_dict_with_sources(self, resolver: ConfigResolver) -> None:
        config = resolver.resolve()
        d = config.as_dict(include_sources=True)
        assert "_sources" in d
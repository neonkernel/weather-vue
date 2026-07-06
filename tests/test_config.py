"""
Tests for ConfigResolver: merge priority, profile switching, and validation.
"""
from __future__ import annotations

import os
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.summarizer.config import ConfigResolver, ConfigError, ResolvedConfig, DEFAULTS
from src.summarizer.profile import ProfileManager
from src.summarizer.schemas import ProfileConfig, CacheConfig, RateLimitConfig, ConfigFile, DefaultConfig


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def tmp_profile_manager(tmp_path: Path) -> ProfileManager:
    return ProfileManager(config_dir=tmp_path)


@pytest.fixture
def resolver_with_manager(tmp_profile_manager: ProfileManager) -> ConfigResolver:
    return ConfigResolver(profile_manager=tmp_profile_manager)


@pytest.fixture
def populated_manager(tmp_profile_manager: ProfileManager) -> ProfileManager:
    """A ProfileManager with some pre-created profiles."""
    tmp_profile_manager.create_profile(
        "work",
        provider="openai",
        model="gpt-4o",
        style="detailed",
        format="markdown",
        description="Work summarization profile",
    )
    tmp_profile_manager.create_profile(
        "quick",
        provider="openai",
        model="gpt-4o-mini",
        style="concise",
        format="text",
    )
    tmp_profile_manager.create_profile(
        "research",
        provider="anthropic",
        model="claude-3-5-sonnet-20241022",
        style="academic",
        format="markdown",
        max_length=500,
        temperature=0.3,
    )
    return tmp_profile_manager


# ---------------------------------------------------------------------------
# Default resolution
# ---------------------------------------------------------------------------

class TestDefaultResolution:
    def test_all_defaults_when_no_config(self, resolver_with_manager: ConfigResolver) -> None:
        resolved = resolver_with_manager.resolve()
        assert resolved.provider == DEFAULTS["provider"]
        assert resolved.model == DEFAULTS["model"]
        assert resolved.style == DEFAULTS["style"]
        assert resolved.format == DEFAULTS["format"]
        assert resolved.cache_enabled == DEFAULTS["cache_enabled"]
        assert resolved.cache_ttl_seconds == DEFAULTS["cache_ttl_seconds"]
        assert resolved.requests_per_minute == DEFAULTS["requests_per_minute"]

    def test_returns_resolved_config_type(self, resolver_with_manager: ConfigResolver) -> None:
        resolved = resolver_with_manager.resolve()
        assert isinstance(resolved, ResolvedConfig)


# ---------------------------------------------------------------------------
# Profile-based resolution
# ---------------------------------------------------------------------------

class TestProfileResolution:
    def test_profile_overrides_defaults(self, populated_manager: ProfileManager) -> None:
        resolver = ConfigResolver(profile_manager=populated_manager)
        resolved = resolver.resolve(profile_name="work")
        assert resolved.provider == "openai"
        assert resolved.model == "gpt-4o"
        assert resolved.style == "detailed"
        assert resolved.format == "markdown"
        assert resolved.active_profile == "work"

    def test_research_profile_resolution(self, populated_manager: ProfileManager) -> None:
        resolver = ConfigResolver(profile_manager=populated_manager)
        resolved = resolver.resolve(profile_name="research")
        assert resolved.provider == "anthropic"
        assert resolved.style == "academic"
        assert resolved.max_length == 500
        assert resolved.temperature == 0.3

    def test_active_profile_used_when_no_explicit_profile(
        self, populated_manager: ProfileManager
    ) -> None:
        populated_manager.set_active_profile("work")
        resolver = ConfigResolver(profile_manager=populated_manager)
        resolved = resolver.resolve()
        assert resolved.active_profile == "work"
        assert resolved.model == "gpt-4o"

    def test_unknown_profile_raises_config_error(
        self, populated_manager: ProfileManager
    ) -> None:
        resolver = ConfigResolver(profile_manager=populated_manager)
        with pytest.raises(ConfigError, match="nonexistent"):
            resolver.resolve(profile_name="nonexistent")

    def test_profile_partial_override(self, tmp_profile_manager: ProfileManager) -> None:
        """Profile that only sets provider should inherit other defaults."""
        tmp_profile_manager.create_profile("partial", provider="anthropic")
        resolver = ConfigResolver(profile_manager=tmp_profile_manager)
        resolved = resolver.resolve(profile_name="partial")
        assert resolved.provider == "anthropic"
        assert resolved.style == DEFAULTS["style"]  # still default
        assert resolved.format == DEFAULTS["format"]  # still default


# ---------------------------------------------------------------------------
# Environment variable resolution
# ---------------------------------------------------------------------------

class TestEnvironmentVariableResolution:
    def test_env_overrides_profile(self, populated_manager: ProfileManager) -> None:
        resolver = ConfigResolver(profile_manager=populated_manager)
        with patch.dict(os.environ, {"SUMMARIZER_PROVIDER": "groq"}):
            resolved = resolver.resolve(profile_name="work")
        # env var overrides profile's provider
        assert resolved.provider == "groq"
        # profile's model still applies
        assert resolved.model == "gpt-4o"

    def test_env_overrides_defaults(self, resolver_with_manager: ConfigResolver) -> None:
        with patch.dict(os.environ, {"SUMMARIZER_STYLE": "bullet", "SUMMARIZER_FORMAT": "json"}):
            resolved = resolver_with_manager.resolve()
        assert resolved.style == "bullet"
        assert resolved.format == "json"

    def test_env_type_coercion_int(self, resolver_with_manager: ConfigResolver) -> None:
        with patch.dict(os.environ, {"SUMMARIZER_MAX_LENGTH": "250"}):
            resolved = resolver_with_manager.resolve()
        assert resolved.max_length == 250
        assert isinstance(resolved.max_length, int)

    def test_env_type_coercion_float(self, resolver_with_manager: ConfigResolver) -> None:
        with patch.dict(os.environ, {"SUMMARIZER_TEMPERATURE": "0.8"}):
            resolved = resolver_with_manager.resolve()
        assert resolved.temperature == pytest.approx(0.8)

    def test_env_cache_disabled(self, resolver_with_manager: ConfigResolver) -> None:
        with patch.dict(os.environ, {"SUMMARIZER_CACHE_ENABLED": "false"}):
            resolved = resolver_with_manager.resolve()
        assert resolved.cache_enabled is False

    def test_env_cache_disabled_zero(self, resolver_with_manager: ConfigResolver) -> None:
        with patch.dict(os.environ, {"SUMMARIZER_CACHE_ENABLED": "0"}):
            resolved = resolver_with_manager.resolve()
        assert resolved.cache_enabled is False

    def test_env_invalid_int_raises_config_error(
        self, resolver_with_manager: ConfigResolver
    ) -> None:
        with patch.dict(os.environ, {"SUMMARIZER_MAX_LENGTH": "not-a-number"}):
            with pytest.raises(ConfigError, match="SUMMARIZER_MAX_LENGTH"):
                resolver_with_manager.resolve()

    def test_env_profile_selection(self, populated_manager: ProfileManager) -> None:
        resolver = ConfigResolver(profile_manager=populated_manager)
        with patch.dict(os.environ, {"SUMMARIZER_PROFILE": "quick"}):
            resolved = resolver.resolve()
        assert resolved.active_profile == "quick"
        assert resolved.style == "concise"


# ---------------------------------------------------------------------------
# CLI flag resolution
# ---------------------------------------------------------------------------

class TestCLIFlagResolution:
    def test_cli_overrides_env_and_profile(self, populated_manager: ProfileManager) -> None:
        resolver = ConfigResolver(profile_manager=populated_manager)
        with patch.dict(os.environ, {"SUMMARIZER_PROVIDER": "groq"}):
            resolved = resolver.resolve(
                cli_flags={"provider": "anthropic"},
                profile_name="work",
            )
        # CLI wins over env and profile
        assert resolved.provider == "anthropic"

    def test_cli_none_values_ignored(self, populated_manager: ProfileManager) -> None:
        resolver = ConfigResolver(profile_manager=populated_manager)
        resolved = resolver.resolve(
            cli_flags={"provider": None, "model": None},
            profile_name="work",
        )
        # Profile values should still apply
        assert resolved.provider == "openai"
        assert resolved.model == "gpt-4o"

    def test_cli_overrides_only_specified_keys(self, populated_manager: ProfileManager) -> None:
        resolver = ConfigResolver(profile_manager=populated_manager)
        resolved = resolver.resolve(
            cli_flags={"style": "bullet"},
            profile_name="work",
        )
        assert resolved.style == "bullet"
        assert resolved.model == "gpt-4o"  # from profile
        assert resolved.format == "markdown"  # from profile

    def test_cli_cache_disabled(self, resolver_with_manager: ConfigResolver) -> None:
        resolved = resolver_with_manager.resolve(
            cli_flags={"cache_enabled": False}
        )
        assert resolved.cache_enabled is False

    def test_full_priority_chain(self, populated_manager: ProfileManager) -> None:
        """default < profile < env < cli"""
        resolver = ConfigResolver(profile_manager=populated_manager)
        populated_manager.set_active_profile("work")

        # work profile: provider=openai, model=gpt-4o, style=detailed, format=markdown
        # env: style=bullet (overrides profile)
        # cli: format=json (overrides env and profile)
        with patch.dict(os.environ, {"SUMMARIZER_STYLE": "bullet"}):
            resolved = resolver.resolve(
                cli_flags={"format": "json"},
            )

        assert resolved.provider == "openai"   # from profile
        assert resolved.model == "gpt-4o"      # from profile
        assert resolved.style == "bullet"      # from env (overrides profile)
        assert resolved.format == "json"       # from cli (overrides env)


# ---------------------------------------------------------------------------
# Profile switching via CLI flag
# ---------------------------------------------------------------------------

class TestProfileSwitchingViaCLI:
    def test_cli_profile_flag_selects_profile(self, populated_manager: ProfileManager) -> None:
        resolver = ConfigResolver(profile_manager=populated_manager)
        resolved = resolver.resolve(cli_flags={"profile": "research"})
        assert resolved.active_profile == "research"
        assert resolved.provider == "anthropic"

    def test_profile_name_arg_takes_precedence(self, populated_manager: ProfileManager) -> None:
        resolver = ConfigResolver(profile_manager=populated_manager)
        # Both profile_name kwarg and cli_flags["profile"] — cli_flags wins
        resolved = resolver.resolve(
            cli_flags={"profile": "quick"},
            profile_name="quick",
        )
        assert resolved.active_profile == "quick"


# ---------------------------------------------------------------------------
# Config file validation errors
# ---------------------------------------------------------------------------

class TestConfigValidationErrors:
    def test_invalid_toml_raises_profile_error(self, tmp_path: Path) -> None:
        config_file = tmp_path / "config.toml"
        config_file.write_text("this is [not valid toml\n")
        pm = ProfileManager(config_dir=tmp_path)
        from src.summarizer.profile import ProfileError
        with pytest.raises(ProfileError, match="Failed to parse"):
            pm.load()

    def test_invalid_provider_in_config_raises_error(self, tmp_path: Path) -> None:
        config_file = tmp_path / "config.toml"
        config_file.write_text(
            '[default]\nprofile = "myprofile"\n\n[myprofile]\nprovider = "invalid_provider"\n'
        )
        pm = ProfileManager(config_dir=tmp_path)
        from src.summarizer.profile import ProfileError
        with pytest.raises(ProfileError, match="Invalid config file"):
            pm.load()

    def test_invalid_style_in_config_raises_error(self, tmp_path: Path) -> None:
        config_file = tmp_path / "config.toml"
        config_file.write_text('[work]\nstyle = "super-detailed"\n')
        pm = ProfileManager(config_dir=tmp_path)
        from src.summarizer.profile import ProfileError
        with pytest.raises(ProfileError, match="Invalid config file"):
            pm.load()

    def test_invalid_format_in_config_raises_error(self, tmp_path: Path) -> None:
        config_file = tmp_path / "config.toml"
        config_file.write_text('[work]\nformat = "pdf"\n')
        pm = ProfileManager(config_dir=tmp_path)
        from src.summarizer.profile import ProfileError
        with pytest.raises(ProfileError, match="Invalid config file"):
            pm.load()
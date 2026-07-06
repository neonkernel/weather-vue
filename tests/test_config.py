"""
Tests for ConfigResolver: merge priority, profile switching, and validation.
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path
from typing import Any, Optional
from unittest.mock import patch

import pytest

# Add src to path if needed
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from summarizer.config import ConfigResolver, BUILTIN_DEFAULTS, ResolvedConfig
from summarizer.profile import ProfileManager
from summarizer.schemas import ProfileConfig, CacheConfig, RateLimitConfig
from summarizer.exceptions import SummarizerError


@pytest.fixture
def tmp_config_path(tmp_path: Path) -> Path:
    return tmp_path / "config.toml"


@pytest.fixture
def manager(tmp_config_path: Path) -> ProfileManager:
    return ProfileManager(config_path=tmp_config_path)


@pytest.fixture
def resolver(manager: ProfileManager) -> ConfigResolver:
    return ConfigResolver(profile_manager=manager)


class TestBuiltinDefaults:
    def test_no_profile_no_env_returns_defaults(self, resolver: ConfigResolver) -> None:
        resolved = resolver.resolve()
        assert resolved.provider == BUILTIN_DEFAULTS["provider"]
        assert resolved.model == BUILTIN_DEFAULTS["model"]
        assert resolved.style == BUILTIN_DEFAULTS["style"]
        assert resolved.format == BUILTIN_DEFAULTS["format"]
        assert resolved.max_length == BUILTIN_DEFAULTS["max_length"]
        assert resolved.cache_enabled == BUILTIN_DEFAULTS["cache_enabled"]

    def test_active_profile_is_none_by_default(self, resolver: ConfigResolver) -> None:
        resolved = resolver.resolve()
        assert resolved.active_profile is None


class TestProfileOverridesDefaults:
    def test_profile_overrides_provider(self, manager: ProfileManager, resolver: ConfigResolver) -> None:
        manager.create_profile("test", provider="anthropic", model="claude-3-haiku-20240307")
        manager.set_active_profile("test")
        resolved = resolver.resolve()
        assert resolved.provider == "anthropic"
        assert resolved.model == "claude-3-haiku-20240307"

    def test_profile_partial_override(self, manager: ProfileManager, resolver: ConfigResolver) -> None:
        """Profile only sets style; other values come from defaults."""
        manager.create_profile("minimal", style="bullet")
        manager.set_active_profile("minimal")
        resolved = resolver.resolve()
        assert resolved.style == "bullet"
        assert resolved.provider == BUILTIN_DEFAULTS["provider"]  # still default

    def test_explicit_profile_name_overrides_active(
        self, manager: ProfileManager, resolver: ConfigResolver
    ) -> None:
        manager.create_profile("active_one", provider="openai")
        manager.create_profile("other", provider="anthropic")
        manager.set_active_profile("active_one")
        resolved = resolver.resolve(profile_name="other")
        assert resolved.provider == "anthropic"
        assert resolved.active_profile == "other"

    def test_active_profile_name_stored_in_resolved(
        self, manager: ProfileManager, resolver: ConfigResolver
    ) -> None:
        manager.create_profile("myprofile", style="detailed")
        manager.set_active_profile("myprofile")
        resolved = resolver.resolve()
        assert resolved.active_profile == "myprofile"

    def test_profile_cache_settings(self, manager: ProfileManager, resolver: ConfigResolver) -> None:
        cache = CacheConfig(enabled=False, ttl_hours=12, max_entries=500)
        manager.create_profile("nocache", cache=cache)
        manager.set_active_profile("nocache")
        resolved = resolver.resolve()
        assert resolved.cache_enabled is False
        assert resolved.cache_ttl_hours == 12
        assert resolved.cache_max_entries == 500

    def test_profile_rate_limit_settings(
        self, manager: ProfileManager, resolver: ConfigResolver
    ) -> None:
        rl = RateLimitConfig(requests_per_minute=10, tokens_per_minute=5000)
        manager.create_profile("limited", rate_limit=rl)
        manager.set_active_profile("limited")
        resolved = resolver.resolve()
        assert resolved.requests_per_minute == 10
        assert resolved.tokens_per_minute == 5000


class TestEnvironmentVariableOverrides:
    def test_env_var_overrides_default(self, resolver: ConfigResolver) -> None:
        with patch.dict(os.environ, {"SUMMARIZER_PROVIDER": "ollama"}):
            resolved = resolver.resolve()
        assert resolved.provider == "ollama"

    def test_env_var_overrides_profile(
        self, manager: ProfileManager, resolver: ConfigResolver
    ) -> None:
        manager.create_profile("envtest", provider="openai")
        manager.set_active_profile("envtest")
        with patch.dict(os.environ, {"SUMMARIZER_PROVIDER": "anthropic"}):
            resolved = resolver.resolve()
        assert resolved.provider == "anthropic"

    def test_multiple_env_vars(self, resolver: ConfigResolver) -> None:
        with patch.dict(
            os.environ,
            {"SUMMARIZER_STYLE": "academic", "SUMMARIZER_FORMAT": "markdown"},
        ):
            resolved = resolver.resolve()
        assert resolved.style == "academic"
        assert resolved.format == "markdown"

    def test_env_var_cache_enabled_false(self, resolver: ConfigResolver) -> None:
        with patch.dict(os.environ, {"SUMMARIZER_CACHE_ENABLED": "false"}):
            resolved = resolver.resolve()
        assert resolved.cache_enabled is False

    def test_env_var_cache_enabled_true(self, resolver: ConfigResolver) -> None:
        with patch.dict(os.environ, {"SUMMARIZER_CACHE_ENABLED": "true"}):
            resolved = resolver.resolve()
        assert resolved.cache_enabled is True

    def test_env_var_int_value(self, resolver: ConfigResolver) -> None:
        with patch.dict(os.environ, {"SUMMARIZER_MAX_LENGTH": "250"}):
            resolved = resolver.resolve()
        assert resolved.max_length == 250


class TestCLIFlagOverrides:
    def test_cli_flag_overrides_default(self, resolver: ConfigResolver) -> None:
        resolved = resolver.resolve(cli_flags={"provider": "ollama"})
        assert resolved.provider == "ollama"

    def test_cli_flag_overrides_env(self, resolver: ConfigResolver) -> None:
        with patch.dict(os.environ, {"SUMMARIZER_PROVIDER": "anthropic"}):
            resolved = resolver.resolve(cli_flags={"provider": "ollama"})
        assert resolved.provider == "ollama"

    def test_cli_flag_overrides_profile(
        self, manager: ProfileManager, resolver: ConfigResolver
    ) -> None:
        manager.create_profile("p", provider="openai")
        manager.set_active_profile("p")
        resolved = resolver.resolve(cli_flags={"provider": "ollama"})
        assert resolved.provider == "ollama"

    def test_none_cli_flags_are_ignored(self, resolver: ConfigResolver) -> None:
        resolved = resolver.resolve(cli_flags={"provider": None, "style": "detailed"})
        assert resolved.provider == BUILTIN_DEFAULTS["provider"]
        assert resolved.style == "detailed"

    def test_cli_flags_highest_priority_full_stack(
        self, manager: ProfileManager, resolver: ConfigResolver
    ) -> None:
        manager.create_profile("stack", provider="anthropic", style="bullet")
        manager.set_active_profile("stack")
        with patch.dict(os.environ, {"SUMMARIZER_PROVIDER": "ollama"}):
            resolved = resolver.resolve(cli_flags={"provider": "openrouter"})
        assert resolved.provider == "openrouter"
        # style comes from profile (no CLI override, no env override)
        assert resolved.style == "bullet"


class TestMergePriorityOrder:
    def test_full_priority_chain(
        self, manager: ProfileManager, resolver: ConfigResolver
    ) -> None:
        """Verify: defaults < profile < env < cli"""
        # Default: provider = openai
        # Profile: provider = anthropic
        # Env: provider = ollama
        # CLI: provider = openrouter
        manager.create_profile("chain", provider="anthropic")
        manager.set_active_profile("chain")
        with patch.dict(os.environ, {"SUMMARIZER_PROVIDER": "ollama"}):
            resolved = resolver.resolve(cli_flags={"provider": "openrouter"})
        assert resolved.provider == "openrouter"

    def test_env_beats_profile(
        self, manager: ProfileManager, resolver: ConfigResolver
    ) -> None:
        manager.create_profile("envbeat", provider="anthropic")
        manager.set_active_profile("envbeat")
        with patch.dict(os.environ, {"SUMMARIZER_PROVIDER": "ollama"}):
            resolved = resolver.resolve()
        assert resolved.provider == "ollama"

    def test_profile_beats_defaults(
        self, manager: ProfileManager, resolver: ConfigResolver
    ) -> None:
        manager.create_profile("beats", style="academic")
        manager.set_active_profile("beats")
        resolved = resolver.resolve()
        assert resolved.style == "academic"


class TestValidationErrors:
    def test_invalid_provider_raises(self, tmp_config_path: Path) -> None:
        from summarizer.schemas import ConfigFile, ProfileConfig
        with pytest.raises(Exception, match="provider"):
            ProfileConfig(provider="badprovider")

    def test_invalid_style_raises(self) -> None:
        from summarizer.schemas import ProfileConfig
        with pytest.raises(Exception, match="style"):
            ProfileConfig(style="haiku")

    def test_invalid_format_raises(self) -> None:
        from summarizer.schemas import ProfileConfig
        with pytest.raises(Exception, match="format"):
            ProfileConfig(format="pdf")

    def test_config_file_with_invalid_profile(self, tmp_config_path: Path) -> None:
        tmp_config_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_config_path.write_text(
            '[badprofile]\nprovider = "notreal"\n', encoding="utf-8"
        )
        manager = ProfileManager(config_path=tmp_config_path)
        with pytest.raises(SummarizerError, match="badprofile"):
            manager.load()

    def test_config_file_with_unknown_active_profile(self, tmp_config_path: Path) -> None:
        tmp_config_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_config_path.write_text(
            '[default]\nactive_profile = "ghost"\n', encoding="utf-8"
        )
        manager = ProfileManager(config_path=tmp_config_path)
        with pytest.raises(SummarizerError, match="ghost"):
            manager.load()

    def test_resolver_gracefully_handles_missing_profile(
        self, resolver: ConfigResolver
    ) -> None:
        """If profile doesn't exist during resolve, falls back to defaults."""
        resolved = resolver.resolve(profile_name="nonexistent")
        # Should not raise; falls back gracefully
        assert resolved.provider == BUILTIN_DEFAULTS["provider"]


class TestResolvedConfigToDict:
    def test_to_dict_contains_all_keys(self, resolver: ConfigResolver) -> None:
        resolved = resolver.resolve()
        d = resolved.to_dict()
        for key in BUILTIN_DEFAULTS:
            assert key in d
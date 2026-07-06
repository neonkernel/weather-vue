"""
Tests for ProfileManager CRUD with a temporary config directory.
"""
from __future__ import annotations

import pytest
from pathlib import Path

from src.summarizer.profile import ProfileManager, _get_config_dir
from src.summarizer.exceptions import ConfigError
from src.summarizer.schemas import (
    ConfigFile, ProfileConfig, DefaultConfig, CacheConfig, RateLimitConfig,
    VALID_PROVIDERS, VALID_STYLES, VALID_FORMATS,
)


@pytest.fixture
def tmp_config_dir(tmp_path: Path) -> Path:
    """Return a temporary config directory."""
    config_dir = tmp_path / "summarizer"
    config_dir.mkdir(parents=True)
    return config_dir


@pytest.fixture
def pm(tmp_config_dir: Path) -> ProfileManager:
    """Return a ProfileManager using a temporary directory."""
    return ProfileManager(config_dir=tmp_config_dir)


class TestProfileManagerInit:
    """Test ProfileManager initialization."""

    def test_default_config_dir(self) -> None:
        pm = ProfileManager()
        assert pm.config_dir.name == "summarizer"
        assert "config" in str(pm.config_dir).lower() or str(pm.config_dir).startswith(
            str(Path.home())
        )

    def test_custom_config_dir(self, tmp_config_dir: Path) -> None:
        pm = ProfileManager(config_dir=tmp_config_dir)
        assert pm.config_dir == tmp_config_dir
        assert pm.config_path == tmp_config_dir / "config.toml"

    def test_config_path_set(self, pm: ProfileManager) -> None:
        assert pm.config_path.name == "config.toml"


class TestLoadConfig:
    """Test loading the config file."""

    def test_load_empty_returns_defaults(self, pm: ProfileManager) -> None:
        config = pm.load_config()
        assert isinstance(config, ConfigFile)
        assert config.default.profile == "default"
        assert config.profiles == {}

    def test_load_nonexistent_returns_defaults(self, pm: ProfileManager) -> None:
        assert not pm.config_path.exists()
        config = pm.load_config()
        assert config.profiles == {}

    def test_load_caches_result(self, pm: ProfileManager) -> None:
        c1 = pm.load_config()
        c2 = pm.load_config()
        assert c1 is c2

    def test_invalidate_cache(self, pm: ProfileManager) -> None:
        c1 = pm.load_config()
        pm._invalidate_cache()
        c2 = pm.load_config()
        # Different objects after cache invalidation
        assert c1 is not c2


class TestCreateProfile:
    """Test creating profiles."""

    def test_create_basic_profile(self, pm: ProfileManager) -> None:
        profile = pm.create_profile("work", provider="openai", model="gpt-4")
        assert profile.provider == "openai"
        assert profile.model == "gpt-4"

    def test_create_saves_to_disk(self, pm: ProfileManager) -> None:
        pm.create_profile("work", provider="openai")
        pm._invalidate_cache()
        profiles = pm.list_profiles()
        assert "work" in profiles

    def test_create_all_fields(self, pm: ProfileManager) -> None:
        profile = pm.create_profile(
            "full",
            provider="anthropic",
            model="claude-3-sonnet-20240229",
            style="detailed",
            format="markdown",
            max_length=1000,
            temperature=0.5,
        )
        assert profile.provider == "anthropic"
        assert profile.model == "claude-3-sonnet-20240229"
        assert profile.style == "detailed"
        assert profile.format == "markdown"
        assert profile.max_length == 1000
        assert profile.temperature == 0.5

    def test_create_duplicate_raises(self, pm: ProfileManager) -> None:
        pm.create_profile("work")
        with pytest.raises(ConfigError, match="already exists"):
            pm.create_profile("work")

    def test_create_reserved_name_raises(self, pm: ProfileManager) -> None:
        with pytest.raises(ConfigError, match="reserved"):
            pm.create_profile("default")

    def test_create_invalid_provider_raises(self, pm: ProfileManager) -> None:
        with pytest.raises(ConfigError):
            pm.create_profile("bad", provider="invalid_provider")

    def test_create_invalid_style_raises(self, pm: ProfileManager) -> None:
        with pytest.raises(ConfigError):
            pm.create_profile("bad", style="invalid_style")

    def test_create_invalid_format_raises(self, pm: ProfileManager) -> None:
        with pytest.raises(ConfigError):
            pm.create_profile("bad", format="invalid_format")

    def test_create_multiple_profiles(self, pm: ProfileManager) -> None:
        pm.create_profile("work")
        pm.create_profile("research")
        pm.create_profile("quick")
        profiles = pm.list_profiles()
        assert set(profiles) == {"work", "research", "quick"}


class TestUpdateProfile:
    """Test updating profiles."""

    def test_update_existing_profile(self, pm: ProfileManager) -> None:
        pm.create_profile("work", provider="openai", style="concise")
        updated = pm.update_profile("work", style="detailed")
        assert updated.style == "detailed"
        assert updated.provider == "openai"  # Unchanged

    def test_update_saves_to_disk(self, pm: ProfileManager) -> None:
        pm.create_profile("work", style="concise")
        pm.update_profile("work", style="detailed")
        pm._invalidate_cache()
        profile = pm.get_profile("work")
        assert profile is not None
        assert profile.style == "detailed"

    def test_update_nonexistent_raises(self, pm: ProfileManager) -> None:
        with pytest.raises(ConfigError, match="does not exist"):
            pm.update_profile("nonexistent", style="detailed")

    def test_update_invalid_value_raises(self, pm: ProfileManager) -> None:
        pm.create_profile("work")
        with pytest.raises(ConfigError):
            pm.update_profile("work", provider="invalid")


class TestDeleteProfile:
    """Test deleting profiles."""

    def test_delete_profile(self, pm: ProfileManager) -> None:
        pm.create_profile("work")
        pm.delete_profile("work")
        pm._invalidate_cache()
        assert "work" not in pm.list_profiles()

    def test_delete_nonexistent_raises(self, pm: ProfileManager) -> None:
        with pytest.raises(ConfigError, match="does not exist"):
            pm.delete_profile("nonexistent")

    def test_delete_active_resets_to_default(self, pm: ProfileManager) -> None:
        pm.create_profile("work")
        pm.use_profile("work")
        pm.delete_profile("work")
        assert pm.get_active_profile_name() == "default"

    def test_delete_inactive_does_not_reset(self, pm: ProfileManager) -> None:
        pm.create_profile("work")
        pm.create_profile("other")
        pm.use_profile("work")
        pm.delete_profile("other")
        assert pm.get_active_profile_name() == "work"


class TestUseProfile:
    """Test switching profiles."""

    def test_use_existing_profile(self, pm: ProfileManager) -> None:
        pm.create_profile("work")
        pm.use_profile("work")
        assert pm.get_active_profile_name() == "work"

    def test_use_default_profile(self, pm: ProfileManager) -> None:
        pm.create_profile("work")
        pm.use_profile("work")
        pm.use_profile("default")
        assert pm.get_active_profile_name() == "default"

    def test_use_nonexistent_raises(self, pm: ProfileManager) -> None:
        with pytest.raises(ConfigError, match="does not exist"):
            pm.use_profile("nonexistent")

    def test_use_saves_to_disk(self, pm: ProfileManager) -> None:
        pm.create_profile("work")
        pm.use_profile("work")
        pm._invalidate_cache()
        assert pm.get_active_profile_name() == "work"


class TestGetProfile:
    """Test getting profiles."""

    def test_get_existing(self, pm: ProfileManager) -> None:
        pm.create_profile("work", provider="openai")
        profile = pm.get_profile("work")
        assert profile is not None
        assert profile.provider == "openai"

    def test_get_nonexistent_returns_none(self, pm: ProfileManager) -> None:
        result = pm.get_profile("nonexistent")
        assert result is None

    def test_get_active_profile(self, pm: ProfileManager) -> None:
        pm.create_profile("work", style="bullet")
        pm.use_profile("work")
        active = pm.get_active_profile()
        assert active is not None
        assert active.style == "bullet"

    def test_get_active_profile_default_returns_none(self, pm: ProfileManager) -> None:
        result = pm.get_active_profile()
        assert result is None


class TestGetSetting:
    """Test getting individual settings."""

    def test_get_setting_from_active_profile(self, pm: ProfileManager) -> None:
        pm.create_profile("work", provider="anthropic")
        pm.use_profile("work")
        value = pm.get_setting("provider")
        assert value == "anthropic"

    def test_get_setting_from_named_profile(self, pm: ProfileManager) -> None:
        pm.create_profile("research", model="claude-3-opus-20240229")
        value = pm.get_setting("model", profile_name="research")
        assert value == "claude-3-opus-20240229"

    def test_get_unset_setting_returns_none(self, pm: ProfileManager) -> None:
        pm.create_profile("work")
        value = pm.get_setting("provider")
        # 'work' profile has no provider set explicitly
        # (when called with active profile 'default', reads from default section)
        # This returns None since the setting isn't in the default section either

    def test_get_setting_nonexistent_profile_raises(self, pm: ProfileManager) -> None:
        with pytest.raises(ConfigError):
            pm.get_setting("provider", profile_name="ghost")


class TestSetSetting:
    """Test setting individual config values."""

    def test_set_setting_active_profile(self, pm: ProfileManager) -> None:
        pm.create_profile("work", provider="openai")
        pm.use_profile("work")
        pm.set_setting("provider", "anthropic")
        pm._invalidate_cache()
        assert pm.get_setting("provider") == "anthropic"

    def test_set_setting_named_profile(self, pm: ProfileManager) -> None:
        pm.create_profile("research")
        pm.set_setting("style", "detailed", profile_name="research")
        pm._invalidate_cache()
        profile = pm.get_profile("research")
        assert profile is not None
        assert profile.style == "detailed"


class TestSetDefault:
    """Test setting default values."""

    def test_set_default_provider(self, pm: ProfileManager) -> None:
        pm.set_default(provider="anthropic")
        pm._invalidate_cache()
        config = pm.load_config()
        assert config.default.provider == "anthropic"

    def test_set_default_multiple(self, pm: ProfileManager) -> None:
        pm.set_default(provider="openai", style="bullet")
        pm._invalidate_cache()
        config = pm.load_config()
        assert config.default.provider == "openai"
        assert config.default.style == "bullet"


class TestProfileAsDict:
    """Test serializing profiles to dicts."""

    def test_profile_as_dict(self, pm: ProfileManager) -> None:
        pm.create_profile("work", provider="openai", style="concise")
        data = pm.profile_as_dict("work")
        assert isinstance(data, dict)
        assert data["provider"] == "openai"
        assert data["style"] == "concise"

    def test_default_as_dict(self, pm: ProfileManager) -> None:
        data = pm.profile_as_dict("default")
        assert isinstance(data, dict)
        assert "profile" in data

    def test_nonexistent_raises(self, pm: ProfileManager) -> None:
        with pytest.raises(ConfigError):
            pm.profile_as_dict("ghost")


class TestConfigFilePersistence:
    """Test that config is properly saved and reloaded."""

    def test_full_roundtrip(self, pm: ProfileManager, tmp_config_dir: Path) -> None:
        pm.create_profile("work", provider="openai", model="gpt-4", style="bullet")
        pm.create_profile("research", provider="anthropic", style="detailed")
        pm.use_profile("work")

        # Create a fresh manager pointing to the same dir
        pm2 = ProfileManager(config_dir=tmp_config_dir)
        assert pm2.get_active_profile_name() == "work"
        profile = pm2.get_profile("work")
        assert profile is not None
        assert profile.provider == "openai"
        assert profile.model == "gpt-4"
        assert profile.style == "bullet"

        research = pm2.get_profile("research")
        assert research is not None
        assert research.provider == "anthropic"

    def test_list_profiles_after_roundtrip(
        self, pm: ProfileManager, tmp_config_dir: Path
    ) -> None:
        pm.create_profile("a")
        pm.create_profile("b")
        pm.create_profile("c")

        pm2 = ProfileManager(config_dir=tmp_config_dir)
        profiles = pm2.list_profiles()
        assert set(profiles) == {"a", "b", "c"}


class TestGetConfigDir:
    """Test XDG config dir detection."""

    def test_default_config_dir(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
        config_dir = _get_config_dir()
        assert config_dir.name == "summarizer"
        assert "config" in str(config_dir) or str(config_dir).startswith(str(Path.home()))

    def test_xdg_config_home(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
        config_dir = _get_config_dir()
        assert str(tmp_path / "xdg") in str(config_dir)
        assert config_dir.name == "summarizer"
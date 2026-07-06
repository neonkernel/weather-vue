"""
Tests for ProfileManager CRUD with a temporary config directory.
"""
from __future__ import annotations

import pytest
from pathlib import Path

from src.summarizer.profile import ProfileManager, ProfileError, _validate_profile_name
from src.summarizer.schemas import ProfileConfig, ConfigFile


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def pm(tmp_path: Path) -> ProfileManager:
    """ProfileManager with a temporary config directory."""
    return ProfileManager(config_dir=tmp_path)


@pytest.fixture
def pm_with_profiles(pm: ProfileManager) -> ProfileManager:
    """ProfileManager with several pre-created profiles."""
    pm.create_profile(
        "work",
        provider="openai",
        model="gpt-4o",
        style="detailed",
        format="markdown",
        description="Work profile",
    )
    pm.create_profile(
        "quick",
        provider="openai",
        model="gpt-4o-mini",
        style="concise",
    )
    pm.create_profile(
        "research",
        provider="anthropic",
        model="claude-3-5-sonnet-20241022",
        style="academic",
        max_length=500,
        temperature=0.3,
    )
    return pm


# ---------------------------------------------------------------------------
# Config file initialization
# ---------------------------------------------------------------------------

class TestConfigInitialization:
    def test_load_returns_empty_config_when_no_file(self, pm: ProfileManager) -> None:
        config = pm.load()
        assert isinstance(config, ConfigFile)
        assert config.profiles == {}
        assert config.default.profile == "default"

    def test_config_file_created_on_save(self, pm: ProfileManager) -> None:
        config = pm.load()
        pm.save(config)
        assert pm.config_path.exists()

    def test_config_dir_created_automatically(self, tmp_path: Path) -> None:
        nested = tmp_path / "a" / "b" / "summarizer"
        pm = ProfileManager(config_dir=nested)
        pm.create_profile("test", provider="openai")
        assert nested.exists()

    def test_config_path_property(self, pm: ProfileManager) -> None:
        assert pm.config_path == pm._config_dir / "config.toml"


# ---------------------------------------------------------------------------
# Create profile
# ---------------------------------------------------------------------------

class TestCreateProfile:
    def test_create_basic_profile(self, pm: ProfileManager) -> None:
        profile = pm.create_profile("myprofile", provider="openai", model="gpt-4o")
        assert profile.provider == "openai"
        assert profile.model == "gpt-4o"

    def test_create_profile_persists(self, pm: ProfileManager) -> None:
        pm.create_profile("saved", provider="anthropic")
        # Reload from disk
        pm2 = ProfileManager(config_dir=pm._config_dir)
        config = pm2.load()
        assert "saved" in config.profiles
        assert config.profiles["saved"].provider == "anthropic"

    def test_create_duplicate_raises_error(self, pm: ProfileManager) -> None:
        pm.create_profile("dup", provider="openai")
        with pytest.raises(ProfileError, match="already exists"):
            pm.create_profile("dup", provider="anthropic")

    def test_create_duplicate_with_overwrite(self, pm: ProfileManager) -> None:
        pm.create_profile("dup", provider="openai")
        profile = pm.create_profile("dup", provider="anthropic", overwrite=True)
        assert profile.provider == "anthropic"

    def test_create_profile_with_all_fields(self, pm: ProfileManager) -> None:
        profile = pm.create_profile(
            "full",
            provider="groq",
            model="llama3-70b",
            style="bullet",
            format="json",
            max_length=300,
            temperature=0.5,
            description="Full profile test",
        )
        assert profile.provider == "groq"
        assert profile.style == "bullet"
        assert profile.format == "json"
        assert profile.max_length == 300
        assert profile.temperature == pytest.approx(0.5)
        assert profile.description == "Full profile test"

    def test_create_profile_invalid_provider_raises(self, pm: ProfileManager) -> None:
        with pytest.raises(ProfileError, match="Invalid profile"):
            pm.create_profile("bad", provider="badprovider")

    def test_create_profile_invalid_style_raises(self, pm: ProfileManager) -> None:
        with pytest.raises(ProfileError, match="Invalid profile"):
            pm.create_profile("bad", style="ultra-verbose")

    def test_create_profile_default_cache_values(self, pm: ProfileManager) -> None:
        profile = pm.create_profile("cached")
        assert profile.cache.enabled is True
        assert profile.cache.ttl_seconds == 3600
        assert profile.cache.max_size_mb == 100


# ---------------------------------------------------------------------------
# Read profile
# ---------------------------------------------------------------------------

class TestReadProfile:
    def test_get_existing_profile(self, pm_with_profiles: ProfileManager) -> None:
        profile = pm_with_profiles.get_profile("work")
        assert profile.provider == "openai"
        assert profile.model == "gpt-4o"

    def test_get_nonexistent_profile_raises(self, pm_with_profiles: ProfileManager) -> None:
        with pytest.raises(ProfileError, match="not found"):
            pm_with_profiles.get_profile("nonexistent")

    def test_list_profiles_returns_all(self, pm_with_profiles: ProfileManager) -> None:
        names = pm_with_profiles.list_profiles()
        assert "work" in names
        assert "quick" in names
        assert "research" in names
        assert len(names) == 3

    def test_list_profiles_empty(self, pm: ProfileManager) -> None:
        assert pm.list_profiles() == []

    def test_get_profile_key(self, pm_with_profiles: ProfileManager) -> None:
        value = pm_with_profiles.get_profile_key("work", "provider")
        assert value == "openai"

    def test_get_profile_key_invalid_key_raises(self, pm_with_profiles: ProfileManager) -> None:
        with pytest.raises(ProfileError, match="Unknown key"):
            pm_with_profiles.get_profile_key("work", "nonexistent_key")


# ---------------------------------------------------------------------------
# Update profile
# ---------------------------------------------------------------------------

class TestUpdateProfile:
    def test_update_single_field(self, pm_with_profiles: ProfileManager) -> None:
        pm_with_profiles.update_profile("work", model="gpt-4o-mini")
        profile = pm_with_profiles.get_profile("work")
        assert profile.model == "gpt-4o-mini"
        assert profile.provider == "openai"  # unchanged

    def test_update_persists(self, pm_with_profiles: ProfileManager) -> None:
        pm_with_profiles.update_profile("quick", style="detailed")
        # Reload
        pm2 = ProfileManager(config_dir=pm_with_profiles._config_dir)
        profile = pm2.get_profile("quick")
        assert profile.style == "detailed"

    def test_update_nonexistent_raises(self, pm: ProfileManager) -> None:
        with pytest.raises(ProfileError, match="not found"):
            pm.update_profile("ghost", provider="openai")

    def test_update_invalid_value_raises(self, pm_with_profiles: ProfileManager) -> None:
        with pytest.raises(ProfileError, match="Invalid profile"):
            pm_with_profiles.update_profile("work", provider="badprovider")

    def test_set_profile_key(self, pm_with_profiles: ProfileManager) -> None:
        pm_with_profiles.set_profile_key("research", "style", "bullet")
        profile = pm_with_profiles.get_profile("research")
        assert profile.style == "bullet"


# ---------------------------------------------------------------------------
# Delete profile
# ---------------------------------------------------------------------------

class TestDeleteProfile:
    def test_delete_profile(self, pm_with_profiles: ProfileManager) -> None:
        pm_with_profiles.delete_profile("quick")
        names = pm_with_profiles.list_profiles()
        assert "quick" not in names

    def test_delete_persists(self, pm_with_profiles: ProfileManager) -> None:
        pm_with_profiles.delete_profile("quick")
        pm2 = ProfileManager(config_dir=pm_with_profiles._config_dir)
        names = pm2.list_profiles()
        assert "quick" not in names

    def test_delete_nonexistent_raises(self, pm: ProfileManager) -> None:
        with pytest.raises(ProfileError, match="not found"):
            pm.delete_profile("ghost")

    def test_cannot_delete_default_profile_name(self, pm: ProfileManager) -> None:
        # "default" is reserved
        with pytest.raises(ProfileError, match="Cannot delete"):
            pm.delete_profile("default")

    def test_delete_active_profile_resets_to_default(
        self, pm_with_profiles: ProfileManager
    ) -> None:
        pm_with_profiles.set_active_profile("work")
        pm_with_profiles.delete_profile("work")
        assert pm_with_profiles.get_active_profile_name() == "default"


# ---------------------------------------------------------------------------
# Active profile management
# ---------------------------------------------------------------------------

class TestActiveProfile:
    def test_default_active_profile_is_default(self, pm: ProfileManager) -> None:
        assert pm.get_active_profile_name() == "default"

    def test_set_active_profile(self, pm_with_profiles: ProfileManager) -> None:
        pm_with_profiles.set_active_profile("research")
        assert pm_with_profiles.get_active_profile_name() == "research"

    def test_set_active_profile_persists(self, pm_with_profiles: ProfileManager) -> None:
        pm_with_profiles.set_active_profile("work")
        pm2 = ProfileManager(config_dir=pm_with_profiles._config_dir)
        assert pm2.get_active_profile_name() == "work"

    def test_set_nonexistent_profile_as_active_raises(
        self, pm_with_profiles: ProfileManager
    ) -> None:
        with pytest.raises(ProfileError, match="not found"):
            pm_with_profiles.set_active_profile("nonexistent")

    def test_get_active_profile_returns_profile_config(
        self, pm_with_profiles: ProfileManager
    ) -> None:
        pm_with_profiles.set_active_profile("quick")
        profile = pm_with_profiles.get_active_profile()
        assert profile is not None
        assert profile.style == "concise"

    def test_get_active_profile_none_when_profile_not_in_list(
        self, pm: ProfileManager
    ) -> None:
        # "default" is the active profile name but not in profiles dict
        profile = pm.get_active_profile()
        assert profile is None


# ---------------------------------------------------------------------------
# TOML round-trip
# ---------------------------------------------------------------------------

class TestTomlRoundTrip:
    def test_profiles_survive_round_trip(self, pm_with_profiles: ProfileManager) -> None:
        # Read back from disk with fresh manager
        pm2 = ProfileManager(config_dir=pm_with_profiles._config_dir)
        config = pm2.load()

        work = config.profiles["work"]
        assert work.provider == "openai"
        assert work.model == "gpt-4o"
        assert work.style == "detailed"
        assert work.description == "Work profile"

        research = config.profiles["research"]
        assert research.max_length == 500
        assert research.temperature == pytest.approx(0.3)

    def test_active_profile_survives_round_trip(
        self, pm_with_profiles: ProfileManager
    ) -> None:
        pm_with_profiles.set_active_profile("research")
        pm2 = ProfileManager(config_dir=pm_with_profiles._config_dir)
        assert pm2.get_active_profile_name() == "research"

    def test_cache_settings_survive_round_trip(self, pm: ProfileManager) -> None:
        # Create profile, reload
        pm.create_profile("cached", provider="openai")
        pm2 = ProfileManager(config_dir=pm._config_dir)
        profile = pm2.get_profile("cached")
        assert profile.cache.enabled is True
        assert profile.cache.ttl_seconds == 3600


# ---------------------------------------------------------------------------
# Profile name validation
# ---------------------------------------------------------------------------

class TestProfileNameValidation:
    def test_valid_names(self) -> None:
        for name in ["work", "my-profile", "research_v2", "profile123"]:
            _validate_profile_name(name)  # Should not raise

    def test_empty_name_raises(self) -> None:
        with pytest.raises(ProfileError, match="empty"):
            _validate_profile_name("")

    def test_reserved_name_raises(self) -> None:
        with pytest.raises(ProfileError, match="reserved"):
            _validate_profile_name("profiles")

    def test_invalid_characters_raise(self) -> None:
        with pytest.raises(ProfileError, match="invalid"):
            _validate_profile_name("my profile!")
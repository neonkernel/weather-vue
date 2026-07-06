"""
Tests for ProfileManager CRUD with a temporary config directory.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from summarizer.exceptions import SummarizerError
from summarizer.profile import ProfileManager, _validate_profile_name
from summarizer.schemas import (
    CacheConfig,
    ProfileConfig,
    RateLimitConfig,
)


@pytest.fixture
def tmp_config_path(tmp_path: Path) -> Path:
    return tmp_path / "config.toml"


@pytest.fixture
def manager(tmp_config_path: Path) -> ProfileManager:
    return ProfileManager(config_path=tmp_config_path)


# ── Create ────────────────────────────────────────────────────────────────────

class TestCreateProfile:
    def test_create_minimal_profile(self, manager: ProfileManager) -> None:
        profile = manager.create_profile("work")
        assert isinstance(profile, ProfileConfig)

    def test_create_profile_with_settings(self, manager: ProfileManager) -> None:
        profile = manager.create_profile("research", provider="anthropic", style="academic")
        assert profile.provider == "anthropic"
        assert profile.style == "academic"

    def test_create_persists_to_disk(self, manager: ProfileManager, tmp_config_path: Path) -> None:
        manager.create_profile("saved", provider="openai")
        assert tmp_config_path.exists()

    def test_create_duplicate_raises(self, manager: ProfileManager) -> None:
        manager.create_profile("dup")
        with pytest.raises(SummarizerError, match="already exists"):
            manager.create_profile("dup")

    def test_create_reserved_name_raises(self, manager: ProfileManager) -> None:
        with pytest.raises(SummarizerError, match="reserved"):
            manager.create_profile("default")

    def test_create_invalid_name_raises(self, manager: ProfileManager) -> None:
        with pytest.raises(SummarizerError, match="invalid characters"):
            manager.create_profile("my profile!")

    def test_create_with_cache_config(self, manager: ProfileManager) -> None:
        cache = CacheConfig(enabled=False, ttl_hours=6)
        profile = manager.create_profile("nocache", cache=cache)
        assert profile.cache is not None
        assert profile.cache.enabled is False
        assert profile.cache.ttl_hours == 6

    def test_create_with_rate_limit(self, manager: ProfileManager) -> None:
        rl = RateLimitConfig(requests_per_minute=10)
        profile = manager.create_profile("slow", rate_limit=rl)
        assert profile.rate_limit is not None
        assert profile.rate_limit.requests_per_minute == 10

    def test_create_with_description(self, manager: ProfileManager) -> None:
        profile = manager.create_profile("described", description="My work profile")
        assert profile.description == "My work profile"


# ── Read ──────────────────────────────────────────────────────────────────────

class TestGetProfile:
    def test_get_existing_profile(self, manager: ProfileManager) -> None:
        manager.create_profile("getme", style="bullet")
        profile = manager.get_profile("getme")
        assert profile.style == "bullet"

    def test_get_nonexistent_raises(self, manager: ProfileManager) -> None:
        with pytest.raises(SummarizerError, match="not found"):
            manager.get_profile("ghost")

    def test_list_profiles_empty(self, manager: ProfileManager) -> None:
        assert manager.list_profiles() == {}

    def test_list_profiles_multiple(self, manager: ProfileManager) -> None:
        manager.create_profile("a")
        manager.create_profile("b")
        manager.create_profile("c")
        profiles = manager.list_profiles()
        assert set(profiles.keys()) == {"a", "b", "c"}


# ── Update ────────────────────────────────────────────────────────────────────

class TestUpdateProfile:
    def test_update_existing_key(self, manager: ProfileManager) -> None:
        manager.create_profile("upd", provider="openai")
        manager.update_profile("upd", provider="anthropic")
        profile = manager.get_profile("upd")
        assert profile.provider == "anthropic"

    def test_update_preserves_unrelated_keys(self, manager: ProfileManager) -> None:
        manager.create_profile("preserve", provider="openai", style="bullet")
        manager.update_profile("preserve", provider="anthropic")
        profile = manager.get_profile("preserve")
        assert profile.provider == "anthropic"
        assert profile.style == "bullet"  # preserved

    def test_update_nonexistent_raises(self, manager: ProfileManager) -> None:
        with pytest.raises(SummarizerError, match="not found"):
            manager.update_profile("nope", style="detailed")

    def test_upsert_creates_if_missing(self, manager: ProfileManager) -> None:
        manager.upsert_profile("brand-new", style="casual")
        profile = manager.get_profile("brand-new")
        assert profile.style == "casual"

    def test_upsert_updates_if_exists(self, manager: ProfileManager) -> None:
        manager.create_profile("upserted", style="concise")
        manager.upsert_profile("upserted", style="detailed")
        profile = manager.get_profile("upserted")
        assert profile.style == "detailed"


# ── Delete ────────────────────────────────────────────────────────────────────

class TestDeleteProfile:
    def test_delete_existing(self, manager: ProfileManager) -> None:
        manager.create_profile("del")
        manager.delete_profile("del")
        with pytest.raises(SummarizerError, match="not found"):
            manager.get_profile("del")

    def test_delete_nonexistent_raises(self, manager: ProfileManager) -> None:
        with pytest.raises(SummarizerError, match="not found"):
            manager.delete_profile("nope")

    def test_delete_clears_active_profile(self, manager: ProfileManager) -> None:
        manager.create_profile("active_del")
        manager.set_active_profile("active_del")
        assert manager.get_active_profile_name() == "active_del"
        manager.delete_profile("active_del")
        assert manager.get_active_profile_name() is None

    def test_delete_non_active_preserves_active(self, manager: ProfileManager) -> None:
        manager.create_profile("keep_active")
        manager.create_profile("delete_me")
        manager.set_active_profile("keep_active")
        manager.delete_profile("delete_me")
        assert manager.get_active_profile_name() == "keep_active"


# ── Rename ────────────────────────────────────────────────────────────────────

class TestRenameProfile:
    def test_rename_existing(self, manager: ProfileManager) -> None:
        manager.create_profile("old", style="casual")
        manager.rename_profile("old", "new")
        with pytest.raises(SummarizerError):
            manager.get_profile("old")
        profile = manager.get_profile("new")
        assert profile.style == "casual"

    def test_rename_updates_active_profile(self, manager: ProfileManager) -> None:
        manager.create_profile("before")
        manager.set_active_profile("before")
        manager.rename_profile("before", "after")
        assert manager.get_active_profile_name() == "after"

    def test_rename_nonexistent_raises(self, manager: ProfileManager) -> None:
        with pytest.raises(SummarizerError, match="not found"):
            manager.rename_profile("ghost", "new")

    def test_rename_to_existing_raises(self, manager: ProfileManager) -> None:
        manager.create_profile("a")
        manager.create_profile("b")
        with pytest.raises(SummarizerError, match="already exists"):
            manager.rename_profile("a", "b")


# ── Active profile ────────────────────────────────────────────────────────────

class TestActiveProfile:
    def test_set_active_profile(self, manager: ProfileManager) -> None:
        manager.create_profile("myprofile")
        manager.set_active_profile("myprofile")
        assert manager.get_active_profile_name() == "myprofile"

    def test_set_active_nonexistent_raises(self, manager: ProfileManager) -> None:
        with pytest.raises(SummarizerError, match="not found"):
            manager.set_active_profile("ghost")

    def test_clear_active_profile(self, manager: ProfileManager) -> None:
        manager.create_profile("p")
        manager.set_active_profile("p")
        manager.clear_active_profile()
        assert manager.get_active_profile_name() is None

    def test_get_active_profile_returns_config(self, manager: ProfileManager) -> None:
        manager.create_profile("theone", provider="anthropic")
        manager.set_active_profile("theone")
        profile = manager.get_active_profile()
        assert profile is not None
        assert profile.provider == "anthropic"

    def test_get_active_profile_none_when_no_active(self, manager: ProfileManager) -> None:
        profile = manager.get_active_profile()
        assert profile is None

    def test_active_profile_persists_across_reload(
        self, manager: ProfileManager, tmp_config_path: Path
    ) -> None:
        manager.create_profile("persistent")
        manager.set_active_profile("persistent")

        # Load a fresh manager from the same path
        new_manager = ProfileManager(config_path=tmp_config_path)
        assert new_manager.get_active_profile_name() == "persistent"


# ── Key-value helpers ─────────────────────────────────────────────────────────

class TestKeyValueHelpers:
    def test_set_and_get_key(self, manager: ProfileManager) -> None:
        manager.create_profile("kv", provider="openai")
        manager.set_profile_key("kv", "style", "detailed")
        value = manager.get_profile_key("kv", "style")
        assert value == "detailed"

    def test_get_nonexistent_key_raises(self, manager: ProfileManager) -> None:
        manager.create_profile("kv2")
        with pytest.raises(SummarizerError, match="Unknown profile key"):
            manager.get_profile_key("kv2", "nonexistent_key")


# ── Persistence ───────────────────────────────────────────────────────────────

class TestPersistence:
    def test_profiles_survive_reload(
        self, manager: ProfileManager, tmp_config_path: Path
    ) -> None:
        manager.create_profile("saved", provider="anthropic", style="academic")

        fresh = ProfileManager(config_path=tmp_config_path)
        fresh.reload()
        profile = fresh.get_profile("saved")
        assert profile.provider == "anthropic"
        assert profile.style == "academic"

    def test_multiple_profiles_survive_reload(
        self, manager: ProfileManager, tmp_config_path: Path
    ) -> None:
        manager.create_profile("work", provider="openai", style="concise")
        manager.create_profile("research", provider="anthropic", style="detailed")
        manager.create_profile("quick", style="bullet")

        fresh = ProfileManager(config_path=tmp_config_path)
        profiles = fresh.list_profiles()
        assert set(profiles.keys()) == {"work", "research", "quick"}

    def test_config_file_created_in_correct_location(
        self, manager: ProfileManager, tmp_config_path: Path
    ) -> None:
        manager.create_profile("loc")
        assert tmp_config_path.exists()

    def test_missing_config_returns_empty(self, tmp_path: Path) -> None:
        path = tmp_path / "nonexistent" / "config.toml"
        m = ProfileManager(config_path=path)
        assert m.list_profiles() == {}
        assert m.get_active_profile_name() is None


# ── Validation ────────────────────────────────────────────────────────────────

class TestValidateName:
    def test_valid_names(self) -> None:
        for name in ["work", "my-profile", "profile_1", "ABC"]:
            _validate_profile_name(name)  # should not raise

    def test_empty_name_raises(self) -> None:
        with pytest.raises(SummarizerError, match="empty"):
            _validate_profile_name("")

    def test_reserved_name_default(self) -> None:
        with pytest.raises(SummarizerError, match="reserved"):
            _validate_profile_name("default")

    def test_reserved_name_profiles(self) -> None:
        with pytest.raises(SummarizerError, match="reserved"):
            _validate_profile_name("profiles")

    def test_invalid_chars(self) -> None:
        with pytest.raises(SummarizerError, match="invalid characters"):
            _validate_profile_name("my profile")

    def test_invalid_chars_special(self) -> None:
        with pytest.raises(SummarizerError, match="invalid characters"):
            _validate_profile_name("profile@work")
"""
ConfigResolver: merges all configuration sources in priority order.

Priority (lowest → highest):
  1. Built-in defaults
  2. Config file profile (active profile or specified profile)
  3. Environment variables
  4. CLI flags
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Optional

from .schemas import ProfileConfig


# ── Built-in defaults ─────────────────────────────────────────────────────────

BUILTIN_DEFAULTS: dict[str, Any] = {
    "provider": "openai",
    "model": "gpt-4o-mini",
    "style": "concise",
    "format": "text",
    "max_length": 500,
    "language": "en",
    "cache_enabled": True,
    "cache_ttl_hours": 24,
    "cache_max_entries": 1000,
    "requests_per_minute": 60,
    "tokens_per_minute": 100000,
}

# Environment variable mapping: env var name → config key
ENV_VAR_MAP: dict[str, str] = {
    "SUMMARIZER_PROVIDER": "provider",
    "SUMMARIZER_MODEL": "model",
    "SUMMARIZER_STYLE": "style",
    "SUMMARIZER_FORMAT": "format",
    "SUMMARIZER_MAX_LENGTH": "max_length",
    "SUMMARIZER_LANGUAGE": "language",
    "SUMMARIZER_CACHE_ENABLED": "cache_enabled",
    "SUMMARIZER_CACHE_TTL_HOURS": "cache_ttl_hours",
    "SUMMARIZER_CACHE_MAX_ENTRIES": "cache_max_entries",
    "SUMMARIZER_REQUESTS_PER_MINUTE": "requests_per_minute",
    "SUMMARIZER_TOKENS_PER_MINUTE": "tokens_per_minute",
}


@dataclass
class ResolvedConfig:
    """The final merged configuration."""
    provider: str = "openai"
    model: str = "gpt-4o-mini"
    style: str = "concise"
    format: str = "text"
    max_length: int = 500
    language: str = "en"
    cache_enabled: bool = True
    cache_ttl_hours: int = 24
    cache_max_entries: int = 1000
    requests_per_minute: int = 60
    tokens_per_minute: int = 100000
    active_profile: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "model": self.model,
            "style": self.style,
            "format": self.format,
            "max_length": self.max_length,
            "language": self.language,
            "cache_enabled": self.cache_enabled,
            "cache_ttl_hours": self.cache_ttl_hours,
            "cache_max_entries": self.cache_max_entries,
            "requests_per_minute": self.requests_per_minute,
            "tokens_per_minute": self.tokens_per_minute,
            "active_profile": self.active_profile,
        }


class ConfigResolver:
    """
    Resolves configuration from multiple sources in priority order:
      1. Built-in defaults
      2. Config file profile
      3. Environment variables
      4. CLI flags (highest priority)
    """

    def __init__(self, profile_manager: Optional[Any] = None) -> None:
        """
        Args:
            profile_manager: A ProfileManager instance. If None, a default one
                             is created lazily.
        """
        self._profile_manager = profile_manager
        self._manager_initialized = profile_manager is not None

    @property
    def profile_manager(self) -> Any:
        if not self._manager_initialized:
            from .profile import ProfileManager
            self._profile_manager = ProfileManager()
            self._manager_initialized = True
        return self._profile_manager

    def resolve(
        self,
        profile_name: Optional[str] = None,
        cli_flags: Optional[dict[str, Any]] = None,
    ) -> ResolvedConfig:
        """
        Resolve the final configuration.

        Args:
            profile_name: Override which profile to use (None = use active profile).
            cli_flags: Dict of CLI flag values. None/missing values are ignored.

        Returns:
            A ResolvedConfig with all sources merged.
        """
        result = dict(BUILTIN_DEFAULTS)

        # Layer 2: Config file profile
        profile_config, active_profile_name = self._load_profile(profile_name)
        if profile_config:
            profile_overrides = self._profile_to_flat_dict(profile_config)
            result.update({k: v for k, v in profile_overrides.items() if v is not None})

        # Layer 3: Environment variables
        env_overrides = self._load_env_vars()
        result.update(env_overrides)

        # Layer 4: CLI flags
        if cli_flags:
            cli_overrides = {k: v for k, v in cli_flags.items() if v is not None}
            result.update(cli_overrides)

        return ResolvedConfig(
            provider=result.get("provider", BUILTIN_DEFAULTS["provider"]),
            model=result.get("model", BUILTIN_DEFAULTS["model"]),
            style=result.get("style", BUILTIN_DEFAULTS["style"]),
            format=result.get("format", BUILTIN_DEFAULTS["format"]),
            max_length=int(result.get("max_length", BUILTIN_DEFAULTS["max_length"])),
            language=result.get("language", BUILTIN_DEFAULTS["language"]),
            cache_enabled=_parse_bool(result.get("cache_enabled", BUILTIN_DEFAULTS["cache_enabled"])),
            cache_ttl_hours=int(result.get("cache_ttl_hours", BUILTIN_DEFAULTS["cache_ttl_hours"])),
            cache_max_entries=int(result.get("cache_max_entries", BUILTIN_DEFAULTS["cache_max_entries"])),
            requests_per_minute=int(result.get("requests_per_minute", BUILTIN_DEFAULTS["requests_per_minute"])),
            tokens_per_minute=int(result.get("tokens_per_minute", BUILTIN_DEFAULTS["tokens_per_minute"])),
            active_profile=active_profile_name,
        )

    def _load_profile(
        self, profile_name: Optional[str]
    ) -> tuple[Optional[ProfileConfig], Optional[str]]:
        """Load a profile config. Returns (ProfileConfig | None, name | None)."""
        try:
            manager = self.profile_manager
        except Exception:
            return None, None

        try:
            if profile_name is not None:
                # Explicit profile requested
                profile = manager.get_profile(profile_name)
                return profile, profile_name
            else:
                # Use active profile
                active_name = manager.get_active_profile_name()
                if active_name:
                    profile = manager.get_active_profile()
                    return profile, active_name
                return None, None
        except Exception:
            # If profile loading fails, continue with other layers
            return None, None

    def _profile_to_flat_dict(self, profile: ProfileConfig) -> dict[str, Any]:
        """Flatten a ProfileConfig into a single-level dict."""
        data = (
            profile.model_dump(exclude_none=True)
            if hasattr(profile, "model_dump")
            else profile.dict(exclude_none=True)
        )
        flat: dict[str, Any] = {}

        for key, value in data.items():
            if key == "cache" and isinstance(value, dict):
                if "enabled" in value:
                    flat["cache_enabled"] = value["enabled"]
                if "ttl_hours" in value:
                    flat["cache_ttl_hours"] = value["ttl_hours"]
                if "max_entries" in value:
                    flat["cache_max_entries"] = value["max_entries"]
            elif key == "rate_limit" and isinstance(value, dict):
                if "requests_per_minute" in value:
                    flat["requests_per_minute"] = value["requests_per_minute"]
                if "tokens_per_minute" in value:
                    flat["tokens_per_minute"] = value["tokens_per_minute"]
            elif key == "description":
                pass  # Skip description
            else:
                flat[key] = value

        return flat

    def _load_env_vars(self) -> dict[str, Any]:
        """Load config values from environment variables."""
        overrides: dict[str, Any] = {}
        for env_var, config_key in ENV_VAR_MAP.items():
            value = os.environ.get(env_var)
            if value is not None:
                overrides[config_key] = value
        return overrides


def _parse_bool(value: Any) -> bool:
    """Parse a boolean value from various types."""
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in ("true", "1", "yes", "on")
    return bool(value)
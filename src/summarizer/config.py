"""
ConfigResolver: merges configuration from multiple sources in priority order.

Priority (lowest to highest):
  1. Hardcoded defaults
  2. Config file profile (active profile from ~/.config/summarizer/config.toml)
  3. Environment variables
  4. CLI flags
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Optional


# ---------------------------------------------------------------------------
# Resolved configuration dataclass
# ---------------------------------------------------------------------------

@dataclass
class ResolvedConfig:
    """The final merged configuration used at runtime."""
    provider: str = "openai"
    model: str = "gpt-4o-mini"
    style: str = "concise"
    format: str = "text"
    max_length: Optional[int] = None
    temperature: Optional[float] = None
    cache_enabled: bool = True
    cache_ttl_seconds: int = 3600
    cache_max_size_mb: int = 100
    requests_per_minute: int = 60
    max_concurrent: int = 5
    active_profile: str = "default"


# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------

DEFAULTS: dict[str, Any] = {
    "provider": "openai",
    "model": "gpt-4o-mini",
    "style": "concise",
    "format": "text",
    "max_length": None,
    "temperature": None,
    "cache_enabled": True,
    "cache_ttl_seconds": 3600,
    "cache_max_size_mb": 100,
    "requests_per_minute": 60,
    "max_concurrent": 5,
    "active_profile": "default",
}

# Environment variable names mapped to resolved config keys
ENV_VAR_MAP: dict[str, str] = {
    "SUMMARIZER_PROVIDER": "provider",
    "SUMMARIZER_MODEL": "model",
    "SUMMARIZER_STYLE": "style",
    "SUMMARIZER_FORMAT": "format",
    "SUMMARIZER_MAX_LENGTH": "max_length",
    "SUMMARIZER_TEMPERATURE": "temperature",
    "SUMMARIZER_CACHE_ENABLED": "cache_enabled",
    "SUMMARIZER_CACHE_TTL": "cache_ttl_seconds",
    "SUMMARIZER_CACHE_MAX_SIZE_MB": "cache_max_size_mb",
    "SUMMARIZER_REQUESTS_PER_MINUTE": "requests_per_minute",
    "SUMMARIZER_MAX_CONCURRENT": "max_concurrent",
    "SUMMARIZER_PROFILE": "active_profile",
}

# Type coercions for environment variables
ENV_TYPE_MAP: dict[str, type] = {
    "max_length": int,
    "temperature": float,
    "cache_enabled": lambda v: v.lower() not in ("0", "false", "no", "off"),
    "cache_ttl_seconds": int,
    "cache_max_size_mb": int,
    "requests_per_minute": int,
    "max_concurrent": int,
}


class ConfigError(Exception):
    """Raised when configuration resolution fails."""
    pass


class ConfigResolver:
    """
    Merges configuration from all sources in priority order.

    Priority (lowest → highest):
      defaults < config file profile < environment variables < CLI flags
    """

    def __init__(self, profile_manager: Optional[Any] = None):
        """
        Args:
            profile_manager: A ProfileManager instance. If None, one is created
                             with the default config path.
        """
        self._profile_manager = profile_manager

    def _get_profile_manager(self) -> Any:
        if self._profile_manager is None:
            from .profile import ProfileManager
            self._profile_manager = ProfileManager()
        return self._profile_manager

    def _load_profile_values(self, profile_name: Optional[str] = None) -> dict[str, Any]:
        """Load values from the config file profile."""
        pm = self._get_profile_manager()

        try:
            config = pm.load()
        except Exception:
            # If config file doesn't exist or can't be read, use empty defaults
            return {}

        # Determine which profile to load
        if profile_name is None:
            profile_name = config.default.profile

        profile = config.get_profile(profile_name)
        if profile is None:
            if profile_name != "default":
                raise ConfigError(
                    f"Profile '{profile_name}' not found in config file."
                )
            return {"active_profile": profile_name}

        result: dict[str, Any] = {"active_profile": profile_name}

        if profile.provider is not None:
            result["provider"] = profile.provider
        if profile.model is not None:
            result["model"] = profile.model
        if profile.style is not None:
            result["style"] = profile.style
        if profile.format is not None:
            result["format"] = profile.format
        if profile.max_length is not None:
            result["max_length"] = profile.max_length
        if profile.temperature is not None:
            result["temperature"] = profile.temperature

        # Cache settings
        result["cache_enabled"] = profile.cache.enabled
        result["cache_ttl_seconds"] = profile.cache.ttl_seconds
        result["cache_max_size_mb"] = profile.cache.max_size_mb

        # Rate limit settings
        result["requests_per_minute"] = profile.rate_limit.requests_per_minute
        result["max_concurrent"] = profile.rate_limit.max_concurrent

        return result

    def _load_env_values(self) -> dict[str, Any]:
        """Load values from environment variables."""
        result: dict[str, Any] = {}
        for env_var, config_key in ENV_VAR_MAP.items():
            value = os.environ.get(env_var)
            if value is not None:
                coerce = ENV_TYPE_MAP.get(config_key)
                if coerce is not None:
                    try:
                        value = coerce(value)
                    except (ValueError, TypeError) as e:
                        raise ConfigError(
                            f"Invalid value for {env_var}='{value}': {e}"
                        ) from e
                result[config_key] = value
        return result

    def resolve(
        self,
        cli_flags: Optional[dict[str, Any]] = None,
        profile_name: Optional[str] = None,
    ) -> ResolvedConfig:
        """
        Build the final ResolvedConfig by merging all sources.

        Args:
            cli_flags: Dict of settings from CLI (None values are ignored).
            profile_name: Explicit profile name to use (overrides config file default).

        Returns:
            ResolvedConfig with all sources merged.
        """
        # Start with defaults
        merged: dict[str, Any] = dict(DEFAULTS)

        # Layer 1: Config file profile
        profile_override = profile_name
        # If CLI specifies --profile, use that for profile loading
        if cli_flags and cli_flags.get("profile"):
            profile_override = cli_flags["profile"]

        try:
            profile_values = self._load_profile_values(profile_override)
            merged.update(profile_values)
        except ConfigError:
            raise
        except Exception:
            pass  # Config file issues are non-fatal at this stage

        # Layer 2: Environment variables
        env_values = self._load_env_values()
        merged.update(env_values)

        # Layer 3: CLI flags (highest priority, skip None values)
        if cli_flags:
            for key, value in cli_flags.items():
                if value is not None and key != "profile":
                    merged[key] = value

        # Build the resolved config
        return ResolvedConfig(
            provider=merged.get("provider", DEFAULTS["provider"]),
            model=merged.get("model", DEFAULTS["model"]),
            style=merged.get("style", DEFAULTS["style"]),
            format=merged.get("format", DEFAULTS["format"]),
            max_length=merged.get("max_length"),
            temperature=merged.get("temperature"),
            cache_enabled=merged.get("cache_enabled", DEFAULTS["cache_enabled"]),
            cache_ttl_seconds=merged.get("cache_ttl_seconds", DEFAULTS["cache_ttl_seconds"]),
            cache_max_size_mb=merged.get("cache_max_size_mb", DEFAULTS["cache_max_size_mb"]),
            requests_per_minute=merged.get("requests_per_minute", DEFAULTS["requests_per_minute"]),
            max_concurrent=merged.get("max_concurrent", DEFAULTS["max_concurrent"]),
            active_profile=merged.get("active_profile", DEFAULTS["active_profile"]),
        )

    def get_active_profile_name(self) -> str:
        """Return the name of the currently active profile."""
        try:
            pm = self._get_profile_manager()
            config = pm.load()
            return config.default.profile
        except Exception:
            return "default"
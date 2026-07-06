"""
ConfigResolver: merges all config sources in priority order.

Priority (lowest to highest):
  1. Built-in defaults
  2. Config file profile
  3. Environment variables
  4. CLI flags
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field, asdict
from typing import Any, Optional

from .exceptions import ConfigError
from .profile import ProfileManager
from .schemas import ProfileConfig


# ── Built-in application defaults ──────────────────────────────────────────

BUILTIN_DEFAULTS: dict[str, Any] = {
    "provider": "openai",
    "model": "gpt-3.5-turbo",
    "style": "concise",
    "format": "text",
    "max_length": 500,
    "temperature": 0.7,
    "cache_enabled": True,
    "cache_ttl_hours": 24,
    "cache_max_size_mb": 100,
    "rate_limit_requests_per_minute": 60,
    "rate_limit_requests_per_day": None,
    "rate_limit_retry_attempts": 3,
    "rate_limit_retry_delay_seconds": 1.0,
}

# Environment variable mapping: env_var_name -> config_key
ENV_VAR_MAP: dict[str, str] = {
    "SUMMARIZER_PROVIDER": "provider",
    "SUMMARIZER_MODEL": "model",
    "SUMMARIZER_STYLE": "style",
    "SUMMARIZER_FORMAT": "format",
    "SUMMARIZER_MAX_LENGTH": "max_length",
    "SUMMARIZER_TEMPERATURE": "temperature",
    "SUMMARIZER_CACHE_ENABLED": "cache_enabled",
    "SUMMARIZER_CACHE_TTL_HOURS": "cache_ttl_hours",
    "SUMMARIZER_CACHE_MAX_SIZE_MB": "cache_max_size_mb",
    "SUMMARIZER_RATE_LIMIT_RPM": "rate_limit_requests_per_minute",
    "SUMMARIZER_RATE_LIMIT_RPD": "rate_limit_requests_per_day",
    "SUMMARIZER_RETRY_ATTEMPTS": "rate_limit_retry_attempts",
    "SUMMARIZER_RETRY_DELAY": "rate_limit_retry_delay_seconds",
    "SUMMARIZER_PROFILE": "profile",
}


@dataclass
class ResolvedConfig:
    """
    The fully resolved configuration after merging all sources.
    All fields have concrete values (no Optionals except where truly optional).
    """
    provider: str = "openai"
    model: str = "gpt-3.5-turbo"
    style: str = "concise"
    format: str = "text"
    max_length: int = 500
    temperature: float = 0.7
    cache_enabled: bool = True
    cache_ttl_hours: int = 24
    cache_max_size_mb: int = 100
    rate_limit_requests_per_minute: int = 60
    rate_limit_requests_per_day: Optional[int] = None
    rate_limit_retry_attempts: int = 3
    rate_limit_retry_delay_seconds: float = 1.0
    profile: str = "default"
    # Source tracking for debugging
    _sources: dict[str, str] = field(default_factory=dict)

    def as_dict(self, include_sources: bool = False) -> dict[str, Any]:
        """Return config as a plain dict."""
        d = asdict(self)
        d.pop("_sources", None)
        if include_sources:
            d["_sources"] = self._sources
        return d

    def __repr__(self) -> str:
        d = self.as_dict()
        items = ", ".join(f"{k}={v!r}" for k, v in d.items())
        return f"ResolvedConfig({items})"


class ConfigResolver:
    """
    Merges configuration from all sources in priority order:
      1. Built-in defaults (lowest)
      2. Config file profile (named profile or [default] section)
      3. Environment variables
      4. CLI flags (highest)

    Usage:
        resolver = ConfigResolver()
        config = resolver.resolve(cli_flags={"provider": "anthropic"})
    """

    def __init__(self, profile_manager: Optional[ProfileManager] = None) -> None:
        self._pm = profile_manager or ProfileManager()

    def resolve(
        self,
        cli_flags: Optional[dict[str, Any]] = None,
        profile_name: Optional[str] = None,
    ) -> ResolvedConfig:
        """
        Resolve configuration by merging all sources.

        Args:
            cli_flags: Dict of CLI-provided flags (None values are ignored).
            profile_name: Override which profile to use (ignores active profile setting).

        Returns:
            ResolvedConfig with all settings merged.
        """
        cli_flags = {k: v for k, v in (cli_flags or {}).items() if v is not None}
        resolved = ResolvedConfig()
        sources: dict[str, str] = {}

        # ── 1. Built-in defaults ──────────────────────────────────────────
        for key, value in BUILTIN_DEFAULTS.items():
            if hasattr(resolved, key):
                setattr(resolved, key, value)
                sources[key] = "default"

        # ── 2. Config file profile ────────────────────────────────────────
        try:
            config_file = self._pm.load_config()

            # Determine which profile to use
            if profile_name is not None:
                active_profile_name = profile_name
            elif "profile" in cli_flags:
                active_profile_name = cli_flags["profile"]
            else:
                active_profile_name = config_file.default.profile

            resolved.profile = active_profile_name

            # Apply [default] section settings first
            default_section = config_file.default
            _apply_default_section(resolved, default_section, sources)

            # Apply named profile settings (override defaults section)
            if active_profile_name != "default":
                profile = config_file.profiles.get(active_profile_name)
                if profile is not None:
                    _apply_profile(resolved, profile, active_profile_name, sources)
                else:
                    # Profile specified but not found – warn but continue
                    import warnings
                    warnings.warn(
                        f"Profile '{active_profile_name}' not found in config file. "
                        "Using built-in defaults.",
                        stacklevel=2,
                    )

        except ConfigError as e:
            # Config file errors are non-fatal during resolution,
            # but we re-raise so the user can fix them
            raise

        # ── 3. Environment variables ──────────────────────────────────────
        env_overrides = _read_env_vars()
        for key, value in env_overrides.items():
            if hasattr(resolved, key) and value is not None:
                try:
                    coerced = _coerce_value(key, value, resolved)
                    setattr(resolved, key, coerced)
                    sources[key] = f"env:{_reverse_env_map().get(key, key.upper())}"
                except (ValueError, TypeError) as e:
                    env_var = _reverse_env_map().get(key, key.upper())
                    raise ConfigError(
                        f"Invalid value for environment variable {env_var}: {e}"
                    ) from e

        # ── 4. CLI flags (highest priority) ───────────────────────────────
        for key, value in cli_flags.items():
            flat_key = _cli_flag_to_key(key)
            if flat_key and hasattr(resolved, flat_key) and value is not None:
                try:
                    coerced = _coerce_value(flat_key, value, resolved)
                    setattr(resolved, flat_key, coerced)
                    sources[flat_key] = "cli"
                except (ValueError, TypeError) as e:
                    raise ConfigError(
                        f"Invalid CLI value for --{key}: {e}"
                    ) from e

        resolved._sources = sources
        return resolved

    def explain(self, cli_flags: Optional[dict[str, Any]] = None) -> str:
        """
        Return a human-readable explanation of where each config value comes from.
        """
        config = self.resolve(cli_flags=cli_flags)
        lines = ["Configuration sources (lowest → highest priority):"]
        lines.append("")
        for key, value in config.as_dict().items():
            source = config._sources.get(key, "default")
            lines.append(f"  {key:40s} = {value!r:20}  [{source}]")
        return "\n".join(lines)


# ── Helpers ────────────────────────────────────────────────────────────────

def _apply_default_section(
    resolved: ResolvedConfig,
    default: Any,
    sources: dict[str, str],
) -> None:
    """Apply [default] section settings to resolved config."""
    mapping = {
        "provider": "provider",
        "model": "model",
        "style": "style",
        "format": "format",
        "max_length": "max_length",
        "temperature": "temperature",
    }
    for attr, key in mapping.items():
        value = getattr(default, attr, None)
        if value is not None:
            setattr(resolved, key, value)
            sources[key] = "config:default"


def _apply_profile(
    resolved: ResolvedConfig,
    profile: ProfileConfig,
    profile_name: str,
    sources: dict[str, str],
) -> None:
    """Apply a named profile's settings to resolved config."""
    source_label = f"config:profile:{profile_name}"

    simple_fields = {
        "provider": "provider",
        "model": "model",
        "style": "style",
        "format": "format",
        "max_length": "max_length",
        "temperature": "temperature",
    }
    for attr, key in simple_fields.items():
        value = getattr(profile, attr, None)
        if value is not None:
            setattr(resolved, key, value)
            sources[key] = source_label

    # Cache sub-settings
    if profile.cache:
        cache = profile.cache
        if cache.enabled is not None:
            resolved.cache_enabled = cache.enabled
            sources["cache_enabled"] = source_label
        if cache.ttl_hours is not None:
            resolved.cache_ttl_hours = cache.ttl_hours
            sources["cache_ttl_hours"] = source_label
        if cache.max_size_mb is not None:
            resolved.cache_max_size_mb = cache.max_size_mb
            sources["cache_max_size_mb"] = source_label

    # Rate limit sub-settings
    if profile.rate_limit:
        rl = profile.rate_limit
        if rl.requests_per_minute is not None:
            resolved.rate_limit_requests_per_minute = rl.requests_per_minute
            sources["rate_limit_requests_per_minute"] = source_label
        if rl.requests_per_day is not None:
            resolved.rate_limit_requests_per_day = rl.requests_per_day
            sources["rate_limit_requests_per_day"] = source_label
        if rl.retry_attempts is not None:
            resolved.rate_limit_retry_attempts = rl.retry_attempts
            sources["rate_limit_retry_attempts"] = source_label
        if rl.retry_delay_seconds is not None:
            resolved.rate_limit_retry_delay_seconds = rl.retry_delay_seconds
            sources["rate_limit_retry_delay_seconds"] = source_label


def _read_env_vars() -> dict[str, Any]:
    """Read environment variables and return as a flat config dict."""
    result: dict[str, Any] = {}
    for env_var, key in ENV_VAR_MAP.items():
        value = os.environ.get(env_var)
        if value is not None:
            result[key] = value
    return result


def _reverse_env_map() -> dict[str, str]:
    """Return a mapping from config key → env var name."""
    return {v: k for k, v in ENV_VAR_MAP.items()}


def _coerce_value(key: str, value: Any, resolved: ResolvedConfig) -> Any:
    """Coerce a string value to the appropriate type based on the key."""
    if isinstance(value, str):
        current = getattr(resolved, key, None)
        if isinstance(current, bool):
            return value.lower() in ("true", "1", "yes", "on")
        elif isinstance(current, int) or key in (
            "max_length", "cache_ttl_hours", "cache_max_size_mb",
            "rate_limit_requests_per_minute", "rate_limit_requests_per_day",
            "rate_limit_retry_attempts",
        ):
            if key == "rate_limit_requests_per_day" and value.lower() in ("none", "null", ""):
                return None
            return int(value)
        elif isinstance(current, float) or key in (
            "temperature", "rate_limit_retry_delay_seconds"
        ):
            return float(value)
        else:
            return value
    return value


def _cli_flag_to_key(flag: str) -> Optional[str]:
    """Convert a CLI flag name to a flat config key."""
    # Direct mappings
    direct = {
        "provider": "provider",
        "model": "model",
        "style": "style",
        "format": "format",
        "max_length": "max_length",
        "temperature": "temperature",
        "profile": "profile",
        "cache": "cache_enabled",
        "cache_enabled": "cache_enabled",
        "cache_ttl": "cache_ttl_hours",
        "cache_ttl_hours": "cache_ttl_hours",
        "cache_max_size": "cache_max_size_mb",
        "cache_max_size_mb": "cache_max_size_mb",
        "rpm": "rate_limit_requests_per_minute",
        "rate_limit_requests_per_minute": "rate_limit_requests_per_minute",
        "rpd": "rate_limit_requests_per_day",
        "rate_limit_requests_per_day": "rate_limit_requests_per_day",
        "retry_attempts": "rate_limit_retry_attempts",
        "rate_limit_retry_attempts": "rate_limit_retry_attempts",
        "retry_delay": "rate_limit_retry_delay_seconds",
        "rate_limit_retry_delay_seconds": "rate_limit_retry_delay_seconds",
    }
    return direct.get(flag)
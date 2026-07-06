"""
ProfileManager: reads/writes ~/.config/summarizer/config.toml
Provides CRUD operations for named configuration profiles.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any, Optional

from .exceptions import SummarizerError
from .schemas import ConfigFile, ProfileConfig, VALID_PROVIDERS, VALID_STYLES, VALID_FORMATS


# Try to import TOML library (stdlib in 3.11+)
if sys.version_info >= (3, 11):
    import tomllib
else:
    try:
        import tomllib
    except ImportError:
        try:
            import tomli as tomllib  # type: ignore[no-redef]
        except ImportError:
            tomllib = None  # type: ignore[assignment]

try:
    import tomli_w  # type: ignore[import]
    HAS_TOMLI_W = True
except ImportError:
    HAS_TOMLI_W = False


def _get_config_dir() -> Path:
    """Return the XDG config directory for the summarizer."""
    xdg_config_home = os.environ.get("XDG_CONFIG_HOME", "")
    if xdg_config_home:
        base = Path(xdg_config_home)
    else:
        base = Path.home() / ".config"
    return base / "summarizer"


def _get_config_path() -> Path:
    """Return the full path to the config file."""
    return _get_config_dir() / "config.toml"


def _write_toml(data: dict[str, Any], path: Path) -> None:
    """Write a dict to a TOML file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    
    if HAS_TOMLI_W:
        with open(path, "wb") as f:
            tomli_w.dump(data, f)
    else:
        # Fallback: write TOML manually (basic implementation)
        lines = _dict_to_toml_lines(data)
        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
            if lines:
                f.write("\n")


def _dict_to_toml_lines(data: dict[str, Any], prefix: str = "") -> list[str]:
    """Convert a nested dict to TOML lines (basic implementation)."""
    lines: list[str] = []
    scalars: dict[str, Any] = {}
    tables: dict[str, Any] = {}

    for key, value in data.items():
        if isinstance(value, dict):
            tables[key] = value
        else:
            scalars[key] = value

    for key, value in scalars.items():
        lines.append(f"{key} = {_toml_value(value)}")

    for key, value in tables.items():
        section = f"{prefix}.{key}" if prefix else key
        if lines or prefix:
            lines.append("")
        lines.append(f"[{section}]")
        lines.extend(_dict_to_toml_lines(value, prefix=section))

    return lines


def _toml_value(value: Any) -> str:
    """Convert a Python value to a TOML string representation."""
    if isinstance(value, bool):
        return "true" if value else "false"
    elif isinstance(value, int):
        return str(value)
    elif isinstance(value, float):
        return str(value)
    elif isinstance(value, str):
        escaped = value.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'
    elif isinstance(value, list):
        items = ", ".join(_toml_value(v) for v in value)
        return f"[{items}]"
    else:
        return f'"{value}"'


class ProfileManager:
    """Manages named configuration profiles stored in config.toml."""

    def __init__(self, config_path: Optional[Path] = None) -> None:
        self.config_path = config_path or _get_config_path()
        self._config: Optional[ConfigFile] = None

    def _load(self) -> ConfigFile:
        """Load and validate the config file, returning a ConfigFile object."""
        if not self.config_path.exists():
            return ConfigFile()

        if tomllib is None:
            raise SummarizerError(
                "No TOML library available. Install 'tomli' for Python < 3.11: "
                "pip install tomli tomli-w"
            )

        try:
            with open(self.config_path, "rb") as f:
                raw = tomllib.load(f)
        except Exception as e:
            raise SummarizerError(f"Failed to read config file {self.config_path}: {e}") from e

        try:
            return ConfigFile.from_dict(raw)
        except ValueError as e:
            raise SummarizerError(str(e)) from e

    def _save(self, config: ConfigFile) -> None:
        """Save the ConfigFile to disk."""
        data = config.to_dict()
        try:
            _write_toml(data, self.config_path)
        except Exception as e:
            raise SummarizerError(f"Failed to write config file {self.config_path}: {e}") from e

    def load(self) -> ConfigFile:
        """Load config (with caching)."""
        if self._config is None:
            self._config = self._load()
        return self._config

    def reload(self) -> ConfigFile:
        """Force reload from disk."""
        self._config = self._load()
        return self._config

    # ── Profile CRUD ─────────────────────────────────────────────────────────

    def list_profiles(self) -> dict[str, ProfileConfig]:
        """Return all profiles."""
        return dict(self.load().profiles)

    def get_profile(self, name: str) -> ProfileConfig:
        """Get a profile by name, raising an error if not found."""
        config = self.load()
        if name not in config.profiles:
            available = ", ".join(sorted(config.profiles.keys())) or "none"
            raise SummarizerError(
                f"Profile '{name}' not found. Available profiles: {available}"
            )
        return config.profiles[name]

    def create_profile(self, name: str, **kwargs: Any) -> ProfileConfig:
        """Create a new profile. Raises if it already exists."""
        config = self.load()
        if name in config.profiles:
            raise SummarizerError(
                f"Profile '{name}' already exists. Use 'config set' to update it."
            )
        return self._upsert_profile(name, config, **kwargs)

    def update_profile(self, name: str, **kwargs: Any) -> ProfileConfig:
        """Update an existing profile field(s). Raises if it doesn't exist."""
        config = self.load()
        if name not in config.profiles:
            available = ", ".join(sorted(config.profiles.keys())) or "none"
            raise SummarizerError(
                f"Profile '{name}' not found. Available profiles: {available}"
            )
        return self._upsert_profile(name, config, merge=True, **kwargs)

    def upsert_profile(self, name: str, **kwargs: Any) -> ProfileConfig:
        """Create or update a profile."""
        config = self.load()
        return self._upsert_profile(name, config, merge=True, **kwargs)

    def _upsert_profile(
        self,
        name: str,
        config: ConfigFile,
        merge: bool = False,
        **kwargs: Any,
    ) -> ProfileConfig:
        _validate_profile_name(name)
        
        if merge and name in config.profiles:
            existing = config.profiles[name]
            existing_data = (
                existing.model_dump(exclude_none=False)
                if hasattr(existing, "model_dump")
                else existing.dict(exclude_none=False)
            )
            # Merge: existing values overridden by new kwargs
            merged = {k: v for k, v in existing_data.items() if v is not None}
            merged.update({k: v for k, v in kwargs.items() if v is not None})
            new_kwargs = merged
        else:
            new_kwargs = {k: v for k, v in kwargs.items() if v is not None}

        try:
            profile = ProfileConfig(**new_kwargs)
        except Exception as e:
            raise SummarizerError(f"Invalid profile settings: {e}") from e

        config.profiles[name] = profile
        self._save(config)
        self._config = config
        return profile

    def delete_profile(self, name: str) -> None:
        """Delete a profile. Also clears active_profile if it matches."""
        config = self.load()
        if name not in config.profiles:
            available = ", ".join(sorted(config.profiles.keys())) or "none"
            raise SummarizerError(
                f"Profile '{name}' not found. Available profiles: {available}"
            )
        del config.profiles[name]
        if config.default.active_profile == name:
            config.default.active_profile = None
        self._save(config)
        self._config = config

    def rename_profile(self, old_name: str, new_name: str) -> None:
        """Rename a profile."""
        config = self.load()
        if old_name not in config.profiles:
            raise SummarizerError(f"Profile '{old_name}' not found.")
        if new_name in config.profiles:
            raise SummarizerError(f"Profile '{new_name}' already exists.")
        _validate_profile_name(new_name)
        
        config.profiles[new_name] = config.profiles.pop(old_name)
        if config.default.active_profile == old_name:
            config.default.active_profile = new_name
        self._save(config)
        self._config = config

    # ── Active profile ────────────────────────────────────────────────────────

    def get_active_profile_name(self) -> Optional[str]:
        """Return the name of the currently active profile, or None."""
        return self.load().default.active_profile

    def set_active_profile(self, name: str) -> None:
        """Set the active profile. Validates that the profile exists."""
        config = self.load()
        if name not in config.profiles:
            available = ", ".join(sorted(config.profiles.keys())) or "none"
            raise SummarizerError(
                f"Profile '{name}' not found. Available profiles: {available}"
            )
        config.default.active_profile = name
        self._save(config)
        self._config = config

    def clear_active_profile(self) -> None:
        """Clear the active profile (revert to defaults)."""
        config = self.load()
        config.default.active_profile = None
        self._save(config)
        self._config = config

    def get_active_profile(self) -> Optional[ProfileConfig]:
        """Return the active ProfileConfig, or None if no profile is active."""
        name = self.get_active_profile_name()
        if name is None:
            return None
        config = self.load()
        return config.profiles.get(name)

    # ── Key-value helpers ─────────────────────────────────────────────────────

    def set_profile_key(self, profile_name: str, key: str, value: Any) -> None:
        """Set a single key on a profile."""
        self.upsert_profile(profile_name, **{key: value})

    def get_profile_key(self, profile_name: str, key: str) -> Any:
        """Get a single key from a profile."""
        profile = self.get_profile(profile_name)
        data = (
            profile.model_dump()
            if hasattr(profile, "model_dump")
            else profile.dict()
        )
        if key not in data:
            valid_keys = ", ".join(sorted(data.keys()))
            raise SummarizerError(
                f"Unknown profile key '{key}'. Valid keys: {valid_keys}"
            )
        return data[key]


def _validate_profile_name(name: str) -> None:
    """Validate that a profile name is acceptable."""
    if not name:
        raise SummarizerError("Profile name cannot be empty.")
    if name in ("default", "profiles"):
        raise SummarizerError(
            f"'{name}' is a reserved name and cannot be used as a profile name."
        )
    invalid_chars = set(name) - set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-")
    if invalid_chars:
        raise SummarizerError(
            f"Profile name '{name}' contains invalid characters: "
            f"{', '.join(sorted(invalid_chars))}. "
            "Use only letters, digits, hyphens, and underscores."
        )
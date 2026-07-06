"""
ProfileManager: reads/writes ~/.config/summarizer/config.toml
Provides CRUD operations for named configuration profiles.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any, Optional

from .schemas import ConfigFile, ProfileConfig, DefaultConfig, VALID_PROVIDERS, VALID_STYLES, VALID_FORMATS
from .exceptions import SummarizerError

try:
    import tomllib
except ImportError:
    try:
        import tomli as tomllib  # type: ignore[no-redef]
    except ImportError:
        tomllib = None  # type: ignore[assignment]

try:
    import tomli_w
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
    """Return the path to the main config file."""
    return _get_config_dir() / "config.toml"


def _dict_to_toml_string(data: dict[str, Any], indent: int = 0) -> str:
    """Simple TOML serializer for our config structure."""
    lines: list[str] = []
    # Write scalar values first
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
        lines.append(f"\n[{key}]")
        for k, v in value.items():
            if not isinstance(v, dict):
                lines.append(f"{k} = {_toml_value(v)}")
        # Nested tables
        for k, v in value.items():
            if isinstance(v, dict):
                lines.append(f"\n[{key}.{k}]")
                for kk, vv in v.items():
                    lines.append(f"{kk} = {_toml_value(vv)}")

    return "\n".join(lines)


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
    elif value is None:
        return '""'
    else:
        return f'"{value}"'


def _config_to_toml(config: ConfigFile) -> str:
    """Serialize a ConfigFile to a TOML string."""
    lines: list[str] = []

    # [default] section
    lines.append("[default]")
    lines.append(f'profile = "{config.default.profile}"')
    lines.append("")

    # Profile sections
    for profile_name, profile in config.profiles.items():
        lines.append(f"[{profile_name}]")
        profile_dict = profile.model_dump(exclude_none=True)

        # Write scalar profile fields
        scalar_keys = ["provider", "model", "style", "format", "max_length",
                       "temperature", "description"]
        for key in scalar_keys:
            if key in profile_dict:
                val = profile_dict[key]
                lines.append(f"{key} = {_toml_value(val)}")

        # Write cache sub-table
        if "cache" in profile_dict:
            cache = profile_dict["cache"]
            lines.append(f"\n[{profile_name}.cache]")
            for k, v in cache.items():
                lines.append(f"{k} = {_toml_value(v)}")

        # Write rate_limit sub-table
        if "rate_limit" in profile_dict:
            rl = profile_dict["rate_limit"]
            lines.append(f"\n[{profile_name}.rate_limit]")
            for k, v in rl.items():
                lines.append(f"{k} = {_toml_value(v)}")

        lines.append("")

    return "\n".join(lines)


class ProfileError(SummarizerError):
    """Raised when a profile operation fails."""
    pass


class ProfileManager:
    """
    Manages named configuration profiles stored in ~/.config/summarizer/config.toml.
    """

    def __init__(self, config_dir: Optional[Path] = None):
        if config_dir is not None:
            self._config_dir = config_dir
        else:
            self._config_dir = _get_config_dir()
        self._config_path = self._config_dir / "config.toml"
        self._config: Optional[ConfigFile] = None

    @property
    def config_path(self) -> Path:
        return self._config_path

    def _ensure_config_dir(self) -> None:
        self._config_dir.mkdir(parents=True, exist_ok=True)

    def _load_raw(self) -> dict[str, Any]:
        """Load the raw TOML data from the config file."""
        if not self._config_path.exists():
            return {}
        if tomllib is None:
            raise ProfileError(
                "No TOML library available. Install 'tomli' for Python < 3.11: pip install tomli"
            )
        try:
            with open(self._config_path, "rb") as f:
                return tomllib.load(f)
        except Exception as e:
            raise ProfileError(f"Failed to parse config file {self._config_path}: {e}") from e

    def load(self) -> ConfigFile:
        """Load and validate the config file, returning a ConfigFile."""
        from pydantic import ValidationError
        raw = self._load_raw()
        try:
            config = ConfigFile.model_validate(raw)
        except ValidationError as e:
            errors = []
            for err in e.errors():
                loc = " -> ".join(str(l) for l in err["loc"])
                errors.append(f"  {loc}: {err['msg']}")
            raise ProfileError(
                f"Invalid config file {self._config_path}:\n" + "\n".join(errors)
            ) from e
        self._config = config
        return config

    def save(self, config: ConfigFile) -> None:
        """Save the ConfigFile to disk."""
        self._ensure_config_dir()
        toml_str = _config_to_toml(config)
        with open(self._config_path, "w", encoding="utf-8") as f:
            f.write(toml_str)
        self._config = config

    def get_config(self) -> ConfigFile:
        """Return cached config or load from disk."""
        if self._config is None:
            self._config = self.load()
        return self._config

    def list_profiles(self) -> list[str]:
        """Return a list of all profile names."""
        config = self.get_config()
        return list(config.profiles.keys())

    def get_profile(self, name: str) -> ProfileConfig:
        """Get a profile by name."""
        config = self.get_config()
        profile = config.get_profile(name)
        if profile is None:
            raise ProfileError(
                f"Profile '{name}' not found. Available profiles: {', '.join(self.list_profiles()) or 'none'}"
            )
        return profile

    def create_profile(
        self,
        name: str,
        overwrite: bool = False,
        **kwargs: Any
    ) -> ProfileConfig:
        """Create a new profile with the given settings."""
        _validate_profile_name(name)
        config = self.get_config()

        if name in config.profiles and not overwrite:
            raise ProfileError(
                f"Profile '{name}' already exists. Use --overwrite to replace it."
            )

        from pydantic import ValidationError
        try:
            profile = ProfileConfig(**kwargs)
        except ValidationError as e:
            errors = []
            for err in e.errors():
                loc = " -> ".join(str(l) for l in err["loc"])
                errors.append(f"  {loc}: {err['msg']}")
            raise ProfileError(
                f"Invalid profile settings:\n" + "\n".join(errors)
            ) from e

        config.profiles[name] = profile
        self.save(config)
        return profile

    def update_profile(self, name: str, **kwargs: Any) -> ProfileConfig:
        """Update an existing profile's settings."""
        config = self.get_config()
        if name not in config.profiles:
            raise ProfileError(f"Profile '{name}' not found.")

        existing = config.profiles[name]
        existing_dict = existing.model_dump()

        # Merge: flatten cache and rate_limit updates
        for key, value in kwargs.items():
            if key in ("cache", "rate_limit") and isinstance(value, dict):
                existing_dict[key].update(value)
            else:
                existing_dict[key] = value

        from pydantic import ValidationError
        try:
            updated = ProfileConfig(**existing_dict)
        except ValidationError as e:
            errors = []
            for err in e.errors():
                loc = " -> ".join(str(l) for l in err["loc"])
                errors.append(f"  {loc}: {err['msg']}")
            raise ProfileError(
                f"Invalid profile settings:\n" + "\n".join(errors)
            ) from e

        config.profiles[name] = updated
        self.save(config)
        return updated

    def delete_profile(self, name: str) -> None:
        """Delete a profile."""
        config = self.get_config()
        if name not in config.profiles:
            raise ProfileError(f"Profile '{name}' not found.")
        if name == "default":
            raise ProfileError("Cannot delete the 'default' profile.")

        del config.profiles[name]

        # If the active profile was deleted, reset to 'default'
        if config.default.profile == name:
            config.default.profile = "default"

        self.save(config)

    def set_active_profile(self, name: str) -> None:
        """Set the active (default) profile."""
        config = self.get_config()

        if name != "default" and name not in config.profiles:
            raise ProfileError(
                f"Profile '{name}' not found. Available profiles: {', '.join(self.list_profiles()) or 'none'}"
            )

        config.default.profile = name
        self.save(config)

    def get_active_profile_name(self) -> str:
        """Return the name of the currently active profile."""
        config = self.get_config()
        return config.default.profile

    def get_active_profile(self) -> Optional[ProfileConfig]:
        """Return the currently active ProfileConfig, or None if not set."""
        config = self.get_config()
        return config.get_active_profile()

    def set_profile_key(self, profile_name: str, key: str, value: Any) -> None:
        """Set a single key in a profile."""
        self.update_profile(profile_name, **{key: value})

    def get_profile_key(self, profile_name: str, key: str) -> Any:
        """Get a single key from a profile."""
        profile = self.get_profile(profile_name)
        profile_dict = profile.model_dump()
        if key not in profile_dict:
            raise ProfileError(
                f"Unknown key '{key}'. Valid keys: {', '.join(sorted(profile_dict.keys()))}"
            )
        return profile_dict[key]


def _validate_profile_name(name: str) -> None:
    """Validate that a profile name is acceptable."""
    reserved = {"default", "profiles"}
    if not name:
        raise ProfileError("Profile name cannot be empty.")
    if not name.replace("_", "").replace("-", "").isalnum():
        raise ProfileError(
            f"Profile name '{name}' is invalid. Use only letters, numbers, hyphens, and underscores."
        )
    if name in reserved:
        raise ProfileError(
            f"'{name}' is a reserved name and cannot be used as a profile name."
        )
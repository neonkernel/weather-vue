"""
ProfileManager: reads/writes ~/.config/summarizer/config.toml
CRUD operations for named configuration profiles.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any, Optional

from .exceptions import ConfigError
from .schemas import ConfigFile, ProfileConfig, DefaultConfig


def _get_config_dir() -> Path:
    """
    Return the XDG Base Directory config path for the summarizer.
    Respects XDG_CONFIG_HOME env var, falls back to ~/.config/summarizer.
    """
    xdg_config_home = os.environ.get("XDG_CONFIG_HOME", "")
    if xdg_config_home:
        base = Path(xdg_config_home)
    else:
        base = Path.home() / ".config"
    return base / "summarizer"


def _load_toml(path: Path) -> dict[str, Any]:
    """Load a TOML file, returning an empty dict if not found."""
    if not path.exists():
        return {}
    try:
        if sys.version_info >= (3, 11):
            import tomllib
            with open(path, "rb") as f:
                return tomllib.load(f)
        else:
            try:
                import tomli
                with open(path, "rb") as f:
                    return tomli.load(f)
            except ImportError:
                # Fallback: try tomllib anyway (might be backported)
                raise ConfigError(
                    "Python < 3.11 requires the 'tomli' package. "
                    "Install it with: pip install tomli"
                )
    except Exception as e:
        if isinstance(e, ConfigError):
            raise
        raise ConfigError(f"Failed to parse config file at {path}: {e}") from e


def _dump_toml(data: dict[str, Any], path: Path) -> None:
    """Write a dict as TOML to a file."""
    try:
        import tomli_w
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "wb") as f:
            tomli_w.dump(data, f)
    except ImportError:
        # Fallback: write TOML manually for simple cases
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(_dict_to_toml_str(data))


def _dict_to_toml_str(data: dict[str, Any], prefix: str = "") -> str:
    """
    Simple TOML serializer for nested dicts (no library dependency).
    Handles strings, ints, floats, bools, and nested tables.
    """
    lines: list[str] = []
    nested: list[tuple[str, dict]] = []

    for key, value in data.items():
        full_key = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            nested.append((full_key, value))
        elif isinstance(value, bool):
            lines.append(f"{key} = {str(value).lower()}")
        elif isinstance(value, str):
            escaped = value.replace("\\", "\\\\").replace('"', '\\"')
            lines.append(f'{key} = "{escaped}"')
        elif isinstance(value, (int, float)):
            lines.append(f"{key} = {value}")
        elif value is None:
            pass  # Skip None values
        else:
            lines.append(f'{key} = "{value}"')

    result = "\n".join(lines)

    for full_key, nested_dict in nested:
        section = f"\n[{full_key}]\n"
        section += _dict_to_toml_str(nested_dict)
        result += section

    return result


class ProfileManager:
    """
    Manages configuration profiles stored in ~/.config/summarizer/config.toml.

    Usage:
        pm = ProfileManager()
        pm.create_profile("work", provider="openai", model="gpt-4")
        pm.use_profile("work")
        profile = pm.get_profile("work")
    """

    def __init__(self, config_dir: Optional[Path] = None) -> None:
        self.config_dir = config_dir or _get_config_dir()
        self.config_path = self.config_dir / "config.toml"
        self._config: Optional[ConfigFile] = None

    def _load(self) -> ConfigFile:
        """Load and validate the config file, caching the result."""
        if self._config is not None:
            return self._config

        raw = _load_toml(self.config_path)
        try:
            from pydantic import ValidationError
            config = ConfigFile.model_validate(raw)
        except Exception as e:
            from pydantic import ValidationError
            if isinstance(e, ValidationError):
                errors = e.errors()
                messages = []
                for err in errors:
                    loc = " -> ".join(str(l) for l in err["loc"])
                    messages.append(f"  {loc}: {err['msg']}")
                raise ConfigError(
                    f"Invalid config file at {self.config_path}:\n" + "\n".join(messages)
                ) from e
            raise ConfigError(f"Failed to load config: {e}") from e

        self._config = config
        return self._config

    def _save(self, config: ConfigFile) -> None:
        """Save the config to disk and invalidate cache."""
        data = config.to_toml_dict()
        _dump_toml(data, self.config_path)
        self._config = config

    def _invalidate_cache(self) -> None:
        self._config = None

    def load_config(self) -> ConfigFile:
        """Public method to load the full config file."""
        return self._load()

    def list_profiles(self) -> list[str]:
        """Return a list of all profile names."""
        config = self._load()
        return list(config.profiles.keys())

    def get_profile(self, name: str) -> Optional[ProfileConfig]:
        """Get a profile by name, or None if it doesn't exist."""
        config = self._load()
        return config.profiles.get(name)

    def get_active_profile_name(self) -> str:
        """Return the name of the currently active profile."""
        config = self._load()
        return config.default.profile

    def get_active_profile(self) -> Optional[ProfileConfig]:
        """Return the currently active profile config, or None if it's 'default'."""
        config = self._load()
        active = config.default.profile
        if active == "default":
            return None
        return config.profiles.get(active)

    def create_profile(self, name: str, **kwargs: Any) -> ProfileConfig:
        """
        Create a new named profile with the given settings.
        Raises ConfigError if profile already exists.
        """
        self._invalidate_cache()
        config = self._load()

        if name in config.profiles:
            raise ConfigError(
                f"Profile '{name}' already exists. Use 'config set' to modify it, "
                "or delete it first."
            )

        if name == "default":
            raise ConfigError(
                "'default' is a reserved profile name. Use 'config use' to set "
                "top-level defaults."
            )

        # Build profile from kwargs
        profile_data = _extract_profile_data(kwargs)
        try:
            from pydantic import ValidationError
            profile = ProfileConfig.model_validate(profile_data)
        except Exception as e:
            from pydantic import ValidationError
            if isinstance(e, ValidationError):
                raise ConfigError(f"Invalid profile settings: {e}") from e
            raise

        config.profiles[name] = profile
        self._save(config)
        return profile

    def update_profile(self, name: str, **kwargs: Any) -> ProfileConfig:
        """
        Update settings on an existing profile.
        Raises ConfigError if profile does not exist.
        """
        self._invalidate_cache()
        config = self._load()

        if name not in config.profiles:
            raise ConfigError(
                f"Profile '{name}' does not exist. "
                f"Available profiles: {', '.join(config.profiles.keys()) or 'none'}. "
                "Use 'config create' to create it."
            )

        existing = config.profiles[name]
        existing_data = existing.model_dump(exclude_none=True)
        updates = _extract_profile_data(kwargs)
        merged = {**existing_data, **updates}

        try:
            from pydantic import ValidationError
            profile = ProfileConfig.model_validate(merged)
        except Exception as e:
            from pydantic import ValidationError
            if isinstance(e, ValidationError):
                raise ConfigError(f"Invalid profile settings: {e}") from e
            raise

        config.profiles[name] = profile
        self._save(config)
        return profile

    def delete_profile(self, name: str) -> None:
        """
        Delete a named profile.
        If it was the active profile, resets active to 'default'.
        """
        self._invalidate_cache()
        config = self._load()

        if name not in config.profiles:
            raise ConfigError(f"Profile '{name}' does not exist.")

        del config.profiles[name]

        # Reset active profile if we just deleted it
        if config.default.profile == name:
            config.default.profile = "default"

        self._save(config)

    def use_profile(self, name: str) -> None:
        """
        Set the active profile.
        Pass 'default' to clear and use built-in defaults.
        """
        self._invalidate_cache()
        config = self._load()

        if name != "default" and name not in config.profiles:
            raise ConfigError(
                f"Profile '{name}' does not exist. "
                f"Available profiles: {', '.join(config.profiles.keys()) or 'none'}. "
                "Use 'config create' to create it."
            )

        config.default.profile = name
        self._save(config)

    def set_default(self, **kwargs: Any) -> None:
        """
        Set top-level default settings (not tied to a named profile).
        """
        self._invalidate_cache()
        config = self._load()
        default_data = config.default.model_dump(exclude_none=True)
        updates = {k: v for k, v in kwargs.items() if v is not None}
        merged = {**default_data, **updates}

        try:
            from pydantic import ValidationError
            config.default = DefaultConfig.model_validate(merged)
        except Exception as e:
            from pydantic import ValidationError
            if isinstance(e, ValidationError):
                raise ConfigError(f"Invalid default settings: {e}") from e
            raise

        self._save(config)

    def get_setting(self, key: str, profile_name: Optional[str] = None) -> Any:
        """
        Get a specific setting value from a profile (or the active profile).
        Returns None if not set.
        """
        config = self._load()
        target_name = profile_name or config.default.profile

        if target_name == "default":
            # Look in [default] section
            return getattr(config.default, key, None)

        profile = config.profiles.get(target_name)
        if profile is None:
            raise ConfigError(f"Profile '{target_name}' does not exist.")

        return getattr(profile, key, None)

    def set_setting(self, key: str, value: Any, profile_name: Optional[str] = None) -> None:
        """
        Set a specific setting in a profile (or the active profile).
        """
        config = self._load()
        target_name = profile_name or config.default.profile

        if target_name == "default":
            self.set_default(**{key: value})
        else:
            self.update_profile(target_name, **{key: value})

    def profile_as_dict(self, name: str) -> dict[str, Any]:
        """Return a profile as a flat dictionary."""
        config = self._load()
        if name == "default":
            return config.default.model_dump(exclude_none=True)
        profile = config.profiles.get(name)
        if profile is None:
            raise ConfigError(f"Profile '{name}' does not exist.")
        return profile.model_dump(exclude_none=True)


def _extract_profile_data(kwargs: dict[str, Any]) -> dict[str, Any]:
    """Extract and clean profile data from kwargs."""
    data: dict[str, Any] = {}
    for k, v in kwargs.items():
        if v is not None:
            data[k] = v
    return data
"""
Pydantic models for configuration file schema validation.
"""
from __future__ import annotations

from typing import Any, Optional

try:
    from pydantic import BaseModel, Field, field_validator, model_validator
    PYDANTIC_V2 = True
except ImportError:
    from pydantic import BaseModel, Field, validator as field_validator
    PYDANTIC_V2 = False


VALID_PROVIDERS = {"openai", "anthropic", "ollama", "openrouter"}
VALID_STYLES = {"concise", "detailed", "bullet", "academic", "casual", "technical"}
VALID_FORMATS = {"text", "markdown", "json", "html"}


class CacheConfig(BaseModel):
    enabled: bool = True
    ttl_hours: int = Field(default=24, ge=0, le=8760)
    max_entries: int = Field(default=1000, ge=1, le=100000)

    class Config:
        extra = "forbid"


class RateLimitConfig(BaseModel):
    requests_per_minute: int = Field(default=60, ge=1, le=10000)
    tokens_per_minute: int = Field(default=100000, ge=1000, le=10000000)

    class Config:
        extra = "forbid"


class ProfileConfig(BaseModel):
    provider: Optional[str] = None
    model: Optional[str] = None
    style: Optional[str] = None
    format: Optional[str] = None
    max_length: Optional[int] = Field(default=None, ge=50, le=10000)
    language: Optional[str] = None
    cache: Optional[CacheConfig] = None
    rate_limit: Optional[RateLimitConfig] = None
    description: Optional[str] = None

    class Config:
        extra = "forbid"

    if PYDANTIC_V2:
        @field_validator("provider")
        @classmethod
        def validate_provider(cls, v: Optional[str]) -> Optional[str]:
            if v is not None and v not in VALID_PROVIDERS:
                raise ValueError(
                    f"Invalid provider '{v}'. Must be one of: {', '.join(sorted(VALID_PROVIDERS))}"
                )
            return v

        @field_validator("style")
        @classmethod
        def validate_style(cls, v: Optional[str]) -> Optional[str]:
            if v is not None and v not in VALID_STYLES:
                raise ValueError(
                    f"Invalid style '{v}'. Must be one of: {', '.join(sorted(VALID_STYLES))}"
                )
            return v

        @field_validator("format")
        @classmethod
        def validate_format(cls, v: Optional[str]) -> Optional[str]:
            if v is not None and v not in VALID_FORMATS:
                raise ValueError(
                    f"Invalid format '{v}'. Must be one of: {', '.join(sorted(VALID_FORMATS))}"
                )
            return v
    else:
        @field_validator("provider")
        @classmethod
        def validate_provider(cls, v: Optional[str]) -> Optional[str]:
            if v is not None and v not in VALID_PROVIDERS:
                raise ValueError(
                    f"Invalid provider '{v}'. Must be one of: {', '.join(sorted(VALID_PROVIDERS))}"
                )
            return v

        @field_validator("style")
        @classmethod
        def validate_style(cls, v: Optional[str]) -> Optional[str]:
            if v is not None and v not in VALID_STYLES:
                raise ValueError(
                    f"Invalid style '{v}'. Must be one of: {', '.join(sorted(VALID_STYLES))}"
                )
            return v

        @field_validator("format")
        @classmethod
        def validate_format(cls, v: Optional[str]) -> Optional[str]:
            if v is not None and v not in VALID_FORMATS:
                raise ValueError(
                    f"Invalid format '{v}'. Must be one of: {', '.join(sorted(VALID_FORMATS))}"
                )
            return v


class DefaultConfig(BaseModel):
    active_profile: Optional[str] = None

    class Config:
        extra = "forbid"


class ConfigFile(BaseModel):
    """Root configuration file model."""
    default: DefaultConfig = Field(default_factory=DefaultConfig)
    profiles: dict[str, ProfileConfig] = Field(default_factory=dict)

    class Config:
        extra = "allow"

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ConfigFile":
        """Parse and validate a config dict (from TOML)."""
        # Extract profiles from top-level keys (everything except 'default')
        default_data = data.get("default", {})
        
        # Profiles can be stored under a [profiles] section or as top-level [profile.name]
        profiles_data: dict[str, Any] = {}
        
        if "profiles" in data:
            profiles_data = data["profiles"]
        
        # Also look for profile.* top-level sections
        for key, value in data.items():
            if key not in ("default", "profiles") and isinstance(value, dict):
                profiles_data[key] = value

        validated_profiles: dict[str, ProfileConfig] = {}
        errors: list[str] = []
        
        for profile_name, profile_data in profiles_data.items():
            try:
                validated_profiles[profile_name] = ProfileConfig(**profile_data)
            except Exception as e:
                errors.append(f"Profile '{profile_name}': {e}")

        if errors:
            raise ValueError("Config file validation errors:\n" + "\n".join(f"  - {e}" for e in errors))

        try:
            default_config = DefaultConfig(**default_data)
        except Exception as e:
            raise ValueError(f"[default] section error: {e}")

        # Validate active_profile references an existing profile
        if default_config.active_profile and default_config.active_profile not in validated_profiles:
            raise ValueError(
                f"Active profile '{default_config.active_profile}' not found in config. "
                f"Available profiles: {', '.join(sorted(validated_profiles.keys())) or 'none'}"
            )

        return cls(default=default_config, profiles=validated_profiles)

    def to_dict(self) -> dict[str, Any]:
        """Convert to a plain dict for TOML serialization."""
        result: dict[str, Any] = {}
        
        # Write [default] section
        default_data = {}
        if self.default.active_profile is not None:
            default_data["active_profile"] = self.default.active_profile
        if default_data:
            result["default"] = default_data

        # Write each profile as a top-level section
        for profile_name, profile in self.profiles.items():
            profile_dict = profile.model_dump(exclude_none=True) if PYDANTIC_V2 else profile.dict(exclude_none=True)
            if profile_dict:
                result[profile_name] = profile_dict

        return result
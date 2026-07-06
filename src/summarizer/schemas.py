"""
Pydantic models for config file schema validation.
"""
from __future__ import annotations

from typing import Any, Optional
from pydantic import BaseModel, Field, field_validator, model_validator


class CacheConfig(BaseModel):
    enabled: bool = True
    ttl_seconds: int = Field(default=3600, ge=0)
    max_size_mb: int = Field(default=100, ge=1)

    @field_validator("ttl_seconds")
    @classmethod
    def validate_ttl(cls, v: int) -> int:
        if v < 0:
            raise ValueError("ttl_seconds must be non-negative")
        return v


class RateLimitConfig(BaseModel):
    requests_per_minute: int = Field(default=60, ge=1)
    max_concurrent: int = Field(default=5, ge=1)


VALID_PROVIDERS = {"openai", "anthropic", "ollama", "groq", "cohere"}
VALID_STYLES = {"concise", "detailed", "bullet", "academic", "casual", "technical"}
VALID_FORMATS = {"text", "markdown", "json", "html"}


class ProfileConfig(BaseModel):
    provider: Optional[str] = None
    model: Optional[str] = None
    style: Optional[str] = None
    format: Optional[str] = None
    cache: CacheConfig = Field(default_factory=CacheConfig)
    rate_limit: RateLimitConfig = Field(default_factory=RateLimitConfig)
    max_length: Optional[int] = Field(default=None, ge=10)
    temperature: Optional[float] = Field(default=None, ge=0.0, le=2.0)
    description: Optional[str] = None

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
    profile: str = "default"


class ConfigFile(BaseModel):
    default: DefaultConfig = Field(default_factory=DefaultConfig)
    profiles: dict[str, ProfileConfig] = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def extract_profiles(cls, data: Any) -> Any:
        """
        TOML config stores profiles as top-level sections like [work], [research].
        We need to separate the reserved keys from profile keys.
        """
        if not isinstance(data, dict):
            return data

        reserved_keys = {"default", "profiles"}
        profiles: dict[str, Any] = data.get("profiles", {})

        for key, value in data.items():
            if key not in reserved_keys and isinstance(value, dict):
                profiles[key] = value

        result = {k: v for k, v in data.items() if k in reserved_keys}
        result["profiles"] = profiles
        return result

    def get_profile(self, name: str) -> Optional[ProfileConfig]:
        return self.profiles.get(name)

    def get_active_profile(self) -> Optional[ProfileConfig]:
        return self.get_profile(self.default.profile)
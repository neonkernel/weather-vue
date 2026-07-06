"""
Pydantic models for config file schema validation.
Used to validate the TOML config file on load.
"""
from __future__ import annotations

from typing import Any, Optional
from pydantic import BaseModel, Field, field_validator, model_validator


VALID_PROVIDERS = {"openai", "anthropic", "ollama", "openrouter"}
VALID_STYLES = {"concise", "detailed", "bullet", "academic", "casual"}
VALID_FORMATS = {"text", "markdown", "json", "html"}


class CacheConfig(BaseModel):
    """Cache settings for a profile."""
    enabled: bool = True
    ttl_hours: int = Field(default=24, ge=1, le=8760)
    max_size_mb: int = Field(default=100, ge=1, le=10240)

    @field_validator("ttl_hours", "max_size_mb", mode="before")
    @classmethod
    def must_be_positive(cls, v: Any) -> Any:
        if isinstance(v, int) and v <= 0:
            raise ValueError("must be a positive integer")
        return v


class RateLimitConfig(BaseModel):
    """Rate limit settings for a profile."""
    requests_per_minute: int = Field(default=60, ge=1, le=10000)
    requests_per_day: Optional[int] = Field(default=None, ge=1)
    retry_attempts: int = Field(default=3, ge=0, le=10)
    retry_delay_seconds: float = Field(default=1.0, ge=0.0, le=60.0)


class ProfileConfig(BaseModel):
    """A named configuration profile."""
    provider: Optional[str] = None
    model: Optional[str] = None
    style: Optional[str] = None
    format: Optional[str] = None
    max_length: Optional[int] = Field(default=None, ge=1, le=100000)
    temperature: Optional[float] = Field(default=None, ge=0.0, le=2.0)
    cache: CacheConfig = Field(default_factory=CacheConfig)
    rate_limit: RateLimitConfig = Field(default_factory=RateLimitConfig)
    # Arbitrary extra fields for extensibility
    extra: dict[str, Any] = Field(default_factory=dict)

    model_config = {"extra": "allow"}

    @field_validator("provider", mode="before")
    @classmethod
    def validate_provider(cls, v: Any) -> Any:
        if v is not None and v not in VALID_PROVIDERS:
            raise ValueError(
                f"Invalid provider '{v}'. Must be one of: {', '.join(sorted(VALID_PROVIDERS))}"
            )
        return v

    @field_validator("style", mode="before")
    @classmethod
    def validate_style(cls, v: Any) -> Any:
        if v is not None and v not in VALID_STYLES:
            raise ValueError(
                f"Invalid style '{v}'. Must be one of: {', '.join(sorted(VALID_STYLES))}"
            )
        return v

    @field_validator("format", mode="before")
    @classmethod
    def validate_format(cls, v: Any) -> Any:
        if v is not None and v not in VALID_FORMATS:
            raise ValueError(
                f"Invalid format '{v}'. Must be one of: {', '.join(sorted(VALID_FORMATS))}"
            )
        return v


class DefaultConfig(BaseModel):
    """The [default] section of config.toml."""
    profile: str = "default"
    provider: Optional[str] = None
    model: Optional[str] = None
    style: Optional[str] = None
    format: Optional[str] = None
    max_length: Optional[int] = Field(default=None, ge=1, le=100000)
    temperature: Optional[float] = Field(default=None, ge=0.0, le=2.0)

    @field_validator("provider", mode="before")
    @classmethod
    def validate_provider(cls, v: Any) -> Any:
        if v is not None and v not in VALID_PROVIDERS:
            raise ValueError(
                f"Invalid provider '{v}'. Must be one of: {', '.join(sorted(VALID_PROVIDERS))}"
            )
        return v

    @field_validator("style", mode="before")
    @classmethod
    def validate_style(cls, v: Any) -> Any:
        if v is not None and v not in VALID_STYLES:
            raise ValueError(
                f"Invalid style '{v}'. Must be one of: {', '.join(sorted(VALID_STYLES))}"
            )
        return v

    @field_validator("format", mode="before")
    @classmethod
    def validate_format(cls, v: Any) -> Any:
        if v is not None and v not in VALID_FORMATS:
            raise ValueError(
                f"Invalid format '{v}'. Must be one of: {', '.join(sorted(VALID_FORMATS))}"
            )
        return v


class ConfigFile(BaseModel):
    """
    Root model for the entire config.toml file.

    Structure:
        [default]
        profile = "work"

        [profiles.work]
        provider = "openai"
        model = "gpt-4"
        style = "concise"

        [profiles.research]
        provider = "anthropic"
        model = "claude-3-opus-20240229"
        style = "detailed"
    """
    default: DefaultConfig = Field(default_factory=DefaultConfig)
    profiles: dict[str, ProfileConfig] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_active_profile_exists(self) -> "ConfigFile":
        active = self.default.profile
        if active != "default" and active not in self.profiles:
            raise ValueError(
                f"Active profile '{active}' referenced in [default] does not exist. "
                f"Available profiles: {', '.join(self.profiles.keys()) or 'none'}"
            )
        return self

    def get_profile(self, name: str) -> Optional[ProfileConfig]:
        """Get a profile by name, or None if not found."""
        return self.profiles.get(name)

    def to_toml_dict(self) -> dict[str, Any]:
        """Convert to a dict suitable for TOML serialization."""
        result: dict[str, Any] = {}

        # Serialize [default] section
        default_data = self.default.model_dump(exclude_none=True)
        if default_data:
            result["default"] = default_data

        # Serialize [profiles.*] sections
        if self.profiles:
            result["profiles"] = {}
            for name, profile in self.profiles.items():
                profile_data = profile.model_dump(exclude_none=True, exclude={"extra"})
                # Flatten cache and rate_limit if they're defaults
                if profile_data.get("cache") == CacheConfig().model_dump():
                    del profile_data["cache"]
                if profile_data.get("rate_limit") == RateLimitConfig().model_dump():
                    del profile_data["rate_limit"]
                result["profiles"][name] = profile_data

        return result
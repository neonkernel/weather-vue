"""
CLI entry point for the summarizer tool.
Includes the `config` subcommand group for managing configuration profiles.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Optional

import click

from .config import ConfigResolver, ConfigError
from .profile import ProfileManager, ProfileError, _get_config_path
from .schemas import VALID_PROVIDERS, VALID_STYLES, VALID_FORMATS


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_profile_manager() -> ProfileManager:
    return ProfileManager()


def _print_profile(name: str, profile: Any, active_name: str) -> None:
    """Pretty-print a single profile."""
    marker = " (active)" if name == active_name else ""
    click.echo(f"\nProfile: {click.style(name, fg='cyan', bold=True)}{marker}")
    if profile.description:
        click.echo(f"  Description : {profile.description}")
    click.echo(f"  Provider    : {profile.provider or '(inherited)'}")
    click.echo(f"  Model       : {profile.model or '(inherited)'}")
    click.echo(f"  Style       : {profile.style or '(inherited)'}")
    click.echo(f"  Format      : {profile.format or '(inherited)'}")
    if profile.max_length is not None:
        click.echo(f"  Max Length  : {profile.max_length}")
    if profile.temperature is not None:
        click.echo(f"  Temperature : {profile.temperature}")
    click.echo(f"  Cache       : enabled={profile.cache.enabled}, ttl={profile.cache.ttl_seconds}s")
    click.echo(f"  Rate Limit  : {profile.rate_limit.requests_per_minute} req/min, "
               f"{profile.rate_limit.max_concurrent} concurrent")


# ---------------------------------------------------------------------------
# Main CLI group
# ---------------------------------------------------------------------------

@click.group()
@click.version_option()
def cli() -> None:
    """Summarizer - AI-powered text summarization tool."""
    pass


# ---------------------------------------------------------------------------
# summarize command
# ---------------------------------------------------------------------------

@cli.command("summarize")
@click.argument("source")
@click.option("--profile", "-p", default=None, help="Configuration profile to use.")
@click.option("--provider", default=None, type=click.Choice(list(VALID_PROVIDERS)), help="LLM provider.")
@click.option("--model", "-m", default=None, help="Model name.")
@click.option("--style", "-s", default=None, type=click.Choice(list(VALID_STYLES)), help="Summary style.")
@click.option("--format", "-f", "fmt", default=None, type=click.Choice(list(VALID_FORMATS)), help="Output format.")
@click.option("--max-length", default=None, type=int, help="Maximum summary length in words.")
@click.option("--temperature", default=None, type=float, help="LLM temperature (0.0-2.0).")
@click.option("--no-cache", is_flag=True, default=False, help="Disable caching for this run.")
def summarize_cmd(
    source: str,
    profile: Optional[str],
    provider: Optional[str],
    model: Optional[str],
    style: Optional[str],
    fmt: Optional[str],
    max_length: Optional[int],
    temperature: Optional[float],
    no_cache: bool,
) -> None:
    """Summarize text from SOURCE (URL, file path, or '-' for stdin)."""
    cli_flags: dict[str, Any] = {
        "profile": profile,
        "provider": provider,
        "model": model,
        "style": style,
        "format": fmt,
        "max_length": max_length,
        "temperature": temperature,
    }
    if no_cache:
        cli_flags["cache_enabled"] = False

    try:
        resolver = ConfigResolver()
        config = resolver.resolve(cli_flags=cli_flags, profile_name=profile)
    except ConfigError as e:
        click.echo(f"Configuration error: {e}", err=True)
        sys.exit(1)

    click.echo(f"Summarizing '{source}' with profile '{config.active_profile}'...")
    click.echo(f"  Provider: {config.provider}, Model: {config.model}")
    click.echo(f"  Style: {config.style}, Format: {config.format}")
    # Actual summarization logic would be invoked here
    click.echo("\n[Summarization not yet connected to output — configuration resolved successfully]")


# ---------------------------------------------------------------------------
# config subcommand group
# ---------------------------------------------------------------------------

@cli.group("config")
def config_group() -> None:
    """Manage configuration profiles."""
    pass


# ---- config list -----------------------------------------------------------

@config_group.command("list")
@click.option("--verbose", "-v", is_flag=True, default=False, help="Show full profile details.")
def config_list(verbose: bool) -> None:
    """List all configuration profiles."""
    pm = _get_profile_manager()
    try:
        config = pm.load()
    except ProfileError as e:
        click.echo(f"Error loading config: {e}", err=True)
        sys.exit(1)

    active = config.default.profile
    profiles = config.profiles

    if not profiles:
        click.echo("No profiles defined.")
        click.echo(f"\nActive profile: {click.style(active, fg='yellow')} (using defaults)")
        return

    click.echo(f"Active profile: {click.style(active, fg='green', bold=True)}\n")
    click.echo("Available profiles:")

    if verbose:
        for name, profile in profiles.items():
            _print_profile(name, profile, active)
    else:
        for name in profiles:
            marker = " ◀ active" if name == active else ""
            click.echo(f"  {click.style(name, fg='cyan')}{marker}")

    click.echo(f"\nConfig file: {pm.config_path}")


# ---- config show -----------------------------------------------------------

@config_group.command("show")
@click.argument("profile_name", default="")
def config_show(profile_name: str) -> None:
    """Show details for a profile (defaults to active profile)."""
    pm = _get_profile_manager()
    try:
        config = pm.load()
        active = config.default.profile

        if not profile_name:
            profile_name = active

        if profile_name not in config.profiles:
            if profile_name == "default" or profile_name == active:
                click.echo(f"Profile '{profile_name}' uses all defaults.")
                resolver = ConfigResolver(pm)
                resolved = resolver.resolve(profile_name=profile_name)
                click.echo("\nResolved settings (defaults):")
                for key, val in resolved.__dict__.items():
                    click.echo(f"  {key}: {val}")
                return
            else:
                click.echo(f"Profile '{profile_name}' not found.", err=True)
                sys.exit(1)

        profile = config.profiles[profile_name]
        _print_profile(profile_name, profile, active)

    except ProfileError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


# ---- config use ------------------------------------------------------------

@config_group.command("use")
@click.argument("profile_name")
def config_use(profile_name: str) -> None:
    """Switch to a named profile (set as active)."""
    pm = _get_profile_manager()
    try:
        pm.set_active_profile(profile_name)
        click.echo(f"Active profile set to: {click.style(profile_name, fg='green', bold=True)}")
    except ProfileError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


# ---- config create ---------------------------------------------------------

@config_group.command("create")
@click.argument("profile_name")
@click.option("--provider", default=None, type=click.Choice(list(VALID_PROVIDERS)), help="LLM provider.")
@click.option("--model", default=None, help="Model name.")
@click.option("--style", default=None, type=click.Choice(list(VALID_STYLES)), help="Summary style.")
@click.option("--format", "fmt", default=None, type=click.Choice(list(VALID_FORMATS)), help="Output format.")
@click.option("--max-length", default=None, type=int, help="Maximum summary length in words.")
@click.option("--temperature", default=None, type=float, help="LLM temperature.")
@click.option("--description", default=None, help="Human-readable description of this profile.")
@click.option("--overwrite", is_flag=True, default=False, help="Overwrite if profile already exists.")
def config_create(
    profile_name: str,
    provider: Optional[str],
    model: Optional[str],
    style: Optional[str],
    fmt: Optional[str],
    max_length: Optional[int],
    temperature: Optional[float],
    description: Optional[str],
    overwrite: bool,
) -> None:
    """Create a new configuration profile."""
    pm = _get_profile_manager()
    kwargs: dict[str, Any] = {}
    if provider is not None:
        kwargs["provider"] = provider
    if model is not None:
        kwargs["model"] = model
    if style is not None:
        kwargs["style"] = style
    if fmt is not None:
        kwargs["format"] = fmt
    if max_length is not None:
        kwargs["max_length"] = max_length
    if temperature is not None:
        kwargs["temperature"] = temperature
    if description is not None:
        kwargs["description"] = description

    try:
        profile = pm.create_profile(profile_name, overwrite=overwrite, **kwargs)
        click.echo(f"Profile {click.style(profile_name, fg='cyan', bold=True)} created.")
        _print_profile(profile_name, profile, pm.get_active_profile_name())
    except ProfileError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


# ---- config set ------------------------------------------------------------

@config_group.command("set")
@click.argument("key")
@click.argument("value")
@click.option("--profile", "-p", default=None, help="Profile to update (defaults to active profile).")
def config_set(key: str, value: str, profile: Optional[str]) -> None:
    """Set a configuration key in a profile.

    KEY is the setting name (e.g. provider, model, style, format).
    VALUE is the new value.

    Examples:
      summarizer config set provider openai
      summarizer config set model gpt-4o --profile work
      summarizer config set temperature 0.7 --profile research
    """
    pm = _get_profile_manager()
    try:
        config = pm.load()
        active = config.default.profile
        target_profile = profile or active

        # Type coerce value
        coerced_value = _coerce_value(key, value)

        if target_profile not in config.profiles:
            # Create profile if it doesn't exist
            pm.create_profile(target_profile, **{key: coerced_value})
            click.echo(f"Created profile '{target_profile}' with {key}={value}")
        else:
            pm.set_profile_key(target_profile, key, coerced_value)
            click.echo(
                f"Set {click.style(key, fg='yellow')} = {click.style(str(value), fg='green')} "
                f"in profile '{target_profile}'"
            )
    except ProfileError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    except ValueError as e:
        click.echo(f"Invalid value: {e}", err=True)
        sys.exit(1)


# ---- config get ------------------------------------------------------------

@config_group.command("get")
@click.argument("key")
@click.option("--profile", "-p", default=None, help="Profile to read from (defaults to active profile).")
def config_get(key: str, profile: Optional[str]) -> None:
    """Get the value of a configuration key.

    Examples:
      summarizer config get provider
      summarizer config get model --profile work
    """
    pm = _get_profile_manager()
    try:
        config = pm.load()
        active = config.default.profile
        target_profile = profile or active

        if target_profile not in config.profiles:
            # Fall back to resolver defaults
            resolver = ConfigResolver(pm)
            resolved = resolver.resolve(profile_name=target_profile)
            resolved_dict = resolved.__dict__
            # Map keys
            key_map = {"format": "format"}
            lookup_key = key.replace("-", "_")
            if lookup_key in resolved_dict:
                click.echo(resolved_dict[lookup_key])
            else:
                click.echo(f"Unknown key: {key}", err=True)
                sys.exit(1)
        else:
            value = pm.get_profile_key(target_profile, key.replace("-", "_"))
            click.echo(value)
    except ProfileError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


# ---- config delete ---------------------------------------------------------

@config_group.command("delete")
@click.argument("profile_name")
@click.option("--yes", "-y", is_flag=True, default=False, help="Skip confirmation prompt.")
def config_delete(profile_name: str, yes: bool) -> None:
    """Delete a configuration profile."""
    pm = _get_profile_manager()
    if not yes:
        click.confirm(f"Delete profile '{profile_name}'?", abort=True)
    try:
        pm.delete_profile(profile_name)
        click.echo(f"Profile {click.style(profile_name, fg='red')} deleted.")
    except ProfileError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


# ---- config path -----------------------------------------------------------

@config_group.command("path")
def config_path() -> None:
    """Show the path to the config file."""
    path = _get_config_path()
    click.echo(str(path))
    if path.exists():
        click.echo(f"  Status: {click.style('exists', fg='green')}")
    else:
        click.echo(f"  Status: {click.style('not created yet', fg='yellow')}")


# ---- config resolve --------------------------------------------------------

@config_group.command("resolve")
@click.option("--profile", "-p", default=None, help="Profile to resolve.")
@click.option("--provider", default=None, type=click.Choice(list(VALID_PROVIDERS)))
@click.option("--model", default=None)
@click.option("--style", default=None, type=click.Choice(list(VALID_STYLES)))
@click.option("--format", "fmt", default=None, type=click.Choice(list(VALID_FORMATS)))
def config_resolve(
    profile: Optional[str],
    provider: Optional[str],
    model: Optional[str],
    style: Optional[str],
    fmt: Optional[str],
) -> None:
    """Show the fully resolved configuration (all sources merged)."""
    pm = _get_profile_manager()
    resolver = ConfigResolver(pm)
    cli_flags: dict[str, Any] = {
        "profile": profile,
        "provider": provider,
        "model": model,
        "style": style,
        "format": fmt,
    }
    try:
        resolved = resolver.resolve(cli_flags=cli_flags, profile_name=profile)
    except ConfigError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)

    click.echo(f"Resolved configuration (profile: {resolved.active_profile}):")
    for key, value in resolved.__dict__.items():
        click.echo(f"  {key:<25} {value}")


# ---------------------------------------------------------------------------
# Value coercion helper
# ---------------------------------------------------------------------------

_KEY_TYPES: dict[str, type] = {
    "max_length": int,
    "temperature": float,
    "cache_ttl_seconds": int,
    "cache_max_size_mb": int,
    "requests_per_minute": int,
    "max_concurrent": int,
    "cache_enabled": lambda v: v.lower() not in ("0", "false", "no", "off"),
}


def _coerce_value(key: str, value: str) -> Any:
    """Coerce a string CLI value to the appropriate Python type."""
    norm_key = key.replace("-", "_")
    coerce = _KEY_TYPES.get(norm_key)
    if coerce is not None:
        try:
            return coerce(value)
        except (ValueError, TypeError) as e:
            raise ValueError(f"Cannot convert '{value}' for key '{key}': {e}") from e
    return value


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    cli()


if __name__ == "__main__":
    main()
"""
CLI entry point for the summarizer tool.
Includes the `config` subcommand group for managing profiles.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Optional

import click

from .exceptions import SummarizerError


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_profile_manager():
    from .profile import ProfileManager
    return ProfileManager()


def _format_profile(name: str, profile: Any, active: Optional[str] = None) -> str:
    """Format a single profile for display."""
    data = (
        profile.model_dump(exclude_none=True)
        if hasattr(profile, "model_dump")
        else profile.dict(exclude_none=True)
    )
    marker = " (active)" if name == active else ""
    lines = [f"[{name}]{marker}"]
    if profile.description:
        lines.append(f"  description = {profile.description}")
    for key, value in data.items():
        if key == "description":
            continue
        if isinstance(value, dict):
            for sub_key, sub_val in value.items():
                lines.append(f"  {key}.{sub_key} = {sub_val}")
        else:
            lines.append(f"  {key} = {value}")
    return "\n".join(lines)


def _echo_success(msg: str) -> None:
    click.echo(click.style("✓ " + msg, fg="green"))


def _echo_error(msg: str) -> None:
    click.echo(click.style("✗ " + msg, fg="red"), err=True)


def _echo_info(msg: str) -> None:
    click.echo(click.style("ℹ " + msg, fg="cyan"))


# ── Main CLI group ────────────────────────────────────────────────────────────

@click.group()
@click.version_option(version="1.0.0", prog_name="summarize")
@click.option("--profile", "-p", default=None, help="Use a specific configuration profile.")
@click.option("--provider", default=None, help="LLM provider to use.")
@click.option("--model", "-m", default=None, help="Model name.")
@click.option("--style", "-s", default=None, help="Summary style.")
@click.option("--format", "-f", "fmt", default=None, help="Output format.")
@click.option("--max-length", default=None, type=int, help="Maximum summary length.")
@click.option("--language", "-l", default=None, help="Output language.")
@click.pass_context
def cli(
    ctx: click.Context,
    profile: Optional[str],
    provider: Optional[str],
    model: Optional[str],
    style: Optional[str],
    fmt: Optional[str],
    max_length: Optional[int],
    language: Optional[str],
) -> None:
    """AI-powered text summarizer with configuration profiles."""
    ctx.ensure_object(dict)
    ctx.obj["profile"] = profile
    ctx.obj["cli_flags"] = {
        "provider": provider,
        "model": model,
        "style": style,
        "format": fmt,
        "max_length": max_length,
        "language": language,
    }


@cli.command()
@click.argument("url_or_text")
@click.pass_context
def summarize(ctx: click.Context, url_or_text: str) -> None:
    """Summarize a URL or text string."""
    from .config import ConfigResolver

    resolver = ConfigResolver()
    resolved = resolver.resolve(
        profile_name=ctx.obj.get("profile"),
        cli_flags=ctx.obj.get("cli_flags", {}),
    )

    click.echo(f"Using provider: {resolved.provider}, model: {resolved.model}")
    click.echo(f"Style: {resolved.style}, Format: {resolved.format}")
    if resolved.active_profile:
        _echo_info(f"Active profile: {resolved.active_profile}")
    click.echo(f"\nSummarizing: {url_or_text[:100]}...")


# ── Config command group ──────────────────────────────────────────────────────

@cli.group("config")
def config_group() -> None:
    """Manage configuration profiles and settings."""
    pass


@config_group.command("list")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON.")
def config_list(as_json: bool) -> None:
    """List all configuration profiles."""
    manager = _get_profile_manager()
    try:
        profiles = manager.list_profiles()
        active = manager.get_active_profile_name()
    except SummarizerError as e:
        _echo_error(str(e))
        sys.exit(1)

    if not profiles:
        _echo_info("No profiles configured.")
        _echo_info(
            f"Config file: {manager.config_path}\n"
            "Create a profile with: summarize config create <name>"
        )
        return

    if as_json:
        output = {}
        for name, profile in profiles.items():
            data = (
                profile.model_dump(exclude_none=True)
                if hasattr(profile, "model_dump")
                else profile.dict(exclude_none=True)
            )
            output[name] = data
        output["_active"] = active
        click.echo(json.dumps(output, indent=2))
        return

    click.echo(f"Profiles (config: {manager.config_path}):\n")
    for name, profile in sorted(profiles.items()):
        click.echo(_format_profile(name, profile, active))
        click.echo()

    if active:
        _echo_info(f"Active profile: {active}")
    else:
        _echo_info("No active profile. Use 'summarize config use <name>' to activate one.")


@config_group.command("create")
@click.argument("name")
@click.option("--provider", default=None, help="LLM provider.")
@click.option("--model", "-m", default=None, help="Model name.")
@click.option("--style", "-s", default=None, help="Summary style.")
@click.option("--format", "-f", "fmt", default=None, help="Output format.")
@click.option("--max-length", default=None, type=int, help="Max summary length.")
@click.option("--language", "-l", default=None, help="Output language.")
@click.option("--description", "-d", default=None, help="Profile description.")
@click.option("--cache-enabled/--no-cache", default=None, help="Enable/disable caching.")
@click.option("--requests-per-minute", default=None, type=int, help="Rate limit.")
@click.option("--activate", is_flag=True, default=False, help="Set as active profile after creating.")
def config_create(
    name: str,
    provider: Optional[str],
    model: Optional[str],
    style: Optional[str],
    fmt: Optional[str],
    max_length: Optional[int],
    language: Optional[str],
    description: Optional[str],
    cache_enabled: Optional[bool],
    requests_per_minute: Optional[int],
    activate: bool,
) -> None:
    """Create a new configuration profile."""
    manager = _get_profile_manager()

    kwargs: dict[str, Any] = {}
    if provider:
        kwargs["provider"] = provider
    if model:
        kwargs["model"] = model
    if style:
        kwargs["style"] = style
    if fmt:
        kwargs["format"] = fmt
    if max_length is not None:
        kwargs["max_length"] = max_length
    if language:
        kwargs["language"] = language
    if description:
        kwargs["description"] = description
    if cache_enabled is not None:
        from .schemas import CacheConfig
        kwargs["cache"] = CacheConfig(enabled=cache_enabled)
    if requests_per_minute is not None:
        from .schemas import RateLimitConfig
        kwargs["rate_limit"] = RateLimitConfig(requests_per_minute=requests_per_minute)

    try:
        manager.create_profile(name, **kwargs)
        _echo_success(f"Created profile '{name}'.")
        if activate:
            manager.set_active_profile(name)
            _echo_success(f"Activated profile '{name}'.")
    except SummarizerError as e:
        _echo_error(str(e))
        sys.exit(1)


@config_group.command("use")
@click.argument("name")
def config_use(name: str) -> None:
    """Set the active configuration profile."""
    manager = _get_profile_manager()
    try:
        manager.set_active_profile(name)
        _echo_success(f"Active profile set to '{name}'.")
    except SummarizerError as e:
        _echo_error(str(e))
        sys.exit(1)


@config_group.command("unset")
def config_unset() -> None:
    """Clear the active profile (revert to defaults)."""
    manager = _get_profile_manager()
    try:
        manager.clear_active_profile()
        _echo_success("Active profile cleared. Using built-in defaults.")
    except SummarizerError as e:
        _echo_error(str(e))
        sys.exit(1)


@config_group.command("set")
@click.argument("profile_name")
@click.argument("key")
@click.argument("value")
def config_set(profile_name: str, key: str, value: str) -> None:
    """Set a key-value pair on a profile.

    Example: summarize config set work provider anthropic
    """
    manager = _get_profile_manager()

    # Type-coerce value based on key
    coerced_value: Any = _coerce_value(key, value)

    try:
        manager.upsert_profile(profile_name, **{key: coerced_value})
        _echo_success(f"Set '{key}' = '{coerced_value}' on profile '{profile_name}'.")
    except SummarizerError as e:
        _echo_error(str(e))
        sys.exit(1)


@config_group.command("get")
@click.argument("profile_name")
@click.argument("key", required=False, default=None)
def config_get(profile_name: str, key: Optional[str]) -> None:
    """Get a setting from a profile.

    If KEY is omitted, shows all settings for the profile.
    """
    manager = _get_profile_manager()
    try:
        if key is None:
            profile = manager.get_profile(profile_name)
            active = manager.get_active_profile_name()
            click.echo(_format_profile(profile_name, profile, active))
        else:
            value = manager.get_profile_key(profile_name, key)
            click.echo(f"{key} = {value}")
    except SummarizerError as e:
        _echo_error(str(e))
        sys.exit(1)


@config_group.command("delete")
@click.argument("name")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompt.")
def config_delete(name: str, yes: bool) -> None:
    """Delete a configuration profile."""
    manager = _get_profile_manager()
    if not yes:
        click.confirm(f"Delete profile '{name}'?", abort=True)
    try:
        manager.delete_profile(name)
        _echo_success(f"Deleted profile '{name}'.")
    except SummarizerError as e:
        _echo_error(str(e))
        sys.exit(1)


@config_group.command("rename")
@click.argument("old_name")
@click.argument("new_name")
def config_rename(old_name: str, new_name: str) -> None:
    """Rename a configuration profile."""
    manager = _get_profile_manager()
    try:
        manager.rename_profile(old_name, new_name)
        _echo_success(f"Renamed profile '{old_name}' to '{new_name}'.")
    except SummarizerError as e:
        _echo_error(str(e))
        sys.exit(1)


@config_group.command("show")
@click.option("--profile", "-p", default=None, help="Profile to use (default: active).")
def config_show(profile: Optional[str]) -> None:
    """Show the resolved configuration (all sources merged)."""
    from .config import ConfigResolver

    resolver = ConfigResolver()
    try:
        resolved = resolver.resolve(profile_name=profile)
    except SummarizerError as e:
        _echo_error(str(e))
        sys.exit(1)

    click.echo("Resolved configuration:\n")
    data = resolved.to_dict()
    for key, value in sorted(data.items()):
        click.echo(f"  {key} = {value}")

    if resolved.active_profile:
        click.echo(f"\nActive profile: {resolved.active_profile}")
    else:
        click.echo("\nNo active profile (using defaults + env vars).")


@config_group.command("path")
def config_path() -> None:
    """Show the path to the config file."""
    manager = _get_profile_manager()
    exists = manager.config_path.exists()
    status = "exists" if exists else "not yet created"
    click.echo(f"{manager.config_path}  ({status})")


def _coerce_value(key: str, value: str) -> Any:
    """Coerce a string value to the appropriate Python type based on the key."""
    int_keys = {"max_length", "requests_per_minute", "tokens_per_minute", "cache_ttl_hours", "cache_max_entries"}
    bool_keys = {"cache_enabled"}

    if key in int_keys:
        try:
            return int(value)
        except ValueError:
            raise SummarizerError(f"Key '{key}' requires an integer value, got: '{value}'")
    elif key in bool_keys:
        if value.lower() in ("true", "1", "yes", "on"):
            return True
        elif value.lower() in ("false", "0", "no", "off"):
            return False
        else:
            raise SummarizerError(f"Key '{key}' requires a boolean value (true/false), got: '{value}'")
    return value


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    cli(obj={})


if __name__ == "__main__":
    main()
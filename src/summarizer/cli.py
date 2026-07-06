"""
CLI entry point for the summarizer tool.
Includes the `config` subcommand group for managing configuration profiles.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional, Any

import click

from .config import ConfigResolver
from .exceptions import ConfigError
from .profile import ProfileManager


# ── Shared context ──────────────────────────────────────────────────────────

pass_profile_manager = click.make_pass_decorator(ProfileManager, ensure=True)


def _get_profile_manager(ctx: click.Context) -> ProfileManager:
    """Get or create a ProfileManager from the Click context."""
    if not hasattr(ctx, "obj") or ctx.obj is None or not isinstance(ctx.obj, dict):
        ctx.ensure_object(dict)
    obj = ctx.obj
    if "profile_manager" not in obj:
        config_dir = obj.get("config_dir")
        obj["profile_manager"] = ProfileManager(
            config_dir=Path(config_dir) if config_dir else None
        )
    return obj["profile_manager"]


# ── Main CLI group ──────────────────────────────────────────────────────────

@click.group()
@click.option(
    "--profile",
    default=None,
    help="Use a specific configuration profile.",
    metavar="NAME",
)
@click.option(
    "--provider",
    default=None,
    help="LLM provider (openai, anthropic, ollama, openrouter).",
)
@click.option(
    "--model",
    default=None,
    help="Model name to use.",
)
@click.option(
    "--style",
    default=None,
    type=click.Choice(["concise", "detailed", "bullet", "academic", "casual"]),
    help="Summarization style.",
)
@click.option(
    "--format",
    "output_format",
    default=None,
    type=click.Choice(["text", "markdown", "json", "html"]),
    help="Output format.",
)
@click.option(
    "--config-dir",
    default=None,
    help="Override config directory path.",
    metavar="PATH",
)
@click.pass_context
def cli(
    ctx: click.Context,
    profile: Optional[str],
    provider: Optional[str],
    model: Optional[str],
    style: Optional[str],
    output_format: Optional[str],
    config_dir: Optional[str],
) -> None:
    """Summarizer - AI-powered text summarization tool."""
    ctx.ensure_object(dict)
    ctx.obj["cli_flags"] = {
        "profile": profile,
        "provider": provider,
        "model": model,
        "style": style,
        "format": output_format,
    }
    if config_dir:
        ctx.obj["config_dir"] = config_dir


@cli.command()
@click.argument("source")
@click.option("--max-length", default=None, type=int, help="Maximum summary length.")
@click.option("--temperature", default=None, type=float, help="LLM temperature (0.0-2.0).")
@click.pass_context
def summarize(
    ctx: click.Context,
    source: str,
    max_length: Optional[int],
    temperature: Optional[float],
) -> None:
    """Summarize text from SOURCE (URL, file path, or '-' for stdin)."""
    pm = _get_profile_manager(ctx)
    resolver = ConfigResolver(profile_manager=pm)

    cli_flags = ctx.obj.get("cli_flags", {})
    cli_flags["max_length"] = max_length
    cli_flags["temperature"] = temperature

    try:
        config = resolver.resolve(cli_flags=cli_flags)
        click.echo(f"Summarizing '{source}' with profile '{config.profile}'...")
        click.echo(f"  Provider : {config.provider}")
        click.echo(f"  Model    : {config.model}")
        click.echo(f"  Style    : {config.style}")
        click.echo(f"  Format   : {config.format}")
        # Actual summarization would happen here
    except ConfigError as e:
        click.secho(f"Configuration error: {e}", fg="red", err=True)
        sys.exit(1)


# ── Config subcommand group ─────────────────────────────────────────────────

@cli.group("config")
@click.pass_context
def config_group(ctx: click.Context) -> None:
    """Manage configuration profiles and settings."""
    ctx.ensure_object(dict)


@config_group.command("list")
@click.option("--verbose", "-v", is_flag=True, help="Show profile details.")
@click.pass_context
def config_list(ctx: click.Context, verbose: bool) -> None:
    """List all configuration profiles."""
    pm = _get_profile_manager(ctx)
    try:
        profiles = pm.list_profiles()
        active = pm.get_active_profile_name()

        if not profiles:
            click.echo("No profiles defined.")
            click.echo(
                "Create one with: summarize config create <name> --provider openai"
            )
            return

        click.echo(f"Active profile: {active}")
        click.echo("")
        click.echo("Profiles:")
        for name in profiles:
            marker = "* " if name == active else "  "
            if verbose:
                profile_dict = pm.profile_as_dict(name)
                click.echo(f"{marker}{name}:")
                for k, v in profile_dict.items():
                    if k not in ("cache", "rate_limit", "extra"):
                        click.echo(f"     {k} = {v}")
            else:
                click.echo(f"{marker}{name}")

    except ConfigError as e:
        click.secho(f"Error: {e}", fg="red", err=True)
        sys.exit(1)


@config_group.command("create")
@click.argument("profile_name")
@click.option("--provider", default=None, help="LLM provider.")
@click.option("--model", default=None, help="Model name.")
@click.option(
    "--style",
    default=None,
    type=click.Choice(["concise", "detailed", "bullet", "academic", "casual"]),
    help="Summarization style.",
)
@click.option(
    "--format",
    "output_format",
    default=None,
    type=click.Choice(["text", "markdown", "json", "html"]),
    help="Output format.",
)
@click.option("--max-length", default=None, type=int, help="Maximum summary length.")
@click.option("--temperature", default=None, type=float, help="LLM temperature.")
@click.option("--cache/--no-cache", default=None, help="Enable/disable cache.")
@click.option("--cache-ttl", default=None, type=int, help="Cache TTL in hours.")
@click.option("--rpm", default=None, type=int, help="Rate limit: requests per minute.")
@click.option("--use", "activate", is_flag=True, help="Set as active profile after creating.")
@click.pass_context
def config_create(
    ctx: click.Context,
    profile_name: str,
    provider: Optional[str],
    model: Optional[str],
    style: Optional[str],
    output_format: Optional[str],
    max_length: Optional[int],
    temperature: Optional[float],
    cache: Optional[bool],
    cache_ttl: Optional[int],
    rpm: Optional[int],
    activate: bool,
) -> None:
    """Create a new configuration profile."""
    pm = _get_profile_manager(ctx)
    try:
        kwargs: dict[str, Any] = {}
        if provider is not None:
            kwargs["provider"] = provider
        if model is not None:
            kwargs["model"] = model
        if style is not None:
            kwargs["style"] = style
        if output_format is not None:
            kwargs["format"] = output_format
        if max_length is not None:
            kwargs["max_length"] = max_length
        if temperature is not None:
            kwargs["temperature"] = temperature

        # Handle nested settings
        if cache is not None or cache_ttl is not None:
            from .schemas import CacheConfig
            cache_data: dict[str, Any] = {}
            if cache is not None:
                cache_data["enabled"] = cache
            if cache_ttl is not None:
                cache_data["ttl_hours"] = cache_ttl
            kwargs["cache"] = cache_data

        if rpm is not None:
            from .schemas import RateLimitConfig
            kwargs["rate_limit"] = {"requests_per_minute": rpm}

        profile = pm.create_profile(profile_name, **kwargs)

        click.secho(f"✓ Profile '{profile_name}' created.", fg="green")

        if activate:
            pm.use_profile(profile_name)
            click.secho(f"✓ Profile '{profile_name}' is now active.", fg="green")

    except ConfigError as e:
        click.secho(f"Error: {e}", fg="red", err=True)
        sys.exit(1)


@config_group.command("use")
@click.argument("profile_name")
@click.pass_context
def config_use(ctx: click.Context, profile_name: str) -> None:
    """Set the active configuration profile."""
    pm = _get_profile_manager(ctx)
    try:
        pm.use_profile(profile_name)
        if profile_name == "default":
            click.secho("✓ Reset to built-in defaults (no profile active).", fg="green")
        else:
            click.secho(f"✓ Now using profile '{profile_name}'.", fg="green")
    except ConfigError as e:
        click.secho(f"Error: {e}", fg="red", err=True)
        sys.exit(1)


@config_group.command("get")
@click.argument("key")
@click.option("--profile", "profile_name", default=None, help="Profile to query.")
@click.pass_context
def config_get(ctx: click.Context, key: str, profile_name: Optional[str]) -> None:
    """Get a configuration setting value."""
    pm = _get_profile_manager(ctx)
    try:
        value = pm.get_setting(key, profile_name=profile_name)
        if value is None:
            click.echo(f"{key} = (not set)")
        else:
            click.echo(f"{key} = {value}")
    except ConfigError as e:
        click.secho(f"Error: {e}", fg="red", err=True)
        sys.exit(1)


@config_group.command("set")
@click.argument("key")
@click.argument("value")
@click.option("--profile", "profile_name", default=None, help="Profile to update.")
@click.pass_context
def config_set(
    ctx: click.Context,
    key: str,
    value: str,
    profile_name: Optional[str],
) -> None:
    """Set a configuration setting value."""
    pm = _get_profile_manager(ctx)
    try:
        pm.set_setting(key, value, profile_name=profile_name)
        target = profile_name or pm.get_active_profile_name()
        click.secho(f"✓ Set '{key}' = '{value}' in profile '{target}'.", fg="green")
    except ConfigError as e:
        click.secho(f"Error: {e}", fg="red", err=True)
        sys.exit(1)


@config_group.command("show")
@click.argument("profile_name", required=False)
@click.option("--resolved", is_flag=True, help="Show fully resolved config with all sources.")
@click.pass_context
def config_show(
    ctx: click.Context,
    profile_name: Optional[str],
    resolved: bool,
) -> None:
    """Show configuration for a profile (or the active profile)."""
    pm = _get_profile_manager(ctx)

    if resolved:
        resolver = ConfigResolver(profile_manager=pm)
        cli_flags = ctx.obj.get("cli_flags", {})
        try:
            explanation = resolver.explain(cli_flags=cli_flags)
            click.echo(explanation)
        except ConfigError as e:
            click.secho(f"Error: {e}", fg="red", err=True)
            sys.exit(1)
        return

    try:
        target = profile_name or pm.get_active_profile_name()
        data = pm.profile_as_dict(target)

        click.echo(f"Profile: {target}")
        click.echo("-" * 40)
        for k, v in data.items():
            if k == "extra":
                continue
            if isinstance(v, dict):
                click.echo(f"[{k}]")
                for sk, sv in v.items():
                    click.echo(f"  {sk} = {sv}")
            else:
                click.echo(f"{k} = {v}")

    except ConfigError as e:
        click.secho(f"Error: {e}", fg="red", err=True)
        sys.exit(1)


@config_group.command("delete")
@click.argument("profile_name")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompt.")
@click.pass_context
def config_delete(ctx: click.Context, profile_name: str, yes: bool) -> None:
    """Delete a configuration profile."""
    pm = _get_profile_manager(ctx)

    if not yes:
        click.confirm(
            f"Delete profile '{profile_name}'? This cannot be undone.",
            abort=True,
        )

    try:
        pm.delete_profile(profile_name)
        click.secho(f"✓ Profile '{profile_name}' deleted.", fg="green")
    except ConfigError as e:
        click.secho(f"Error: {e}", fg="red", err=True)
        sys.exit(1)


@config_group.command("path")
@click.pass_context
def config_path(ctx: click.Context) -> None:
    """Show the path to the config file."""
    pm = _get_profile_manager(ctx)
    click.echo(str(pm.config_path))
    if pm.config_path.exists():
        click.echo("(file exists)")
    else:
        click.echo("(file does not exist yet)")


@config_group.command("init")
@click.option("--force", is_flag=True, help="Overwrite existing config file.")
@click.pass_context
def config_init(ctx: click.Context, force: bool) -> None:
    """Initialize config file with example profiles."""
    pm = _get_profile_manager(ctx)

    if pm.config_path.exists() and not force:
        click.secho(
            f"Config file already exists at {pm.config_path}. "
            "Use --force to overwrite.",
            fg="yellow",
        )
        sys.exit(1)

    try:
        # Create example profiles
        pm._invalidate_cache()

        # Write a minimal starter config manually
        from .schemas import ConfigFile, DefaultConfig, ProfileConfig, CacheConfig
        from .profile import _dump_toml

        config = ConfigFile(
            default=DefaultConfig(profile="default"),
            profiles={
                "quick": ProfileConfig(
                    provider="openai",
                    model="gpt-3.5-turbo",
                    style="concise",
                    format="text",
                    max_length=200,
                ),
                "work": ProfileConfig(
                    provider="openai",
                    model="gpt-4",
                    style="bullet",
                    format="markdown",
                    max_length=500,
                ),
                "research": ProfileConfig(
                    provider="anthropic",
                    model="claude-3-opus-20240229",
                    style="detailed",
                    format="markdown",
                    max_length=2000,
                ),
            },
        )

        pm._save(config)
        click.secho(f"✓ Config initialized at {pm.config_path}", fg="green")
        click.echo("\nExample profiles created: quick, work, research")
        click.echo("Use 'summarize config use <profile>' to activate one.")

    except ConfigError as e:
        click.secho(f"Error: {e}", fg="red", err=True)
        sys.exit(1)


def main() -> None:
    """Main entry point."""
    cli(obj={})


if __name__ == "__main__":
    main()
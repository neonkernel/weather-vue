"""Command-line interface for the summarizer package."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import List, Optional

import click

from .config import Config
from .logger import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Helper: load plugin registry lazily so startup cost is only paid when needed
# ---------------------------------------------------------------------------


def _get_registry():
    from .plugins import get_registry

    return get_registry()


# ---------------------------------------------------------------------------
# Root command group
# ---------------------------------------------------------------------------


@click.group()
@click.version_option(package_name="summarizer")
@click.option("--verbose", "-v", is_flag=True, default=False, help="Enable verbose logging.")
@click.pass_context
def cli(ctx: click.Context, verbose: bool) -> None:
    """AI-powered article summarizer."""
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose
    if verbose:
        import logging

        logging.basicConfig(level=logging.DEBUG)


# ---------------------------------------------------------------------------
# summarize (main command)
# ---------------------------------------------------------------------------


@cli.command("summarize")
@click.argument("sources", nargs=-1, required=False)
@click.option("--file", "-f", "source_file", type=click.Path(exists=True), default=None,
              help="File containing one URL/path per line.")
@click.option("--style", "-s", default=None, help="Summary style (e.g. brief, detailed).")
@click.option("--format", "output_format", default="text",
              type=click.Choice(["text", "json", "markdown"], case_sensitive=False),
              help="Output format.")
@click.option("--no-plugins", is_flag=True, default=False,
              help="Disable post-processors.")
@click.option("--postprocessors", "-p", default=None,
              help="Comma-separated list of post-processor names to apply (default: all).")
@click.pass_context
def summarize_cmd(
    ctx: click.Context,
    sources: tuple,
    source_file: Optional[str],
    style: Optional[str],
    output_format: str,
    no_plugins: bool,
    postprocessors: Optional[str],
) -> None:
    """Summarize one or more articles.

    SOURCES can be URLs or file paths.
    """
    from .summarize import summarize_article
    from .formatter import format_summary

    all_sources: List[str] = list(sources)
    if source_file:
        lines = Path(source_file).read_text(encoding="utf-8").splitlines()
        all_sources.extend(line.strip() for line in lines if line.strip())

    if not all_sources:
        click.echo(ctx.get_help())
        sys.exit(0)

    registry = None if no_plugins else _get_registry()
    processor_names: Optional[List[str]] = None
    if postprocessors:
        processor_names = [p.strip() for p in postprocessors.split(",")]

    for source in all_sources:
        try:
            summary = summarize_article(source, style=style)
        except Exception as exc:  # noqa: BLE001
            click.echo(f"ERROR: {source}: {exc}", err=True)
            continue

        if registry is not None:
            summary = registry.apply_postprocessors(
                summary, article_text="", names=processor_names
            )

        click.echo(format_summary(summary, fmt=output_format))


# ---------------------------------------------------------------------------
# plugins subcommand group
# ---------------------------------------------------------------------------


@cli.group("plugins")
def plugins_group() -> None:
    """Manage and inspect summarizer plugins."""


@plugins_group.command("list")
@click.option("--json", "as_json", is_flag=True, default=False,
              help="Output as JSON.")
def plugins_list(as_json: bool) -> None:
    """List all discovered plugins (extractors, post-processors, formatters)."""
    import json as json_mod

    registry = _get_registry()
    all_plugins = registry.list_all()

    if as_json:
        click.echo(json_mod.dumps(all_plugins, indent=2))
        return

    _LABELS = {
        "summarizer.extractors": "Extractors",
        "summarizer.postprocessors": "Post-Processors",
        "summarizer.formatters": "Formatters",
    }

    total = 0
    for group_key, label in _LABELS.items():
        plugins = all_plugins.get(group_key, {})
        click.echo(f"\n{click.style(label, bold=True)} ({len(plugins)} registered)")
        if plugins:
            for name, fqn in plugins.items():
                click.echo(f"  {click.style(name, fg='green')}  →  {fqn}")
                total += 1
        else:
            click.echo("  (none)")

    if registry.errors:
        click.echo(f"\n{click.style('Load errors:', fg='red', bold=True)}")
        for err in registry.errors:
            click.echo(f"  ✗ {err}")

    click.echo(f"\nTotal: {total} plugin(s) registered.")


@plugins_group.command("info")
@click.argument("name")
def plugins_info(name: str) -> None:
    """Show detailed information about a specific plugin by NAME."""
    from .plugins import EP_EXTRACTORS, EP_POSTPROCESSORS, EP_FORMATTERS

    registry = _get_registry()
    all_plugins = registry.list_all()

    for group_key, plugins in all_plugins.items():
        if name in plugins:
            fqn = plugins[name]
            click.echo(f"Name:   {name}")
            click.echo(f"Group:  {group_key}")
            click.echo(f"Class:  {fqn}")

            # Try to show description / version
            dest_map = {
                EP_EXTRACTORS: registry.extractors,
                EP_POSTPROCESSORS: registry.postprocessors,
                EP_FORMATTERS: registry.formatters,
            }
            cls = dest_map.get(group_key, {}).get(name)
            if cls:
                instance = cls()
                meta = instance.get_metadata()
                click.echo(f"Desc:   {meta.get('description', '(none)')}")
                click.echo(f"Version:{meta.get('version', '?')}")
            return

    click.echo(f"Plugin '{name}' not found.", err=True)
    sys.exit(1)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    cli(obj={})


if __name__ == "__main__":
    main()
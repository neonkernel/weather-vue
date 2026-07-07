"""Command-line interface for the summarizer package."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import List, Optional

import click

from summarizer.plugins import registry as plugin_registry


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _apply_postprocessors(summary, article_text: str):
    """Run all registered post-processors on *summary* and return the result."""
    for pp in plugin_registry.postprocessors:
        try:
            summary = pp.process(summary, article_text)
        except Exception as exc:  # pragma: no cover – defensive
            click.echo(
                f"[warn] Post-processor {pp.name!r} raised an error: {exc}",
                err=True,
            )
    return summary


# ---------------------------------------------------------------------------
# CLI group
# ---------------------------------------------------------------------------


@click.group()
@click.version_option()
def cli() -> None:
    """Summarizer – AI-powered article summarization tool."""
    # Discover plugins once at startup
    plugin_registry.discover()


# ---------------------------------------------------------------------------
# summarize subcommand
# ---------------------------------------------------------------------------


@cli.command("summarize")
@click.argument("source")
@click.option(
    "--format",
    "output_format",
    default="text",
    show_default=True,
    help="Output format: text | json | markdown",
)
@click.option(
    "--no-postprocess",
    is_flag=True,
    default=False,
    help="Skip all registered post-processors.",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(dir_okay=False, writable=True),
    default=None,
    help="Write output to this file instead of stdout.",
)
def summarize_cmd(source: str, output_format: str, no_postprocess: bool, output: Optional[str]) -> None:
    """Summarize an article from URL or a local file path."""
    try:
        from summarizer.summarize import summarize_source
    except ImportError as exc:
        click.echo(f"Error importing summarize module: {exc}", err=True)
        sys.exit(1)

    try:
        result = summarize_source(source)
    except Exception as exc:
        click.echo(f"Error summarizing {source!r}: {exc}", err=True)
        sys.exit(1)

    # Apply post-processors unless opted out
    if not no_postprocess:
        article_text = getattr(result, "article_text", "") or ""
        result = _apply_postprocessors(result, article_text)

    # Apply custom formatter if one matches
    formatter = plugin_registry.get_formatter(output_format)
    if formatter is not None:
        rendered = formatter.format(result)
    else:
        rendered = _default_render(result, output_format)

    if output:
        Path(output).write_text(rendered, encoding="utf-8")
        click.echo(f"Output written to {output}")
    else:
        click.echo(rendered)


def _default_render(result, output_format: str) -> str:
    """Render a summary using a built-in format (text / json / markdown)."""
    if output_format == "json":
        data = {}
        for attr in ("url", "title", "summary", "metadata"):
            val = getattr(result, attr, None)
            if val is not None:
                data[attr] = val
        return json.dumps(data, indent=2, default=str)

    if output_format == "markdown":
        title = getattr(result, "title", "Summary") or "Summary"
        url = getattr(result, "url", "") or ""
        summary_text = getattr(result, "summary", "") or ""
        meta = getattr(result, "metadata", {}) or {}

        lines = [f"# {title}", ""]
        if url:
            lines += [f"**Source:** {url}", ""]
        lines += [summary_text, ""]

        if meta:
            lines.append("## Metadata")
            lines.append("```json")
            lines.append(json.dumps(meta, indent=2, default=str))
            lines.append("```")

        return "\n".join(lines)

    # Default: plain text
    title = getattr(result, "title", "") or ""
    summary_text = getattr(result, "summary", "") or ""
    meta = getattr(result, "metadata", {}) or {}

    parts = []
    if title:
        parts.append(f"Title: {title}")
    parts.append(summary_text)
    if meta:
        if "keywords" in meta:
            parts.append("Keywords: " + ", ".join(meta["keywords"]))
        if "readability" in meta:
            r = meta["readability"]
            parts.append(
                f"Readability: {r.get('label', '')} "
                f"(FRE={r.get('flesch_reading_ease', '')}, "
                f"FK Grade={r.get('flesch_kincaid_grade', '')})"
            )
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# plugins subcommand group
# ---------------------------------------------------------------------------


@cli.group("plugins")
def plugins_group() -> None:
    """Manage and inspect summarizer plugins."""


@plugins_group.command("list")
@click.option(
    "--json",
    "as_json",
    is_flag=True,
    default=False,
    help="Output the plugin list as JSON.",
)
def plugins_list(as_json: bool) -> None:
    """List all discovered plugins grouped by type."""
    data = plugin_registry.summary()

    if as_json:
        click.echo(json.dumps(data, indent=2))
        return

    _print_plugin_section("Extractors", data["extractors"])
    _print_plugin_section("Post-Processors", data["postprocessors"])
    _print_plugin_section("Formatters", data["formatters"])

    total = sum(len(v) for v in data.values())
    click.echo(f"\n{total} plugin(s) discovered.")


def _print_plugin_section(title: str, plugins: List[dict]) -> None:
    click.echo(f"\n{'─' * 40}")
    click.echo(f"  {title} ({len(plugins)})")
    click.echo(f"{'─' * 40}")
    if not plugins:
        click.echo("  (none)")
        return
    for p in plugins:
        click.echo(f"  • {p['name']}")
        click.echo(f"      class  : {p['module']}.{p['class']}")
        if p.get("description"):
            click.echo(f"      desc   : {p['description']}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    cli()
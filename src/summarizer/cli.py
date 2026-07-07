"""
Command-line interface for the summarizer package.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import List, Optional

import click

from .plugins import registry as plugin_registry


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _apply_postprocessors(summary, article_text: str = "", config: dict | None = None):
    """Run all registered post-processors against *summary* in registration order."""
    for pp_cls in plugin_registry.postprocessors.values():
        try:
            pp = pp_cls()
            summary = pp.process(summary, article_text=article_text, config=config)
        except Exception as exc:  # pragma: no cover
            click.echo(
                click.style(f"[warn] Post-processor '{pp_cls.name}' failed: {exc}", fg="yellow"),
                err=True,
            )
    return summary


# ---------------------------------------------------------------------------
# CLI group
# ---------------------------------------------------------------------------

@click.group()
@click.version_option()
@click.option("--verbose", "-v", is_flag=True, default=False, help="Enable verbose logging.")
@click.pass_context
def cli(ctx: click.Context, verbose: bool) -> None:
    """Summarizer — AI-powered article summarisation tool."""
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose

    # Discover plugins once at startup
    plugin_registry.discover()

    if verbose:
        import logging
        logging.basicConfig(level=logging.DEBUG)


# ---------------------------------------------------------------------------
# summarize  (core command)
# ---------------------------------------------------------------------------

@cli.command("summarize")
@click.argument("source")
@click.option(
    "--format",
    "-f",
    "output_format",
    default="text",
    type=click.Choice(["text", "json", "markdown"], case_sensitive=False),
    help="Output format.",
)
@click.option("--no-postprocess", is_flag=True, default=False, help="Skip post-processors.")
@click.option(
    "--keyword-top-n",
    default=10,
    type=int,
    show_default=True,
    help="Number of keywords to extract (keyword_extractor plugin).",
)
@click.pass_context
def summarize_cmd(
    ctx: click.Context,
    source: str,
    output_format: str,
    no_postprocess: bool,
    keyword_top_n: int,
) -> None:
    """Summarise an article from a URL or file path."""
    from .summarize import summarize_source

    verbose = ctx.obj.get("verbose", False)

    try:
        result = summarize_source(source, verbose=verbose)
    except Exception as exc:
        click.echo(click.style(f"Error: {exc}", fg="red"), err=True)
        sys.exit(1)

    if not no_postprocess:
        article_text = getattr(result, "article_text", "") or ""
        pp_config = {"keyword_top_n": keyword_top_n}
        result = _apply_postprocessors(result, article_text=article_text, config=pp_config)

    # Output
    if output_format == "json":
        click.echo(json.dumps(_to_dict(result), indent=2, ensure_ascii=False))
    elif output_format == "markdown":
        click.echo(_to_markdown(result))
    else:
        click.echo(_to_text(result))


# ---------------------------------------------------------------------------
# plugins  (sub-group)
# ---------------------------------------------------------------------------

@cli.group("plugins")
def plugins_group() -> None:
    """Commands for inspecting the plugin registry."""


@plugins_group.command("list")
@click.option(
    "--json",
    "as_json",
    is_flag=True,
    default=False,
    help="Output as JSON.",
)
def plugins_list(as_json: bool) -> None:
    """List all discovered plugins (extractors, post-processors, formatters)."""
    # Discovery is triggered by the root cli() callback, but call again to be safe
    plugin_registry.discover()
    data = plugin_registry.all_plugins()

    if as_json:
        click.echo(json.dumps(data, indent=2))
        return

    total = sum(len(v) for v in data.values())
    click.echo(click.style(f"Discovered {total} plugin(s)\n", bold=True))

    sections = [
        ("Extractors", "extractors", "cyan"),
        ("Post-Processors", "postprocessors", "green"),
        ("Formatters", "formatters", "magenta"),
    ]

    for title, key, colour in sections:
        items = data[key]
        click.echo(click.style(f"  {title} ({len(items)})", fg=colour, bold=True))
        if items:
            for item in items:
                click.echo(f"    • {item['name']:<30} {item['description']}")
        else:
            click.echo("    (none)")
        click.echo()


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------

def _to_dict(summary) -> dict:
    if hasattr(summary, "__dict__"):
        return summary.__dict__
    if hasattr(summary, "_asdict"):
        return summary._asdict()
    return {"summary": str(summary)}


def _to_text(summary) -> str:
    lines = []
    d = _to_dict(summary)
    for key, val in d.items():
        if isinstance(val, list):
            lines.append(f"{key.upper()}: {', '.join(str(v) for v in val)}")
        elif val:
            lines.append(f"{key.upper()}: {val}")
    return "\n".join(lines)


def _to_markdown(summary) -> str:
    d = _to_dict(summary)
    title = d.get("title", "Summary")
    lines = [f"# {title}", ""]
    for key, val in d.items():
        if key == "title":
            continue
        if isinstance(val, list):
            lines.append(f"**{key}**: {', '.join(str(v) for v in val)}")
        elif val:
            lines.append(f"**{key}**: {val}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:  # pragma: no cover
    cli(obj={})


if __name__ == "__main__":  # pragma: no cover
    main()
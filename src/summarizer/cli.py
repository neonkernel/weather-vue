"""
CLI entry point for the summarizer package.

Commands
--------
summarize run        – Summarise one or more URLs / files
summarize batch      – Batch processing from a file of URLs
summarize plugins    – Plugin management subcommands
  plugins list       – List all discovered plugins
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path
from typing import List, Optional

import click

from summarizer.config import Config
from summarizer.exceptions import SummarizerError
from summarizer.logger import configure_logging

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_registry():
    """Lazy-import the plugin registry to avoid circular imports at module load."""
    from summarizer.plugins import registry
    return registry


def _apply_postprocessors(summary, article_text: str = ""):
    """
    Run all registered post-processors against a Summary object in order.

    Args:
        summary: A Summary instance returned by the LLM pipeline.
        article_text: The original article plain text (may be empty).

    Returns:
        The (potentially modified) Summary object.
    """
    reg = _get_registry()
    postprocessors = reg.get_postprocessors()
    if not postprocessors:
        return summary

    for pp in postprocessors:
        try:
            summary = pp.process(summary, article_text=article_text)
            logger.debug("Post-processor '%s' applied successfully.", pp.name)
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "Post-processor '%s' raised an exception and was skipped: %s",
                getattr(pp, "name", repr(pp)),
                exc,
            )
    return summary


# ---------------------------------------------------------------------------
# Root command group
# ---------------------------------------------------------------------------


@click.group()
@click.option(
    "--config",
    "-c",
    "config_path",
    default=None,
    type=click.Path(exists=False),
    help="Path to a TOML configuration file.",
)
@click.option(
    "--verbose", "-v", is_flag=True, default=False, help="Enable verbose/debug logging."
)
@click.pass_context
def cli(ctx: click.Context, config_path: Optional[str], verbose: bool) -> None:
    """Summarizer – AI-powered article summarisation tool."""
    ctx.ensure_object(dict)
    configure_logging(debug=verbose)

    cfg = Config.load(config_path) if config_path else Config()
    ctx.obj["config"] = cfg
    ctx.obj["verbose"] = verbose


# ---------------------------------------------------------------------------
# `summarize run` command
# ---------------------------------------------------------------------------


@cli.command("run")
@click.argument("sources", nargs=-1, required=True)
@click.option(
    "--format",
    "-f",
    "output_format",
    default="text",
    show_default=True,
    help="Output format. Use a registered formatter name or 'text' / 'json'.",
)
@click.option(
    "--output",
    "-o",
    "output_file",
    default=None,
    type=click.Path(),
    help="Write output to this file instead of stdout.",
)
@click.option(
    "--style",
    "-s",
    default=None,
    help="Summary style (e.g. 'brief', 'detailed', 'bullet').",
)
@click.option(
    "--no-postprocess",
    is_flag=True,
    default=False,
    help="Skip all registered post-processors.",
)
@click.pass_context
def run_command(
    ctx: click.Context,
    sources: tuple,
    output_format: str,
    output_file: Optional[str],
    style: Optional[str],
    no_postprocess: bool,
) -> None:
    """Summarise one or more article URLs or file paths."""
    from summarizer.summarize import summarize_source

    config: Config = ctx.obj["config"]
    if style:
        config.style = style

    results = []
    for source in sources:
        try:
            click.echo(f"Summarising: {source}", err=True)
            summary, article_text = summarize_source(source, config=config)

            if not no_postprocess:
                summary = _apply_postprocessors(summary, article_text=article_text)

            results.append(summary)
        except SummarizerError as exc:
            click.echo(f"Error summarising '{source}': {exc}", err=True)
            sys.exit(1)

    # Determine output formatter
    reg = _get_registry()
    fmt = reg.get_formatter(output_format)

    if fmt is not None:
        output_text = fmt.format_many(results)
    elif output_format == "json":
        output_text = json.dumps(
            [s.model_dump() if hasattr(s, "model_dump") else vars(s) for s in results],
            indent=2,
            default=str,
        )
    else:
        # Default plain-text rendering
        parts = []
        for s in results:
            title = getattr(s, "title", "") or ""
            summary_text = getattr(s, "summary", "") or ""
            parts.append(f"# {title}\n\n{summary_text}" if title else summary_text)
        output_text = "\n\n---\n\n".join(parts)

    if output_file:
        Path(output_file).write_text(output_text, encoding="utf-8")
        click.echo(f"Output written to {output_file}", err=True)
    else:
        click.echo(output_text)


# ---------------------------------------------------------------------------
# `summarize batch` command
# ---------------------------------------------------------------------------


@cli.command("batch")
@click.argument("url_file", type=click.Path(exists=True))
@click.option("--format", "-f", "output_format", default="text", show_default=True)
@click.option("--output", "-o", "output_file", default=None, type=click.Path())
@click.option("--no-postprocess", is_flag=True, default=False)
@click.pass_context
def batch_command(
    ctx: click.Context,
    url_file: str,
    output_format: str,
    output_file: Optional[str],
    no_postprocess: bool,
) -> None:
    """Batch summarise URLs listed one-per-line in URL_FILE."""
    from summarizer.batch import run_batch

    config: Config = ctx.obj["config"]
    sources = Path(url_file).read_text(encoding="utf-8").splitlines()
    sources = [s.strip() for s in sources if s.strip() and not s.startswith("#")]

    if not sources:
        click.echo("No sources found in file.", err=True)
        sys.exit(1)

    click.echo(f"Batch processing {len(sources)} sources…", err=True)
    summaries = run_batch(sources, config=config)

    if not no_postprocess:
        summaries = [_apply_postprocessors(s) for s in summaries]

    reg = _get_registry()
    fmt = reg.get_formatter(output_format)

    if fmt is not None:
        output_text = fmt.format_many(summaries)
    elif output_format == "json":
        output_text = json.dumps(
            [s.model_dump() if hasattr(s, "model_dump") else vars(s) for s in summaries],
            indent=2,
            default=str,
        )
    else:
        parts = []
        for s in summaries:
            title = getattr(s, "title", "") or ""
            summary_text = getattr(s, "summary", "") or ""
            parts.append(f"# {title}\n\n{summary_text}" if title else summary_text)
        output_text = "\n\n---\n\n".join(parts)

    if output_file:
        Path(output_file).write_text(output_text, encoding="utf-8")
        click.echo(f"Output written to {output_file}", err=True)
    else:
        click.echo(output_text)


# ---------------------------------------------------------------------------
# `summarize plugins` command group
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
    help="Output plugin list as JSON.",
)
def plugins_list(as_json: bool) -> None:
    """List all discovered plugins (extractors, post-processors, formatters)."""
    reg = _get_registry()
    all_plugins = reg.list_all()

    if as_json:
        click.echo(json.dumps(all_plugins, indent=2))
        return

    # Human-readable output
    sections = [
        ("Extractors", all_plugins.get("extractors", [])),
        ("Post-Processors", all_plugins.get("postprocessors", [])),
        ("Formatters", all_plugins.get("formatters", [])),
    ]

    total = sum(len(v) for _, v in sections)
    click.echo(f"\nDiscovered {total} plugin(s):\n")

    for section_name, plugins in sections:
        click.echo(click.style(f"  {section_name}:", bold=True))
        if not plugins:
            click.echo("    (none)")
        else:
            for p in plugins:
                name = p.get("name", "?")
                desc = p.get("description", "")
                cls = p.get("class", "")
                click.echo(f"    • {click.style(name, fg='green')}")
                if desc:
                    click.echo(f"      {desc}")
                if cls:
                    click.echo(f"      class: {click.style(cls, dim=True)}")
        click.echo()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """Package entry point called by the console_scripts setup."""
    cli(obj={})


if __name__ == "__main__":
    main()
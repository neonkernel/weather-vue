"""
CLI entry point for the article summarizer.
"""

import logging
import sys
from pathlib import Path
from typing import Optional

import click

from summarizer import __version__
from summarizer.cache import SummaryCache
from summarizer.config import get_config
from summarizer.exceptions import SummarizerError
from summarizer.summarize import summarize_url
from summarizer.ui import (
    display_summary,
    print_error,
    print_info,
    print_success,
    print_warning,
    set_quiet,
    spinner,
)

logger = logging.getLogger(__name__)


def _setup_logging(verbose: bool, quiet: bool) -> None:
    """Configure root logging based on verbosity flags."""
    if quiet:
        level = logging.CRITICAL
    elif verbose:
        level = logging.DEBUG
    else:
        level = logging.WARNING

    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


@click.group(invoke_without_command=True)
@click.pass_context
@click.version_option(version=__version__, prog_name="summarizer")
def cli(ctx: click.Context) -> None:
    """Article summarizer powered by LLMs."""
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


@cli.command("summarize")
@click.argument("url")
@click.option(
    "--style",
    "-s",
    default="concise",
    show_default=True,
    help="Summary style: concise, detailed, bullet, eli5",
)
@click.option(
    "--provider",
    "-p",
    default=None,
    help="LLM provider to use (overrides config)",
)
@click.option(
    "--model",
    "-m",
    default=None,
    help="Model name to use (overrides config)",
)
@click.option(
    "--no-cache",
    is_flag=True,
    default=False,
    help="Bypass cache for this request (result is still stored)",
)
@click.option(
    "--clear-cache",
    is_flag=True,
    default=False,
    help="Clear the entire cache before running",
)
@click.option(
    "--quiet",
    "-q",
    is_flag=True,
    default=False,
    help="Suppress all UI output; only print the summary text to stdout",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    default=False,
    help="Enable verbose/debug logging",
)
@click.option(
    "--output",
    "-o",
    default=None,
    type=click.Path(dir_okay=False, writable=True),
    help="Write summary text to this file instead of stdout",
)
@click.option(
    "--no-metadata",
    is_flag=True,
    default=False,
    help="Do not display provider / model / token metadata",
)
def summarize_command(
    url: str,
    style: str,
    provider: Optional[str],
    model: Optional[str],
    no_cache: bool,
    clear_cache: bool,
    quiet: bool,
    verbose: bool,
    output: Optional[str],
    no_metadata: bool,
) -> None:
    """Summarize the article at URL."""
    _setup_logging(verbose=verbose, quiet=quiet)
    set_quiet(quiet)

    config = get_config()
    effective_provider = provider or config.provider
    effective_model = model or config.model

    # Handle cache management
    cache = SummaryCache(enabled=not no_cache)

    if clear_cache:
        with SummaryCache() as full_cache:
            removed = full_cache.clear()
            print_info(f"Cache cleared ({removed} entries removed)", quiet=quiet)

    try:
        with spinner("Summarizing article…", quiet=quiet):
            summary = summarize_url(
                url=url,
                style=style,
                provider=effective_provider,
                model=effective_model,
                cache=cache if not no_cache else None,
            )

        # Output
        summary_text = getattr(summary, "text", None) or getattr(summary, "summary", None) or str(summary)

        if output:
            out_path = Path(output)
            out_path.write_text(summary_text, encoding="utf-8")
            print_success(f"Summary written to {out_path}", quiet=quiet)
        else:
            if quiet:
                # In quiet mode, only print the raw summary text to stdout
                click.echo(summary_text)
            else:
                display_summary(summary, quiet=quiet, show_metadata=not no_metadata)

        cache.close()

    except SummarizerError as exc:
        print_error(str(exc), quiet=quiet)
        cache.close()
        sys.exit(1)
    except KeyboardInterrupt:
        print_warning("\nInterrupted.", quiet=quiet)
        cache.close()
        sys.exit(130)
    except Exception as exc:
        logger.exception("Unexpected error")
        print_error(f"Unexpected error: {exc}", quiet=quiet)
        cache.close()
        sys.exit(1)


@cli.command("cache")
@click.option(
    "--clear",
    is_flag=True,
    default=False,
    help="Clear all cached summaries",
)
@click.option(
    "--stats",
    is_flag=True,
    default=False,
    help="Show cache statistics",
)
@click.option(
    "--quiet",
    "-q",
    is_flag=True,
    default=False,
)
def cache_command(clear: bool, stats: bool, quiet: bool) -> None:
    """Manage the summary cache."""
    _setup_logging(verbose=False, quiet=quiet)
    set_quiet(quiet)

    cache = SummaryCache()

    if clear:
        removed = cache.clear()
        print_success(f"Cache cleared ({removed} entries removed)", quiet=quiet)

    if stats or not clear:
        size = cache.size
        cache_dir = cache.cache_dir
        print_info(f"Cache directory: {cache_dir}", quiet=quiet)
        print_info(f"Cached entries:  {size}", quiet=quiet)

    cache.close()


def main() -> None:
    """Entry point for the summarizer CLI."""
    cli()


if __name__ == "__main__":
    main()
"""Command-line interface for the summarizer."""

from __future__ import annotations

import logging
import sys
from typing import Optional

import click

from .cache import SummaryCache
from .config import settings
from .exceptions import SummarizerError
from .styles import SummaryStyle
from .summarize import summarize_url
from .ui import display_cache_cleared, display_error, display_summary

logger = logging.getLogger(__name__)


def _configure_logging(verbose: bool, quiet: bool) -> None:
    level = logging.WARNING
    if quiet:
        level = logging.ERROR
    elif verbose:
        level = logging.DEBUG
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


@click.command()
@click.argument("url")
@click.option(
    "--style",
    "-s",
    type=click.Choice([s.value for s in SummaryStyle], case_sensitive=False),
    default=SummaryStyle.CONCISE.value,
    show_default=True,
    help="Summary style.",
)
@click.option(
    "--provider",
    "-p",
    default=None,
    help="LLM provider to use (overrides config).",
)
@click.option(
    "--model",
    "-m",
    default=None,
    help="Model name (overrides config).",
)
@click.option(
    "--no-cache",
    "no_cache",
    is_flag=True,
    default=False,
    help="Bypass the local cache (always re-summarize).",
)
@click.option(
    "--clear-cache",
    "clear_cache",
    is_flag=True,
    default=False,
    help="Clear the entire cache before running.",
)
@click.option(
    "--quiet",
    "-q",
    is_flag=True,
    default=False,
    help="Suppress all UI output; print only the summary text.",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    default=False,
    help="Enable debug logging.",
)
def main(
    url: str,
    style: str,
    provider: Optional[str],
    model: Optional[str],
    no_cache: bool,
    clear_cache: bool,
    quiet: bool,
    verbose: bool,
) -> None:
    """Summarize an article at URL."""
    _configure_logging(verbose=verbose, quiet=quiet)

    cache = SummaryCache(enabled=not no_cache)

    # Handle --clear-cache
    if clear_cache:
        count = cache.clear()
        display_cache_cleared(count, quiet=quiet)

    # Resolve provider / model from config if not specified on CLI
    effective_provider = provider or settings.default_provider
    effective_model = model or settings.default_model

    # Check cache first
    cached_result = cache.get(
        url=url,
        style=style,
        provider=effective_provider,
        model=effective_model,
    )

    if cached_result is not None:
        display_summary(cached_result, quiet=quiet, cached=True)
        cache.close()
        return

    # Run summarization
    try:
        summary = summarize_url(
            url=url,
            style=style,
            provider=effective_provider,
            model=effective_model,
            quiet=quiet,
        )
    except SummarizerError as exc:
        display_error(str(exc), quiet=quiet)
        cache.close()
        sys.exit(1)
    except Exception as exc:  # noqa: BLE001
        display_error(f"Unexpected error: {exc}", quiet=quiet)
        logger.exception("Unexpected error during summarization")
        cache.close()
        sys.exit(1)

    # Store in cache
    cache.set(
        url=url,
        style=style,
        provider=effective_provider,
        model=effective_model,
        summary=summary,
    )
    cache.close()

    display_summary(summary, quiet=quiet, cached=False)


if __name__ == "__main__":
    main()
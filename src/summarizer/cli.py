"""
Command-line interface for the article summariser.
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import Optional

from .cache import SummaryCache
from .config import load_config
from .exceptions import SummarizerError
from .styles import STYLES
from . import ui


logger = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="summarizer",
        description="Summarise web articles using LLMs.",
    )

    # Positional
    parser.add_argument(
        "url",
        nargs="?",
        help="URL of the article to summarise (omit to read from stdin).",
    )

    # Model / provider selection
    parser.add_argument(
        "--provider",
        default=None,
        help="LLM provider to use (openai, anthropic, gemini, ollama, …).",
    )
    parser.add_argument(
        "--model",
        default=None,
        help="Model name/ID to use.",
    )

    # Style
    parser.add_argument(
        "--style",
        default="concise",
        choices=list(STYLES.keys()),
        help="Summarisation style (default: concise).",
    )

    # Cache control
    cache_group = parser.add_mutually_exclusive_group()
    cache_group.add_argument(
        "--no-cache",
        action="store_true",
        default=False,
        help="Bypass the cache: always call the LLM and do not store the result.",
    )
    cache_group.add_argument(
        "--clear-cache",
        action="store_true",
        default=False,
        help="Clear the entire cache before running.",
    )

    # UI control
    parser.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        default=False,
        help="Suppress all UI output; only the summary text is written to stdout.",
    )

    # Output
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=None,
        help="Write the summary to a file instead of stdout.",
    )

    # Debug / verbosity
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        default=False,
        help="Enable verbose logging.",
    )

    return parser


def _configure_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.WARNING
    logging.basicConfig(
        format="%(levelname)s %(name)s: %(message)s",
        level=level,
        stream=sys.stderr,
    )


def main(argv: Optional[list[str]] = None) -> int:
    """Entry point. Returns an exit code."""
    parser = build_parser()
    args = parser.parse_args(argv)

    _configure_logging(args.verbose)
    ui.set_quiet(args.quiet)

    # ------------------------------------------------------------------ cache
    cache = SummaryCache()

    if args.clear_cache:
        count = cache.clear()
        ui.print_status(f"Cleared {count} entries from the summary cache.", style="bold yellow")
        if args.url is None:
            return 0

    # ------------------------------------------------------------------ config
    try:
        config = load_config()
    except SummarizerError as exc:
        ui.print_error(str(exc))
        return 1

    provider_name: str = args.provider or config.default_provider
    model_name: str = args.model or config.default_model

    # ------------------------------------------------------------------ input
    if args.url:
        url = args.url
        raw_text: Optional[str] = None
    else:
        # Read from stdin
        ui.print_status("Reading from stdin…", style="dim")
        raw_text = sys.stdin.read()
        url = "<stdin>"

    # ------------------------------------------------------------------ summarise
    from .summarize import summarize

    try:
        with ui.spinner("Fetching and summarising…"):
            summary, from_cache = summarize(
                url=url,
                raw_text=raw_text,
                style=args.style,
                provider=provider_name,
                model=model_name,
                cache=cache if not args.no_cache else None,
            )
    except SummarizerError as exc:
        ui.print_error(str(exc))
        return 1
    except KeyboardInterrupt:
        ui.print_error("Interrupted.")
        return 130

    # ------------------------------------------------------------------ output
    if args.output:
        args.output.write_text(summary.text, encoding="utf-8")
        ui.print_status(f"Summary written to {args.output}", style="bold green")
    else:
        ui.print_summary(summary, from_cache=from_cache)

    cache.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
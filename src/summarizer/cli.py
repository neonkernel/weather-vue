"""
CLI entry point for the summarizer package.

Commands:
    summarize <url> [options]   - Summarize a URL
    summarize plugins list      - List all discovered plugins
"""

from __future__ import annotations

import argparse
import logging
import sys
from typing import Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="summarize",
        description="Summarize articles from URLs using an LLM backend.",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose/debug logging.",
    )
    parser.add_argument(
        "--no-plugins",
        action="store_true",
        help="Disable the plugin system entirely.",
    )

    subparsers = parser.add_subparsers(dest="command", metavar="COMMAND")

    # ---- summarize <url> ----
    summarize_parser = subparsers.add_parser(
        "summarize",
        help="Summarize one or more URLs.",
    )
    summarize_parser.add_argument(
        "urls",
        nargs="+",
        metavar="URL",
        help="One or more URLs to summarize.",
    )
    summarize_parser.add_argument(
        "--format",
        "-f",
        default="text",
        metavar="FORMAT",
        help="Output format (text, json, markdown, or a custom formatter name).",
    )
    summarize_parser.add_argument(
        "--no-postprocess",
        action="store_true",
        help="Skip post-processors even if plugins are enabled.",
    )
    summarize_parser.add_argument(
        "--all-postprocessors",
        action="store_true",
        help="Run ALL post-processors, not just those enabled by default.",
    )

    # ---- plugins ----
    plugins_parser = subparsers.add_parser(
        "plugins",
        help="Manage and inspect plugins.",
    )
    plugins_subparsers = plugins_parser.add_subparsers(
        dest="plugins_command", metavar="SUBCOMMAND"
    )
    plugins_subparsers.add_parser(
        "list",
        help="List all discovered plugins.",
    )

    return parser


def _print_plugins_table(registry) -> None:
    """Print a formatted table of all discovered plugins."""
    rows = registry.summary_table()
    if not rows:
        print("No plugins discovered.")
        return

    # Column widths
    col_type = max(len("TYPE"), max(len(r["type"]) for r in rows))
    col_name = max(len("NAME"), max(len(r["name"]) for r in rows))
    col_class = max(len("CLASS"), max(len(r["class"]) for r in rows))
    col_enabled = max(len("DEFAULT"), max(len(r["enabled_by_default"]) for r in rows))
    col_desc = max(len("DESCRIPTION"), max(len(r["description"]) for r in rows))

    header = (
        f"{'TYPE':<{col_type}}  "
        f"{'NAME':<{col_name}}  "
        f"{'CLASS':<{col_class}}  "
        f"{'DEFAULT':<{col_enabled}}  "
        f"{'DESCRIPTION':<{col_desc}}"
    )
    separator = "-" * len(header)

    print(f"\nDiscovered plugins ({len(rows)} total):\n")
    print(header)
    print(separator)
    for r in rows:
        print(
            f"{r['type']:<{col_type}}  "
            f"{r['name']:<{col_name}}  "
            f"{r['class']:<{col_class}}  "
            f"{r['enabled_by_default']:<{col_enabled}}  "
            f"{r['description']:<{col_desc}}"
        )
    print()


def _setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.WARNING
    logging.basicConfig(
        level=level,
        format="%(levelname)s %(name)s: %(message)s",
    )


# ---------------------------------------------------------------------------
# Sub-command handlers
# ---------------------------------------------------------------------------

def handle_plugins_list(args: argparse.Namespace) -> int:
    """Handle `summarize plugins list`."""
    from summarizer.plugins import get_registry

    registry = get_registry(auto_discover=True)
    _print_plugins_table(registry)
    return 0


def handle_summarize(args: argparse.Namespace) -> int:
    """
    Handle `summarize summarize <url> ...`.

    This is a stub that demonstrates how the plugin system integrates
    with the summarization pipeline. Production code would call the
    actual LLM pipeline here.
    """
    from summarizer.plugins import get_registry, reset_registry

    use_plugins = not getattr(args, "no_plugins", False)
    run_postprocess = not getattr(args, "no_postprocess", False)
    all_postprocessors = getattr(args, "all_postprocessors", False)

    registry = None
    if use_plugins:
        registry = get_registry(auto_discover=True)

    for url in args.urls:
        print(f"Summarizing: {url}")

        # --- In a real pipeline this would call the LLM service ---
        # summary = summarize_url(url)
        # For demonstration we create a lightweight stub:
        summary = _stub_summary(url)

        # Apply custom extractor (if one matches the URL)
        if registry:
            extractor = registry.get_extractor_for(url)
            if extractor:
                logger.info("Using custom extractor: %s", extractor.name)

        # Apply post-processors
        if registry and run_postprocess:
            article_text = getattr(summary, "_article_text", "")
            summary = registry.apply_postprocessors(
                summary,
                article_text=article_text,
                enabled_only=not all_postprocessors,
            )

        # Select formatter
        formatted = _format_summary(summary, args.format, registry)
        print(formatted)
        print()

    return 0


def _stub_summary(url: str):
    """
    A minimal stub Summary object used when the real LLM pipeline is not
    available (for CLI integration testing).
    """

    class _Summary:
        def __init__(self, url: str) -> None:
            self.url = url
            self.text = (
                "This is a placeholder summary. "
                "The article discusses important developments in the field. "
                "Researchers have found significant results that may impact future work."
            )
            self.metadata: dict = {}
            self._article_text = (
                "This is the original article text. "
                "It contains many words and sentences about various topics. "
                "The research paper presents novel findings in the domain of machine learning. "
                "Scientists studied the effects of various parameters on model performance. "
                "The results indicate a statistically significant improvement over baseline methods."
            )

        def __str__(self) -> str:
            return self.text

    return _Summary(url)


def _format_summary(summary, format_name: str, registry) -> str:
    """
    Format a summary using either a built-in format or a registered formatter.
    """
    # Try custom formatter first
    if registry:
        for formatter in registry.formatters:
            if formatter.name == format_name:
                try:
                    return formatter.format(summary)
                except Exception as exc:
                    logger.warning("Formatter %r failed: %s", formatter, exc)

    # Built-in formats
    text = getattr(summary, "text", str(summary))
    metadata = getattr(summary, "metadata", {})

    if format_name == "json":
        import json

        data = {"summary": text, **metadata}
        return json.dumps(data, indent=2)

    elif format_name == "markdown":
        lines = [f"## Summary\n\n{text}"]
        if metadata:
            lines.append("\n### Metadata\n")
            for key, value in metadata.items():
                lines.append(f"- **{key}**: {value}")
        return "\n".join(lines)

    else:  # default: plain text
        lines = [text]
        if metadata:
            lines.append("\nMetadata:")
            for key, value in metadata.items():
                lines.append(f"  {key}: {value}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def main(argv: Optional[list[str]] = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    _setup_logging(getattr(args, "verbose", False))

    if args.command == "plugins":
        if args.plugins_command == "list":
            return handle_plugins_list(args)
        else:
            # No subcommand given — show help
            parser.parse_args(["plugins", "--help"])
            return 1

    elif args.command == "summarize":
        return handle_summarize(args)

    else:
        parser.print_help()
        return 0


if __name__ == "__main__":
    sys.exit(main())
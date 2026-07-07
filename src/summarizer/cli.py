"""
Command-line interface for the summarizer package.

Commands
--------
summarize url <url> [options]   – Summarise a single URL
summarize batch <file> [options] – Summarise a list of URLs from a file
summarize plugins list           – List all discovered plugins
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from typing import List, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="summarize",
        description="AI-powered article summariser",
    )
    parser.add_argument(
        "--log-level",
        default="WARNING",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Set the logging verbosity (default: WARNING)",
    )

    subparsers = parser.add_subparsers(dest="command", metavar="<command>")

    # ---- url ---------------------------------------------------------------
    url_parser = subparsers.add_parser("url", help="Summarise a single URL")
    url_parser.add_argument("url", help="URL of the article to summarise")
    url_parser.add_argument(
        "--format",
        dest="output_format",
        default=None,
        help="Output format name (must match a registered formatter plugin)",
    )
    url_parser.add_argument(
        "--no-postprocess",
        action="store_true",
        default=False,
        help="Skip all registered post-processors",
    )
    url_parser.add_argument(
        "--postprocessors",
        nargs="*",
        metavar="NAME",
        default=None,
        help="Run only the named post-processors (space-separated)",
    )
    url_parser.add_argument(
        "--output",
        "-o",
        default=None,
        metavar="FILE",
        help="Write output to FILE instead of stdout",
    )

    # ---- batch -------------------------------------------------------------
    batch_parser = subparsers.add_parser("batch", help="Summarise a list of URLs from a file")
    batch_parser.add_argument("file", help="Path to a file containing one URL per line")
    batch_parser.add_argument(
        "--format",
        dest="output_format",
        default=None,
        help="Output format name (must match a registered formatter plugin)",
    )
    batch_parser.add_argument(
        "--no-postprocess",
        action="store_true",
        default=False,
        help="Skip all registered post-processors",
    )
    batch_parser.add_argument(
        "--postprocessors",
        nargs="*",
        metavar="NAME",
        default=None,
        help="Run only the named post-processors (space-separated)",
    )
    batch_parser.add_argument(
        "--output",
        "-o",
        default=None,
        metavar="FILE",
        help="Write output to FILE instead of stdout",
    )
    batch_parser.add_argument(
        "--concurrency",
        type=int,
        default=4,
        help="Number of concurrent workers (default: 4)",
    )

    # ---- plugins -----------------------------------------------------------
    plugins_parser = subparsers.add_parser("plugins", help="Plugin management commands")
    plugins_subparsers = plugins_parser.add_subparsers(
        dest="plugins_command", metavar="<plugins-command>"
    )

    plugins_list_parser = plugins_subparsers.add_parser(
        "list", help="List all discovered plugins"
    )
    plugins_list_parser.add_argument(
        "--json",
        action="store_true",
        dest="as_json",
        default=False,
        help="Output as JSON",
    )
    plugins_list_parser.add_argument(
        "--type",
        dest="plugin_type",
        choices=["extractors", "postprocessors", "formatters"],
        default=None,
        help="Filter by plugin type",
    )

    return parser


# ---------------------------------------------------------------------------
# Post-processing helpers
# ---------------------------------------------------------------------------


def _apply_postprocessors(
    summary: object,
    article_text: Optional[str],
    *,
    no_postprocess: bool,
    filter_names: Optional[List[str]],
) -> object:
    """
    Apply registered post-processors to *summary*.

    Args:
        summary: The summary object to process.
        article_text: Original article text passed to each processor.
        no_postprocess: If True, skip all post-processors.
        filter_names: If set, only run post-processors whose name is in this list.

    Returns:
        The (possibly modified) summary object.
    """
    if no_postprocess:
        return summary

    from summarizer.plugins import registry  # local import to allow lazy loading

    processors = registry.get_postprocessors()

    if filter_names is not None:
        processors = [p for p in processors if p.name in filter_names]

    for processor in processors:
        try:
            summary = processor.process(summary, article_text=article_text)
        except Exception as exc:
            logger.warning(
                "Post-processor %r raised an exception: %s", processor.name, exc
            )

    return summary


# ---------------------------------------------------------------------------
# Output / formatting helpers
# ---------------------------------------------------------------------------


def _format_summary(summary: object, format_name: Optional[str]) -> str:
    """
    Format *summary* using the named formatter plugin, or fall back to str().
    """
    if format_name is None:
        return str(summary)

    from summarizer.plugins import registry

    formatter = registry.get_formatter(format_name)
    if formatter is None:
        logger.warning(
            "Formatter %r not found; falling back to default string output.", format_name
        )
        return str(summary)

    return formatter.format(summary)


def _write_output(text: str, output_path: Optional[str]) -> None:
    """Write *text* to *output_path* or to stdout."""
    if output_path:
        with open(output_path, "w", encoding="utf-8") as fh:
            fh.write(text)
        print(f"Output written to {output_path}", file=sys.stderr)
    else:
        print(text)


# ---------------------------------------------------------------------------
# Command handlers
# ---------------------------------------------------------------------------


def _cmd_url(args: argparse.Namespace) -> int:
    """Handle the `url` sub-command."""
    try:
        from summarizer.summarize import summarize_url  # type: ignore
    except ImportError:
        # Stub for environments where the full summarize module isn't wired up
        print(f"[summarize url] Would summarise: {args.url}", file=sys.stderr)
        return 0

    try:
        result = summarize_url(args.url)
    except Exception as exc:
        print(f"Error summarising URL: {exc}", file=sys.stderr)
        return 1

    article_text = getattr(result, "_article_text", None)
    result = _apply_postprocessors(
        result,
        article_text,
        no_postprocess=args.no_postprocess,
        filter_names=args.postprocessors,
    )

    output = _format_summary(result, args.output_format)
    _write_output(output, args.output)
    return 0


def _cmd_batch(args: argparse.Namespace) -> int:
    """Handle the `batch` sub-command."""
    try:
        with open(args.file, "r", encoding="utf-8") as fh:
            urls = [line.strip() for line in fh if line.strip() and not line.startswith("#")]
    except OSError as exc:
        print(f"Error reading file {args.file!r}: {exc}", file=sys.stderr)
        return 1

    try:
        from summarizer.batch import summarize_batch  # type: ignore
    except ImportError:
        print(
            f"[summarize batch] Would summarise {len(urls)} URLs from {args.file}",
            file=sys.stderr,
        )
        return 0

    try:
        results = summarize_batch(urls, concurrency=args.concurrency)
    except Exception as exc:
        print(f"Error during batch summarisation: {exc}", file=sys.stderr)
        return 1

    outputs: List[str] = []
    for result in results:
        article_text = getattr(result, "_article_text", None)
        result = _apply_postprocessors(
            result,
            article_text,
            no_postprocess=args.no_postprocess,
            filter_names=args.postprocessors,
        )
        outputs.append(_format_summary(result, args.output_format))

    _write_output("\n\n---\n\n".join(outputs), args.output)
    return 0


def _cmd_plugins_list(args: argparse.Namespace) -> int:
    """Handle the `plugins list` sub-command."""
    from summarizer.plugins import registry

    registry.load()
    all_plugins = registry.list_all()

    # Apply type filter if requested
    if args.plugin_type:
        all_plugins = {args.plugin_type: all_plugins[args.plugin_type]}

    if args.as_json:
        print(json.dumps(all_plugins, indent=2))
        return 0

    # Pretty-print table
    _print_plugins_table(all_plugins)
    return 0


def _print_plugins_table(all_plugins: dict) -> None:
    """Render plugin information as a human-readable table."""
    type_labels = {
        "extractors": "Extractors",
        "postprocessors": "Post-Processors",
        "formatters": "Formatters",
    }

    total = sum(len(v) for v in all_plugins.values())
    print(f"\nDiscovered plugins ({total} total)\n{'=' * 60}")

    for group_key, plugins in all_plugins.items():
        label = type_labels.get(group_key, group_key.title())
        print(f"\n{label} ({len(plugins)})")
        print("-" * 40)

        if not plugins:
            print("  (none)")
            continue

        for plugin in plugins:
            name = plugin.get("name", "—")
            description = plugin.get("description", "")
            class_path = f"{plugin.get('module', '')}.{plugin.get('class', '')}"
            print(f"  • {name}")
            if description:
                # Wrap long descriptions
                words = description.split()
                line = "      "
                for word in words:
                    if len(line) + len(word) + 1 > 72:
                        print(line)
                        line = "      " + word + " "
                    else:
                        line += word + " "
                if line.strip():
                    print(line)
            print(f"      [{class_path}]")

    print()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main(argv: Optional[List[str]] = None) -> int:
    """
    Main CLI entry point.

    Args:
        argv: Argument list (defaults to sys.argv[1:]).

    Returns:
        Exit code (0 = success).
    """
    parser = _build_parser()
    args = parser.parse_args(argv)

    # Configure logging
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(levelname)s %(name)s: %(message)s",
    )

    if args.command == "url":
        return _cmd_url(args)

    if args.command == "batch":
        return _cmd_batch(args)

    if args.command == "plugins":
        if args.plugins_command == "list":
            return _cmd_plugins_list(args)
        # No sub-command given — show help
        parser.parse_args(["plugins", "--help"])
        return 0

    # No command given
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
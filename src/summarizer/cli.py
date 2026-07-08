"""
Command-line interface for the summarizer package.

Usage examples:
    summarize url https://example.com/article
    summarize file article.txt
    summarize batch urls.txt
    summarize plugins list
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
        description="Summarize articles from URLs or files using an LLM backend.",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose/debug logging.",
    )
    parser.add_argument(
        "--format",
        choices=["text", "json", "markdown"],
        default="text",
        help="Output format for summaries (default: text).",
    )
    parser.add_argument(
        "--no-plugins",
        action="store_true",
        dest="no_plugins",
        help="Disable all post-processors and plugin loading.",
    )

    subparsers = parser.add_subparsers(dest="command", metavar="COMMAND")

    # -- url subcommand
    url_parser = subparsers.add_parser("url", help="Summarize an article from a URL.")
    url_parser.add_argument("url", help="URL of the article to summarize.")
    url_parser.add_argument(
        "--keywords", type=int, default=0, metavar="N",
        help="Extract top-N keywords (0 = disabled).",
    )
    url_parser.add_argument(
        "--readability", action="store_true",
        help="Compute readability scores for the summary.",
    )

    # -- file subcommand
    file_parser = subparsers.add_parser("file", help="Summarize an article from a local file.")
    file_parser.add_argument("path", help="Path to the text file.")
    file_parser.add_argument(
        "--keywords", type=int, default=0, metavar="N",
        help="Extract top-N keywords (0 = disabled).",
    )
    file_parser.add_argument(
        "--readability", action="store_true",
        help="Compute readability scores for the summary.",
    )

    # -- batch subcommand
    batch_parser = subparsers.add_parser(
        "batch", help="Summarize multiple URLs listed in a file (one per line)."
    )
    batch_parser.add_argument("url_file", help="Path to a file containing URLs.")
    batch_parser.add_argument(
        "--keywords", type=int, default=0, metavar="N",
        help="Extract top-N keywords per article (0 = disabled).",
    )
    batch_parser.add_argument(
        "--readability", action="store_true",
        help="Compute readability scores for each summary.",
    )

    # -- plugins subcommand
    plugins_parser = subparsers.add_parser(
        "plugins", help="Manage and inspect plugins."
    )
    plugins_sub = plugins_parser.add_subparsers(dest="plugins_command", metavar="SUBCOMMAND")
    plugins_sub.add_parser(
        "list", help="List all discovered extractors, post-processors, and formatters."
    )

    return parser


def _configure_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.WARNING
    logging.basicConfig(
        format="%(levelname)s %(name)s: %(message)s",
        level=level,
        stream=sys.stderr,
    )


# ---------------------------------------------------------------------------
# Plugin listing
# ---------------------------------------------------------------------------

def _cmd_plugins_list() -> None:
    """Print all discovered plugins grouped by type."""
    from summarizer.plugins import get_registry

    registry = get_registry()

    sections = [
        ("Extractors", registry.all_extractors()),
        ("Post-Processors", registry.all_postprocessors()),
        ("Formatters", registry.all_formatters()),
    ]

    any_found = False
    for section_name, plugins in sections:
        if not plugins:
            print(f"\n[{section_name}]")
            print("  (none discovered)")
            continue

        any_found = True
        print(f"\n[{section_name}]")
        for cls in plugins:
            name = getattr(cls, "name", cls.__name__)
            description = getattr(cls, "description", "")
            module = cls.__module__
            builtin_tag = " [built-in]" if module.startswith("summarizer.plugins.builtin") else ""
            print(f"  • {name}{builtin_tag}")
            if description:
                print(f"    {description}")
            print(f"    Module: {module}")

    print()


# ---------------------------------------------------------------------------
# Post-processor application
# ---------------------------------------------------------------------------

def _apply_postprocessors(
    summary,
    article_text: str,
    *,
    enable_keywords: int = 0,
    enable_readability: bool = False,
    no_plugins: bool = False,
) -> None:
    """
    Apply registered post-processors to *summary* in-place.

    Args:
        summary: The Summary object to enrich.
        article_text: The original article text.
        enable_keywords: If > 0, run the keyword extractor with this many keywords.
        enable_readability: If True, run the readability scorer.
        no_plugins: If True, skip all post-processing.
    """
    if no_plugins:
        return

    from summarizer.plugins import get_registry

    registry = get_registry()

    if enable_keywords > 0:
        kw_cls = registry.get_postprocessor("keyword_extractor")
        if kw_cls:
            try:
                processor = kw_cls(top_n=enable_keywords)
                processor.process(summary, article_text, top_n=enable_keywords)
                logger.debug("keyword_extractor applied (top_n=%d)", enable_keywords)
            except Exception as exc:  # noqa: BLE001
                logger.warning("keyword_extractor failed: %s", exc)
        else:
            logger.warning("keyword_extractor plugin not found in registry.")

    if enable_readability:
        rd_cls = registry.get_postprocessor("readability_scorer")
        if rd_cls:
            try:
                processor = rd_cls()
                processor.process(summary, article_text)
                logger.debug("readability_scorer applied")
            except Exception as exc:  # noqa: BLE001
                logger.warning("readability_scorer failed: %s", exc)
        else:
            logger.warning("readability_scorer plugin not found in registry.")


# ---------------------------------------------------------------------------
# Output rendering
# ---------------------------------------------------------------------------

def _render_summary(summary, fmt: str = "text") -> str:
    """Render a Summary to a string in the requested format."""
    if fmt == "json":
        data: dict = {}
        for field in ("url", "title", "summary", "model", "metadata"):
            val = getattr(summary, field, None)
            if val is not None:
                data[field] = val
        return json.dumps(data, indent=2, default=str)

    if fmt == "markdown":
        lines = []
        title = getattr(summary, "title", None)
        url = getattr(summary, "url", None)
        if title:
            lines.append(f"# {title}")
        if url:
            lines.append(f"*Source: {url}*\n")
        summary_text = getattr(summary, "summary", str(summary))
        lines.append(summary_text)
        metadata = getattr(summary, "metadata", None)
        if metadata:
            lines.append("\n---")
            if "keywords" in metadata:
                lines.append(f"**Keywords:** {', '.join(metadata['keywords'])}")
            if "readability" in metadata:
                rd = metadata["readability"]
                lines.append(
                    f"**Readability:** {rd['flesch_reading_ease_label']} "
                    f"(Flesch {rd['flesch_reading_ease']}, "
                    f"FK Grade {rd['flesch_kincaid_grade']})"
                )
        return "\n".join(lines)

    # Default: plain text
    lines = []
    title = getattr(summary, "title", None)
    url = getattr(summary, "url", None)
    if title:
        lines.append(f"Title: {title}")
    if url:
        lines.append(f"URL:   {url}")
    summary_text = getattr(summary, "summary", str(summary))
    lines.append(f"\n{summary_text}")
    metadata = getattr(summary, "metadata", None)
    if metadata:
        if "keywords" in metadata:
            lines.append(f"\nKeywords: {', '.join(metadata['keywords'])}")
        if "readability" in metadata:
            rd = metadata["readability"]
            lines.append(
                f"Readability: {rd['flesch_reading_ease_label']} "
                f"(Flesch Reading Ease: {rd['flesch_reading_ease']}, "
                f"FK Grade: {rd['flesch_kincaid_grade']})"
            )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Sub-command handlers
# ---------------------------------------------------------------------------

def _cmd_url(args) -> int:
    """Handle the `summarize url` subcommand."""
    try:
        from summarizer.summarize import summarize_url
    except ImportError:
        print("ERROR: summarize_url not available. Check your installation.", file=sys.stderr)
        return 1

    try:
        summary, article_text = summarize_url(args.url, return_article_text=True)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    _apply_postprocessors(
        summary,
        article_text,
        enable_keywords=args.keywords,
        enable_readability=args.readability,
        no_plugins=args.no_plugins,
    )
    print(_render_summary(summary, fmt=args.format))
    return 0


def _cmd_file(args) -> int:
    """Handle the `summarize file` subcommand."""
    try:
        from summarizer.summarize import summarize_text
    except ImportError:
        print("ERROR: summarize_text not available. Check your installation.", file=sys.stderr)
        return 1

    try:
        with open(args.path, "r", encoding="utf-8") as fh:
            article_text = fh.read()
        summary = summarize_text(article_text)
    except FileNotFoundError:
        print(f"ERROR: File not found: {args.path}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    _apply_postprocessors(
        summary,
        article_text,
        enable_keywords=args.keywords,
        enable_readability=args.readability,
        no_plugins=args.no_plugins,
    )
    print(_render_summary(summary, fmt=args.format))
    return 0


def _cmd_batch(args) -> int:
    """Handle the `summarize batch` subcommand."""
    try:
        from summarizer.batch import batch_summarize
    except ImportError:
        print("ERROR: batch_summarize not available. Check your installation.", file=sys.stderr)
        return 1

    try:
        with open(args.url_file, "r", encoding="utf-8") as fh:
            urls = [line.strip() for line in fh if line.strip()]
    except FileNotFoundError:
        print(f"ERROR: File not found: {args.url_file}", file=sys.stderr)
        return 1

    try:
        results = batch_summarize(urls)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    for url, (summary, article_text) in zip(urls, results):
        _apply_postprocessors(
            summary,
            article_text,
            enable_keywords=args.keywords,
            enable_readability=args.readability,
            no_plugins=args.no_plugins,
        )
        print(_render_summary(summary, fmt=args.format))
        print("\n" + "=" * 80 + "\n")

    return 0


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main(argv: Optional[List[str]] = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    _configure_logging(getattr(args, "verbose", False))

    if args.command is None:
        parser.print_help()
        return 0

    if args.command == "plugins":
        if args.plugins_command == "list":
            _cmd_plugins_list()
            return 0
        else:
            # Show help for the plugins subcommand
            parser.parse_args(["plugins", "--help"])
            return 0

    if args.command == "url":
        return _cmd_url(args)

    if args.command == "file":
        return _cmd_file(args)

    if args.command == "batch":
        return _cmd_batch(args)

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
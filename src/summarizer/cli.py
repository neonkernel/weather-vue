"""
Command-line interface for the summarizer package.

Commands
--------
summarize run        – Summarise one or more articles
summarize plugins    – Inspect registered plugins
  summarize plugins list
"""

from __future__ import annotations

import argparse
import sys
import textwrap
from typing import List, Optional, Sequence

from .plugins import registry


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_PLUGIN_TYPE_ORDER = ("extractor", "postprocessor", "formatter")


def _print_plugin_table(rows: List[dict]) -> None:
    """Pretty-print a table of plugin rows."""
    if not rows:
        print("No plugins discovered.")
        return

    # Column widths
    col_type_w = max(len("TYPE"), max(len(r["type"]) for r in rows))
    col_name_w = max(len("NAME"), max(len(r["name"]) for r in rows))
    col_ver_w = max(len("VERSION"), max(len(r["version"]) for r in rows))
    # description gets the rest – cap at 60 chars for terminal friendliness
    col_desc_w = 60

    sep = (
        f"+-{'-' * col_type_w}-+-{'-' * col_name_w}-+-{'-' * col_ver_w}-+"
        f"-{'-' * col_desc_w}-+"
    )
    header = (
        f"| {'TYPE':<{col_type_w}} | {'NAME':<{col_name_w}} "
        f"| {'VERSION':<{col_ver_w}} | {'DESCRIPTION':<{col_desc_w}} |"
    )

    print(sep)
    print(header)
    print(sep)

    current_type: Optional[str] = None
    for row in rows:
        if row["type"] != current_type:
            current_type = row["type"]
        desc = row["description"]
        if len(desc) > col_desc_w:
            desc = desc[: col_desc_w - 3] + "..."
        print(
            f"| {row['type']:<{col_type_w}} | {row['name']:<{col_name_w}} "
            f"| {row['version']:<{col_ver_w}} | {desc:<{col_desc_w}} |"
        )

    print(sep)
    print(f"\n{len(rows)} plugin(s) loaded.")


# ---------------------------------------------------------------------------
# Sub-command handlers
# ---------------------------------------------------------------------------


def cmd_plugins_list(_args: argparse.Namespace) -> int:
    """Handle ``summarize plugins list``."""
    # Force (re-)discovery every time the CLI is invoked so the output is fresh
    registry.discover()
    rows = registry.summary_table()
    _print_plugin_table(rows)
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    """
    Handle ``summarize run``.

    This is a thin demonstration that wires up post-processors after a
    (simulated) summarisation step.  In a real integration you would call
    the actual summarisation pipeline here.
    """
    from .models import Summary

    # ------------------------------------------------------------------
    # Simulate summarisation (replace with real pipeline call)
    # ------------------------------------------------------------------
    original_text: str = args.text or ""
    summary_text: str = f"[Summary of: {original_text[:80]}...]" if original_text else ""

    summary = Summary(
        text=summary_text,
        source=args.source or "<stdin>",
        model=getattr(args, "model", "gpt-4o"),
        style=getattr(args, "style", "brief"),
    )

    # ------------------------------------------------------------------
    # Apply registered post-processors
    # ------------------------------------------------------------------
    registry.discover()
    for pp in registry.postprocessors:
        try:
            summary = pp.process(summary, original_text)
        except Exception as exc:  # noqa: BLE001
            print(f"[warning] Post-processor {pp.name!r} failed: {exc}", file=sys.stderr)

    # ------------------------------------------------------------------
    # Output
    # ------------------------------------------------------------------
    fmt_name: Optional[str] = getattr(args, "formatter", None)
    if fmt_name:
        fmt = registry.get_formatter(fmt_name)
        if fmt is None:
            print(
                f"[error] Formatter {fmt_name!r} not found. "
                f"Available: {[f.name for f in registry.formatters]}",
                file=sys.stderr,
            )
            return 1
        output = fmt.format(summary)
    else:
        # Default plain-text output
        output = summary.text
        if summary.metadata:
            output += "\n\n--- Metadata ---"
            for key, value in summary.metadata.items():
                output += f"\n  {key}: {value}"

    print(output)
    return 0


# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="summarize",
        description="AI-powered article summariser with plugin support.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", metavar="COMMAND")
    subparsers.required = True

    # ---- run ----------------------------------------------------------------
    run_parser = subparsers.add_parser("run", help="Summarise one or more articles.")
    run_parser.add_argument("--source", metavar="URL_OR_PATH", help="Source URL or file path.")
    run_parser.add_argument(
        "--text", metavar="TEXT", help="Raw article text (for testing)."
    )
    run_parser.add_argument(
        "--model", metavar="MODEL", default="gpt-4o", help="LLM model to use."
    )
    run_parser.add_argument(
        "--style",
        metavar="STYLE",
        default="brief",
        choices=["brief", "detailed", "bullet"],
        help="Summarisation style.",
    )
    run_parser.add_argument(
        "--formatter",
        metavar="NAME",
        default=None,
        help="Name of a registered formatter plugin to use for output.",
    )
    run_parser.set_defaults(func=cmd_run)

    # ---- plugins ------------------------------------------------------------
    plugins_parser = subparsers.add_parser("plugins", help="Inspect registered plugins.")
    plugins_subparsers = plugins_parser.add_subparsers(
        dest="plugins_command", metavar="PLUGINS_COMMAND"
    )
    plugins_subparsers.required = True

    list_parser = plugins_subparsers.add_parser("list", help="List all discovered plugins.")
    list_parser.set_defaults(func=cmd_plugins_list)

    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Entry point for the ``summarize`` CLI command."""
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
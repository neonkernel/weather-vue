"""Formatter: renders a Summary object as plain text, Markdown, or JSON."""

import json
from dataclasses import asdict
from datetime import datetime

from .models import Summary
from .styles import OutputFormat


class Formatter:
    """Renders Summary objects in various output formats."""

    def format(self, summary: Summary, fmt: OutputFormat) -> str:
        """Format a Summary object according to the specified OutputFormat.

        Args:
            summary: The Summary dataclass instance to render.
            fmt: The desired OutputFormat (TEXT, MARKDOWN, or JSON).

        Returns:
            A string representation in the requested format.
        """
        if fmt == OutputFormat.TEXT:
            return self._format_text(summary)
        elif fmt == OutputFormat.MARKDOWN:
            return self._format_markdown(summary)
        elif fmt == OutputFormat.JSON:
            return self._format_json(summary)
        else:
            raise ValueError(f"Unsupported output format: {fmt}")

    def _format_text(self, summary: Summary) -> str:
        """Render summary as plain text."""
        lines = []

        if summary.title:
            lines.append(summary.title)
            lines.append("=" * len(summary.title))
            lines.append("")

        lines.append(summary.body)
        lines.append("")

        # Metadata footer
        meta_parts = []
        if summary.word_count is not None:
            meta_parts.append(f"Words: {summary.word_count}")
        if summary.model:
            meta_parts.append(f"Model: {summary.model}")
        if summary.source_url:
            meta_parts.append(f"Source: {summary.source_url}")
        if summary.style:
            meta_parts.append(f"Style: {summary.style}")
        if summary.created_at:
            if isinstance(summary.created_at, datetime):
                meta_parts.append(f"Generated: {summary.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
            else:
                meta_parts.append(f"Generated: {summary.created_at}")

        if meta_parts:
            lines.append("---")
            lines.extend(meta_parts)

        return "\n".join(lines)

    def _format_markdown(self, summary: Summary) -> str:
        """Render summary as Markdown with title, metadata, and body."""
        lines = []

        # Title header
        title = summary.title or "Summary"
        lines.append(f"# {title}")
        lines.append("")

        # Metadata table
        meta_rows = []
        if summary.source_url:
            meta_rows.append(f"| **Source** | {summary.source_url} |")
        if summary.model:
            meta_rows.append(f"| **Model** | `{summary.model}` |")
        if summary.style:
            meta_rows.append(f"| **Style** | {summary.style} |")
        if summary.word_count is not None:
            meta_rows.append(f"| **Word Count** | {summary.word_count} |")
        if summary.created_at:
            if isinstance(summary.created_at, datetime):
                ts = summary.created_at.strftime("%Y-%m-%d %H:%M:%S UTC")
            else:
                ts = str(summary.created_at)
            meta_rows.append(f"| **Generated** | {ts} |")

        if meta_rows:
            lines.append("| Field | Value |")
            lines.append("|-------|-------|")
            lines.extend(meta_rows)
            lines.append("")

        # Divider
        lines.append("---")
        lines.append("")

        # Summary body
        lines.append("## Summary")
        lines.append("")
        lines.append(summary.body)
        lines.append("")

        return "\n".join(lines)

    def _format_json(self, summary: Summary) -> str:
        """Render summary as a JSON string."""
        data = asdict(summary)

        # Convert datetime objects to ISO strings for JSON serialization
        for key, value in data.items():
            if isinstance(value, datetime):
                data[key] = value.isoformat()

        return json.dumps(data, indent=2, ensure_ascii=False)
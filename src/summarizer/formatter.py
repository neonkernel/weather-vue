"""Formatter class for rendering Summary objects in different output formats."""

import json
from dataclasses import asdict
from datetime import datetime

from .models import Summary
from .styles import OutputFormat


class Formatter:
    """Renders a Summary object as plain text, Markdown, or JSON."""

    def format(self, summary: Summary, fmt: OutputFormat) -> str:
        """
        Format a Summary object according to the specified OutputFormat.

        Args:
            summary: The Summary dataclass instance to format.
            fmt: The desired output format.

        Returns:
            A string representation of the summary in the requested format.
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
        """Render the summary as plain text."""
        lines = []

        if summary.title:
            lines.append(summary.title)
            lines.append("=" * len(summary.title))
            lines.append("")

        if summary.source_url:
            lines.append(f"Source: {summary.source_url}")

        if summary.model:
            lines.append(f"Model: {summary.model}")

        if summary.word_count is not None:
            lines.append(f"Word count: {summary.word_count}")

        if summary.style:
            lines.append(f"Style: {summary.style}")

        if lines and lines[-1] != "":
            lines.append("")

        lines.append(summary.content)

        return "\n".join(lines)

    def _format_markdown(self, summary: Summary) -> str:
        """Render the summary as Markdown with title header and metadata."""
        lines = []

        # Title header
        title = summary.title or "Summary"
        lines.append(f"# {title}")
        lines.append("")

        # Metadata section
        metadata_lines = []

        if summary.source_url:
            metadata_lines.append(f"- **Source:** {summary.source_url}")

        if summary.model:
            metadata_lines.append(f"- **Model:** {summary.model}")

        if summary.word_count is not None:
            metadata_lines.append(f"- **Word count:** {summary.word_count}")

        if summary.style:
            metadata_lines.append(f"- **Style:** {summary.style}")

        if summary.created_at:
            if isinstance(summary.created_at, datetime):
                created_str = summary.created_at.strftime("%Y-%m-%d %H:%M:%S UTC")
            else:
                created_str = str(summary.created_at)
            metadata_lines.append(f"- **Generated:** {created_str}")

        if metadata_lines:
            lines.append("## Metadata")
            lines.append("")
            lines.extend(metadata_lines)
            lines.append("")

        # Summary body
        lines.append("## Summary")
        lines.append("")
        lines.append(summary.content)
        lines.append("")

        return "\n".join(lines)

    def _format_json(self, summary: Summary) -> str:
        """Render the summary as JSON, serializing the full Summary dataclass."""
        data = asdict(summary)

        # Convert datetime objects to ISO format strings
        for key, value in data.items():
            if isinstance(value, datetime):
                data[key] = value.isoformat()

        return json.dumps(data, indent=2, default=str)
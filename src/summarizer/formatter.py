"""Formatter class for rendering Summary objects in various output formats."""

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
            summary: The Summary object to format.
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
        """Render summary as plain text."""
        lines = []

        if hasattr(summary, "title") and summary.title:
            lines.append(summary.title)
            lines.append("=" * len(summary.title))
            lines.append("")

        lines.append(summary.body)

        metadata_parts = []
        if hasattr(summary, "word_count") and summary.word_count is not None:
            metadata_parts.append(f"Word count: {summary.word_count}")
        if hasattr(summary, "source_url") and summary.source_url:
            metadata_parts.append(f"Source: {summary.source_url}")
        if hasattr(summary, "model") and summary.model:
            metadata_parts.append(f"Model: {summary.model}")

        if metadata_parts:
            lines.append("")
            lines.append("---")
            lines.extend(metadata_parts)

        return "\n".join(lines)

    def _format_markdown(self, summary: Summary) -> str:
        """Render summary as Markdown with title header and metadata."""
        lines = []

        # Title header
        title = getattr(summary, "title", None) or "Summary"
        lines.append(f"# {title}")
        lines.append("")

        # Metadata block
        metadata_lines = []
        if hasattr(summary, "word_count") and summary.word_count is not None:
            metadata_lines.append(f"- **Word count:** {summary.word_count}")
        if hasattr(summary, "source_url") and summary.source_url:
            metadata_lines.append(f"- **Source:** [{summary.source_url}]({summary.source_url})")
        if hasattr(summary, "model") and summary.model:
            metadata_lines.append(f"- **Model:** `{summary.model}`")
        if hasattr(summary, "style") and summary.style:
            style_value = summary.style.value if hasattr(summary.style, "value") else summary.style
            metadata_lines.append(f"- **Style:** {style_value}")
        if hasattr(summary, "created_at") and summary.created_at:
            if isinstance(summary.created_at, datetime):
                metadata_lines.append(f"- **Generated:** {summary.created_at.strftime('%Y-%m-%d %H:%M:%S UTC')}")
            else:
                metadata_lines.append(f"- **Generated:** {summary.created_at}")

        if metadata_lines:
            lines.append("## Metadata")
            lines.append("")
            lines.extend(metadata_lines)
            lines.append("")

        # Summary body
        lines.append("## Summary")
        lines.append("")
        lines.append(summary.body)
        lines.append("")

        return "\n".join(lines)

    def _format_json(self, summary: Summary) -> str:
        """Render summary as JSON, serializing the full Summary dataclass."""
        try:
            data = asdict(summary)
        except TypeError:
            # Fallback for non-dataclass Summary objects
            data = {k: v for k, v in vars(summary).items()}

        # Convert non-serializable types
        data = self._make_serializable(data)

        return json.dumps(data, indent=2, ensure_ascii=False)

    def _make_serializable(self, obj):
        """Recursively convert non-JSON-serializable objects."""
        if isinstance(obj, dict):
            return {k: self._make_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._make_serializable(item) for item in obj]
        elif isinstance(obj, datetime):
            return obj.isoformat()
        elif hasattr(obj, "value"):
            # Handle Enum types
            return obj.value
        else:
            return obj
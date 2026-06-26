"""Summary styles and output format enums."""

from enum import Enum


class SummaryStyle(Enum):
    """Available summary styles."""
    BULLETS = "bullets"
    BRIEF = "brief"
    DETAILED = "detailed"
    ELI5 = "eli5"
    TLDR = "tldr"


class OutputFormat(Enum):
    """Available output formats."""
    TEXT = "text"
    MARKDOWN = "markdown"
    JSON = "json"


# Human-readable descriptions for each style
STYLE_DESCRIPTIONS = {
    SummaryStyle.BULLETS: "Bullet-point summary highlighting key facts",
    SummaryStyle.BRIEF: "Concise executive brief (2-3 paragraphs)",
    SummaryStyle.DETAILED: "Comprehensive detailed analysis",
    SummaryStyle.ELI5: "Explain Like I'm 5 — simple, accessible language",
    SummaryStyle.TLDR: "One-sentence TL;DR",
}
"""Summary styles and output format enumerations."""

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
    SummaryStyle.BULLETS: "Bullet-point list of key takeaways",
    SummaryStyle.BRIEF: "Short executive brief (2-3 paragraphs)",
    SummaryStyle.DETAILED: "Comprehensive detailed analysis",
    SummaryStyle.ELI5: "Explain like I'm 5 years old",
    SummaryStyle.TLDR: "One-sentence TL;DR summary",
}

# Prompt template keys for each style
STYLE_PROMPT_KEYS = {
    SummaryStyle.BULLETS: "bullets",
    SummaryStyle.BRIEF: "brief",
    SummaryStyle.DETAILED: "detailed",
    SummaryStyle.ELI5: "eli5",
    SummaryStyle.TLDR: "tldr",
}
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


# Maps each SummaryStyle to its prompt template key
STYLE_PROMPT_MAP = {
    SummaryStyle.BULLETS: "bullets",
    SummaryStyle.BRIEF: "brief",
    SummaryStyle.DETAILED: "detailed",
    SummaryStyle.ELI5: "eli5",
    SummaryStyle.TLDR: "tldr",
}
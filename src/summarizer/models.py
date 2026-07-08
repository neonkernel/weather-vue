"""
Domain models for the summarizer package.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class Summary:
    """
    Represents a summarised article.

    Attributes:
        text: The summary text produced by the LLM.
        title: Optional title of the source article.
        source: URL or file path of the source article.
        model: The LLM model identifier used to produce the summary.
        style: The summarisation style requested (e.g. "brief", "detailed").
        metadata: A free-form dict for post-processors to attach additional data.
    """

    text: str
    title: Optional[str] = None
    source: Optional[str] = None
    model: Optional[str] = None
    style: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.metadata is None:
            self.metadata = {}
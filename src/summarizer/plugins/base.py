"""
Base ABCs for all plugin types in the summarizer plugin system.

Plugin authors should subclass one of these ABCs to create custom plugins:
- BaseExtractor: custom article extraction logic
- BasePostProcessor: transforms the Summary after LLM response
- BaseFormatter: custom output formats
"""

from __future__ import annotations

import abc
from typing import Any, Optional


class BaseExtractor(abc.ABC):
    """
    Abstract base class for custom article extractors.

    Subclass this to provide custom extraction logic for specific
    content sources (e.g., paywalled sites, custom CMSes, PDFs).
    """

    # Human-readable name for this extractor
    name: str = "unnamed_extractor"

    # Description shown in `plugins list`
    description: str = ""

    @abc.abstractmethod
    def can_handle(self, url: str) -> bool:
        """
        Return True if this extractor can handle the given URL.

        Args:
            url: The URL to check.

        Returns:
            True if this extractor should be used for the given URL.
        """
        ...

    @abc.abstractmethod
    def extract(self, url: str, **kwargs: Any) -> dict[str, Any]:
        """
        Extract article content from the given URL.

        Args:
            url: The URL to extract content from.
            **kwargs: Additional options passed by the caller.

        Returns:
            A dict with at least 'text' (str) and optionally
            'title' (str), 'author' (str), 'date' (str), 'html' (str).

        Raises:
            ExtractionError: if content cannot be extracted.
        """
        ...

    def __repr__(self) -> str:
        return f"<Extractor: {self.name}>"


class BasePostProcessor(abc.ABC):
    """
    Abstract base class for post-processors.

    Subclass this to transform or enrich a Summary object after
    the LLM has generated the summary text.
    """

    # Human-readable name for this post-processor
    name: str = "unnamed_postprocessor"

    # Description shown in `plugins list`
    description: str = ""

    # Whether this processor is enabled by default
    enabled_by_default: bool = False

    @abc.abstractmethod
    def process(self, summary: Any, article_text: str = "", **kwargs: Any) -> Any:
        """
        Process and enrich a Summary object.

        Args:
            summary: The Summary object produced by the LLM pipeline.
            article_text: The original article text (for analysis).
            **kwargs: Additional options.

        Returns:
            The (potentially modified) Summary object. Processors should
            add their results to summary.metadata or a dedicated field.
        """
        ...

    def __repr__(self) -> str:
        return f"<PostProcessor: {self.name}>"


class BaseFormatter(abc.ABC):
    """
    Abstract base class for custom output formatters.

    Subclass this to produce custom output formats (e.g., HTML,
    Slack messages, database inserts) from a Summary object.
    """

    # Human-readable name for this formatter
    name: str = "unnamed_formatter"

    # Description shown in `plugins list`
    description: str = ""

    # File extension hint (e.g., ".html", ".json")
    extension: str = ".txt"

    @abc.abstractmethod
    def format(self, summary: Any, **kwargs: Any) -> str:
        """
        Format a Summary object into a string representation.

        Args:
            summary: The Summary object to format.
            **kwargs: Additional options.

        Returns:
            A string representation of the summary.
        """
        ...

    def __repr__(self) -> str:
        return f"<Formatter: {self.name}>"
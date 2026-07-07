"""
Base ABCs for all plugin types.

Plugin authors should subclass one of:
- BaseExtractor: custom article extraction logic
- BasePostProcessor: transforms Summary after LLM response
- BaseFormatter: custom output formats
"""

from __future__ import annotations

import abc
from typing import Any, Optional


class BaseExtractor(abc.ABC):
    """
    Abstract base class for custom article extractors.

    Extractors are responsible for fetching and parsing raw content
    from a URL or other source into plain text.
    """

    #: Human-readable name shown in `plugins list`
    name: str = ""
    #: Short description shown in `plugins list`
    description: str = ""

    @abc.abstractmethod
    def can_handle(self, url: str) -> bool:
        """
        Return True if this extractor knows how to handle the given URL.

        The registry will call each extractor's ``can_handle`` in registration
        order and use the first one that returns True.

        Args:
            url: The URL to be extracted.

        Returns:
            bool: Whether this extractor can process the URL.
        """

    @abc.abstractmethod
    def extract(self, url: str) -> str:
        """
        Fetch and return the plain-text content of the article at *url*.

        Args:
            url: The URL to extract content from.

        Returns:
            str: The extracted plain-text article body.

        Raises:
            ExtractionError: If extraction fails.
        """


class BasePostProcessor(abc.ABC):
    """
    Abstract base class for post-processors.

    Post-processors receive the completed Summary object (and optionally the
    original article text) and may augment or transform it in place.
    """

    #: Human-readable name shown in `plugins list`
    name: str = ""
    #: Short description shown in `plugins list`
    description: str = ""

    @abc.abstractmethod
    def process(self, summary: Any, article_text: Optional[str] = None) -> Any:
        """
        Process/augment the summary object.

        Args:
            summary: The Summary dataclass/object returned by the LLM client.
            article_text: The original article text, if available.

        Returns:
            The (possibly modified) summary object.
        """


class BaseFormatter(abc.ABC):
    """
    Abstract base class for output formatters.

    Formatters convert a Summary object into a string representation
    in a particular format (e.g., HTML, Markdown, JSON, CSV).
    """

    #: Human-readable name shown in `plugins list`
    name: str = ""
    #: Short description shown in `plugins list`
    description: str = ""
    #: File extension hint (e.g. ".html", ".md") — used by CLI when writing output
    extension: str = ".txt"

    @abc.abstractmethod
    def format(self, summary: Any) -> str:
        """
        Convert a Summary object to a formatted string.

        Args:
            summary: The Summary dataclass/object to format.

        Returns:
            str: The formatted output string.
        """
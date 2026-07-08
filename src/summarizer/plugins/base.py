"""
Base ABCs for all plugin types: BaseExtractor, BasePostProcessor, BaseFormatter.
Plugin authors must subclass these and implement the required methods.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from summarizer.models import Summary


class BaseExtractor(ABC):
    """
    Base class for custom article extractors.

    Extractors are responsible for fetching and parsing content from a URL
    or other source into plain text suitable for summarization.
    """

    #: Human-readable name for this extractor (used in CLI listing)
    name: str = "unnamed_extractor"
    #: Short description shown in `summarize plugins list`
    description: str = ""

    @abstractmethod
    def can_handle(self, url: str) -> bool:
        """
        Return True if this extractor can handle the given URL/source.

        Args:
            url: The URL or source identifier to check.

        Returns:
            True if this extractor should be used for the given source.
        """
        ...

    @abstractmethod
    def extract(self, url: str, **kwargs: Any) -> str:
        """
        Extract and return the plain-text content from the given source.

        Args:
            url: The URL or source identifier to extract from.
            **kwargs: Additional options (e.g., timeout, headers).

        Returns:
            Plain-text content of the article.

        Raises:
            ExtractionError: If extraction fails.
        """
        ...

    def __repr__(self) -> str:
        return f"<Extractor name={self.name!r}>"


class BasePostProcessor(ABC):
    """
    Base class for post-processors that transform a Summary after LLM response.

    Post-processors receive the Summary object and the original article text,
    and may add metadata, annotations, or modify the summary fields.
    """

    #: Human-readable name for this post-processor
    name: str = "unnamed_postprocessor"
    #: Short description shown in `summarize plugins list`
    description: str = ""

    @abstractmethod
    def process(self, summary: Summary, article_text: str, **kwargs: Any) -> Summary:
        """
        Process the summary and return a (potentially modified) Summary.

        Args:
            summary: The Summary object produced by the LLM.
            article_text: The original article text that was summarized.
            **kwargs: Additional options passed from configuration.

        Returns:
            A Summary object (may be the same instance, mutated, or a new one).
        """
        ...

    def __repr__(self) -> str:
        return f"<PostProcessor name={self.name!r}>"


class BaseFormatter(ABC):
    """
    Base class for custom output formatters.

    Formatters convert a Summary (or list of Summaries) into a string
    representation in a custom format (e.g., HTML, CSV, custom JSON schema).
    """

    #: Human-readable name for this formatter
    name: str = "unnamed_formatter"
    #: Short description shown in `summarize plugins list`
    description: str = ""
    #: File extension hint for output files (e.g., "html", "csv")
    extension: str = "txt"

    @abstractmethod
    def format_summary(self, summary: Summary, **kwargs: Any) -> str:
        """
        Format a single Summary into a string.

        Args:
            summary: The Summary to format.
            **kwargs: Additional formatting options.

        Returns:
            String representation of the summary.
        """
        ...

    def format_batch(self, summaries: List[Summary], **kwargs: Any) -> str:
        """
        Format a list of Summaries into a single string.

        Default implementation joins individual formatted summaries with
        a separator. Override for custom batch behaviour.

        Args:
            summaries: List of Summary objects to format.
            **kwargs: Additional formatting options.

        Returns:
            String representation of all summaries.
        """
        separator = "\n" + "=" * 80 + "\n"
        return separator.join(self.format_summary(s, **kwargs) for s in summaries)

    def __repr__(self) -> str:
        return f"<Formatter name={self.name!r}>"
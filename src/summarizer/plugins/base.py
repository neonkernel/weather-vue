"""
Base ABCs for all plugin types: BaseExtractor, BasePostProcessor, BaseFormatter.

Plugin authors should subclass one of these abstract base classes and implement
the required methods. Plugins are discovered via Python entry points defined in
pyproject.toml.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from summarizer.models import Summary


class BaseExtractor(ABC):
    """
    Abstract base class for custom article extractors.

    Extractors are responsible for fetching and parsing raw article content
    from a given URL or file path. Implement this to support custom sources
    or extraction logic.
    """

    #: Human-readable name for this extractor (used in plugin listings).
    name: str = "unnamed_extractor"

    #: Short description shown in `summarize plugins list`.
    description: str = ""

    @abstractmethod
    def can_handle(self, source: str) -> bool:
        """
        Return True if this extractor can process the given source URL/path.

        Args:
            source: A URL string or file path to potentially extract from.

        Returns:
            True if this extractor should be used for the given source.
        """
        ...

    @abstractmethod
    def extract(self, source: str) -> Dict[str, Any]:
        """
        Extract article content from the given source.

        Args:
            source: A URL string or file path to extract content from.

        Returns:
            A dictionary with at minimum:
                - ``text`` (str): The plain text content of the article.
                - ``title`` (str, optional): The article title.
                - ``url`` (str, optional): Canonical URL.
                - ``metadata`` (dict, optional): Any extra metadata.
        """
        ...


class BasePostProcessor(ABC):
    """
    Abstract base class for post-processors that transform Summary objects
    after the LLM response has been received.

    Post-processors can enrich summaries with additional computed fields,
    annotations, scores, or any other transformations.
    """

    #: Human-readable name for this post-processor (used in plugin listings).
    name: str = "unnamed_postprocessor"

    #: Short description shown in `summarize plugins list`.
    description: str = ""

    @abstractmethod
    def process(self, summary: Summary, article_text: str = "") -> Summary:
        """
        Transform or enrich a Summary object.

        This method receives the Summary produced by the LLM and the original
        article text (if available), and returns a (potentially modified) Summary.

        Implementations should not mutate the input summary in place; instead,
        return a new or updated Summary instance (or the same instance if mutation
        is intentional and documented).

        Args:
            summary: The Summary object produced by the LLM pipeline.
            article_text: The original article plain text (may be empty string).

        Returns:
            A Summary object (the same or a modified copy).
        """
        ...


class BaseFormatter(ABC):
    """
    Abstract base class for custom output formatters.

    Formatters convert a Summary (or list of summaries) into a string
    representation for display or file output.
    """

    #: Human-readable name for this formatter (used in plugin listings).
    name: str = "unnamed_formatter"

    #: Short description shown in `summarize plugins list`.
    description: str = ""

    #: File extension hint (e.g. ".md", ".html", ".csv") — used when writing to file.
    extension: str = ".txt"

    @abstractmethod
    def format(self, summary: Summary, **kwargs: Any) -> str:
        """
        Format a single Summary as a string.

        Args:
            summary: The Summary object to format.
            **kwargs: Additional formatter-specific options.

        Returns:
            A string representation of the summary.
        """
        ...

    def format_many(self, summaries: list, **kwargs: Any) -> str:
        """
        Format multiple summaries as a single string.

        The default implementation joins individual formatted summaries with
        a double newline separator. Override for custom multi-summary layouts.

        Args:
            summaries: A list of Summary objects.
            **kwargs: Additional formatter-specific options.

        Returns:
            A combined string representation.
        """
        parts = [self.format(s, **kwargs) for s in summaries]
        return "\n\n".join(parts)
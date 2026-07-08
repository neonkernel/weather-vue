"""
Base ABCs for all plugin types.

Plugin authors should subclass one of these ABCs and implement the required
abstract methods, then register their class via the appropriate entry point
group in their package's pyproject.toml.
"""

from __future__ import annotations

import abc
from typing import Any, Dict, List, Optional

from ..models import Summary


class BaseExtractor(abc.ABC):
    """
    Base class for custom article extractors.

    Extractors are responsible for fetching and parsing raw text content
    from a source (URL, file path, etc.).

    Entry point group: ``summarizer.extractors``
    """

    #: Human-readable name shown in ``summarize plugins list``
    name: str = ""
    #: Short description of what this extractor does
    description: str = ""
    #: Version string for the extractor
    version: str = "0.1.0"

    @abc.abstractmethod
    def can_handle(self, source: str) -> bool:
        """
        Return True if this extractor can handle the given source string.

        The plugin registry calls this method to determine which extractor
        should be used for a given source.  The first extractor that returns
        True wins.

        Args:
            source: A URL, file path, or other identifier for the content.

        Returns:
            True if this extractor is able to process *source*.
        """

    @abc.abstractmethod
    def extract(self, source: str, **kwargs: Any) -> str:
        """
        Extract and return the raw text content from *source*.

        Args:
            source: A URL, file path, or other identifier for the content.
            **kwargs: Optional extractor-specific parameters.

        Returns:
            The plain-text body of the article.

        Raises:
            ExtractionError: If the content cannot be retrieved or parsed.
        """

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} name={self.name!r} version={self.version!r}>"


class BasePostProcessor(abc.ABC):
    """
    Base class for post-processors that transform a :class:`~summarizer.models.Summary`
    after the LLM has produced it.

    Post-processors can enrich the summary with additional metadata fields
    (e.g. keywords, readability scores) or mutate the text in-place.

    Entry point group: ``summarizer.postprocessors``
    """

    #: Human-readable name shown in ``summarize plugins list``
    name: str = ""
    #: Short description of what this post-processor does
    description: str = ""
    #: Version string for the post-processor
    version: str = "0.1.0"

    @abc.abstractmethod
    def process(self, summary: Summary, original_text: str, **kwargs: Any) -> Summary:
        """
        Process *summary* and return the (possibly mutated) result.

        Implementations should avoid replacing the Summary object wholesale;
        instead, update ``summary.metadata`` or ``summary.text`` in-place and
        return *summary*.

        Args:
            summary: The :class:`~summarizer.models.Summary` produced by the LLM.
            original_text: The raw article text that was summarised.
            **kwargs: Optional processor-specific parameters.

        Returns:
            The enriched / transformed :class:`~summarizer.models.Summary`.
        """

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} name={self.name!r} version={self.version!r}>"


class BaseFormatter(abc.ABC):
    """
    Base class for custom output formatters.

    Formatters convert a :class:`~summarizer.models.Summary` object into a
    string (or bytes) representation suitable for a particular output target
    (terminal, Markdown file, JSON API response, etc.).

    Entry point group: ``summarizer.formatters``
    """

    #: Human-readable name shown in ``summarize plugins list``
    name: str = ""
    #: Short description of what this formatter produces
    description: str = ""
    #: Version string for the formatter
    version: str = "0.1.0"
    #: File extension hint, e.g. ``".md"`` or ``".json"``
    extension: str = ".txt"

    @abc.abstractmethod
    def format(self, summary: Summary, **kwargs: Any) -> str:
        """
        Render *summary* to a string.

        Args:
            summary: The :class:`~summarizer.models.Summary` to render.
            **kwargs: Optional formatter-specific parameters.

        Returns:
            A string representation of the summary.
        """

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} name={self.name!r} version={self.version!r}>"
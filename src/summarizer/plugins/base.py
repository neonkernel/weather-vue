"""
Base ABCs for all plugin types.
"""
from __future__ import annotations

import abc
from typing import Any, Dict, List, Optional


class BaseExtractor(abc.ABC):
    """
    Base class for custom article extractors.

    Plugin authors subclass this to provide alternative article extraction
    logic (e.g. extracting from PDFs, custom CMS APIs, etc.).
    """

    # Human-readable name shown in `summarize plugins list`
    name: str = "unnamed_extractor"
    description: str = ""

    @abc.abstractmethod
    def can_handle(self, source: str) -> bool:
        """
        Return True if this extractor can handle the given source string
        (URL, file path, or other identifier).
        """

    @abc.abstractmethod
    def extract(self, source: str) -> Dict[str, Any]:
        """
        Extract article content from *source*.

        Must return a dict with at least:
            {
                "title": str,
                "text":  str,
                "url":   str,   # or empty string
                "html":  str,   # or empty string
            }
        """


class BasePostProcessor(abc.ABC):
    """
    Base class for summary post-processors.

    A post-processor receives the raw ``Summary`` object produced by the LLM
    and may enrich or mutate it before it reaches the formatter / output layer.
    """

    name: str = "unnamed_postprocessor"
    description: str = ""

    @abc.abstractmethod
    def process(
        self,
        summary: Any,
        *,
        article_text: str = "",
        config: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """
        Process and return the (possibly mutated) summary.

        Parameters
        ----------
        summary:
            The ``Summary`` dataclass / object returned by the LLM layer.
        article_text:
            The original article plain-text (useful for keyword extraction,
            readability scoring, etc.).
        config:
            Optional per-invocation config dict passed from the CLI / API.

        Returns
        -------
        The (optionally mutated) summary object.
        """


class BaseFormatter(abc.ABC):
    """
    Base class for custom output formatters.

    Plugin authors subclass this to add new output formats beyond the built-in
    plain-text, JSON, and Markdown renderers.
    """

    name: str = "unnamed_formatter"
    description: str = ""
    #: File extension hint, e.g. ".html"
    extension: str = ".txt"

    @abc.abstractmethod
    def format(self, summary: Any, config: Optional[Dict[str, Any]] = None) -> str:
        """
        Render *summary* to a string in the desired output format.

        Parameters
        ----------
        summary:
            The ``Summary`` dataclass / object returned by the LLM layer.
        config:
            Optional per-invocation config dict.

        Returns
        -------
        Formatted string representation.
        """
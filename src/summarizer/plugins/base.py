"""Base ABCs for all plugin types."""

from __future__ import annotations

import abc
from typing import Any, Dict, List, Optional


class BaseExtractor(abc.ABC):
    """Base class for custom article extractors.

    Plugin authors should subclass this and implement `extract`.
    Register via the `summarizer.extractors` entry point group.
    """

    #: Human-readable name for this extractor
    name: str = "base_extractor"
    #: Short description shown in `plugins list`
    description: str = ""

    @abc.abstractmethod
    def extract(self, url: str, raw_html: str) -> Dict[str, Any]:
        """Extract structured content from raw HTML.

        Parameters
        ----------
        url:
            The URL the HTML was fetched from.
        raw_html:
            The raw HTML string of the page.

        Returns
        -------
        dict with at least the key ``"text"`` containing the main article text.
        Additional optional keys: ``"title"``, ``"author"``, ``"published_date"``.
        """

    def supports(self, url: str) -> bool:  # noqa: ARG002
        """Return True if this extractor can handle the given URL.

        Override to restrict the extractor to specific domains / URL patterns.
        The registry uses the first extractor whose ``supports()`` returns True.
        """
        return True


class BasePostProcessor(abc.ABC):
    """Base class for summary post-processors.

    Plugin authors should subclass this and implement `process`.
    Register via the `summarizer.postprocessors` entry point group.
    """

    name: str = "base_postprocessor"
    description: str = ""

    @abc.abstractmethod
    def process(self, summary: "Summary", article_text: str) -> "Summary":  # type: ignore[name-defined]  # noqa: F821
        """Transform or annotate a Summary object.

        Parameters
        ----------
        summary:
            The :class:`~summarizer.models.Summary` produced by the LLM step.
        article_text:
            The original (pre-LLM) article text, useful for keyword extraction
            and readability scoring on the source material.

        Returns
        -------
        The (possibly mutated) Summary object.
        """


class BaseFormatter(abc.ABC):
    """Base class for custom output formatters.

    Plugin authors should subclass this and implement `format`.
    Register via the `summarizer.formatters` entry point group.
    """

    name: str = "base_formatter"
    description: str = ""
    #: File extension produced by this formatter, e.g. ``"html"``
    extension: str = "txt"

    @abc.abstractmethod
    def format(self, summary: "Summary") -> str:  # type: ignore[name-defined]  # noqa: F821
        """Render a Summary to a string in this formatter's output format.

        Parameters
        ----------
        summary:
            The :class:`~summarizer.models.Summary` to render.

        Returns
        -------
        A string representation of the summary.
        """
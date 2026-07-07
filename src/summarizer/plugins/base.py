"""Abstract base classes for all summarizer plugin types.

Plugin authors must subclass the appropriate ABC and implement the
required abstract methods.  The :class:`PluginRegistry` validates each
loaded plugin against these ABCs before accepting it.

Example
-------
Create a custom post-processor::

    from summarizer.plugins.base import BasePostProcessor
    from summarizer.models import Summary

    class UpperCasePostProcessor(BasePostProcessor):
        \"\"\"Converts the summary text to upper-case (contrived demo).\"\"\"

        name = "uppercase"
        description = "Converts summary text to upper-case."

        def process(self, summary: Summary, article_text: str = "") -> Summary:
            return summary.model_copy(update={"text": summary.text.upper()})

Then register via pyproject.toml::

    [project.entry-points."summarizer.postprocessors"]
    uppercase = "mypkg.processors:UpperCasePostProcessor"
"""

from __future__ import annotations

import abc
from typing import Any, Dict


class PluginBase(abc.ABC):
    """Mixin providing common plugin metadata."""

    #: Short machine-readable identifier (snake_case).
    name: str = ""
    #: Human-readable description shown by ``summarize plugins list``.
    description: str = ""
    #: Semantic version of the plugin.
    version: str = "0.1.0"

    def get_metadata(self) -> Dict[str, str]:
        """Return plugin metadata as a plain dict."""
        return {
            "name": self.name or type(self).__name__,
            "description": self.description,
            "version": self.version,
            "class": f"{type(self).__module__}.{type(self).__qualname__}",
        }


# ---------------------------------------------------------------------------
# Extractor
# ---------------------------------------------------------------------------


class BaseExtractor(PluginBase):
    """ABC for custom article extraction logic.

    An extractor receives a raw URL or HTML string and returns the plain
    article text that will be passed to the LLM.
    """

    @abc.abstractmethod
    def extract(self, source: str) -> str:
        """Extract article text from *source*.

        Parameters
        ----------
        source:
            Either a URL string or raw HTML/text content.

        Returns
        -------
        str
            The extracted plain-text article body.
        """


# ---------------------------------------------------------------------------
# Post-processor
# ---------------------------------------------------------------------------


class BasePostProcessor(PluginBase):
    """ABC for transforming a :class:`~summarizer.models.Summary` after LLM
    generation.

    Post-processors are chained sequentially; each receives the output of
    the previous one.  They may mutate :pyattr:`Summary.metadata` or other
    fields but **must** return a :class:`~summarizer.models.Summary` instance.
    """

    @abc.abstractmethod
    def process(self, summary: Any, article_text: str = "") -> Any:
        """Transform *summary* and return the (possibly modified) instance.

        Parameters
        ----------
        summary:
            A ``Summary`` dataclass / Pydantic model instance.
        article_text:
            The original article body, available for processors that need
            it (e.g., keyword extraction from the source text).

        Returns
        -------
        Summary
            The transformed summary.  Returning the same object (mutated
            in-place) is acceptable.
        """


# ---------------------------------------------------------------------------
# Formatter
# ---------------------------------------------------------------------------


class BaseFormatter(PluginBase):
    """ABC for custom output formatters.

    A formatter serialises a :class:`~summarizer.models.Summary` to a
    string in a domain-specific format (e.g., Markdown, HTML, CSV, …).
    """

    @abc.abstractmethod
    def format(self, summary: Any) -> str:
        """Serialise *summary* to a string.

        Parameters
        ----------
        summary:
            A ``Summary`` dataclass / Pydantic model instance.

        Returns
        -------
        str
            The formatted output string.
        """
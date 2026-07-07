"""
PluginRegistry: discovers, loads, and validates plugins via entry_points().

Plugin hook groups:
  - summarizer.extractors      → subclasses of BaseExtractor
  - summarizer.postprocessors  → subclasses of BasePostProcessor
  - summarizer.formatters      → subclasses of BaseFormatter

Usage::

    from summarizer.plugins import registry

    # Get all registered post-processors
    for pp in registry.get_postprocessors():
        summary = pp.process(summary, article_text)

    # Get a specific formatter by name
    fmt = registry.get_formatter("markdown")
    output = fmt.format(summary)
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional, Type

from summarizer.plugins.base import BaseExtractor, BaseFormatter, BasePostProcessor

logger = logging.getLogger(__name__)

# Entry point group names
_EP_EXTRACTORS = "summarizer.extractors"
_EP_POSTPROCESSORS = "summarizer.postprocessors"
_EP_FORMATTERS = "summarizer.formatters"


def _load_entry_points(group: str) -> list:
    """
    Load entry points for the given group, compatible with Python 3.9+.

    Returns a list of importlib.metadata EntryPoint objects.
    """
    try:
        from importlib.metadata import entry_points

        eps = entry_points()
        # Python 3.12+ / 3.9+ with select support
        if hasattr(eps, "select"):
            return list(eps.select(group=group))
        # Older interface returns a dict
        return list(eps.get(group, []))
    except Exception as exc:
        logger.warning("Failed to load entry points for group '%s': %s", group, exc)
        return []


class PluginLoadError(Exception):
    """Raised when a plugin cannot be loaded or fails validation."""


class PluginRegistry:
    """
    Central registry for all summarizer plugins.

    Discovers plugins at construction time from installed entry points and
    from any explicitly registered classes (useful for testing or programmatic
    use without installing the package).
    """

    def __init__(self, autoload: bool = True) -> None:
        self._extractors: Dict[str, BaseExtractor] = {}
        self._postprocessors: Dict[str, BasePostProcessor] = {}
        self._formatters: Dict[str, BaseFormatter] = {}

        if autoload:
            self._discover_all()

    # ------------------------------------------------------------------
    # Discovery
    # ------------------------------------------------------------------

    def _discover_all(self) -> None:
        """Discover and register all installed plugins."""
        self._discover_extractors()
        self._discover_postprocessors()
        self._discover_formatters()

    def _discover_extractors(self) -> None:
        for ep in _load_entry_points(_EP_EXTRACTORS):
            self._load_and_register_extractor(ep)

    def _discover_postprocessors(self) -> None:
        for ep in _load_entry_points(_EP_POSTPROCESSORS):
            self._load_and_register_postprocessor(ep)

    def _discover_formatters(self) -> None:
        for ep in _load_entry_points(_EP_FORMATTERS):
            self._load_and_register_formatter(ep)

    # ------------------------------------------------------------------
    # Loading helpers
    # ------------------------------------------------------------------

    def _load_class(self, ep) -> type:
        """
        Load the class from an entry point, raising PluginLoadError on failure.
        """
        try:
            cls = ep.load()
            return cls
        except Exception as exc:
            raise PluginLoadError(
                f"Failed to load plugin entry point '{ep.name}' "
                f"(value={getattr(ep, 'value', '?')}): {exc}"
            ) from exc

    def _load_and_register_extractor(self, ep) -> None:
        try:
            cls = self._load_class(ep)
            self.register_extractor(cls)
        except PluginLoadError as exc:
            logger.error("Extractor plugin load error: %s", exc)

    def _load_and_register_postprocessor(self, ep) -> None:
        try:
            cls = self._load_class(ep)
            self.register_postprocessor(cls)
        except PluginLoadError as exc:
            logger.error("PostProcessor plugin load error: %s", exc)

    def _load_and_register_formatter(self, ep) -> None:
        try:
            cls = self._load_class(ep)
            self.register_formatter(cls)
        except PluginLoadError as exc:
            logger.error("Formatter plugin load error: %s", exc)

    # ------------------------------------------------------------------
    # Registration (programmatic / manual)
    # ------------------------------------------------------------------

    def register_extractor(self, cls: Type[BaseExtractor]) -> None:
        """
        Validate and register an extractor class.

        Args:
            cls: A class that must be a subclass of BaseExtractor.

        Raises:
            PluginLoadError: If cls is not a valid BaseExtractor subclass.
        """
        if not (isinstance(cls, type) and issubclass(cls, BaseExtractor)):
            raise PluginLoadError(
                f"Cannot register extractor: {cls!r} is not a subclass of BaseExtractor."
            )
        instance = cls()
        name = getattr(instance, "name", None) or cls.__name__
        if name in self._extractors:
            logger.warning("Overwriting existing extractor plugin '%s'.", name)
        self._extractors[name] = instance
        logger.debug("Registered extractor plugin: '%s'", name)

    def register_postprocessor(self, cls: Type[BasePostProcessor]) -> None:
        """
        Validate and register a post-processor class.

        Args:
            cls: A class that must be a subclass of BasePostProcessor.

        Raises:
            PluginLoadError: If cls is not a valid BasePostProcessor subclass.
        """
        if not (isinstance(cls, type) and issubclass(cls, BasePostProcessor)):
            raise PluginLoadError(
                f"Cannot register post-processor: {cls!r} is not a subclass of BasePostProcessor."
            )
        instance = cls()
        name = getattr(instance, "name", None) or cls.__name__
        if name in self._postprocessors:
            logger.warning("Overwriting existing post-processor plugin '%s'.", name)
        self._postprocessors[name] = instance
        logger.debug("Registered post-processor plugin: '%s'", name)

    def register_formatter(self, cls: Type[BaseFormatter]) -> None:
        """
        Validate and register a formatter class.

        Args:
            cls: A class that must be a subclass of BaseFormatter.

        Raises:
            PluginLoadError: If cls is not a valid BaseFormatter subclass.
        """
        if not (isinstance(cls, type) and issubclass(cls, BaseFormatter)):
            raise PluginLoadError(
                f"Cannot register formatter: {cls!r} is not a subclass of BaseFormatter."
            )
        instance = cls()
        name = getattr(instance, "name", None) or cls.__name__
        if name in self._formatters:
            logger.warning("Overwriting existing formatter plugin '%s'.", name)
        self._formatters[name] = instance
        logger.debug("Registered formatter plugin: '%s'", name)

    # ------------------------------------------------------------------
    # Accessors
    # ------------------------------------------------------------------

    def get_extractors(self) -> List[BaseExtractor]:
        """Return all registered extractor instances."""
        return list(self._extractors.values())

    def get_extractor(self, name: str) -> Optional[BaseExtractor]:
        """Return a registered extractor by name, or None."""
        return self._extractors.get(name)

    def get_postprocessors(self) -> List[BasePostProcessor]:
        """Return all registered post-processor instances."""
        return list(self._postprocessors.values())

    def get_postprocessor(self, name: str) -> Optional[BasePostProcessor]:
        """Return a registered post-processor by name, or None."""
        return self._postprocessors.get(name)

    def get_formatters(self) -> List[BaseFormatter]:
        """Return all registered formatter instances."""
        return list(self._formatters.values())

    def get_formatter(self, name: str) -> Optional[BaseFormatter]:
        """Return a registered formatter by name, or None."""
        return self._formatters.get(name)

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    def list_all(self) -> Dict[str, List[Dict[str, str]]]:
        """
        Return a structured dict of all registered plugins grouped by type.

        Returns:
            A dict with keys ``"extractors"``, ``"postprocessors"``, ``"formatters"``,
            each mapping to a list of ``{"name": ..., "description": ..., "class": ...}``
            dictionaries.
        """
        def _describe(instances: dict) -> List[Dict[str, str]]:
            result = []
            for name, inst in instances.items():
                result.append(
                    {
                        "name": name,
                        "description": getattr(inst, "description", ""),
                        "class": f"{type(inst).__module__}.{type(inst).__qualname__}",
                    }
                )
            return result

        return {
            "extractors": _describe(self._extractors),
            "postprocessors": _describe(self._postprocessors),
            "formatters": _describe(self._formatters),
        }

    def __repr__(self) -> str:
        return (
            f"PluginRegistry("
            f"extractors={len(self._extractors)}, "
            f"postprocessors={len(self._postprocessors)}, "
            f"formatters={len(self._formatters)})"
        )


# ---------------------------------------------------------------------------
# Module-level singleton registry (lazy-initialised on first import)
# ---------------------------------------------------------------------------

registry: PluginRegistry = PluginRegistry(autoload=True)

__all__ = [
    "PluginRegistry",
    "PluginLoadError",
    "registry",
    "BaseExtractor",
    "BasePostProcessor",
    "BaseFormatter",
]
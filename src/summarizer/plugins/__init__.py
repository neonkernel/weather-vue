"""
Plugin system for the summarizer package.

This module provides the PluginRegistry which discovers and loads plugins
via Python's importlib.metadata entry points system.

Entry point groups:
    summarizer.extractors      - Custom article extractors (BaseExtractor)
    summarizer.postprocessors  - Summary post-processors (BasePostProcessor)
    summarizer.formatters      - Custom output formatters (BaseFormatter)
"""

from __future__ import annotations

import logging
from typing import Optional, Type

from .base import BaseExtractor, BaseFormatter, BasePostProcessor

logger = logging.getLogger(__name__)

# Entry point group names
EP_EXTRACTORS = "summarizer.extractors"
EP_POSTPROCESSORS = "summarizer.postprocessors"
EP_FORMATTERS = "summarizer.formatters"


def _load_entry_points(group: str) -> list:
    """Load entry points for a given group, compatible with Python 3.9+."""
    try:
        from importlib.metadata import entry_points

        eps = entry_points()
        # Python 3.12+ and 3.9+ with select() support
        if hasattr(eps, "select"):
            return list(eps.select(group=group))
        # Older Python 3.9 fallback
        return list(eps.get(group, []))
    except Exception as exc:  # pragma: no cover
        logger.warning("Failed to load entry points for group %r: %s", group, exc)
        return []


class PluginRegistry:
    """
    Discovers, loads, and validates plugins via importlib.metadata entry points.

    Usage::

        registry = PluginRegistry()
        registry.discover()

        for ep in registry.extractors:
            print(ep.name)
    """

    def __init__(self) -> None:
        self._extractors: list[BaseExtractor] = []
        self._postprocessors: list[BasePostProcessor] = []
        self._formatters: list[BaseFormatter] = []
        self._discovered = False

    # ------------------------------------------------------------------
    # Discovery
    # ------------------------------------------------------------------

    def discover(self, include_builtin: bool = True) -> "PluginRegistry":
        """
        Discover and load all registered plugins.

        Args:
            include_builtin: If True (default), load built-in plugins first.

        Returns:
            self, for chaining.
        """
        if include_builtin:
            self._load_builtin_plugins()

        self._discover_entry_points(EP_EXTRACTORS, BaseExtractor, self._extractors)
        self._discover_entry_points(
            EP_POSTPROCESSORS, BasePostProcessor, self._postprocessors
        )
        self._discover_entry_points(EP_FORMATTERS, BaseFormatter, self._formatters)

        self._discovered = True
        logger.info(
            "Plugin discovery complete: %d extractor(s), %d post-processor(s), %d formatter(s)",
            len(self._extractors),
            len(self._postprocessors),
            len(self._formatters),
        )
        return self

    def _load_builtin_plugins(self) -> None:
        """Load built-in plugins that ship with the package."""
        builtin_postprocessors = [
            "src.summarizer.plugins.builtin.keyword_extractor:KeywordExtractor",
            "src.summarizer.plugins.builtin.readability:ReadabilityScorer",
        ]
        for dotted in builtin_postprocessors:
            try:
                cls = self._import_class(dotted)
                instance = self._instantiate(cls, BasePostProcessor)
                if instance is not None:
                    self._postprocessors.append(instance)
                    logger.debug("Loaded built-in post-processor: %s", cls.__name__)
            except Exception as exc:
                logger.warning("Failed to load built-in plugin %r: %s", dotted, exc)

    def _discover_entry_points(
        self,
        group: str,
        base_cls: type,
        registry_list: list,
    ) -> None:
        """Load plugins from the given entry point group."""
        eps = _load_entry_points(group)
        for ep in eps:
            try:
                cls = ep.load()
                instance = self._instantiate(cls, base_cls)
                if instance is not None:
                    registry_list.append(instance)
                    logger.debug(
                        "Loaded plugin %r from group %r", ep.name, group
                    )
            except Exception as exc:
                logger.warning(
                    "Failed to load plugin %r from group %r: %s",
                    ep.name,
                    group,
                    exc,
                )

    # ------------------------------------------------------------------
    # Instantiation & validation
    # ------------------------------------------------------------------

    @staticmethod
    def _import_class(dotted_path: str) -> type:
        """
        Import a class from a dotted path string like 'module.path:ClassName'.
        """
        if ":" not in dotted_path:
            raise ValueError(
                f"Invalid plugin path {dotted_path!r}. "
                "Expected 'module.path:ClassName' format."
            )
        module_path, class_name = dotted_path.rsplit(":", 1)
        import importlib

        module = importlib.import_module(module_path)
        cls = getattr(module, class_name)
        return cls

    @staticmethod
    def _instantiate(cls: type, base_cls: type) -> Optional[object]:
        """
        Validate that cls is a proper subclass of base_cls and instantiate it.

        Returns None (with a warning) if validation fails.
        """
        if cls is base_cls:
            logger.warning(
                "Plugin class %r is the base class itself — skipping.", cls
            )
            return None
        if not (isinstance(cls, type) and issubclass(cls, base_cls)):
            logger.warning(
                "Plugin class %r does not subclass %r — skipping.",
                cls,
                base_cls,
            )
            return None
        try:
            return cls()
        except Exception as exc:
            logger.warning(
                "Failed to instantiate plugin class %r: %s", cls, exc
            )
            return None

    # ------------------------------------------------------------------
    # Accessors
    # ------------------------------------------------------------------

    @property
    def extractors(self) -> list[BaseExtractor]:
        """Return list of loaded extractor instances."""
        return list(self._extractors)

    @property
    def postprocessors(self) -> list[BasePostProcessor]:
        """Return list of loaded post-processor instances."""
        return list(self._postprocessors)

    @property
    def formatters(self) -> list[BaseFormatter]:
        """Return list of loaded formatter instances."""
        return list(self._formatters)

    # ------------------------------------------------------------------
    # Manual registration (for testing / programmatic use)
    # ------------------------------------------------------------------

    def register_extractor(self, extractor: BaseExtractor) -> None:
        """Manually register an extractor instance."""
        if not isinstance(extractor, BaseExtractor):
            raise TypeError(f"{extractor!r} is not a BaseExtractor subclass instance.")
        self._extractors.append(extractor)

    def register_postprocessor(self, postprocessor: BasePostProcessor) -> None:
        """Manually register a post-processor instance."""
        if not isinstance(postprocessor, BasePostProcessor):
            raise TypeError(
                f"{postprocessor!r} is not a BasePostProcessor subclass instance."
            )
        self._postprocessors.append(postprocessor)

    def register_formatter(self, formatter: BaseFormatter) -> None:
        """Manually register a formatter instance."""
        if not isinstance(formatter, BaseFormatter):
            raise TypeError(f"{formatter!r} is not a BaseFormatter subclass instance.")
        self._formatters.append(formatter)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def get_extractor_for(self, url: str) -> Optional[BaseExtractor]:
        """
        Return the first extractor that can handle the given URL,
        or None if no registered extractor matches.
        """
        for extractor in self._extractors:
            try:
                if extractor.can_handle(url):
                    return extractor
            except Exception as exc:
                logger.warning(
                    "Extractor %r raised during can_handle(): %s", extractor, exc
                )
        return None

    def apply_postprocessors(
        self,
        summary: object,
        article_text: str = "",
        enabled_only: bool = True,
        **kwargs,
    ) -> object:
        """
        Apply all registered post-processors to a Summary object in order.

        Args:
            summary: The Summary object to process.
            article_text: The original article text.
            enabled_only: If True, only run processors with enabled_by_default=True.
            **kwargs: Extra keyword arguments forwarded to each processor.

        Returns:
            The enriched Summary object.
        """
        for proc in self._postprocessors:
            if enabled_only and not proc.enabled_by_default:
                continue
            try:
                summary = proc.process(summary, article_text=article_text, **kwargs)
            except Exception as exc:
                logger.warning(
                    "Post-processor %r raised an error: %s", proc, exc
                )
        return summary

    def summary_table(self) -> list[dict]:
        """
        Return a list of dicts describing all discovered plugins.
        Useful for the `plugins list` CLI command.
        """
        rows = []
        for p in self._extractors:
            rows.append(
                {
                    "type": "extractor",
                    "name": getattr(p, "name", type(p).__name__),
                    "class": type(p).__qualname__,
                    "description": getattr(p, "description", ""),
                    "enabled_by_default": "—",
                }
            )
        for p in self._postprocessors:
            rows.append(
                {
                    "type": "postprocessor",
                    "name": getattr(p, "name", type(p).__name__),
                    "class": type(p).__qualname__,
                    "description": getattr(p, "description", ""),
                    "enabled_by_default": str(
                        getattr(p, "enabled_by_default", False)
                    ),
                }
            )
        for p in self._formatters:
            rows.append(
                {
                    "type": "formatter",
                    "name": getattr(p, "name", type(p).__name__),
                    "class": type(p).__qualname__,
                    "description": getattr(p, "description", ""),
                    "enabled_by_default": "—",
                }
            )
        return rows


# Module-level singleton — use this in application code
_registry: Optional[PluginRegistry] = None


def get_registry(auto_discover: bool = True) -> PluginRegistry:
    """
    Return the global PluginRegistry singleton, discovering plugins on first call.

    Args:
        auto_discover: If True and the registry hasn't been initialised yet,
                       call registry.discover() automatically.

    Returns:
        The global PluginRegistry instance.
    """
    global _registry
    if _registry is None:
        _registry = PluginRegistry()
        if auto_discover:
            _registry.discover()
    return _registry


def reset_registry() -> None:
    """Reset the global registry (primarily useful in tests)."""
    global _registry
    _registry = None
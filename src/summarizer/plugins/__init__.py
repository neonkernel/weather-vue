"""
Plugin Registry for the summarizer package.

Discovers and loads plugins via Python's importlib.metadata entry points.
Three plugin groups are supported:

  summarizer.extractors     → subclasses of BaseExtractor
  summarizer.postprocessors → subclasses of BasePostProcessor
  summarizer.formatters     → subclasses of BaseFormatter

Usage::

    from summarizer.plugins import registry

    # Registry is loaded at first import
    for pp in registry.get_postprocessors():
        summary = pp.process(summary, article_text)
"""

from __future__ import annotations

import logging
from importlib.metadata import entry_points
from typing import Dict, List, Optional, Type

from summarizer.plugins.base import BaseExtractor, BaseFormatter, BasePostProcessor

logger = logging.getLogger(__name__)

# Entry-point group names
_GROUP_EXTRACTORS = "summarizer.extractors"
_GROUP_POSTPROCESSORS = "summarizer.postprocessors"
_GROUP_FORMATTERS = "summarizer.formatters"


class PluginLoadError(Exception):
    """Raised when a plugin cannot be loaded or fails validation."""


class PluginRegistry:
    """
    Discovers and holds references to all registered plugins.

    Plugins are discovered once (lazily on first access or explicitly via
    :meth:`load`) from the installed package entry points.
    """

    def __init__(self) -> None:
        self._extractors: Dict[str, BaseExtractor] = {}
        self._postprocessors: Dict[str, BasePostProcessor] = {}
        self._formatters: Dict[str, BaseFormatter] = {}
        self._loaded = False

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------

    def load(self, raise_on_error: bool = False) -> None:
        """
        Discover and instantiate all registered plugins.

        Args:
            raise_on_error: If True, re-raise exceptions encountered while
                loading individual plugins instead of logging and continuing.
        """
        self._extractors.clear()
        self._postprocessors.clear()
        self._formatters.clear()

        self._load_group(
            _GROUP_EXTRACTORS,
            BaseExtractor,
            self._extractors,
            raise_on_error=raise_on_error,
        )
        self._load_group(
            _GROUP_POSTPROCESSORS,
            BasePostProcessor,
            self._postprocessors,
            raise_on_error=raise_on_error,
        )
        self._load_group(
            _GROUP_FORMATTERS,
            BaseFormatter,
            self._formatters,
            raise_on_error=raise_on_error,
        )

        self._loaded = True
        logger.debug(
            "Plugin registry loaded: %d extractors, %d post-processors, %d formatters",
            len(self._extractors),
            len(self._postprocessors),
            len(self._formatters),
        )

    def _load_group(
        self,
        group: str,
        base_class: type,
        store: dict,
        raise_on_error: bool = False,
    ) -> None:
        """Load all entry points for *group* and store validated instances."""
        try:
            eps = entry_points(group=group)
        except Exception as exc:  # pragma: no cover
            logger.warning("Could not query entry points for group %r: %s", group, exc)
            return

        for ep in eps:
            try:
                plugin_class: Type = ep.load()
            except Exception as exc:
                msg = f"Failed to load plugin {ep.name!r} from group {group!r}: {exc}"
                if raise_on_error:
                    raise PluginLoadError(msg) from exc
                logger.warning(msg)
                continue

            # Validate inheritance
            if not (isinstance(plugin_class, type) and issubclass(plugin_class, base_class)):
                msg = (
                    f"Plugin {ep.name!r} ({plugin_class!r}) does not subclass "
                    f"{base_class.__name__}; skipping."
                )
                if raise_on_error:
                    raise PluginLoadError(msg)
                logger.warning(msg)
                continue

            # Instantiate
            try:
                instance = plugin_class()
            except Exception as exc:
                msg = f"Failed to instantiate plugin {ep.name!r}: {exc}"
                if raise_on_error:
                    raise PluginLoadError(msg) from exc
                logger.warning(msg)
                continue

            # Use the plugin's own .name attribute if set, otherwise ep.name
            plugin_name = getattr(instance, "name", None) or ep.name
            store[plugin_name] = instance
            logger.debug("Loaded plugin %r (%s) from group %r", plugin_name, plugin_class, group)

    def _ensure_loaded(self) -> None:
        if not self._loaded:
            self.load()

    # ------------------------------------------------------------------
    # Accessors
    # ------------------------------------------------------------------

    def get_extractors(self) -> List[BaseExtractor]:
        """Return all registered extractor instances."""
        self._ensure_loaded()
        return list(self._extractors.values())

    def get_postprocessors(self) -> List[BasePostProcessor]:
        """Return all registered post-processor instances."""
        self._ensure_loaded()
        return list(self._postprocessors.values())

    def get_formatters(self) -> List[BaseFormatter]:
        """Return all registered formatter instances."""
        self._ensure_loaded()
        return list(self._formatters.values())

    def get_extractor(self, name: str) -> Optional[BaseExtractor]:
        self._ensure_loaded()
        return self._extractors.get(name)

    def get_postprocessor(self, name: str) -> Optional[BasePostProcessor]:
        self._ensure_loaded()
        return self._postprocessors.get(name)

    def get_formatter(self, name: str) -> Optional[BaseFormatter]:
        self._ensure_loaded()
        return self._formatters.get(name)

    def find_extractor_for(self, url: str) -> Optional[BaseExtractor]:
        """Return the first extractor that can handle *url*, or None."""
        self._ensure_loaded()
        for extractor in self._extractors.values():
            try:
                if extractor.can_handle(url):
                    return extractor
            except Exception as exc:
                logger.warning(
                    "Extractor %r raised while checking can_handle(%r): %s",
                    extractor.name,
                    url,
                    exc,
                )
        return None

    # ------------------------------------------------------------------
    # Introspection helpers (used by `plugins list` CLI command)
    # ------------------------------------------------------------------

    def list_all(self) -> Dict[str, List[dict]]:
        """
        Return a dict summarising all loaded plugins by type.

        Returns::

            {
                "extractors": [{"name": ..., "description": ..., "class": ...}, ...],
                "postprocessors": [...],
                "formatters": [...],
            }
        """
        self._ensure_loaded()

        def _describe(instances: dict) -> List[dict]:
            return [
                {
                    "name": inst.name or key,
                    "description": getattr(inst, "description", "") or "",
                    "class": type(inst).__qualname__,
                    "module": type(inst).__module__,
                }
                for key, inst in instances.items()
            ]

        return {
            "extractors": _describe(self._extractors),
            "postprocessors": _describe(self._postprocessors),
            "formatters": _describe(self._formatters),
        }

    def register_extractor(self, instance: BaseExtractor) -> None:
        """Programmatically register an extractor (useful in tests)."""
        if not isinstance(instance, BaseExtractor):
            raise TypeError(f"Expected BaseExtractor, got {type(instance)}")
        self._ensure_loaded()
        key = instance.name or type(instance).__name__
        self._extractors[key] = instance

    def register_postprocessor(self, instance: BasePostProcessor) -> None:
        """Programmatically register a post-processor (useful in tests)."""
        if not isinstance(instance, BasePostProcessor):
            raise TypeError(f"Expected BasePostProcessor, got {type(instance)}")
        self._ensure_loaded()
        key = instance.name or type(instance).__name__
        self._postprocessors[key] = instance

    def register_formatter(self, instance: BaseFormatter) -> None:
        """Programmatically register a formatter (useful in tests)."""
        if not isinstance(instance, BaseFormatter):
            raise TypeError(f"Expected BaseFormatter, got {type(instance)}")
        self._ensure_loaded()
        key = instance.name or type(instance).__name__
        self._formatters[key] = instance


# Module-level singleton
registry = PluginRegistry()
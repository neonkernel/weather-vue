"""Plugin registry: discovers and loads plugins via importlib.metadata entry points."""

from __future__ import annotations

import importlib
import logging
from typing import Dict, List, Optional, Type

from summarizer.plugins.base import BaseExtractor, BaseFormatter, BasePostProcessor

logger = logging.getLogger(__name__)

# Entry-point group names
_EP_EXTRACTORS = "summarizer.extractors"
_EP_POSTPROCESSORS = "summarizer.postprocessors"
_EP_FORMATTERS = "summarizer.formatters"


def _load_entry_points(group: str) -> List:
    """Load all entry points for a given group, compatible with Python 3.9+."""
    try:
        from importlib.metadata import entry_points

        eps = entry_points()
        # Python 3.12+ / importlib_metadata: eps is a SelectableGroups object
        if hasattr(eps, "select"):
            return list(eps.select(group=group))
        # Python 3.9-3.11: eps is a dict
        return list(eps.get(group, []))
    except Exception as exc:  # pragma: no cover
        logger.warning("Failed to load entry points for group %r: %s", group, exc)
        return []


class PluginRegistry:
    """Discovers, loads, and provides access to all registered plugins.

    Usage
    -----
    ::

        registry = PluginRegistry()
        registry.discover()

        for pp in registry.postprocessors:
            summary = pp.process(summary, article_text)
    """

    def __init__(self) -> None:
        self._extractors: Dict[str, BaseExtractor] = {}
        self._postprocessors: Dict[str, BasePostProcessor] = {}
        self._formatters: Dict[str, BaseFormatter] = {}
        self._discovered = False

    # ------------------------------------------------------------------
    # Discovery
    # ------------------------------------------------------------------

    def discover(self) -> None:
        """Discover and instantiate all plugins from entry points + built-ins."""
        if self._discovered:
            return

        self._load_builtin_plugins()
        self._load_entry_point_plugins(
            _EP_EXTRACTORS, BaseExtractor, self._extractors
        )
        self._load_entry_point_plugins(
            _EP_POSTPROCESSORS, BasePostProcessor, self._postprocessors
        )
        self._load_entry_point_plugins(
            _EP_FORMATTERS, BaseFormatter, self._formatters
        )
        self._discovered = True
        logger.debug(
            "Plugin discovery complete: %d extractors, %d post-processors, %d formatters",
            len(self._extractors),
            len(self._postprocessors),
            len(self._formatters),
        )

    def _load_builtin_plugins(self) -> None:
        """Register built-in plugins that ship with the package."""
        builtin_postprocessors = [
            "summarizer.plugins.builtin.keyword_extractor:KeywordExtractor",
            "summarizer.plugins.builtin.readability:ReadabilityScorer",
        ]
        for dotted in builtin_postprocessors:
            module_path, class_name = dotted.rsplit(":", 1)
            try:
                mod = importlib.import_module(module_path)
                cls: Type[BasePostProcessor] = getattr(mod, class_name)
                self._register_instance(cls, BasePostProcessor, self._postprocessors)
            except Exception as exc:
                logger.warning(
                    "Failed to load built-in post-processor %r: %s", dotted, exc
                )

    def _load_entry_point_plugins(
        self,
        group: str,
        base_cls: type,
        registry_dict: dict,
    ) -> None:
        eps = _load_entry_points(group)
        for ep in eps:
            try:
                cls = ep.load()
                self._register_instance(cls, base_cls, registry_dict)
            except Exception as exc:
                logger.warning(
                    "Failed to load plugin %r from group %r: %s",
                    getattr(ep, "name", ep),
                    group,
                    exc,
                )

    @staticmethod
    def _register_instance(cls: type, base_cls: type, registry_dict: dict) -> None:
        """Validate cls against base_cls and add an instance to registry_dict."""
        if not (isinstance(cls, type) and issubclass(cls, base_cls)):
            raise TypeError(
                f"Plugin class {cls!r} is not a subclass of {base_cls.__name__}"
            )
        instance = cls()
        name = getattr(instance, "name", cls.__name__)
        if name in registry_dict:
            logger.debug("Plugin %r already registered; skipping duplicate.", name)
            return
        registry_dict[name] = instance
        logger.debug("Registered plugin: %s (%s)", name, cls.__qualname__)

    # ------------------------------------------------------------------
    # Accessors
    # ------------------------------------------------------------------

    @property
    def extractors(self) -> List[BaseExtractor]:
        return list(self._extractors.values())

    @property
    def postprocessors(self) -> List[BasePostProcessor]:
        return list(self._postprocessors.values())

    @property
    def formatters(self) -> List[BaseFormatter]:
        return list(self._formatters.values())

    def get_extractor(self, name: str) -> Optional[BaseExtractor]:
        return self._extractors.get(name)

    def get_postprocessor(self, name: str) -> Optional[BasePostProcessor]:
        return self._postprocessors.get(name)

    def get_formatter(self, name: str) -> Optional[BaseFormatter]:
        return self._formatters.get(name)

    def extractor_for_url(self, url: str) -> Optional[BaseExtractor]:
        """Return the first extractor that claims to support *url*."""
        for ext in self._extractors.values():
            try:
                if ext.supports(url):
                    return ext
            except Exception:
                pass
        return None

    # ------------------------------------------------------------------
    # Introspection helpers (used by CLI `plugins list`)
    # ------------------------------------------------------------------

    def summary(self) -> Dict[str, List[Dict[str, str]]]:
        """Return a structured summary of all discovered plugins."""

        def _describe(obj) -> Dict[str, str]:
            return {
                "name": getattr(obj, "name", type(obj).__name__),
                "class": type(obj).__qualname__,
                "module": type(obj).__module__,
                "description": getattr(obj, "description", ""),
            }

        return {
            "extractors": [_describe(p) for p in self._extractors.values()],
            "postprocessors": [_describe(p) for p in self._postprocessors.values()],
            "formatters": [_describe(p) for p in self._formatters.values()],
        }


# Module-level singleton – lazily populated by calling `.discover()`
registry = PluginRegistry()
"""
PluginRegistry: discovers and loads plugins via importlib.metadata entry_points().

Supports three entry-point groups:
  - summarizer.extractors
  - summarizer.postprocessors
  - summarizer.formatters
"""
from __future__ import annotations

import logging
from typing import Dict, List, Optional, Type

from summarizer.plugins.base import BaseExtractor, BaseFormatter, BasePostProcessor

logger = logging.getLogger(__name__)

# Entry-point group names
EXTRACTOR_GROUP = "summarizer.extractors"
POSTPROCESSOR_GROUP = "summarizer.postprocessors"
FORMATTER_GROUP = "summarizer.formatters"


class PluginLoadError(Exception):
    """Raised when a plugin cannot be loaded or fails validation."""


class PluginRegistry:
    """
    Central registry for all discovered plugins.

    Plugins are discovered at instantiation time via importlib.metadata
    entry_points(). Built-in plugins are registered explicitly so they
    are always available even when not installed as separate packages.
    """

    def __init__(self, load_builtins: bool = True) -> None:
        self._extractors: Dict[str, Type[BaseExtractor]] = {}
        self._postprocessors: Dict[str, Type[BasePostProcessor]] = {}
        self._formatters: Dict[str, Type[BaseFormatter]] = {}

        if load_builtins:
            self._register_builtins()

        self._discover_entry_points()

    # ------------------------------------------------------------------
    # Registration helpers
    # ------------------------------------------------------------------

    def register_extractor(self, cls: Type[BaseExtractor], *, override: bool = False) -> None:
        """Register an extractor class."""
        self._validate_plugin(cls, BaseExtractor, "extractor")
        name = getattr(cls, "name", None) or cls.__name__
        if name in self._extractors and not override:
            logger.warning("Extractor %r already registered; skipping duplicate.", name)
            return
        self._extractors[name] = cls
        logger.debug("Registered extractor: %s", name)

    def register_postprocessor(
        self, cls: Type[BasePostProcessor], *, override: bool = False
    ) -> None:
        """Register a post-processor class."""
        self._validate_plugin(cls, BasePostProcessor, "post-processor")
        name = getattr(cls, "name", None) or cls.__name__
        if name in self._postprocessors and not override:
            logger.warning("PostProcessor %r already registered; skipping duplicate.", name)
            return
        self._postprocessors[name] = cls
        logger.debug("Registered post-processor: %s", name)

    def register_formatter(self, cls: Type[BaseFormatter], *, override: bool = False) -> None:
        """Register a formatter class."""
        self._validate_plugin(cls, BaseFormatter, "formatter")
        name = getattr(cls, "name", None) or cls.__name__
        if name in self._formatters and not override:
            logger.warning("Formatter %r already registered; skipping duplicate.", name)
            return
        self._formatters[name] = cls
        logger.debug("Registered formatter: %s", name)

    # ------------------------------------------------------------------
    # Accessors
    # ------------------------------------------------------------------

    def get_extractor(self, name: str) -> Optional[Type[BaseExtractor]]:
        return self._extractors.get(name)

    def get_postprocessor(self, name: str) -> Optional[Type[BasePostProcessor]]:
        return self._postprocessors.get(name)

    def get_formatter(self, name: str) -> Optional[Type[BaseFormatter]]:
        return self._formatters.get(name)

    def all_extractors(self) -> List[Type[BaseExtractor]]:
        return list(self._extractors.values())

    def all_postprocessors(self) -> List[Type[BasePostProcessor]]:
        return list(self._postprocessors.values())

    def all_formatters(self) -> List[Type[BaseFormatter]]:
        return list(self._formatters.values())

    # ------------------------------------------------------------------
    # Discovery
    # ------------------------------------------------------------------

    def _discover_entry_points(self) -> None:
        """Load plugins declared via importlib.metadata entry_points."""
        try:
            from importlib.metadata import entry_points
        except ImportError:  # Python < 3.9 fallback
            try:
                from importlib_metadata import entry_points  # type: ignore
            except ImportError:
                logger.warning(
                    "importlib.metadata not available; skipping entry-point discovery."
                )
                return

        self._load_group(entry_points, EXTRACTOR_GROUP, BaseExtractor, self.register_extractor)
        self._load_group(
            entry_points, POSTPROCESSOR_GROUP, BasePostProcessor, self.register_postprocessor
        )
        self._load_group(entry_points, FORMATTER_GROUP, BaseFormatter, self.register_formatter)

    def _load_group(self, entry_points_fn, group: str, base_cls, register_fn) -> None:
        """Discover and register all entry points in a given group."""
        try:
            # Python 3.9+ supports group= keyword; 3.8 returns a dict
            eps = entry_points(group=group)
        except TypeError:
            eps = entry_points().get(group, [])  # type: ignore

        for ep in eps:
            try:
                plugin_cls = ep.load()
                register_fn(plugin_cls)
                logger.info("Loaded plugin %r from entry point %r", ep.name, group)
            except Exception as exc:  # noqa: BLE001
                logger.error(
                    "Failed to load plugin %r from group %r: %s", ep.name, group, exc
                )

    # ------------------------------------------------------------------
    # Built-in registration
    # ------------------------------------------------------------------

    def _register_builtins(self) -> None:
        """Register built-in plugins bundled with the package."""
        try:
            from summarizer.plugins.builtin.keyword_extractor import KeywordExtractor

            self.register_postprocessor(KeywordExtractor)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Could not load built-in KeywordExtractor: %s", exc)

        try:
            from summarizer.plugins.builtin.readability import ReadabilityScorer

            self.register_postprocessor(ReadabilityScorer)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Could not load built-in ReadabilityScorer: %s", exc)

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    @staticmethod
    def _validate_plugin(cls, base_cls, kind: str) -> None:
        """Validate that *cls* is a proper subclass of *base_cls*."""
        if not isinstance(cls, type):
            raise PluginLoadError(
                f"Plugin {cls!r} is not a class; expected a {kind} subclass of {base_cls.__name__}."
            )
        if not issubclass(cls, base_cls):
            raise PluginLoadError(
                f"Plugin {cls.__name__!r} does not subclass {base_cls.__name__}. "
                f"All {kind} plugins must inherit from {base_cls.__name__}."
            )
        # Ensure abstract methods are implemented
        abstract_methods = getattr(cls, "__abstractmethods__", frozenset())
        if abstract_methods:
            raise PluginLoadError(
                f"Plugin {cls.__name__!r} has unimplemented abstract methods: "
                f"{', '.join(sorted(abstract_methods))}. "
                f"Please implement all required methods."
            )


# ---------------------------------------------------------------------------
# Module-level singleton – lazily created so import is cheap
# ---------------------------------------------------------------------------

_registry: Optional[PluginRegistry] = None


def get_registry(*, reload: bool = False) -> PluginRegistry:
    """
    Return the global PluginRegistry singleton.

    Args:
        reload: If True, discard the cached registry and rebuild it.

    Returns:
        The global PluginRegistry instance.
    """
    global _registry
    if _registry is None or reload:
        _registry = PluginRegistry()
    return _registry
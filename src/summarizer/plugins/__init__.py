"""
PluginRegistry: discovers, loads, and validates plugins via entry_points().
"""
from __future__ import annotations

import importlib
import logging
from typing import Dict, List, Optional, Type

from .base import BaseExtractor, BaseFormatter, BasePostProcessor

logger = logging.getLogger(__name__)

# Entry-point group names — must match pyproject.toml
_EP_EXTRACTORS = "summarizer.extractors"
_EP_POSTPROCESSORS = "summarizer.postprocessors"
_EP_FORMATTERS = "summarizer.formatters"


def _load_entry_points(group: str) -> List:
    """
    Load entry points for *group* using importlib.metadata (Python ≥ 3.9).
    Falls back gracefully if the package is not installed in the environment.
    """
    try:
        from importlib.metadata import entry_points  # type: ignore

        # Python 3.12+ signature
        eps = entry_points(group=group)
    except TypeError:
        # Python 3.9 – 3.11 fallback
        from importlib.metadata import entry_points as _ep

        eps = _ep().get(group, [])
    return list(eps)


class PluginRegistry:
    """
    Central registry for all plugin types.

    Usage::

        registry = PluginRegistry()
        registry.discover()

        for pp in registry.postprocessors.values():
            summary = pp().process(summary, article_text=text)
    """

    def __init__(self) -> None:
        self.extractors: Dict[str, Type[BaseExtractor]] = {}
        self.postprocessors: Dict[str, Type[BasePostProcessor]] = {}
        self.formatters: Dict[str, Type[BaseFormatter]] = {}
        self._discovered = False

    # ------------------------------------------------------------------
    # Discovery
    # ------------------------------------------------------------------

    def discover(self, *, include_builtin: bool = True) -> None:
        """
        Discover all plugins from entry points and (optionally) built-ins.

        Safe to call multiple times — subsequent calls are no-ops unless
        *force* is True.
        """
        if self._discovered:
            return

        if include_builtin:
            self._register_builtins()

        self._load_group(_EP_EXTRACTORS, BaseExtractor, self.extractors)
        self._load_group(_EP_POSTPROCESSORS, BasePostProcessor, self.postprocessors)
        self._load_group(_EP_FORMATTERS, BaseFormatter, self.formatters)

        self._discovered = True
        logger.debug(
            "Plugin discovery complete: %d extractors, %d postprocessors, %d formatters",
            len(self.extractors),
            len(self.postprocessors),
            len(self.formatters),
        )

    def rediscover(self) -> None:
        """Force re-discovery (useful in tests)."""
        self._discovered = False
        self.extractors.clear()
        self.postprocessors.clear()
        self.formatters.clear()
        self.discover()

    # ------------------------------------------------------------------
    # Manual registration (used for built-ins and in tests)
    # ------------------------------------------------------------------

    def register_extractor(self, cls: Type[BaseExtractor]) -> None:
        self._validate(cls, BaseExtractor)
        self.extractors[cls.name] = cls
        logger.debug("Registered extractor: %s", cls.name)

    def register_postprocessor(self, cls: Type[BasePostProcessor]) -> None:
        self._validate(cls, BasePostProcessor)
        self.postprocessors[cls.name] = cls
        logger.debug("Registered postprocessor: %s", cls.name)

    def register_formatter(self, cls: Type[BaseFormatter]) -> None:
        self._validate(cls, BaseFormatter)
        self.formatters[cls.name] = cls
        logger.debug("Registered formatter: %s", cls.name)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _register_builtins(self) -> None:
        """Load the built-in post-processors shipped with the package."""
        try:
            from .builtin.keyword_extractor import KeywordExtractor

            self.register_postprocessor(KeywordExtractor)
        except Exception as exc:  # pragma: no cover
            logger.warning("Failed to load built-in KeywordExtractor: %s", exc)

        try:
            from .builtin.readability import ReadabilityScorer

            self.register_postprocessor(ReadabilityScorer)
        except Exception as exc:  # pragma: no cover
            logger.warning("Failed to load built-in ReadabilityScorer: %s", exc)

    def _load_group(
        self,
        group: str,
        base_cls: type,
        registry: dict,
    ) -> None:
        for ep in _load_entry_points(group):
            try:
                cls = ep.load()
            except Exception as exc:
                logger.error(
                    "Failed to load plugin '%s' from group '%s': %s",
                    ep.name,
                    group,
                    exc,
                )
                continue

            try:
                self._validate(cls, base_cls)
            except TypeError as exc:
                logger.error(
                    "Plugin '%s' failed validation: %s",
                    ep.name,
                    exc,
                )
                continue

            name = getattr(cls, "name", ep.name)
            registry[name] = cls
            logger.debug("Loaded plugin '%s' from entry point '%s'", name, ep.name)

    @staticmethod
    def _validate(cls: type, base_cls: type) -> None:
        if not (isinstance(cls, type) and issubclass(cls, base_cls)):
            raise TypeError(
                f"{cls!r} is not a subclass of {base_cls.__name__}"
            )

    # ------------------------------------------------------------------
    # Introspection helpers
    # ------------------------------------------------------------------

    def all_plugins(self) -> Dict[str, List[dict]]:
        """Return a structured dict of all registered plugins for display."""
        return {
            "extractors": [
                {"name": cls.name, "description": cls.description, "class": cls.__qualname__}
                for cls in self.extractors.values()
            ],
            "postprocessors": [
                {"name": cls.name, "description": cls.description, "class": cls.__qualname__}
                for cls in self.postprocessors.values()
            ],
            "formatters": [
                {"name": cls.name, "description": cls.description, "class": cls.__qualname__}
                for cls in self.formatters.values()
            ],
        }


# ---------------------------------------------------------------------------
# Module-level singleton — import this everywhere you need plugin access
# ---------------------------------------------------------------------------
registry = PluginRegistry()
"""Plugin registry for the summarizer package.

Discovers and loads plugins via Python entry points defined in pyproject.toml.
"""

from __future__ import annotations

import logging
from importlib.metadata import entry_points
from typing import TYPE_CHECKING, Dict, List, Optional, Type

from .base import BaseExtractor, BaseFormatter, BasePostProcessor

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

# Entry point group names
EP_EXTRACTORS = "summarizer.extractors"
EP_POSTPROCESSORS = "summarizer.postprocessors"
EP_FORMATTERS = "summarizer.formatters"

_BASE_CLASS_MAP = {
    EP_EXTRACTORS: BaseExtractor,
    EP_POSTPROCESSORS: BasePostProcessor,
    EP_FORMATTERS: BaseFormatter,
}


class PluginLoadError(Exception):
    """Raised when a plugin cannot be loaded or fails validation."""


class PluginRegistry:
    """Central registry that discovers, validates, and exposes plugins.

    Usage
    -----
    registry = PluginRegistry()
    registry.discover()

    for name, cls in registry.postprocessors.items():
        instance = cls()
        summary = instance.process(summary, article_text)
    """

    def __init__(self) -> None:
        self._extractors: Dict[str, Type[BaseExtractor]] = {}
        self._postprocessors: Dict[str, Type[BasePostProcessor]] = {}
        self._formatters: Dict[str, Type[BaseFormatter]] = {}
        self._errors: List[str] = []

    # ------------------------------------------------------------------
    # Public accessors
    # ------------------------------------------------------------------

    @property
    def extractors(self) -> Dict[str, Type[BaseExtractor]]:
        return dict(self._extractors)

    @property
    def postprocessors(self) -> Dict[str, Type[BasePostProcessor]]:
        return dict(self._postprocessors)

    @property
    def formatters(self) -> Dict[str, Type[BaseFormatter]]:
        return dict(self._formatters)

    @property
    def errors(self) -> List[str]:
        return list(self._errors)

    # ------------------------------------------------------------------
    # Discovery
    # ------------------------------------------------------------------

    def discover(self) -> None:
        """Load all plugins from entry points and built-ins."""
        self._load_builtin_plugins()
        self._load_entry_point_group(EP_EXTRACTORS)
        self._load_entry_point_group(EP_POSTPROCESSORS)
        self._load_entry_point_group(EP_FORMATTERS)

    def _load_builtin_plugins(self) -> None:
        """Register built-in post-processors shipped with the package."""
        try:
            from .builtin.keyword_extractor import KeywordExtractor

            self._register(EP_POSTPROCESSORS, "keyword_extractor", KeywordExtractor)
        except Exception as exc:  # noqa: BLE001
            msg = f"Failed to load built-in KeywordExtractor: {exc}"
            logger.warning(msg)
            self._errors.append(msg)

        try:
            from .builtin.readability import ReadabilityScorer

            self._register(EP_POSTPROCESSORS, "readability", ReadabilityScorer)
        except Exception as exc:  # noqa: BLE001
            msg = f"Failed to load built-in ReadabilityScorer: {exc}"
            logger.warning(msg)
            self._errors.append(msg)

    def _load_entry_point_group(self, group: str) -> None:
        """Discover and validate plugins for a given entry-point group."""
        try:
            eps = entry_points(group=group)
        except Exception as exc:  # noqa: BLE001
            msg = f"Error reading entry points for group '{group}': {exc}"
            logger.warning(msg)
            self._errors.append(msg)
            return

        for ep in eps:
            try:
                cls = ep.load()
            except Exception as exc:  # noqa: BLE001
                msg = f"Cannot load plugin '{ep.name}' from group '{group}': {exc}"
                logger.warning(msg)
                self._errors.append(msg)
                continue

            try:
                self._register(group, ep.name, cls)
            except PluginLoadError as exc:
                logger.warning(str(exc))
                self._errors.append(str(exc))

    def _register(self, group: str, name: str, cls: type) -> None:
        """Validate *cls* against the expected ABC and store it."""
        base_cls = _BASE_CLASS_MAP.get(group)
        if base_cls is None:
            raise PluginLoadError(f"Unknown plugin group: '{group}'")

        if not (isinstance(cls, type) and issubclass(cls, base_cls)):
            raise PluginLoadError(
                f"Plugin '{name}' in group '{group}' must be a subclass of "
                f"{base_cls.__name__}, got {cls!r}."
            )

        dest: Dict[str, type]
        if group == EP_EXTRACTORS:
            dest = self._extractors  # type: ignore[assignment]
        elif group == EP_POSTPROCESSORS:
            dest = self._postprocessors  # type: ignore[assignment]
        else:
            dest = self._formatters  # type: ignore[assignment]

        if name in dest:
            logger.debug("Plugin '%s' in group '%s' already registered; skipping.", name, group)
            return

        dest[name] = cls  # type: ignore[assignment]
        logger.debug("Registered plugin '%s' -> %s (group: %s)", name, cls.__qualname__, group)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def list_all(self) -> Dict[str, Dict[str, str]]:
        """Return a structured dict of all registered plugins for display."""
        return {
            EP_EXTRACTORS: {
                name: f"{cls.__module__}.{cls.__qualname__}"
                for name, cls in self._extractors.items()
            },
            EP_POSTPROCESSORS: {
                name: f"{cls.__module__}.{cls.__qualname__}"
                for name, cls in self._postprocessors.items()
            },
            EP_FORMATTERS: {
                name: f"{cls.__module__}.{cls.__qualname__}"
                for name, cls in self._formatters.items()
            },
        }

    def apply_postprocessors(
        self,
        summary: "Summary",  # type: ignore[name-defined]  # noqa: F821
        article_text: str = "",
        *,
        names: Optional[List[str]] = None,
    ) -> "Summary":  # type: ignore[name-defined]  # noqa: F821
        """Run all (or a named subset of) post-processors against *summary*.

        Parameters
        ----------
        summary:
            The ``Summary`` dataclass instance to transform.
        article_text:
            The original article body, used by processors that need it.
        names:
            Optional allow-list of processor names to run. ``None`` means all.
        """
        processors = self._postprocessors
        if names is not None:
            processors = {k: v for k, v in processors.items() if k in names}

        for name, cls in processors.items():
            try:
                instance = cls()
                summary = instance.process(summary, article_text)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Post-processor '%s' failed: %s", name, exc)

        return summary


# ---------------------------------------------------------------------------
# Module-level singleton – lazily populated on first access
# ---------------------------------------------------------------------------

_registry: Optional[PluginRegistry] = None


def get_registry(*, force_reload: bool = False) -> PluginRegistry:
    """Return the global :class:`PluginRegistry`, discovering plugins if needed."""
    global _registry  # noqa: PLW0603
    if _registry is None or force_reload:
        _registry = PluginRegistry()
        _registry.discover()
    return _registry
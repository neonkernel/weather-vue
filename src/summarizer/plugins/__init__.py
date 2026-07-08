"""
Plugin subsystem for the summarizer package.

The :class:`PluginRegistry` discovers plugins via Python entry points and
exposes them to the rest of the application.  Three entry-point groups are
supported:

* ``summarizer.extractors``   – subclasses of :class:`~.base.BaseExtractor`
* ``summarizer.postprocessors`` – subclasses of :class:`~.base.BasePostProcessor`
* ``summarizer.formatters``   – subclasses of :class:`~.base.BaseFormatter`

Usage::

    from summarizer.plugins import registry

    # Access all discovered post-processors
    for pp in registry.postprocessors:
        summary = pp.process(summary, original_text)
"""

from __future__ import annotations

import logging
from importlib.metadata import entry_points
from typing import Dict, List, Optional, Type

from .base import BaseExtractor, BaseFormatter, BasePostProcessor

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Entry-point group names
# ---------------------------------------------------------------------------

_EP_EXTRACTORS = "summarizer.extractors"
_EP_POSTPROCESSORS = "summarizer.postprocessors"
_EP_FORMATTERS = "summarizer.formatters"


class PluginLoadError(Exception):
    """Raised when a plugin cannot be loaded or fails validation."""


class PluginRegistry:
    """
    Discovers, loads, and exposes plugins for all three hook types.

    The registry is **lazy**: plugins are not discovered until
    :meth:`discover` is called (or you access one of the public list
    properties, which call :meth:`discover` automatically).

    Attributes:
        extractors: List of instantiated :class:`~.base.BaseExtractor` plugins.
        postprocessors: List of instantiated :class:`~.base.BasePostProcessor` plugins.
        formatters: List of instantiated :class:`~.base.BaseFormatter` plugins.
    """

    def __init__(self) -> None:
        self._extractors: List[BaseExtractor] = []
        self._postprocessors: List[BasePostProcessor] = []
        self._formatters: List[BaseFormatter] = []
        self._discovered: bool = False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def extractors(self) -> List[BaseExtractor]:
        """Return all loaded extractor plugins."""
        if not self._discovered:
            self.discover()
        return list(self._extractors)

    @property
    def postprocessors(self) -> List[BasePostProcessor]:
        """Return all loaded post-processor plugins."""
        if not self._discovered:
            self.discover()
        return list(self._postprocessors)

    @property
    def formatters(self) -> List[BaseFormatter]:
        """Return all loaded formatter plugins."""
        if not self._discovered:
            self.discover()
        return list(self._formatters)

    def discover(self) -> None:
        """
        Discover and load all plugins from installed entry points.

        This method is idempotent; calling it multiple times reloads plugins.
        Errors in individual plugins are logged and skipped so that a single
        bad plugin does not break the whole application.
        """
        self._extractors = self._load_group(_EP_EXTRACTORS, BaseExtractor)  # type: ignore[assignment]
        self._postprocessors = self._load_group(_EP_POSTPROCESSORS, BasePostProcessor)  # type: ignore[assignment]
        self._formatters = self._load_group(_EP_FORMATTERS, BaseFormatter)  # type: ignore[assignment]
        self._discovered = True
        logger.debug(
            "Plugin discovery complete: %d extractors, %d postprocessors, %d formatters",
            len(self._extractors),
            len(self._postprocessors),
            len(self._formatters),
        )

    def get_extractor(self, name: str) -> Optional[BaseExtractor]:
        """Return the first extractor whose :attr:`~.base.BaseExtractor.name` matches *name*."""
        for ext in self.extractors:
            if ext.name == name:
                return ext
        return None

    def get_postprocessor(self, name: str) -> Optional[BasePostProcessor]:
        """Return the first post-processor whose :attr:`~.base.BasePostProcessor.name` matches *name*."""
        for pp in self.postprocessors:
            if pp.name == name:
                return pp
        return None

    def get_formatter(self, name: str) -> Optional[BaseFormatter]:
        """Return the first formatter whose :attr:`~.base.BaseFormatter.name` matches *name*."""
        for fmt in self.formatters:
            if fmt.name == name:
                return fmt
        return None

    def register_extractor(self, extractor: BaseExtractor) -> None:
        """Programmatically register an extractor instance (useful for tests)."""
        _validate_plugin(extractor, BaseExtractor)
        if not self._discovered:
            self.discover()
        self._extractors.append(extractor)

    def register_postprocessor(self, postprocessor: BasePostProcessor) -> None:
        """Programmatically register a post-processor instance (useful for tests)."""
        _validate_plugin(postprocessor, BasePostProcessor)
        if not self._discovered:
            self.discover()
        self._postprocessors.append(postprocessor)

    def register_formatter(self, formatter: BaseFormatter) -> None:
        """Programmatically register a formatter instance (useful for tests)."""
        _validate_plugin(formatter, BaseFormatter)
        if not self._discovered:
            self.discover()
        self._formatters.append(formatter)

    def summary_table(self) -> List[Dict[str, str]]:
        """
        Return a list of dicts suitable for tabular display in the CLI.

        Each dict has keys: ``type``, ``name``, ``version``, ``description``.
        """
        if not self._discovered:
            self.discover()

        rows: List[Dict[str, str]] = []
        for plugin in self._extractors:
            rows.append(_plugin_row("extractor", plugin))
        for plugin in self._postprocessors:
            rows.append(_plugin_row("postprocessor", plugin))
        for plugin in self._formatters:
            rows.append(_plugin_row("formatter", plugin))
        return rows

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _load_group(self, group: str, base_cls: type) -> list:
        loaded: list = []
        eps = _get_entry_points(group)
        for ep in eps:
            try:
                cls = ep.load()
            except Exception as exc:
                logger.warning("Failed to load plugin %r from group %r: %s", ep.name, group, exc)
                continue

            try:
                instance = _instantiate_and_validate(cls, base_cls, ep.name)
            except PluginLoadError as exc:
                logger.warning(str(exc))
                continue

            loaded.append(instance)
            logger.debug("Loaded plugin %r (%s)", ep.name, cls.__qualname__)

        return loaded


# ---------------------------------------------------------------------------
# Module-level singleton registry
# ---------------------------------------------------------------------------

#: The global plugin registry.  Import this object to access plugins.
registry = PluginRegistry()


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _get_entry_points(group: str):
    """
    Return entry points for *group*, compatible with Python 3.9+.

    ``importlib.metadata.entry_points`` accepts a ``group`` keyword argument
    in Python 3.12+ and also in 3.9 via the ``select`` method.
    """
    try:
        # Python 3.12+ / importlib_metadata 3.6+
        return entry_points(group=group)
    except TypeError:
        # Older stdlib fallback
        return entry_points().get(group, [])


def _validate_plugin(instance: object, base_cls: type) -> None:
    """Raise :class:`PluginLoadError` if *instance* is not a valid plugin."""
    if not isinstance(instance, base_cls):
        raise PluginLoadError(
            f"Plugin {instance!r} must be an instance of {base_cls.__name__}."
        )
    if not getattr(instance, "name", ""):
        raise PluginLoadError(
            f"Plugin {instance!r} must define a non-empty 'name' attribute."
        )


def _instantiate_and_validate(cls: type, base_cls: type, ep_name: str) -> object:
    """Instantiate *cls* and validate it against *base_cls*."""
    if not isinstance(cls, type):
        raise PluginLoadError(
            f"Entry point {ep_name!r} must point to a class, got {type(cls).__name__}."
        )
    if not issubclass(cls, base_cls):
        raise PluginLoadError(
            f"Plugin class {cls.__qualname__!r} (entry point {ep_name!r}) must subclass "
            f"{base_cls.__name__}."
        )
    try:
        instance = cls()
    except Exception as exc:
        raise PluginLoadError(
            f"Failed to instantiate plugin {cls.__qualname__!r}: {exc}"
        ) from exc

    _validate_plugin(instance, base_cls)
    return instance


def _plugin_row(type_label: str, plugin: object) -> Dict[str, str]:
    return {
        "type": type_label,
        "name": getattr(plugin, "name", ""),
        "version": getattr(plugin, "version", ""),
        "description": getattr(plugin, "description", ""),
    }
# Plugin Development Guide

This guide explains how to write, package, and distribute custom plugins for
the **summarizer** package using its lightweight entry-point–based plugin
system.

---

## Table of Contents

1. [Architecture overview](#architecture-overview)
2. [Plugin types](#plugin-types)
   - [Extractor](#extractor)
   - [Post-Processor](#post-processor)
   - [Formatter](#formatter)
3. [Writing your first plugin](#writing-your-first-plugin)
4. [Registering via `pyproject.toml`](#registering-via-pyprojecttoml)
5. [Installing and testing locally](#installing-and-testing-locally)
6. [Listing discovered plugins](#listing-discovered-plugins)
7. [Complete example: `sentiment` post-processor](#complete-example-sentiment-post-processor)
8. [Error handling & best practices](#error-handling--best-practices)
9. [API reference](#api-reference)

---

## Architecture overview

```
┌─────────────────────────────────────────────────────────┐
│                     summarizer CLI                      │
│  summarize <url>  ──►  LLM  ──►  PostProcessors  ──►  Output │
└──────────────┬──────────────────────────┬───────────────┘
               │                          │
        PluginRegistry             PluginRegistry
        .extractors                .postprocessors
        .formatters
               ▲                          ▲
  importlib.metadata.entry_points()  (same mechanism)
               │
  [project.entry-points."summarizer.extractors"]
  my_extractor = "mypkg.extractors:MyExtractor"
```

At startup the `PluginRegistry` calls `importlib.metadata.entry_points()` for
each of the three plugin groups and validates that every loaded class is a
proper subclass of the corresponding ABC (`BaseExtractor`,
`BasePostProcessor`, or `BaseFormatter`).

---

## Plugin types

### Extractor

Group key: `summarizer.extractors`  
Base class: `summarizer.plugins.base.BaseExtractor`

An **Extractor** receives a source string (URL or raw HTML) and returns the
plain article text that is forwarded to the LLM.

```python
from summarizer.plugins.base import BaseExtractor

class MyExtractor(BaseExtractor):
    name = "my_extractor"
    description = "Downloads and parses articles from MyBlog."

    def extract(self, source: str) -> str:
        # source is either a URL or raw HTML
        ...
        return plain_text
```

### Post-Processor

Group key: `summarizer.postprocessors`  
Base class: `summarizer.plugins.base.BasePostProcessor`

A **Post-Processor** transforms the `Summary` object *after* the LLM has
generated a response.  Processors are chained sequentially; each receives the
output of the previous one.

```python
from summarizer.plugins.base import BasePostProcessor

class MyPostProcessor(BasePostProcessor):
    name = "my_processor"
    description = "Appends a disclaimer to every summary."

    def process(self, summary, article_text: str = ""):
        disclaimer = "\n\n*This summary was auto-generated.*"
        return summary.model_copy(update={"text": summary.text + disclaimer})
```

### Formatter

Group key: `summarizer.formatters`  
Base class: `summarizer.plugins.base.BaseFormatter`

A **Formatter** serialises a `Summary` object to a string in a custom format
(Markdown, HTML, CSV, …).

```python
from summarizer.plugins.base import BaseFormatter

class MyFormatter(BaseFormatter):
    name = "html"
    description = "Renders summaries as HTML fragments."

    def format(self, summary) -> str:
        return f"<article><p>{summary.text}</p></article>"
```

---

## Writing your first plugin

### 1. Create a Python package

```
my_summarizer_plugins/
├── pyproject.toml
└── src/
    └── my_summarizer_plugins/
        ├── __init__.py
        └── processors.py
```

### 2. Implement the plugin class

```python
# src/my_summarizer_plugins/processors.py
from summarizer.plugins.base import BasePostProcessor


class UpperCaseProcessor(BasePostProcessor):
    """Converts every summary to upper-case (demo only)."""

    name = "uppercase"
    description = "Converts the summary text to upper-case."
    version = "0.1.0"

    def process(self, summary, article_text: str = ""):
        return summary.model_copy(update={"text": summary.text.upper()})
```

### 3. Register the entry point

```toml
# pyproject.toml for my_summarizer_plugins
[project.entry-points."summarizer.postprocessors"]
uppercase = "my_summarizer_plugins.processors:UpperCaseProcessor"
```

---

## Registering via `pyproject.toml`

The full schema for each group is:

```toml
# Custom extractor
[project.entry-points."summarizer.extractors"]
<name> = "<python.module.path>:<ClassName>"

# Custom post-processor
[project.entry-points."summarizer.postprocessors"]
<name> = "<python.module.path>:<ClassName>"

# Custom formatter
[project.entry-points."summarizer.formatters"]
<name> = "<python.module.path>:<ClassName>"
```

- `<name>` must be a unique identifier within its group (snake_case recommended).
- If two plugins share a name the first registered wins; a debug log is emitted.

---

## Installing and testing locally

```bash
# Development install (editable)
pip install -e path/to/my_summarizer_plugins

# Verify the entry point is visible
python -c "
from importlib.metadata import entry_points
eps = entry_points(group='summarizer.postprocessors')
print(list(eps))
"
```

Run the built-in `plugins list` command to confirm:

```bash
summarize plugins list
```

---

## Listing discovered plugins

```bash
# Human-readable table
summarize plugins list

# JSON output (useful for scripting)
summarize plugins list --json

# Detailed info about a single plugin
summarize plugins info keyword_extractor
```

---

## Complete example: `sentiment` post-processor

Below is a complete, runnable example that uses the
[`textblob`](https://textblob.readthedocs.io/) library to attach a sentiment
score to each summary.

### Directory layout

```
summarizer_sentiment/
├── pyproject.toml
└── src/
    └── summarizer_sentiment/
        ├── __init__.py
        └── sentiment.py
```

### `sentiment.py`

```python
"""Sentiment post-processor using TextBlob."""

from summarizer.plugins.base import BasePostProcessor


class SentimentAnalyser(BasePostProcessor):
    """Attaches TextBlob polarity and subjectivity to summary.metadata."""

    name = "sentiment"
    description = "Adds TextBlob sentiment polarity/subjectivity to summary metadata."
    version = "0.1.0"

    def process(self, summary, article_text: str = ""):
        try:
            from textblob import TextBlob  # type: ignore
        except ImportError as exc:
            raise RuntimeError(
                "Install textblob: pip install textblob"
            ) from exc

        blob = TextBlob(summary.text)
        sentiment = {
            "polarity": round(blob.sentiment.polarity, 4),
            "subjectivity": round(blob.sentiment.subjectivity, 4),
        }

        existing = dict(getattr(summary, "metadata", {}) or {})
        existing["sentiment"] = sentiment
        return summary.model_copy(update={"metadata": existing})
```

### `pyproject.toml`

```toml
[project]
name = "summarizer-sentiment"
version = "0.1.0"
dependencies = ["summarizer", "textblob>=0.18"]

[project.entry-points."summarizer.postprocessors"]
sentiment = "summarizer_sentiment.sentiment:SentimentAnalyser"
```

### Usage

```bash
pip install -e ./summarizer_sentiment
summarize plugins list
# → Post-Processors: keyword_extractor, readability, sentiment

summarize summarize https://example.com/article
# summary now has .metadata["sentiment"] = {"polarity": 0.12, "subjectivity": 0.45}
```

---

## Error handling & best practices

| Concern | Recommendation |
|---------|---------------|
| Import errors | Wrap optional imports in `try/except ImportError` and raise `RuntimeError` with a helpful message. |
| Side effects | Keep `__init__` lightweight; defer heavy imports to `process()` / `extract()` / `format()`. |
| Idempotency | Post-processors should be safe to run multiple times. |
| Metadata keys | Use a namespaced key (e.g. `"mypkg.score"`) to avoid clashing with other plugins. |
| Exceptions | Let exceptions propagate; the `PluginRegistry` will log them and skip the processor without crashing the pipeline. |
| Versioning | Set `version` on your class and increment it when the metadata schema changes. |

---

## API reference

### `summarizer.plugins.base.PluginBase`

All plugin ABCs inherit from `PluginBase`.

| Attribute | Type | Description |
|-----------|------|-------------|
| `name` | `str` | Unique identifier (snake_case). |
| `description` | `str` | Human-readable description. |
| `version` | `str` | Semantic version string. |

**Method:** `get_metadata() -> dict` — returns all metadata as a plain dict.

---

### `summarizer.plugins.base.BaseExtractor`

Abstract method:

```python
def extract(self, source: str) -> str: ...
```

---

### `summarizer.plugins.base.BasePostProcessor`

Abstract method:

```python
def process(self, summary: Summary, article_text: str = "") -> Summary: ...
```

---

### `summarizer.plugins.base.BaseFormatter`

Abstract method:

```python
def format(self, summary: Summary) -> str: ...
```

---

### `summarizer.plugins.PluginRegistry`

| Method | Description |
|--------|-------------|
| `discover()` | Load all plugins (built-ins + entry points). |
| `extractors` | `dict[str, type[BaseExtractor]]` |
| `postprocessors` | `dict[str, type[BasePostProcessor]]` |
| `formatters` | `dict[str, type[BaseFormatter]]` |
| `errors` | `list[str]` – load errors that did not abort startup. |
| `list_all()` | Returns a nested dict of all plugins for display. |
| `apply_postprocessors(summary, article_text, *, names)` | Run post-processors and return the transformed summary. |

---

### `summarizer.plugins.get_registry(*, force_reload=False)`

Returns the module-level singleton `PluginRegistry`.  Call
`get_registry(force_reload=True)` in tests to get a fresh instance.
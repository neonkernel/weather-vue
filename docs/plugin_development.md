# Plugin Development Guide

This guide explains how to write, distribute, and test custom plugins for the
**summarizer** package.  Plugins extend the tool without modifying its source
code, making them easy to distribute as standalone PyPI packages.

---

## Overview

The summarizer supports three plugin hook types:

| Hook type | Entry-point group | Base class | Purpose |
|---|---|---|---|
| Extractor | `summarizer.extractors` | `BaseExtractor` | Custom article content fetching |
| Post-processor | `summarizer.postprocessors` | `BasePostProcessor` | Enrich/mutate summaries after the LLM call |
| Formatter | `summarizer.formatters` | `BaseFormatter` | Custom output formats |

Plugins are discovered automatically at startup via Python's
[`importlib.metadata`](https://docs.python.org/3/library/importlib.metadata.html)
entry-points mechanism.

---

## Quick Start: A Complete Plugin Package

The following example creates a post-processor that capitalises every word in
the summary.

### 1. Create the package layout

```
my_summarizer_plugin/
├── pyproject.toml
└── my_summarizer_plugin/
    ├── __init__.py
    └── processors.py
```

### 2. Write the plugin class (`processors.py`)

```python
from summarizer.plugins.base import BasePostProcessor
from typing import Any, Dict, Optional


class TitleCaseProcessor(BasePostProcessor):
    """Converts the summary text to Title Case."""

    name = "title_case"                        # unique identifier
    description = "Converts summary to Title Case."

    def process(
        self,
        summary: Any,
        *,
        article_text: str = "",
        config: Optional[Dict[str, Any]] = None,
    ) -> Any:
        if hasattr(summary, "summary") and summary.summary:
            summary.summary = summary.summary.title()
        return summary
```

### 3. Register the entry point (`pyproject.toml`)

```toml
[build-system]
requires = ["setuptools>=68", "wheel"]
build-backend = "setuptools.backends.legacy:build"

[project]
name = "my-summarizer-plugin"
version = "0.1.0"
dependencies = ["summarizer"]

[project.entry-points."summarizer.postprocessors"]
title_case = "my_summarizer_plugin.processors:TitleCaseProcessor"
```

> The key on the left (`title_case`) is the entry-point name used during
> discovery; it does **not** have to match `cls.name`, although keeping them
> consistent is good practice.

### 4. Install your plugin

```bash
pip install -e .
```

After installation, `summarize plugins list` will show your plugin:

```
Post-Processors (3)
  • keyword_extractor      Extracts top-N keywords …
  • readability_scorer     Computes Flesch Reading Ease …
  • title_case             Converts summary to Title Case.
```

---

## Writing a Custom Extractor

Extractors tell the summarizer how to fetch and parse content from non-standard
sources (e.g. PDF files, internal APIs, S3 buckets).

```python
from summarizer.plugins.base import BaseExtractor
from typing import Any, Dict


class PDFExtractor(BaseExtractor):
    """Extracts text from local PDF files."""

    name = "pdf_extractor"
    description = "Extracts article text from PDF files."

    def can_handle(self, source: str) -> bool:
        return source.lower().endswith(".pdf")

    def extract(self, source: str) -> Dict[str, Any]:
        import pdfplumber  # installed separately
        with pdfplumber.open(source) as pdf:
            text = "\n".join(
                page.extract_text() or "" for page in pdf.pages
            )
        return {
            "title": source,
            "text": text,
            "url": "",
            "html": "",
        }
```

Register it under `summarizer.extractors`:

```toml
[project.entry-points."summarizer.extractors"]
pdf = "my_package.extractors:PDFExtractor"
```

### `extract()` return contract

The dict returned by `extract()` **must** contain at minimum:

| Key | Type | Description |
|-----|------|-------------|
| `title` | `str` | Article title (may be empty) |
| `text` | `str` | Plain-text body |
| `url` | `str` | Canonical URL or empty string |
| `html` | `str` | Raw HTML or empty string |

---

## Writing a Custom Formatter

Formatters control how the final summary is rendered to a string.

```python
from summarizer.plugins.base import BaseFormatter
from typing import Any, Dict, Optional
import json


class JSONLFormatter(BaseFormatter):
    """Outputs each summary as a single JSON-Lines record."""

    name = "jsonl"
    description = "Renders the summary as a JSON-Lines record."
    extension = ".jsonl"

    def format(self, summary: Any, config: Optional[Dict[str, Any]] = None) -> str:
        data = summary.__dict__ if hasattr(summary, "__dict__") else {"summary": str(summary)}
        return json.dumps(data, ensure_ascii=False)
```

Register it under `summarizer.formatters`:

```toml
[project.entry-points."summarizer.formatters"]
jsonl = "my_package.formatters:JSONLFormatter"
```

---

## Built-in Post-Processors

Two post-processors are bundled with the summarizer and registered
automatically (no entry-point declaration required):

### `keyword_extractor`

**Class**: `summarizer.plugins.builtin.keyword_extractor.KeywordExtractor`

Extracts the top-N keywords from the original article text using a
single-document TF-IDF approximation.  No external dependencies needed.

**Adds to summary**:
- `summary.keywords` — `List[str]`

**Configuration** (passed via `--keyword-top-n` CLI flag or `config` dict):
- `keyword_top_n` (int, default `10`) — number of keywords to return.

---

### `readability_scorer`

**Class**: `summarizer.plugins.builtin.readability.ReadabilityScorer`

Computes the [Flesch Reading Ease](https://en.wikipedia.org/wiki/Flesch%E2%80%93Kincaid_readability_tests)
score for the **summary text** (not the article).

**Adds to summary**:
- `summary.readability_score` — `float` in `[0, 100]`
- `summary.readability_label` — `str` e.g. `"Standard"`, `"Easy"`, …

| Score | Label |
|-------|-------|
| 90–100 | Very Easy |
| 80–90  | Easy |
| 70–80  | Fairly Easy |
| 60–70  | Standard |
| 50–60  | Fairly Difficult |
| 30–50  | Difficult |
| 0–30   | Very Confusing |

---

## Plugin Lifecycle

```
summarize <source>
    │
    ├── PluginRegistry.discover()          ← importlib.metadata entry points
    │       ├── _register_builtins()
    │       ├── _load_group("summarizer.extractors", …)
    │       ├── _load_group("summarizer.postprocessors", …)
    │       └── _load_group("summarizer.formatters", …)
    │
    ├── [optional] extractor selection     ← can_handle() called in order
    │
    ├── LLM summarisation
    │
    ├── post-processors (in registration order)
    │       ├── KeywordExtractor.process(summary, article_text=…)
    │       ├── ReadabilityScorer.process(summary)
    │       └── … your plugin …
    │
    └── formatter.format(summary)
```

---

## Error Handling

The `PluginRegistry` logs a warning and **skips** any plugin that:

* fails to load (e.g. missing dependency during `ep.load()`),
* is not a subclass of the declared base ABC.

This means a broken third-party plugin will never prevent the core
summarizer from running.

---

## Testing Your Plugin

A minimal test using `pytest`:

```python
from my_summarizer_plugin.processors import TitleCaseProcessor


class FakeSummary:
    def __init__(self, text):
        self.summary = text


def test_title_case():
    pp = TitleCaseProcessor()
    s = FakeSummary("hello world from the summarizer.")
    result = pp.process(s, article_text="")
    assert result.summary == "Hello World From The Summarizer."
```

To test that your plugin is discoverable after installation:

```python
from summarizer.plugins import PluginRegistry


def test_plugin_discovered():
    reg = PluginRegistry()
    reg.discover()
    assert "title_case" in reg.postprocessors
```

---

## Publishing to PyPI

1. Build: `python -m build`
2. Upload: `twine upload dist/*`

Users install with `pip install my-summarizer-plugin` and the plugin is
active immediately — no configuration changes required.

---

## Reference

### `BaseExtractor`

```python
class BaseExtractor(abc.ABC):
    name: str           # unique plugin identifier
    description: str    # shown in `summarize plugins list`

    def can_handle(self, source: str) -> bool: ...
    def extract(self, source: str) -> Dict[str, Any]: ...
```

### `BasePostProcessor`

```python
class BasePostProcessor(abc.ABC):
    name: str
    description: str

    def process(
        self,
        summary: Any,
        *,
        article_text: str = "",
        config: Optional[Dict[str, Any]] = None,
    ) -> Any: ...
```

### `BaseFormatter`

```python
class BaseFormatter(abc.ABC):
    name: str
    description: str
    extension: str      # e.g. ".html"

    def format(self, summary: Any, config: Optional[Dict[str, Any]] = None) -> str: ...
```
# Plugin Development Guide

This guide explains how to write, package, and distribute plugins for the
**summarizer** package.  Plugins allow you to add custom extraction logic,
post-process summaries, and define new output formats without modifying the
core library.

---

## Table of Contents

1. [Plugin Types](#1-plugin-types)
2. [How Plugins Are Discovered](#2-how-plugins-are-discovered)
3. [Writing a Post-Processor Plugin](#3-writing-a-post-processor-plugin)
4. [Writing an Extractor Plugin](#4-writing-an-extractor-plugin)
5. [Writing a Formatter Plugin](#5-writing-a-formatter-plugin)
6. [Packaging and Distribution](#6-packaging-and-distribution)
7. [Testing Your Plugin](#7-testing-your-plugin)
8. [Built-in Plugins Reference](#8-built-in-plugins-reference)
9. [Complete Example: Sentiment Scorer](#9-complete-example-sentiment-scorer)

---

## 1. Plugin Types

The summarizer package defines three entry-point groups:

| Group | Base Class | Purpose |
|---|---|---|
| `summarizer.extractors` | `BaseExtractor` | Fetch & parse raw article text |
| `summarizer.postprocessors` | `BasePostProcessor` | Enrich or transform a `Summary` after LLM generation |
| `summarizer.formatters` | `BaseFormatter` | Render a `Summary` to a string for output |

---

## 2. How Plugins Are Discovered

The `PluginRegistry` uses Python's built-in
[`importlib.metadata.entry_points`](https://docs.python.org/3/library/importlib.metadata.html)
to discover installed plugins at startup.

When you install a package that declares entry points in the correct groups,
those plugins are automatically loaded the next time `summarize` is invoked.
No configuration file changes are required.

```
┌──────────────────────┐
│   pip install pkg    │  ← installs your wheel / sdist
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│ importlib.metadata   │  ← reads [project.entry-points] from package metadata
│   entry_points()     │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│   PluginRegistry     │  ← instantiates & validates each plugin class
│   .discover()        │
└──────────────────────┘
```

---

## 3. Writing a Post-Processor Plugin

Post-processors receive a `Summary` object *after* the LLM has produced the
text and can add metadata, rewrite the text, or perform any side-effect.

### Minimal example

```python
# my_plugin/sentiment.py

from summarizer.plugins.base import BasePostProcessor
from summarizer.models import Summary


class SentimentScorer(BasePostProcessor):
    """Adds a sentiment score to the summary metadata."""

    name = "sentiment_scorer"
    description = "Scores the sentiment of the summary text"
    version = "0.1.0"

    def process(self, summary: Summary, original_text: str, **kwargs) -> Summary:
        # Perform your analysis here.
        # For illustration we use a trivial heuristic:
        positive_words = {"great", "excellent", "amazing", "good", "best"}
        negative_words = {"bad", "terrible", "awful", "worst", "poor"}

        words = set(summary.text.lower().split())
        pos = len(words & positive_words)
        neg = len(words & negative_words)

        if pos > neg:
            sentiment = "positive"
        elif neg > pos:
            sentiment = "negative"
        else:
            sentiment = "neutral"

        # Always mutate summary.metadata (never replace the Summary object)
        summary.metadata["sentiment"] = sentiment
        return summary
```

### Rules

* **Always return the same `Summary` object** – do not replace it.
* Store additional data in `summary.metadata` (a plain `dict`).
* You may modify `summary.text` but document this behaviour clearly.
* Do not raise uncaught exceptions; wrap errors and degrade gracefully.

---

## 4. Writing an Extractor Plugin

Extractors are responsible for fetching raw article text from a source
(URL, file path, database record, etc.).

```python
# my_plugin/pdf_extractor.py

from summarizer.plugins.base import BaseExtractor


class PdfExtractor(BaseExtractor):
    """Extract text from local PDF files."""

    name = "pdf_extractor"
    description = "Reads plain text from a local PDF using PyMuPDF"
    version = "0.1.0"

    def can_handle(self, source: str) -> bool:
        return source.lower().endswith(".pdf")

    def extract(self, source: str, **kwargs) -> str:
        import fitz  # PyMuPDF – declared as a dependency of your package

        doc = fitz.open(source)
        text_parts = [page.get_text() for page in doc]
        return "\n".join(text_parts)
```

### Rules

* Implement `can_handle` to return `True` only when you are confident your
  extractor can process the source.  The registry uses this to select the
  right extractor.
* Raise a descriptive exception (or your own `ExtractionError` subclass) when
  extraction fails so that the caller can handle it cleanly.

---

## 5. Writing a Formatter Plugin

Formatters render a `Summary` to a string for a particular output target.

```python
# my_plugin/html_formatter.py

from summarizer.plugins.base import BaseFormatter
from summarizer.models import Summary


class HtmlFormatter(BaseFormatter):
    """Renders a summary as a minimal HTML page."""

    name = "html_formatter"
    description = "Renders the summary as an HTML page"
    version = "0.1.0"
    extension = ".html"

    def format(self, summary: Summary, **kwargs) -> str:
        title = summary.title or "Summary"
        keywords = summary.metadata.get("keywords", [])
        kw_html = ", ".join(keywords) if keywords else "N/A"

        return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8"><title>{title}</title></head>
<body>
  <h1>{title}</h1>
  <p>{summary.text}</p>
  <footer><small>Keywords: {kw_html}</small></footer>
</body>
</html>"""
```

---

## 6. Packaging and Distribution

Declare your entry points in `pyproject.toml` (PEP 517/518 standard):

```toml
[project.entry-points."summarizer.postprocessors"]
sentiment_scorer = "my_plugin.sentiment:SentimentScorer"

[project.entry-points."summarizer.extractors"]
pdf_extractor = "my_plugin.pdf_extractor:PdfExtractor"

[project.entry-points."summarizer.formatters"]
html_formatter = "my_plugin.html_formatter:HtmlFormatter"
```

> **Tip:** Entry-point names (the left-hand side, e.g. `sentiment_scorer`)
> must be unique across all installed packages for a given group.  Choose
> descriptive names to avoid collisions.

After running `pip install -e .` (editable install) or uploading to PyPI,
your plugins will be discovered automatically.

### Minimal `pyproject.toml` for a plugin package

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "summarizer-sentiment"
version = "0.1.0"
description = "Sentiment scoring plugin for the summarizer package"
requires-python = ">=3.9"
dependencies = ["summarizer>=0.1.0"]

[project.entry-points."summarizer.postprocessors"]
sentiment_scorer = "summarizer_sentiment.sentiment:SentimentScorer"
```

---

## 7. Testing Your Plugin

You can programmatically register plugins via the `PluginRegistry` API,
which is useful for unit tests without entry-point installation:

```python
# tests/test_sentiment.py

import pytest
from summarizer.models import Summary
from summarizer.plugins import PluginRegistry
from my_plugin.sentiment import SentimentScorer


def test_sentiment_scorer_positive():
    pp = SentimentScorer()
    summary = Summary(text="This is an excellent and amazing article.")
    result = pp.process(summary, original_text="")
    assert result.metadata["sentiment"] == "positive"


def test_sentiment_scorer_in_registry():
    registry = PluginRegistry()
    registry._discovered = True  # skip entry-point scan
    registry.register_postprocessor(SentimentScorer())
    assert registry.get_postprocessor("sentiment_scorer") is not None
```

You can also verify your entry points are registered correctly by running:

```bash
summarize plugins list
```

after installing your package.

---

## 8. Built-in Plugins Reference

The summarizer package ships two built-in post-processors:

### `keyword_extractor`

**Class:** `summarizer.plugins.builtin.keyword_extractor.KeywordExtractor`

Extracts the top-N keywords from the **original article text** using TF-IDF.
Uses `scikit-learn`'s `TfidfVectorizer` when available; falls back to a
pure-Python implementation otherwise.

**Metadata added:**

```python
summary.metadata["keywords"]  # List[str], e.g. ["machine learning", "neural network"]
```

**Constructor parameters:**

| Parameter | Default | Description |
|---|---|---|
| `top_n` | `10` | Number of keywords to extract |

---

### `readability_scorer`

**Class:** `summarizer.plugins.builtin.readability.ReadabilityScorer`

Computes Flesch-Kincaid readability metrics for the **summary text**.
Requires no external dependencies.

**Metadata added:**

```python
summary.metadata["readability_ease"]   # float 0–100 (higher = easier)
summary.metadata["readability_grade"]  # float (US school grade level)
summary.metadata["readability_label"]  # str, e.g. "Easy", "Difficult"
```

---

## 9. Complete Example: Sentiment Scorer

This section walks through the full workflow for creating and distributing
a `summarizer-sentiment` plugin package.

### Project layout

```
summarizer-sentiment/
├── pyproject.toml
├── README.md
└── summarizer_sentiment/
    ├── __init__.py
    └── sentiment.py
```

### `summarizer_sentiment/sentiment.py`

```python
"""Sentiment scoring post-processor for the summarizer package."""

from summarizer.plugins.base import BasePostProcessor
from summarizer.models import Summary


class SentimentScorer(BasePostProcessor):
    name = "sentiment_scorer"
    description = "Classifies the summary sentiment as positive, negative, or neutral"
    version = "0.1.0"

    # Simple word lists – replace with a real model for production use.
    _POSITIVE = frozenset({"great", "excellent", "amazing", "good", "best", "outstanding"})
    _NEGATIVE = frozenset({"bad", "terrible", "awful", "worst", "poor", "dreadful"})

    def process(self, summary: Summary, original_text: str, **kwargs) -> Summary:
        words = set(summary.text.lower().split())
        pos = len(words & self._POSITIVE)
        neg = len(words & self._NEGATIVE)

        summary.metadata["sentiment"] = (
            "positive" if pos > neg else "negative" if neg > pos else "neutral"
        )
        summary.metadata["sentiment_pos_count"] = pos
        summary.metadata["sentiment_neg_count"] = neg
        return summary
```

### `pyproject.toml`

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "summarizer-sentiment"
version = "0.1.0"
description = "Sentiment scoring plugin for the summarizer package"
requires-python = ">=3.9"
dependencies = ["summarizer>=0.1.0"]

[project.entry-points."summarizer.postprocessors"]
sentiment_scorer = "summarizer_sentiment.sentiment:SentimentScorer"
```

### Installation and verification

```bash
# Install your plugin in development mode
pip install -e .

# Verify it appears in the registry
summarize plugins list
# +--------------+-------------------+---------+----------------------------------------------+
# | TYPE         | NAME              | VERSION | DESCRIPTION                                  |
# +--------------+-------------------+---------+----------------------------------------------+
# | postprocessor| keyword_extractor | 1.0.0   | Extracts top-N keywords from the original... |
# | postprocessor| readability_scorer| 1.0.0   | Computes Flesch-Kincaid readability scores...|
# | postprocessor| sentiment_scorer  | 0.1.0   | Classifies the summary sentiment as posit... |
# +--------------+-------------------+---------+----------------------------------------------+

# Run a summary with your plugin applied automatically
summarize run --text "This is an excellent article about machine learning."
```

---

*For questions or to share your plugin with the community, please open an
issue or pull request on the project repository.*
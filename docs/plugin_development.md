# Plugin Development Guide

This guide explains how to write, package, and distribute custom plugins for the **Summarizer** tool.

---

## Overview

Summarizer supports three categories of plugins, each registered via Python [entry points](https://packaging.python.org/en/latest/specifications/entry-points/):

| Category | Entry-point group | Base class | Purpose |
|---|---|---|---|
| Extractors | `summarizer.extractors` | `BaseExtractor` | Custom HTML-to-text extraction logic |
| Post-processors | `summarizer.postprocessors` | `BasePostProcessor` | Transforms / annotates a `Summary` after the LLM step |
| Formatters | `summarizer.formatters` | `BaseFormatter` | Custom output formats (HTML, CSV, …) |

Plugins are discovered automatically at startup via `importlib.metadata.entry_points()`. No configuration file or import hook is required – just install your package and run `summarizer`.

---

## Quick-start: writing a post-processor

### 1. Create your package

```
my_summarizer_plugin/
    __init__.py
    sentiment.py
pyproject.toml
```

### 2. Implement `BasePostProcessor`

```python
# my_summarizer_plugin/sentiment.py

from summarizer.plugins.base import BasePostProcessor


class SentimentAnalyzer(BasePostProcessor):
    """Attaches a naive sentiment score to each summary."""

    name = "sentiment_analyzer"
    description = "Adds a positive/negative/neutral sentiment label to the summary."

    def process(self, summary, article_text: str):
        text = getattr(summary, "summary", "") or ""
        # Replace with a real sentiment model as needed
        positive_words = {"great", "excellent", "good", "positive", "success"}
        negative_words = {"bad", "terrible", "poor", "negative", "failure"}

        tokens = set(text.lower().split())
        pos = len(tokens & positive_words)
        neg = len(tokens & negative_words)

        if pos > neg:
            label = "positive"
        elif neg > pos:
            label = "negative"
        else:
            label = "neutral"

        if summary.metadata is None:
            summary.metadata = {}
        summary.metadata["sentiment"] = label
        return summary
```

**Rules for implementing a plugin:**

- Subclass the appropriate base class (`BaseExtractor`, `BasePostProcessor`, or `BaseFormatter`).
- Set `name` to a unique snake_case string – this is how the registry identifies your plugin.
- Set `description` to a short human-readable sentence.
- Implement the required abstract method(s) (see API reference below).
- Do **not** call `super().__init__()` unless you need it – the default `__init__` does nothing.

### 3. Register via entry points

In your `pyproject.toml`:

```toml
[project.entry-points."summarizer.postprocessors"]
sentiment_analyzer = "my_summarizer_plugin.sentiment:SentimentAnalyzer"
```

The key (`sentiment_analyzer`) is just a label – the registry uses `plugin.name` for identification. By convention, keep both identical.

### 4. Install and verify

```bash
pip install -e .          # or: pip install my-summarizer-plugin
summarizer plugins list
```

You should see your plugin listed under **Post-Processors**.

---

## Writing a custom Extractor

Extractors let you replace the built-in HTML extraction for specific sites.

```python
from summarizer.plugins.base import BaseExtractor
from bs4 import BeautifulSoup


class MediumExtractor(BaseExtractor):
    name = "medium_extractor"
    description = "Extracts article text from Medium.com pages."

    def supports(self, url: str) -> bool:
        return "medium.com" in url

    def extract(self, url: str, raw_html: str) -> dict:
        soup = BeautifulSoup(raw_html, "html.parser")
        article = soup.find("article")
        text = article.get_text(separator="\n") if article else ""
        title_tag = soup.find("h1")
        title = title_tag.get_text() if title_tag else ""
        return {
            "text": text,
            "title": title,
        }
```

Register in `pyproject.toml`:

```toml
[project.entry-points."summarizer.extractors"]
medium_extractor = "my_package.extractors:MediumExtractor"
```

**The registry calls `extractor.supports(url)` and uses the first extractor that returns `True`.**
If no extractor claims a URL, the built-in extraction pipeline is used.

Return dict keys:

| Key | Required | Description |
|---|---|---|
| `text` | ✅ | The main article text |
| `title` | ❌ | Article title |
| `author` | ❌ | Author name(s) |
| `published_date` | ❌ | ISO 8601 date string |

---

## Writing a custom Formatter

```python
import csv
import io
from summarizer.plugins.base import BaseFormatter


class CsvFormatter(BaseFormatter):
    name = "csv"
    description = "Renders the summary as a single-row CSV."
    extension = "csv"

    def format(self, summary) -> str:
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(["url", "title", "summary"])
        writer.writerow([
            getattr(summary, "url", ""),
            getattr(summary, "title", ""),
            getattr(summary, "summary", ""),
        ])
        return buf.getvalue()
```

Register in `pyproject.toml`:

```toml
[project.entry-points."summarizer.formatters"]
csv = "my_package.formatters:CsvFormatter"
```

Use it on the command line:

```bash
summarizer summarize https://example.com/article --format csv
```

---

## API Reference

### `BaseExtractor`

| Member | Type | Description |
|---|---|---|
| `name` | `str` | Unique identifier |
| `description` | `str` | Human-readable description |
| `extract(url, raw_html)` | `abstractmethod` | Returns a `dict` with at least `"text"` |
| `supports(url)` | `method` | Returns `True` if this extractor handles the URL (default: always `True`) |

### `BasePostProcessor`

| Member | Type | Description |
|---|---|---|
| `name` | `str` | Unique identifier |
| `description` | `str` | Human-readable description |
| `process(summary, article_text)` | `abstractmethod` | Mutates / wraps `summary`; must return the `Summary` object |

### `BaseFormatter`

| Member | Type | Description |
|---|---|---|
| `name` | `str` | Unique identifier |
| `description` | `str` | Human-readable description |
| `extension` | `str` | File extension (e.g. `"html"`) |
| `format(summary)` | `abstractmethod` | Returns a string |

---

## Built-in plugins

Summarizer ships with two built-in post-processors:

### `keyword_extractor`

Extracts the top N keywords from the article using TF-IDF and stores them in `summary.metadata["keywords"]`.

```python
# Result:
summary.metadata["keywords"]  # → ["machine", "learning", "neural", ...]
```

Configurable `top_n` (default: 10). No external dependencies.

### `readability_scorer`

Computes [Flesch Reading Ease](https://en.wikipedia.org/wiki/Flesch%E2%80%93Kincaid_readability_tests) and Flesch-Kincaid Grade Level for the summary text.

```python
# Result:
summary.metadata["readability"]
# → {
#     "flesch_reading_ease": 72.3,
#     "flesch_kincaid_grade": 8.1,
#     "label": "Fairly Easy",
# }
```

No external dependencies.

---

## Error handling

- If a plugin fails to **load** (import error, wrong base class, etc.), a warning is logged and discovery continues.
- If a plugin fails during **execution** (`process`, `extract`, `format`), the CLI logs a warning and proceeds without that plugin's output.
- Duplicate plugin names (same `name` attribute) are silently deduplicated – the first one registered wins.

---

## Testing your plugin

```python
# tests/test_my_plugin.py

from my_summarizer_plugin.sentiment import SentimentAnalyzer
from unittest.mock import MagicMock


def test_sentiment_positive():
    analyzer = SentimentAnalyzer()
    summary = MagicMock()
    summary.summary = "This is an excellent and great article about success."
    summary.metadata = {}
    result = analyzer.process(summary, article_text="...")
    assert result.metadata["sentiment"] == "positive"
```

Run your tests normally with `pytest`. You do not need to install your package in editable mode to run unit tests – just ensure `summarizer` itself is installed.

---

## Distribution

Publish your plugin to PyPI like any other package:

```bash
python -m build
twine upload dist/*
```

Users install it with:

```bash
pip install my-summarizer-plugin
```

Plugin discovery is automatic after installation – no configuration required.

**Naming convention:** use the prefix `summarizer-` for your PyPI package name (e.g. `summarizer-sentiment-analyzer`) so users can find plugins easily.
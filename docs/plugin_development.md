# Plugin Development Guide

This guide explains how to write, package, and distribute custom plugins for the
`summarizer` package.  Plugins allow you to extend summarizer's behaviour in
three ways:

| Plugin Type       | Entry-point group              | Purpose                                          |
|-------------------|-------------------------------|--------------------------------------------------|
| Extractor         | `summarizer.extractors`        | Custom article fetching / parsing logic          |
| Post-processor    | `summarizer.postprocessors`    | Transform / enrich the summary after LLM output  |
| Formatter         | `summarizer.formatters`        | Render a summary in a custom output format       |

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Project Layout](#project-layout)
3. [Writing a Post-Processor](#writing-a-post-processor)
4. [Writing an Extractor](#writing-an-extractor)
5. [Writing a Formatter](#writing-a-formatter)
6. [Registering Plugins via Entry Points](#registering-plugins-via-entry-points)
7. [Installing Your Plugin](#installing-your-plugin)
8. [Verifying Discovery](#verifying-discovery)
9. [Built-in Plugins](#built-in-plugins)
10. [Testing Your Plugin](#testing-your-plugin)
11. [Error Handling & Best Practices](#error-handling--best-practices)
12. [Full Example](#full-example)

---

## Quick Start

```bash
# Create a new plugin package
mkdir summarizer-sentiment-plugin
cd summarizer-sentiment-plugin

# Install summarizer so the base classes are importable
pip install summarizer

# Create the plugin module
touch summarizer_sentiment/__init__.py
touch summarizer_sentiment/plugin.py
touch pyproject.toml
```

---

## Project Layout

```
summarizer-sentiment-plugin/
├── pyproject.toml                  ← declares entry points
├── README.md
└── summarizer_sentiment/
    ├── __init__.py
    └── plugin.py                   ← your plugin class lives here
```

---

## Writing a Post-Processor

Post-processors receive the `Summary` object produced by the LLM client (and
optionally the raw article text) and may augment it in place.  They are applied
automatically when running `summarize url` or `summarize batch`.

```python
# summarizer_sentiment/plugin.py
from typing import Any, Optional
from summarizer.plugins.base import BasePostProcessor


class SentimentAnalyser(BasePostProcessor):
    """Adds a sentiment label to every summary."""

    name: str = "sentiment_analyser"
    description: str = "Adds positive/negative/neutral sentiment to the summary."

    def process(self, summary: Any, article_text: Optional[str] = None) -> Any:
        """
        Analyse the sentiment of the summary text and attach it.

        Args:
            summary: The summary object (has at least a .summary str attribute).
            article_text: The original article, if available.

        Returns:
            The augmented summary object.
        """
        text = getattr(summary, "summary", "") or ""
        # Replace with your real sentiment model:
        sentiment = self._analyse(text)
        summary.sentiment = sentiment
        return summary

    def _analyse(self, text: str) -> str:
        positive_words = {"great", "excellent", "good", "positive", "happy"}
        negative_words = {"bad", "terrible", "poor", "negative", "sad"}
        words = set(text.lower().split())
        pos = len(words & positive_words)
        neg = len(words & negative_words)
        if pos > neg:
            return "positive"
        if neg > pos:
            return "negative"
        return "neutral"
```

### Required interface

```python
class BasePostProcessor(ABC):
    name: str = ""          # shown in `plugins list`
    description: str = ""   # shown in `plugins list`

    @abstractmethod
    def process(self, summary: Any, article_text: Optional[str] = None) -> Any:
        ...
```

---

## Writing an Extractor

Extractors fetch and parse raw content from a URL.  The registry calls
`can_handle()` on each extractor in registration order and uses the first one
that returns `True`.

```python
# summarizer_paywalled/extractor.py
from summarizer.plugins.base import BaseExtractor


class PaywallExtractor(BaseExtractor):
    """Extracts articles from paywalled news sites using a custom API."""

    name: str = "paywall_extractor"
    description: str = "Extracts paywalled articles via a bypass API."

    SUPPORTED_DOMAINS = {"example-news.com", "premium-press.com"}

    def can_handle(self, url: str) -> bool:
        from urllib.parse import urlparse
        domain = urlparse(url).netloc.lstrip("www.")
        return domain in self.SUPPORTED_DOMAINS

    def extract(self, url: str) -> str:
        import httpx
        # Call your bypass API / scraper here
        response = httpx.get(f"https://my-api.example.com/extract?url={url}")
        response.raise_for_status()
        return response.json()["text"]
```

### Required interface

```python
class BaseExtractor(ABC):
    name: str = ""
    description: str = ""

    @abstractmethod
    def can_handle(self, url: str) -> bool: ...

    @abstractmethod
    def extract(self, url: str) -> str: ...
```

---

## Writing a Formatter

Formatters convert a `Summary` object into a string.  Use them to produce HTML,
Markdown, CSV, or any other format.

```python
# summarizer_html_fmt/formatter.py
from summarizer.plugins.base import BaseFormatter
from typing import Any


class HtmlFormatter(BaseFormatter):
    """Renders summaries as an HTML fragment."""

    name: str = "html"
    description: str = "Renders the summary as an HTML <article> element."
    extension: str = ".html"

    def format(self, summary: Any) -> str:
        title = getattr(summary, "title", "Summary")
        body = getattr(summary, "summary", str(summary))
        keywords = getattr(summary, "keywords", [])
        kw_html = ", ".join(f"<code>{k}</code>" for k in keywords)
        return (
            f"<article>\n"
            f"  <h1>{title}</h1>\n"
            f"  <p>{body}</p>\n"
            f"  <footer>Keywords: {kw_html}</footer>\n"
            f"</article>"
        )
```

### Required interface

```python
class BaseFormatter(ABC):
    name: str = ""
    description: str = ""
    extension: str = ".txt"   # file extension hint used by the CLI

    @abstractmethod
    def format(self, summary: Any) -> str: ...
```

---

## Registering Plugins via Entry Points

Add the following to your package's **`pyproject.toml`**:

```toml
[project.entry-points."summarizer.postprocessors"]
sentiment_analyser = "summarizer_sentiment.plugin:SentimentAnalyser"

# For an extractor:
[project.entry-points."summarizer.extractors"]
paywall_extractor = "summarizer_paywalled.extractor:PaywallExtractor"

# For a formatter:
[project.entry-points."summarizer.formatters"]
html = "summarizer_html_fmt.formatter:HtmlFormatter"
```

The key on the left (e.g. `sentiment_analyser`) is the entry-point name used
during discovery.  The value must be an importable path in the form
`module.path:ClassName`.

> **Supported groups**
>
> | Group                          | Base class            |
> |--------------------------------|-----------------------|
> | `summarizer.extractors`        | `BaseExtractor`       |
> | `summarizer.postprocessors`    | `BasePostProcessor`   |
> | `summarizer.formatters`        | `BaseFormatter`       |

---

## Installing Your Plugin

```bash
# Development (editable) install
pip install -e .

# Or publish to PyPI and install normally
pip install summarizer-sentiment-plugin
```

Once installed, the plugin is automatically discovered the next time the
summarizer runs.

---

## Verifying Discovery

After installation, use the built-in CLI command to confirm your plugin appears:

```bash
# List all discovered plugins
summarize plugins list

# Filter by type
summarize plugins list --type postprocessors

# Machine-readable JSON output
summarize plugins list --json
```

Example output:

```
Discovered plugins (3 total)
============================================================

Extractors (0)
----------------------------------------
  (none)

Post-Processors (3)
----------------------------------------
  • keyword_extractor
      Extracts the top-N keywords from the original article using TF-IDF.
      [summarizer.plugins.builtin.keyword_extractor.KeywordExtractor]
  • readability_scorer
      Computes Flesch-Kincaid readability metrics for the summary text.
      [summarizer.plugins.builtin.readability.ReadabilityScorer]
  • sentiment_analyser
      Adds positive/negative/neutral sentiment to the summary.
      [summarizer_sentiment.plugin.SentimentAnalyser]

Formatters (0)
----------------------------------------
  (none)
```

---

## Built-in Plugins

The `summarizer` package ships two built-in post-processors:

### `keyword_extractor`

- **Class**: `summarizer.plugins.builtin.keyword_extractor.KeywordExtractor`
- **What it does**: Extracts the top-N keywords from the original article text
  using a self-contained TF-IDF implementation.  Falls back to the summary text
  if the article is unavailable.  Attaches results as `summary.keywords`.
- **Configuration**: Pass `top_n=15` at instantiation (default: 10).
- **NLTK integration**: If `nltk` is installed and the `stopwords` corpus is
  available, it is used automatically; otherwise a built-in English stop-word
  list is used.

### `readability_scorer`

- **Class**: `summarizer.plugins.builtin.readability.ReadabilityScorer`
- **What it does**: Computes Flesch Reading Ease and Flesch-Kincaid Grade Level
  scores for the summary text.  Attaches a `ReadabilityResult` dataclass as
  `summary.readability`.
- **No external dependencies**: Pure-Python syllable counting heuristic.

---

## Testing Your Plugin

We recommend testing your plugin in isolation before publishing:

```python
# tests/test_my_plugin.py
import pytest
from summarizer_sentiment.plugin import SentimentAnalyser


class StubSummary:
    def __init__(self, text):
        self.summary = text


def test_positive_sentiment():
    pp = SentimentAnalyser()
    s = StubSummary("This is a great and excellent product!")
    result = pp.process(s)
    assert result.sentiment == "positive"


def test_negative_sentiment():
    pp = SentimentAnalyser()
    s = StubSummary("This is a terrible and bad experience.")
    result = pp.process(s)
    assert result.sentiment == "negative"


def test_neutral_sentiment():
    pp = SentimentAnalyser()
    s = StubSummary("The sky is blue.")
    result = pp.process(s)
    assert result.sentiment == "neutral"


def test_process_returns_summary():
    """process() must return the summary object."""
    pp = SentimentAnalyser()
    s = StubSummary("hello")
    result = pp.process(s)
    assert result is s


def test_plugin_is_registered_after_install():
    """Integration test: verify entry-point discovery works."""
    from summarizer.plugins import PluginRegistry
    registry = PluginRegistry()
    registry.load()
    pp = registry.get_postprocessor("sentiment_analyser")
    assert pp is not None
    assert isinstance(pp, SentimentAnalyser)
```

Run your tests:

```bash
# Install in editable mode first so entry points are registered
pip install -e .
pytest tests/
```

---

## Error Handling & Best Practices

### Graceful degradation

If your plugin has optional dependencies (e.g. a heavy ML model), handle
`ImportError` gracefully:

```python
class MyMLPostProcessor(BasePostProcessor):
    name = "my_ml_processor"
    description = "Uses a transformer model (requires `transformers`)."

    def __init__(self):
        try:
            from transformers import pipeline  # type: ignore
            self._pipe = pipeline("sentiment-analysis")
        except ImportError:
            self._pipe = None

    def process(self, summary, article_text=None):
        if self._pipe is None:
            return summary  # skip silently
        summary.ml_sentiment = self._pipe(summary.summary)[0]["label"]
        return summary
```

### Always return the summary

`process()` **must** return the summary object (even if unchanged).  The
registry chains post-processors and each one receives the output of the
previous one.

### Thread safety

Post-processor instances are shared across calls.  Do not store per-request
state on `self`.

### Name uniqueness

Choose a `name` that is unlikely to clash with other plugins.  We recommend
prefixing it with your organisation or package name (e.g.
`"acme_sentiment_analyser"`).

### `can_handle` must not raise

Extractor `can_handle()` is called speculatively.  Any exception inside it is
caught and logged as a warning, and the extractor is skipped.  Keep it fast
and side-effect-free.

---

## Full Example

Below is a complete, self-contained plugin package that adds a word-count
post-processor.

**`pyproject.toml`**

```toml
[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.backends.legacy:build"

[project]
name = "summarizer-wordcount-plugin"
version = "0.1.0"
description = "Adds word count to summarizer summaries"
requires-python = ">=3.10"
dependencies = ["summarizer"]

[project.entry-points."summarizer.postprocessors"]
word_count = "summarizer_wordcount.plugin:WordCountProcessor"
```

**`summarizer_wordcount/__init__.py`**

```python
# (empty)
```

**`summarizer_wordcount/plugin.py`**

```python
import re
from typing import Any, Optional
from summarizer.plugins.base import BasePostProcessor


class WordCountProcessor(BasePostProcessor):
    """Attaches the word count of the summary as summary.word_count."""

    name: str = "word_count"
    description: str = "Counts words in the summary and attaches as summary.word_count."

    def process(self, summary: Any, article_text: Optional[str] = None) -> Any:
        text = getattr(summary, "summary", "") or ""
        summary.word_count = len(re.findall(r"\b\w+\b", text))
        return summary
```

**Install and verify**

```bash
pip install -e .
summarize plugins list --type postprocessors
# → word_count should appear in the list
```

That's it!  Your plugin is now automatically applied every time a summary is
generated.
# Summarizer Plugin Development Guide

This guide explains how to write, package, and distribute custom plugins for the
`summarizer` tool. Plugins let you extend the tool's behaviour — adding new
article extractors, post-processing steps, or output formats — **without
modifying the core package source**.

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Plugin Hook Types](#2-plugin-hook-types)
3. [Writing a Plugin Package](#3-writing-a-plugin-package)
4. [Complete Example: Sentiment Post-Processor](#4-complete-example-sentiment-post-processor)
5. [Registering Plugins via Entry Points](#5-registering-plugins-via-entry-points)
6. [Testing Your Plugin](#6-testing-your-plugin)
7. [Discovering Installed Plugins](#7-discovering-installed-plugins)
8. [Built-in Plugins Reference](#8-built-in-plugins-reference)
9. [FAQ & Troubleshooting](#9-faq--troubleshooting)

---

## 1. Architecture Overview

```
┌────────────────────────────────────────────────────┐
│                   summarizer CLI                   │
│                                                    │
│  1. Fetch article                                  │
│  2. (optional) Custom Extractor                    │
│  3. LLM → Summary object                          │
│  4. Post-processors (in registration order)        │
│  5. Formatter → string output                      │
└────────────────────────────────────────────────────┘
```

The `PluginRegistry` discovers plugins at startup by reading **Python package
entry points** (see [PEP 517 / importlib.metadata][1]).  It validates each class
against the appropriate ABC and stores a single instance per plugin name.

[1]: https://docs.python.org/3/library/importlib.metadata.html#entry-points

---

## 2. Plugin Hook Types

| Hook Group | Base Class | Purpose |
|---|---|---|
| `summarizer.extractors` | `BaseExtractor` | Custom article fetching / parsing |
| `summarizer.postprocessors` | `BasePostProcessor` | Enrich Summary after LLM response |
| `summarizer.formatters` | `BaseFormatter` | Custom output string formatting |

All base classes live in `summarizer.plugins.base`.

---

## 3. Writing a Plugin Package

A plugin is a regular Python package that:

1. Contains one or more classes that subclass a `Base*` ABC.
2. Declares entry points under one of the `summarizer.*` groups in its
   `pyproject.toml`.

### Minimal directory layout

```
my-summarizer-plugin/
├── pyproject.toml
├── README.md
└── src/
    └── my_plugin/
        ├── __init__.py
        └── my_processor.py
```

### Install alongside summarizer

```bash
pip install -e .          # install your plugin in development mode
pip install summarizer    # ensure the core package is also installed
```

Once both packages are installed, `summarize plugins list` will show your plugin.

---

## 4. Complete Example: Sentiment Post-Processor

This example adds a simple sentiment label to every summary using
[TextBlob](https://textblob.readthedocs.io/).

### `src/my_plugin/sentiment.py`

```python
"""Sentiment analysis post-processor for summarizer."""
from __future__ import annotations

from summarizer.models import Summary
from summarizer.plugins.base import BasePostProcessor


class SentimentPostProcessor(BasePostProcessor):
    """Adds a sentiment label to summary.metadata['sentiment']."""

    name = "sentiment_analyzer"
    description = "Uses TextBlob to label summary sentiment as positive/negative/neutral."

    def process(self, summary: Summary, article_text: str = "") -> Summary:
        try:
            from textblob import TextBlob  # soft dependency
        except ImportError:
            return summary  # gracefully skip if TextBlob not installed

        text = getattr(summary, "summary", "") or ""
        if not text.strip():
            return summary

        polarity = TextBlob(text).sentiment.polarity

        if polarity > 0.1:
            label = "positive"
        elif polarity < -0.1:
            label = "negative"
        else:
            label = "neutral"

        if summary.metadata is None:
            summary.metadata = {}

        summary.metadata["sentiment"] = {
            "label": label,
            "polarity": round(polarity, 4),
        }
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
description = "Sentiment analysis plugin for summarizer"
requires-python = ">=3.9"
dependencies = [
    "summarizer",
    "textblob>=0.17",
]

[project.entry-points."summarizer.postprocessors"]
sentiment_analyzer = "my_plugin.sentiment:SentimentPostProcessor"

[tool.hatch.build.targets.wheel]
packages = ["src/my_plugin"]
```

After `pip install -e .`, run:

```bash
summarize plugins list
# → Post-Processors:
#     • sentiment_analyzer
#       Uses TextBlob to label summary sentiment as positive/negative/neutral.
```

---

## 5. Registering Plugins via Entry Points

Entry points are the standard Python mechanism for plugin discovery.  They are
defined in the **plugin package's** `pyproject.toml` (not the core package).

### Syntax

```toml
[project.entry-points."<group>"]
<name> = "<module.path>:<ClassName>"
```

### The three groups

| Group | Base class |
|---|---|
| `summarizer.extractors` | `BaseExtractor` |
| `summarizer.postprocessors` | `BasePostProcessor` |
| `summarizer.formatters` | `BaseFormatter` |

### Example — registering all three types

```toml
[project.entry-points."summarizer.extractors"]
pdf_extractor = "my_plugin.pdf:PdfExtractor"

[project.entry-points."summarizer.postprocessors"]
sentiment_analyzer = "my_plugin.sentiment:SentimentPostProcessor"

[project.entry-points."summarizer.formatters"]
html_formatter = "my_plugin.html_fmt:HtmlFormatter"
```

> **Tip:** The `name` on the left-hand side must be unique across all installed
> plugins of the same type.  Duplicate names produce a warning and the last one
> registered wins.

---

## 6. Testing Your Plugin

You can test your plugin without registering entry points by using the
programmatic registration API:

```python
from summarizer.plugins import PluginRegistry

# Create an isolated registry (no auto-discovery)
registry = PluginRegistry(autoload=False)

# Register your class directly
from my_plugin.sentiment import SentimentPostProcessor
registry.register_postprocessor(SentimentPostProcessor)

# Run it
from unittest.mock import MagicMock
summary = MagicMock()
summary.summary = "The company reported record profits this quarter."
summary.metadata = {}

pp = registry.get_postprocessor("sentiment_analyzer")
result = pp.process(summary)
assert result.metadata["sentiment"]["label"] == "positive"
```

### Full test example

```python
import pytest
from summarizer.plugins import PluginRegistry, PluginLoadError
from my_plugin.sentiment import SentimentPostProcessor


def test_sentiment_registered():
    reg = PluginRegistry(autoload=False)
    reg.register_postprocessor(SentimentPostProcessor)
    assert reg.get_postprocessor("sentiment_analyzer") is not None


def test_sentiment_not_subclass_raises():
    class FakeProcessor:
        pass

    reg = PluginRegistry(autoload=False)
    with pytest.raises(PluginLoadError, match="BasePostProcessor"):
        reg.register_postprocessor(FakeProcessor)


def test_sentiment_process():
    pp = SentimentPostProcessor()
    from unittest.mock import MagicMock
    summary = MagicMock()
    summary.summary = "Excellent results exceeded all expectations."
    summary.metadata = {}
    result = pp.process(summary)
    assert result.metadata["sentiment"]["label"] == "positive"
```

---

## 7. Discovering Installed Plugins

```bash
# Human-readable table
summarize plugins list

# JSON output (useful for tooling / CI)
summarize plugins list --json
```

Sample output:

```
Discovered 3 plugin(s):

  Extractors:
    (none)

  Post-Processors:
    • keyword_extractor
      Extracts the top-N keywords from the article using TF-IDF scoring ...
      class: summarizer.plugins.builtin.keyword_extractor.KeywordExtractor
    • readability_scorer
      Computes Flesch Reading Ease and Flesch-Kincaid Grade Level ...
      class: summarizer.plugins.builtin.readability.ReadabilityScorer

  Formatters:
    (none)
```

---

## 8. Built-in Plugins Reference

### `KeywordExtractor` (post-processor)

**Entry point:** `keyword_extractor`  
**Module:** `summarizer.plugins.builtin.keyword_extractor`

Extracts the top-N keywords from the **original article text** using a
TF-IDF-style approach (no external dependencies required; NLTK stopwords used
when available).

**Output** (added to `summary.metadata["keywords"]`):

```python
[
    {"term": "machine", "score": 0.042},
    {"term": "learning", "score": 0.038},
    ...
]
```

**Constructor arguments:**

| Parameter | Default | Description |
|---|---|---|
| `top_n` | `10` | Maximum number of keywords to return |

---

### `ReadabilityScorer` (post-processor)

**Entry point:** `readability_scorer`  
**Module:** `summarizer.plugins.builtin.readability`

Computes Flesch Reading Ease and Flesch-Kincaid Grade Level for the **summary
text** using only the Python standard library.

**Output** (added to `summary.metadata["readability"]`):

```python
{
    "flesch_ease": 72.4,         # 0–100; higher = easier to read
    "flesch_kincaid_grade": 8.2, # US school grade level
    "label": "Fairly Easy",      # human-readable difficulty
    "word_count": 45,
    "sentence_count": 3,
    "syllable_count": 62
}
```

**Flesch Reading Ease score interpretation:**

| Score | Difficulty |
|---|---|
| 90–100 | Very Easy (5th grade) |
| 80–90 | Easy |
| 70–80 | Fairly Easy |
| 60–70 | Standard |
| 50–60 | Fairly Difficult |
| 30–50 | Difficult |
| 0–30 | Very Confusing |

---

## 9. FAQ & Troubleshooting

**Q: My plugin doesn't appear in `summarize plugins list`.**

A: Make sure the package is installed in the same Python environment as
`summarizer`. Run `pip show my-plugin-package` to confirm.  If installed,
check that the entry point group name matches exactly (case-sensitive).

---

**Q: I get `PluginLoadError: ... is not a subclass of BasePostProcessor`.**

A: Ensure you are importing `BasePostProcessor` from
`summarizer.plugins.base` and that your class directly or indirectly inherits
from it.

---

**Q: Can I register multiple plugins from one package?**

A: Yes. Add multiple entries under the same group:

```toml
[project.entry-points."summarizer.postprocessors"]
my_first  = "my_package.processors:FirstProcessor"
my_second = "my_package.processors:SecondProcessor"
```

---

**Q: How do I control the order post-processors run in?**

A: Post-processors are applied in the order they are returned by
`registry.get_postprocessors()`, which reflects the order they were registered
(insertion order). For deterministic ordering across multiple packages, prefer
a single plugin package that chains processors explicitly.

---

**Q: Can I use async code in a plugin?**

A: The `BasePostProcessor.process()` and `BaseExtractor.extract()` signatures
are synchronous.  If you need async I/O, run it inside the method using
`asyncio.run()` or `nest_asyncio`.  A future version of summarizer may add
async plugin hooks.

---

**Q: Where should I handle import errors for optional dependencies?**

A: Import soft dependencies *inside* the method that uses them, and return the
summary unchanged if the import fails.  This way the plugin degrades gracefully:

```python
def process(self, summary, article_text=""):
    try:
        import some_optional_library
    except ImportError:
        return summary   # skip silently
    # ... use the library
```
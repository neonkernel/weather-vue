# Plugin Development Guide

This guide explains how to write, package, and distribute custom plugins for
the **summarizer** package.

## Overview

The summarizer plugin system is built on Python's standard
[`importlib.metadata`](https://docs.python.org/3/library/importlib.metadata.html)
entry points mechanism.  You can extend the summarizer without forking or
modifying the core package by:

1. Creating a Python package that subclasses one of the provided ABCs.
2. Declaring an entry point in your package's `pyproject.toml`.
3. Installing your package in the same virtual environment as summarizer.

---

## Plugin Hook Types

| Entry point group           | Base class              | Purpose |
|-----------------------------|-------------------------|---------|
| `summarizer.extractors`     | `BaseExtractor`         | Custom article extraction logic (e.g. paywalled sites, PDFs) |
| `summarizer.postprocessors` | `BasePostProcessor`     | Enrich / transform a `Summary` after LLM generation |
| `summarizer.formatters`     | `BaseFormatter`         | Produce custom output formats (Slack, HTML, database …) |

---

## Base Classes

All base classes live in `summarizer.plugins.base`.

### `BaseExtractor`

```python
from summarizer.plugins.base import BaseExtractor

class MyExtractor(BaseExtractor):
    name = "my_extractor"
    description = "Extracts content from my-site.example.com."

    def can_handle(self, url: str) -> bool:
        """Return True when this extractor should be used."""
        return "my-site.example.com" in url

    def extract(self, url: str, **kwargs) -> dict:
        """
        Fetch and return article content.

        Must return a dict with at least:
            text  (str)  – plain-text article body
        May also include:
            title  (str)
            author (str)
            date   (str)
            html   (str)
        """
        import httpx
        response = httpx.get(url, follow_redirects=True)
        response.raise_for_status()
        # ... your parsing logic ...
        return {"text": "...", "title": "..."}
```

The registry calls `can_handle(url)` for each registered extractor in
registration order and uses the **first** one that returns `True`.

---

### `BasePostProcessor`

```python
from summarizer.plugins.base import BasePostProcessor

class SentimentAnalyser(BasePostProcessor):
    name = "sentiment_analyser"
    description = "Adds a sentiment score to the summary metadata."
    enabled_by_default = True          # run automatically

    def process(self, summary, article_text: str = "", **kwargs):
        """
        Enrich summary and return it.

        Args:
            summary:      The Summary object produced by the LLM pipeline.
                          Read text from summary.text / summary.content.
                          Write results to summary.metadata (dict).
            article_text: The original article text (if needed for analysis).

        Returns:
            The (potentially modified) summary object.
        """
        # Example using a hypothetical sentiment library
        from mylib import analyse_sentiment
        score = analyse_sentiment(summary.text)
        summary.metadata["sentiment"] = score
        return summary
```

Set `enabled_by_default = True` so that the processor runs automatically
whenever `registry.apply_postprocessors()` is called with `enabled_only=True`
(the default).  Processors with `enabled_by_default = False` are only applied
when the caller explicitly passes `enabled_only=False` or
`--all-postprocessors` via the CLI.

---

### `BaseFormatter`

```python
from summarizer.plugins.base import BaseFormatter

class SlackFormatter(BaseFormatter):
    name = "slack"
    description = "Formats summaries as Slack block kit messages."
    extension = ".json"

    def format(self, summary, **kwargs) -> str:
        """
        Return a string representation of the summary.

        For Slack this would be a JSON payload; for HTML it would be HTML, etc.
        """
        import json
        blocks = [
            {"type": "section", "text": {"type": "mrkdwn", "text": f"*Summary*\n{summary.text}"}},
        ]
        return json.dumps({"blocks": blocks}, indent=2)
```

Use `--format slack` on the CLI to select this formatter.

---

## Packaging Your Plugin

### Directory structure

```
my-summarizer-plugin/
├── pyproject.toml
├── README.md
└── src/
    └── my_plugin/
        ├── __init__.py
        └── processors.py
```

### `pyproject.toml`

```toml
[build-system]
requires = ["setuptools>=68", "wheel"]
build-backend = "setuptools.backends.legacy:build"

[project]
name = "my-summarizer-plugin"
version = "0.1.0"
dependencies = ["summarizer>=0.1"]

# -----------------------------------------------------------------
# Register your plugins as entry points.
# The key (left of =) is the name shown in `summarize plugins list`.
# The value is the import path in "module.path:ClassName" format.
# -----------------------------------------------------------------

[project.entry-points."summarizer.postprocessors"]
sentiment = "my_plugin.processors:SentimentAnalyser"

[project.entry-points."summarizer.extractors"]
mysite = "my_plugin.extractors:MySiteExtractor"

[project.entry-points."summarizer.formatters"]
slack = "my_plugin.formatters:SlackFormatter"

[tool.setuptools.packages.find]
where = ["src"]
```

### Install in development mode

```bash
pip install -e .
```

After installation, your plugins will appear in:

```bash
summarize plugins list
```

---

## Built-in Plugins

The summarizer ships with two built-in post-processors as reference
implementations:

### `KeywordExtractor`

| Attribute | Value |
|-----------|-------|
| Entry point name | `keyword_extractor` |
| Enabled by default | Yes |
| Module | `summarizer.plugins.builtin.keyword_extractor` |

Extracts the top-N keywords from the **original article text** using a TF-IDF
approach.  When [NLTK](https://www.nltk.org/) is installed it uses NLTK's
English stop-word list; otherwise a built-in fallback list is used.

Results are stored in `summary.metadata["keywords"]` as a `list[str]`.

**Configuration:**

```python
# Override number of keywords via process() kwargs
registry.apply_postprocessors(summary, article_text=text, top_n=15)
```

---

### `ReadabilityScorer`

| Attribute | Value |
|-----------|-------|
| Entry point name | `readability_scorer` |
| Enabled by default | Yes |
| Module | `summarizer.plugins.builtin.readability` |

Computes Flesch Reading Ease and Flesch-Kincaid Grade Level scores for the
**generated summary text**.  No external dependencies required.

Results stored in `summary.metadata`:

| Key | Type | Description |
|-----|------|-------------|
| `readability_score` | float | Flesch Reading Ease (0–100; higher = easier) |
| `readability_label` | str | Human-readable label (e.g. "Standard") |
| `flesch_kincaid_grade` | float | Approximate US school grade level |
| `readability_word_count` | int | Number of words in the summary |
| `readability_sentence_count` | int | Number of sentences in the summary |

---

## CLI Reference

### List all plugins

```bash
summarize plugins list
```

Example output:

```
Discovered plugins (2 total):

TYPE           NAME                  CLASS                 DEFAULT  DESCRIPTION
-------------- --------------------- --------------------- -------- ------------------------------------------
postprocessor  keyword_extractor     KeywordExtractor      True     Extracts top-N keywords ...
postprocessor  readability_scorer    ReadabilityScorer     True     Computes Flesch-Kincaid readability scores
```

### Disable plugins entirely

```bash
summarize --no-plugins summarize https://example.com/article
```

### Skip post-processors

```bash
summarize summarize --no-postprocess https://example.com/article
```

### Run all post-processors (including non-default ones)

```bash
summarize summarize --all-postprocessors https://example.com/article
```

### Use a custom formatter

```bash
summarize summarize --format slack https://example.com/article
```

---

## Advanced: Programmatic Use

```python
from summarizer.plugins import get_registry

# Get (or create) the global registry and discover all plugins
registry = get_registry()

# Find the right extractor for a URL
extractor = registry.get_extractor_for("https://my-site.example.com/post/1")
if extractor:
    article = extractor.extract("https://my-site.example.com/post/1")

# Apply all enabled post-processors
summary = my_llm_pipeline(article["text"])
summary = registry.apply_postprocessors(summary, article_text=article["text"])

# Format with a named formatter
for formatter in registry.formatters:
    if formatter.name == "slack":
        payload = formatter.format(summary)
        send_to_slack(payload)
        break

# Manual registration (useful in tests or one-off scripts)
from my_plugin.processors import SentimentAnalyser
registry.register_postprocessor(SentimentAnalyser())
```

---

## Testing Your Plugin

```python
# tests/test_my_plugin.py
import pytest
from summarizer.plugins import PluginRegistry, reset_registry
from my_plugin.processors import SentimentAnalyser


@pytest.fixture(autouse=True)
def clean_registry():
    reset_registry()
    yield
    reset_registry()


def test_sentiment_analyser_adds_metadata():
    registry = PluginRegistry()
    registry.register_postprocessor(SentimentAnalyser())

    class _Summary:
        text = "This is a wonderful article about great things!"
        metadata = {}

    summary = _Summary()
    result = registry.apply_postprocessors(summary, enabled_only=True)
    assert "sentiment" in result.metadata
```

---

## Error Handling

The `PluginRegistry` is designed to be **fault-tolerant**:

- If a plugin **fails to import**, a warning is logged and discovery continues.
- If a plugin class does **not subclass** the required ABC, it is silently
  skipped with a warning.
- If a plugin **fails to instantiate**, the error is caught and logged.
- If a post-processor **raises during `process()`**, the error is caught,
  logged as a warning, and the next processor is run.

This means a broken third-party plugin will never crash the summarization
pipeline.

---

## FAQ

**Q: Can I register multiple plugins of the same type?**  
A: Yes. All matching plugins are applied — extractors are tried in order until
one returns `True` from `can_handle()`; post-processors and formatters are all
registered and available.

**Q: Can I depend on other summarizer internals?**  
A: The public API is `summarizer.plugins.base` and `summarizer.plugins`.
Internal modules (prefixed with `_`) are not part of the public API and may
change without notice.

**Q: My plugin isn't being discovered. What should I check?**  
A: Run `pip show my-summarizer-plugin` to confirm it's installed.  Run
`python -c "from importlib.metadata import entry_points; print(entry_points())"` 
to confirm the entry points are registered.  Make sure you ran
`pip install -e .` (or a full install) after editing `pyproject.toml`.
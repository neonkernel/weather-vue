# Plugin Development Guide

This guide explains how to extend the `summarizer` package by writing and
distributing custom plugins.  Three plugin types are available:

| Type | Base class | Entry-point group |
|---|---|---|
| Extractor | `BaseExtractor` | `summarizer.extractors` |
| Post-processor | `BasePostProcessor` | `summarizer.postprocessors` |
| Formatter | `BaseFormatter` | `summarizer.formatters` |

---

## Quick-start: writing a custom post-processor

### 1. Create your plugin package

```
my-summarizer-plugin/
├── pyproject.toml
└── my_summarizer_plugin/
    ├── __init__.py
    └── processors.py
```

### 2. Implement the plugin class

```python
# my_summarizer_plugin/processors.py
from __future__ import annotations
from typing import Any
from summarizer.plugins.base import BasePostProcessor
from summarizer.models import Summary


class SentimentAnnotator(BasePostProcessor):
    """Adds a rough sentiment label to each summary."""

    name = "sentiment_annotator"
    description = "Adds a positive/negative/neutral sentiment label to the summary metadata."

    def process(self, summary: Summary, article_text: str, **kwargs: Any) -> Summary:
        # Simple heuristic — replace with a real model in production.
        positive_words = {"great", "excellent", "wonderful", "best", "love"}
        negative_words = {"terrible", "awful", "worst", "hate", "disaster"}

        text = (summary.summary or "").lower()
        pos = sum(1 for w in positive_words if w in text)
        neg = sum(1 for w in negative_words if w in text)

        if pos > neg:
            sentiment = "positive"
        elif neg > pos:
            sentiment = "negative"
        else:
            sentiment = "neutral"

        if summary.metadata is None:
            summary.metadata = {}
        summary.metadata["sentiment"] = sentiment
        return summary
```

### 3. Register via `pyproject.toml`

```toml
[project]
name = "my-summarizer-plugin"
version = "0.1.0"
dependencies = ["summarizer"]

[project.entry-points."summarizer.postprocessors"]
sentiment_annotator = "my_summarizer_plugin.processors:SentimentAnnotator"
```

### 4. Install and verify

```bash
# Install your plugin in the same environment as summarizer
pip install -e .

# Verify it is discovered
summarize plugins list
```

You should see your plugin listed under **Post-Processors**.

---

## Writing a custom Extractor

Extractors are responsible for fetching and parsing article content from a
URL before it is sent to the LLM.  The registry iterates over all registered
extractors and calls the first one whose `can_handle()` returns `True`.

```python
# my_summarizer_plugin/extractors.py
from __future__ import annotations
from typing import Any
from summarizer.plugins.base import BaseExtractor


class PdfExtractor(BaseExtractor):
    """Extracts plain text from PDF URLs."""

    name = "pdf_extractor"
    description = "Downloads and extracts text from PDF files."

    def can_handle(self, url: str) -> bool:
        return url.lower().endswith(".pdf")

    def extract(self, url: str, **kwargs: Any) -> str:
        import urllib.request
        # Real implementation would use pdfminer, PyMuPDF, etc.
        with urllib.request.urlopen(url) as resp:
            raw_bytes = resp.read()
        # Placeholder – replace with real PDF parsing
        return f"[PDF content from {url} — {len(raw_bytes)} bytes]"
```

Register in `pyproject.toml`:

```toml
[project.entry-points."summarizer.extractors"]
pdf_extractor = "my_summarizer_plugin.extractors:PdfExtractor"
```

---

## Writing a custom Formatter

Formatters convert `Summary` objects to custom string representations.

```python
# my_summarizer_plugin/formatters.py
from __future__ import annotations
from typing import Any
from summarizer.plugins.base import BaseFormatter
from summarizer.models import Summary


class CsvFormatter(BaseFormatter):
    """Formats summaries as CSV rows."""

    name = "csv_formatter"
    description = "Outputs summaries as CSV: url,title,summary"
    extension = "csv"

    def format_summary(self, summary: Summary, **kwargs: Any) -> str:
        import csv
        import io
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow([
            getattr(summary, "url", ""),
            getattr(summary, "title", ""),
            getattr(summary, "summary", ""),
        ])
        return buf.getvalue().strip()

    def format_batch(self, summaries, **kwargs: Any) -> str:
        import csv
        import io
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(["url", "title", "summary"])
        for s in summaries:
            writer.writerow([
                getattr(s, "url", ""),
                getattr(s, "title", ""),
                getattr(s, "summary", ""),
            ])
        return buf.getvalue().strip()
```

Register in `pyproject.toml`:

```toml
[project.entry-points."summarizer.formatters"]
csv_formatter = "my_summarizer_plugin.formatters:CsvFormatter"
```

---

## Plugin discovery mechanism

Plugins are discovered at startup using Python's `importlib.metadata`
entry-point API.  The `PluginRegistry` singleton (accessible via
`summarizer.plugins.get_registry()`) loads all entry points in the three
recognised groups.

```python
from summarizer.plugins import get_registry

registry = get_registry()

# Access registered plugins
for cls in registry.all_postprocessors():
    print(cls.name, "-", cls.description)
```

### Loading order

1. **Built-in plugins** are registered first (always available).
2. **Entry-point plugins** are loaded in the order returned by
   `importlib.metadata.entry_points()` (installation order).
3. If two plugins share the same `name`, the second one is skipped with a
   warning.  Use `register_postprocessor(cls, override=True)` to force
   replacement.

---

## Error handling for plugin authors

- If your plugin class does not subclass the correct base class, a
  `PluginLoadError` is raised during registration.
- If your plugin has unimplemented abstract methods, a `PluginLoadError` is
  also raised.
- Errors during entry-point loading (e.g., missing dependency) are logged
  at `ERROR` level but do **not** crash the application.

To enable debug logging and see all plugin activity:

```bash
summarize --verbose plugins list
```

---

## Base class API reference

### `BaseExtractor`

| Member | Type | Description |
|---|---|---|
| `name` | `str` | Unique plugin name |
| `description` | `str` | Short human-readable description |
| `can_handle(url)` | `bool` | Return `True` if this extractor handles the URL |
| `extract(url, **kwargs)` | `str` | Return plain-text article content |

### `BasePostProcessor`

| Member | Type | Description |
|---|---|---|
| `name` | `str` | Unique plugin name |
| `description` | `str` | Short human-readable description |
| `process(summary, article_text, **kwargs)` | `Summary` | Enrich/transform the summary |

### `BaseFormatter`

| Member | Type | Description |
|---|---|---|
| `name` | `str` | Unique plugin name |
| `description` | `str` | Short human-readable description |
| `extension` | `str` | Output file extension hint |
| `format_summary(summary, **kwargs)` | `str` | Format a single summary |
| `format_batch(summaries, **kwargs)` | `str` | Format multiple summaries (optional override) |

---

## Built-in plugins

The following post-processors are bundled with `summarizer` and always
available:

### `keyword_extractor`

Extracts the top-N keywords from the original article text using TF-IDF.
Keywords are stored in `summary.metadata["keywords"]` as a list of strings.

```python
# Enabled via CLI:
summarize url https://example.com/article --keywords 10

# Enabled programmatically:
from summarizer.plugins.builtin.keyword_extractor import KeywordExtractor
proc = KeywordExtractor(top_n=10)
summary = proc.process(summary, article_text)
print(summary.metadata["keywords"])
```

### `readability_scorer`

Computes Flesch Reading Ease and Flesch-Kincaid Grade Level for the
generated summary.  Results are stored in `summary.metadata["readability"]`.

```python
# Enabled via CLI:
summarize url https://example.com/article --readability

# Enabled programmatically:
from summarizer.plugins.builtin.readability import ReadabilityScorer
scorer = ReadabilityScorer()
summary = scorer.process(summary, article_text)
print(summary.metadata["readability"])
# {'flesch_reading_ease': 65.3,
#  'flesch_reading_ease_label': 'Standard',
#  'flesch_kincaid_grade': 9.1}
```

---

## Publishing your plugin

1. Bump the `version` in your `pyproject.toml`.
2. Build: `python -m build`
3. Publish: `twine upload dist/*`

Users install your plugin with:

```bash
pip install my-summarizer-plugin
```

The plugin is automatically discovered the next time `summarize` is run —
no configuration file changes are required.
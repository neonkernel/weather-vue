# Article Summarizer

A command-line tool that fetches an article from a URL and produces an AI-powered summary in a variety of styles and output formats.

---

## Features

- **Five summary styles** — bullets, brief, detailed, ELI5, and TL;DR
- **Three output formats** — plain text, Markdown, and JSON
- **File output** — write directly to a file instead of stdout
- Configurable LLM model via `--model` or a config file

---

## Installation

```bash
pip install -e .
```

---

## Quick Start

```bash
# Brief summary (default) printed as plain text
summarizer https://example.com/article
```

---

## CLI Reference

```
Usage: summarizer [OPTIONS] URL

  Summarize the article at URL and print the result.

Options:
  --style    [bullets|brief|detailed|eli5|tldr]
                  Summary style. Default: brief
  --format   [text|markdown|json]
                  Output format. Default: text
  --output   PATH
                  Write output to this file instead of stdout.
  --model    TEXT
                  Override the LLM model from config.
  --config   PATH
                  Path to a custom configuration file.
  --verbose       Enable verbose/debug logging.
  --version       Show the version and exit.
  --help          Show this message and exit.
```

---

## Summary Styles

| Style      | Flag value  | Description                                      |
|------------|-------------|--------------------------------------------------|
| Brief      | `brief`     | Short executive brief (2–3 paragraphs). Default. |
| Bullets    | `bullets`   | Key takeaways as a bullet-point list             |
| Detailed   | `detailed`  | Comprehensive analysis with labelled sections    |
| ELI5       | `eli5`      | Explain Like I'm 5 — simple language, analogies  |
| TL;DR      | `tldr`      | Single sentence capturing the essence            |

---

## Output Formats

| Format     | Flag value  | Description                                           |
|------------|-------------|-------------------------------------------------------|
| Plain text | `text`      | Clean readable text. Default.                         |
| Markdown   | `markdown`  | Title header, metadata section, and formatted body    |
| JSON       | `json`      | Full JSON object including all metadata fields        |

### Markdown output structure

```markdown
# Article Title

## Metadata

- **Source:** https://example.com/article
- **Model:** gpt-4o
- **Word count:** 312
- **Style:** brief
- **Generated:** 2026-06-26 12:00:00 UTC

## Summary

The summary body text appears here …
```

### JSON output structure

```json
{
  "content": "The summary body text …",
  "title": "Article Title",
  "source_url": "https://example.com/article",
  "model": "gpt-4o",
  "word_count": 312,
  "style": "brief",
  "created_at": "2026-06-26T12:00:00"
}
```

---

## Examples

```bash
# 1. Default: brief summary, plain text
summarizer https://example.com/article

# 2. Bullet-point summary in Markdown
summarizer https://example.com/article --style bullets --format markdown

# 3. Detailed summary saved to a Markdown file
summarizer https://example.com/article --style detailed --format markdown --output summary.md

# 4. ELI5 explanation as plain text
summarizer https://example.com/article --style eli5

# 5. One-sentence TL;DR in Markdown
summarizer https://example.com/article --style tldr --format markdown

# 6. Full JSON summary (all metadata included)
summarizer https://example.com/article --style brief --format json

# 7. JSON summary written to a file
summarizer https://example.com/article --style detailed --format json --output summary.json

# 8. Use a specific model
summarizer https://example.com/article --model gpt-4o-mini

# 9. Combine a custom model with a custom style and Markdown output
summarizer https://example.com/article --style bullets --format markdown --model claude-3-5-sonnet-20241022
```

---

## Configuration

Create a `config.toml` (or pass `--config /path/to/config.toml`) to set defaults:

```toml
model = "gpt-4o"
verbose = false
```

---

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run a specific test file
pytest tests/test_formatter.py -v
pytest tests/test_styles.py -v
```
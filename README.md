# Article Summarizer

A command-line tool that fetches an article from a URL, local file, or stdin and generates a summary using a large language model.

---

## Installation

```bash
pip install -e .
```

Or with [uv](https://github.com/astral-sh/uv):

```bash
uv pip install -e .
```

---

## Quick Start

```bash
# Summarize a URL (default: brief style, plain-text output)
summarizer https://example.com/article

# Summarize a local file
summarizer article.txt

# Pipe text via stdin
cat article.txt | summarizer
```

---

## CLI Reference

```
Usage: summarizer [OPTIONS] [SOURCE]

  Summarize an article from a URL, local file, or stdin.

  SOURCE can be a URL (https://…), a local file path, or omitted to read
  from stdin.

Options:
  --style [brief|bullets|detailed|eli5|tldr]
                                  Summary style.  [default: brief]
  --format [text|markdown|json]   Output format.  [default: text]
  -o, --output FILE               Write output to FILE instead of stdout.
  --model TEXT                    Override the LLM model from config.
  --url TEXT                      Attach a source URL as metadata (useful
                                  when SOURCE is a local file or stdin).
  --version                       Show the version and exit.
  --help                          Show this message and exit.
```

---

## Summary Styles

| Style | Flag | Description |
|-------|------|-------------|
| **Brief** | `--style brief` | Concise executive brief of 2–3 paragraphs *(default)* |
| **Bullets** | `--style bullets` | Bullet-point list of 5–10 key facts |
| **Detailed** | `--style detailed` | Comprehensive analysis with context, evidence, and conclusion |
| **ELI5** | `--style eli5` | Explain Like I'm 5 — simple language, relatable analogies |
| **TL;DR** | `--style tldr` | One-sentence takeaway prefixed with "TL;DR:" |

### Examples

```bash
# Default executive brief
summarizer https://example.com/article

# Bullet-point summary
summarizer https://example.com/article --style bullets

# Detailed analysis
summarizer https://example.com/article --style detailed

# Explain Like I'm 5
summarizer article.txt --style eli5

# One-sentence TL;DR
summarizer https://example.com/article --style tldr
```

---

## Output Formats

| Format | Flag | Description |
|--------|------|-------------|
| **Text** | `--format text` | Plain text with optional metadata footer *(default)* |
| **Markdown** | `--format markdown` | Markdown with `# Title`, metadata table, and `## Summary` section |
| **JSON** | `--format json` | JSON object with all Summary fields including metadata |

### Examples

```bash
# Plain text (default)
summarizer https://example.com/article --format text

# Markdown — pipe to a .md file
summarizer https://example.com/article --format markdown

# JSON — pipe to jq for processing
summarizer https://example.com/article --format json | jq .

# Save Markdown output to a file
summarizer https://example.com/article --format markdown -o summary.md

# Save JSON output to a file
summarizer https://example.com/article --format json -o summary.json
```

---

## Combining Styles & Formats

```bash
# Bullet points as Markdown saved to a file
summarizer https://example.com/article \
  --style bullets \
  --format markdown \
  -o bullets.md

# Detailed analysis as JSON
summarizer article.txt \
  --style detailed \
  --format json \
  -o detailed.json

# ELI5 as Markdown
cat article.txt | summarizer --style eli5 --format markdown

# TL;DR as JSON with source URL metadata
summarizer https://example.com/article \
  --style tldr \
  --format json

# Local file with explicit source URL metadata
summarizer article.txt \
  --url https://original-source.com/article \
  --style brief \
  --format markdown \
  -o summary.md
```

---

## Markdown Output Structure

```markdown
# Article Title (or "Summary" if none detected)

| Field      | Value                        |
|------------|------------------------------|
| **Source** | https://example.com/article  |
| **Model**  | `gpt-4o`                     |
| **Style**  | brief                        |
| **Word Count** | 142                      |
| **Generated** | 2026-06-26 12:00:00 UTC   |

---

## Summary

This is the summary body text…
```

---

## JSON Output Schema

```json
{
  "body": "The full summary text…",
  "title": "Detected or inferred title",
  "source_url": "https://example.com/article",
  "model": "gpt-4o",
  "style": "brief",
  "word_count": 142,
  "created_at": "2026-06-26T12:00:00"
}
```

---

## Configuration

Set your API key and default model via environment variables or a `.env` file:

```env
OPENAI_API_KEY=sk-...
SUMMARIZER_MODEL=gpt-4o
```

---

## Development

```bash
# Run tests
pytest

# Run a specific test file
pytest tests/test_formatter.py -v
pytest tests/test_styles.py -v
```
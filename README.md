# Summarizer

A command-line tool that ingests web articles or local files and produces AI-generated summaries using an LLM backend.

---

## Installation

```bash
pip install -e .
```

---

## Quick Start

```bash
# Summarize a URL with default settings (brief style, plain text output)
summarize https://example.com/article

# Summarize a local file
summarize path/to/article.txt
```

---

## CLI Reference

```
Usage: summarize [OPTIONS] URL_OR_FILE

  Summarize a URL or local file using an LLM.

  URL_OR_FILE can be an HTTP/HTTPS URL or a path to a local text/HTML file.

Options:
  --style [bullets|brief|detailed|eli5|tldr]
                                  Summary style to use.  [default: brief]
  --format [text|markdown|json]   Output format.  [default: text]
  -o, --output PATH               Write output to a file instead of stdout.
  --model TEXT                    LLM model to use (overrides config default).
  -v, --verbose                   Enable verbose logging.
  --help                          Show this message and exit.
```

---

## Summary Styles

| Style      | Description                                                        |
|------------|--------------------------------------------------------------------|
| `brief`    | 2–4 sentence executive summary of the most important points        |
| `bullets`  | 5–10 bullet points covering key ideas, facts, and takeaways        |
| `detailed` | Comprehensive multi-paragraph summary covering all major topics    |
| `eli5`     | Simple explanation using plain language, as if for a 10-year-old  |
| `tldr`     | Ultra-short 1–2 sentence TL;DR capturing the core message         |

---

## Output Formats

| Format     | Description                                                        |
|------------|--------------------------------------------------------------------|
| `text`     | Plain text — title (if available), body, and metadata footer       |
| `markdown` | Markdown document with `# Title`, `## Metadata`, `## Summary`      |
| `json`     | JSON object containing all fields from the Summary data model      |

### JSON Schema

```json
{
  "body": "string",
  "title": "string | null",
  "source_url": "string | null",
  "model": "string | null",
  "word_count": "integer | null",
  "style": "string | null",
  "created_at": "ISO 8601 datetime string"
}
```

---

## Examples

### Style Examples

```bash
# Default: brief executive summary
summarize https://example.com/article

# Bullet-point list
summarize https://example.com/article --style bullets

# Comprehensive detailed summary
summarize https://example.com/article --style detailed

# Explain like I'm 5
summarize https://example.com/article --style eli5

# One-sentence TL;DR
summarize https://example.com/article --style tldr
```

### Format Examples

```bash
# Plain text (default)
summarize https://example.com/article --format text

# Markdown output
summarize https://example.com/article --format markdown

# JSON output
summarize https://example.com/article --format json
```

### Combined Style + Format Examples

```bash
# Bullet points in Markdown — great for documentation
summarize https://example.com/article --style bullets --format markdown

# Detailed summary as JSON — useful for downstream processing
summarize https://example.com/article --style detailed --format json

# ELI5 as Markdown
summarize https://example.com/article --style eli5 --format markdown

# Brief TL;DR as JSON
summarize https://example.com/article --style tldr --format json
```

### Writing to a File

```bash
# Save a Markdown summary to a file
summarize https://example.com/article \
  --style bullets \
  --format markdown \
  --output summary.md

# Save a JSON summary
summarize https://example.com/article \
  --style detailed \
  --format json \
  --output summary.json

# Short form using -o flag
summarize path/to/article.txt --style brief -o output.txt
```

### Using a Specific Model

```bash
# Override the default model
summarize https://example.com/article --model gpt-4o --style detailed
```

---

## Configuration

The default LLM model and API settings can be configured in `src/summarizer/config.py` or via environment variables. See that file for available options.

---

## Development

### Running Tests

```bash
# Run all tests
pytest

# Run style tests only
pytest tests/test_styles.py -v

# Run formatter tests only
pytest tests/test_formatter.py -v
```

### Project Structure

```
src/summarizer/
├── cli.py          # Click CLI entry point
├── config.py       # Configuration and defaults
├── formatter.py    # Formatter class (text / Markdown / JSON)
├── models.py       # Summary dataclass
├── styles.py       # SummaryStyle and OutputFormat enums
├── llm/
│   ├── prompts.py  # Style-specific prompt templates
│   └── client.py   # LLM API client
└── ingestion/      # URL and file ingestion logic
```
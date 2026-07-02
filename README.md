# Article Summarizer

A CLI tool for summarizing articles using Large Language Models (LLMs).

## Features

- Summarize articles from URLs or local files
- Multiple summary styles (default, bullet, tldr, academic)
- Batch processing of multiple articles concurrently
- CSV, JSON, and JSONL export of batch results
- Dry-run mode for validation without LLM calls
- Token usage and cost estimation
- Rich terminal output

## Installation

```bash
pip install -e .
```

## Usage

### Single Article

```bash
# Summarize a URL
summarizer summarize https://example.com/article

# Summarize a local file
summarizer summarize article.txt

# Choose a style
summarizer summarize https://example.com/article --style bullet

# Save output
summarizer summarize https://example.com/article --output summary.txt

# Dry run (fetch without calling LLM)
summarizer summarize https://example.com/article --dry-run
```

### Batch Processing

The `batch` subcommand lets you summarize multiple articles concurrently from a URL list file or a directory of text/HTML files.

```bash
# Summarize URLs from a list file (one URL per line)
summarizer batch urls.txt

# Process a directory of .txt and .html files
summarizer batch articles/

# Use 8 concurrent workers
summarizer batch urls.txt --workers 8

# Export results to CSV
summarizer batch urls.txt --output results.csv --format csv

# Export results to JSON Lines
summarizer batch urls.txt --output results.jsonl --format jsonl

# Export results to JSON
summarizer batch urls.txt --output results.json --format json

# Dry run: fetch and validate all sources without calling LLM
summarizer batch urls.txt --dry-run

# Combine options
summarizer batch articles/ --workers 4 --output report.csv --format csv --style bullet
```

#### URL List File Format

Create a plain text file with one URL or file path per line. Lines starting with `#` are treated as comments and ignored.

```text
# My article list
https://example.com/article-one
https://example.com/article-two
/path/to/local/article.txt
```

#### Batch Output

After processing, a Rich table is displayed showing:

- Status (success/failure) for each item
- Processing duration per item
- Token usage per item
- Error messages for failed items

Aggregate statistics shown at the end:

- Total items processed
- Successes and failures
- Total processing time
- Total token usage
- Estimated cost

#### Exit Codes

- `0` — All items processed successfully
- `1` — One or more items failed (other items still processed)
- `130` — Batch interrupted by Ctrl+C

## Configuration

Set the following environment variables:

| Variable | Description | Default |
|---|---|---|
| `OPENAI_API_KEY` | OpenAI API key | — |
| `ANTHROPIC_API_KEY` | Anthropic API key | — |
| `SUMMARIZER_MODEL` | Default LLM model | `gpt-3.5-turbo` |
| `SUMMARIZER_STYLE` | Default summary style | `default` |
| `SUMMARIZER_MAX_TOKENS` | Max tokens per summary | `1024` |
| `SUMMARIZER_TEMPERATURE` | LLM temperature | `0.3` |
| `SUMMARIZER_CACHE_DIR` | Cache directory | — |

## Development

```bash
# Install development dependencies
pip install -e ".[dev]"

# Run tests
pytest tests/

# Run batch tests only
pytest tests/test_batch.py -v
```
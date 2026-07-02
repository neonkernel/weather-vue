# Summarizer

AI-powered article summarization tool with support for single articles and batch processing.

## Features

- Summarize articles from URLs or local files
- Multiple summary styles: default, brief, detailed, bullet
- **Batch processing** of multiple articles from a URL list or directory
- Concurrent processing with configurable worker threads
- Export results to CSV or JSON Lines
- Dry-run mode for validation without LLM calls
- Rich terminal output with progress and cost estimates

## Installation

```bash
pip install -e .
```

## Usage

### Single Article

```bash
# Summarize from a URL
summarizer summarize https://example.com/article

# Summarize a local file
summarizer summarize ./article.txt

# Choose a style
summarizer summarize https://example.com/article --style brief

# Save output to file
summarizer summarize https://example.com/article --output summary.txt
```

### Batch Processing

The `batch` subcommand processes multiple articles concurrently from a URL list file or a directory.

#### Input formats

**URL list file** (one URL per line, `#` for comments):

```
# urls.txt
https://example.com/article-1
https://example.com/article-2
https://example.com/article-3
```

**Directory** containing `.txt` or `.html` files:

```
articles/
  article-1.txt
  article-2.html
  article-3.txt
```

#### Basic usage

```bash
# Process a URL list file with default 4 workers
summarizer batch urls.txt

# Process a directory of articles
summarizer batch ./articles/

# Use 8 parallel workers
summarizer batch urls.txt --workers 8
```

#### Output formats

```bash
# Export results to CSV
summarizer batch urls.txt --output results.csv

# Export results to JSON Lines
summarizer batch urls.txt --output results.jsonl

# Explicitly set format
summarizer batch urls.txt --output results.dat --format csv
summarizer batch urls.txt --output results.dat --format jsonl
```

#### Dry-run mode

Fetch and validate all sources without calling the LLM:

```bash
summarizer batch urls.txt --dry-run
```

#### Full example

```bash
summarizer batch urls.txt \
  --workers 8 \
  --style brief \
  --output results.csv \
  --format csv \
  --dry-run
```

#### Summary styles

| Style     | Description                          |
|-----------|--------------------------------------|
| default   | Balanced summary (default)           |
| brief     | 2–3 sentence summary                 |
| detailed  | Comprehensive multi-paragraph summary|
| bullet    | Bullet-point key takeaways           |

### Output

After batch completion, a Rich table is displayed in the terminal showing:

- Status (success/failure) per source
- Processing duration
- Token usage and estimated cost
- Article title or error message

Aggregate totals are shown at the bottom:

```
Batch Processing Results
╭────┬─────────────────────────────┬────────┬──────────┬────────┬──────────┬───────────────────────╮
│  # │ Source                      │ Status │ Duration │ Tokens │ Cost     │ Title / Error         │
├────┼─────────────────────────────┼────────┼──────────┼────────┼──────────┼───────────────────────┤
│  1 │ https://example.com/art...  │ ✓ OK   │ 2.1s     │ 1,234  │ $0.0025  │ Example Article Title │
│  2 │ https://example.com/bro...  │ ✗ FAIL │ 0.3s     │ -      │ -        │ ConnectionError: ...  │
╰────┴─────────────────────────────┴────────┴──────────┴────────┴──────────┴───────────────────────╯

Summary: 1 succeeded | 1 failed | 2 total
Tokens: 1,234 total | Est. Cost: $0.0025 | Avg Duration: 1.2s
```

### Exit Codes

| Code | Meaning                                   |
|------|-------------------------------------------|
| 0    | All sources processed successfully        |
| 1    | Fatal error (e.g., invalid source path)   |
| 2    | Partial success (some sources failed)     |

## CSV Output Format

| Column           | Description                              |
|------------------|------------------------------------------|
| source           | URL or file path                         |
| status           | `success` or `failure`                   |
| title            | Article title                            |
| duration_seconds | Processing time in seconds               |
| tokens_used      | LLM tokens consumed                      |
| cost_estimate    | Estimated API cost in USD                |
| error            | Error message (empty on success)         |
| summary_excerpt  | First 200 characters of summary          |
| timestamp        | ISO 8601 timestamp (UTC)                 |
| dry_run          | Whether this was a dry-run               |

## JSON Lines Output Format

Each line is a JSON object:

```json
{"source": "https://example.com/article", "status": "success", "title": "Article Title", "word_count": 850, "duration_seconds": 2.1, "tokens_used": 1234, "cost_estimate": 0.0025, "error": null, "summary": "Full summary text...", "timestamp": "2026-07-02T12:00:00", "dry_run": false}
```

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest tests/

# Run batch tests only
pytest tests/test_batch.py -v
```
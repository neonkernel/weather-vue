# Article Summarizer

A CLI tool and library for fetching, ingesting, and summarizing web articles and local text files using LLMs.

---

## Installation

```bash
pip install -e .
```

---

## Quick Start

### Summarize a single article

```bash
summarizer summarize https://example.com/article
```

Save the output to a file:

```bash
summarizer summarize https://example.com/article --output summary.txt
```

Choose a summary style:

```bash
summarizer summarize https://example.com/article --style bullets
```

---

## Batch Processing

The `batch` subcommand lets you summarize multiple articles concurrently from:

- A `.txt` file containing one URL per line
- A directory of `.txt` or `.html` article files
- A single URL or file path

### Basic usage

```bash
summarizer batch urls.txt
```

### Options

| Flag | Default | Description |
|------|---------|-------------|
| `--workers` / `-w` | `4` | Number of parallel worker threads (1–64) |
| `--output` / `-o` | — | Write results to a CSV or JSON Lines file |
| `--format` | `auto` | Output format: `auto` (inferred from extension), `csv`, or `jsonl` |
| `--style` | `concise` | Summary style applied to every article |
| `--model` | — | LLM model override |
| `--dry-run` | `False` | Fetch and validate sources **without** calling the LLM |

### Examples

```bash
# Process 5 URLs with 8 workers, save CSV results
summarizer batch urls.txt --workers 8 --output results.csv

# Summarize all articles in a directory
summarizer batch articles/

# Validate all URLs without calling the LLM
summarizer batch urls.txt --dry-run

# Export results as JSON Lines
summarizer batch urls.txt --output results.jsonl --format jsonl

# Use a specific model and detailed style
summarizer batch urls.txt --model gpt-4o --style detailed --output out.csv
```

### URL list file format

```
# Lines starting with '#' are ignored
# Blank lines are also ignored
https://example.com/article-1
https://example.com/article-2
https://example.com/article-3
```

### Output formats

**CSV** (`.csv`):

| Column | Description |
|--------|-------------|
| `source` | Original URL or file path |
| `success` | `True` / `False` |
| `tokens_used` | Token count for this item |
| `cost_estimate` | Estimated USD cost |
| `duration_seconds` | Wall-clock time to process |
| `error` | Error message if failed |
| `summary_text` | Generated summary text |

**JSON Lines** (`.jsonl`):

Each line is a JSON object with the same fields plus `article_title` and `article_word_count`.

### Batch summary table

After processing, a Rich table is printed to stdout:

```
╭────────────────────────────────────────────────────────────────────╮
│                    Batch Processing Results                        │
├───┬──────────────────────────────────┬────────┬────────┬──────────┤
│ # │ Source                           │ Status │ Tokens │ Duration │
├───┼──────────────────────────────────┼────────┼────────┼──────────┤
│ 1 │ https://example.com/article-1   │ ✓ OK   │    452 │    2.34s │
│ 2 │ https://example.com/article-2   │ ✓ OK   │    381 │    1.87s │
│ 3 │ https://example.com/article-3   │ ✗ FAIL │      - │    0.12s │
╰───┴──────────────────────────────────┴────────┴────────┴──────────╯

Summary: 3 items | 2 succeeded | 1 failed | Total tokens: 833 | Est. cost: $0.001666 | Wall time: 4.33s
```

Token usage and estimated cost are shown per-item and aggregated at the end.

---

## Debug mode

```bash
summarizer --debug batch urls.txt
```

---

## Architecture

```
src/summarizer/
├── cli.py          # Click CLI (summarize + batch subcommands)
├── batch.py        # BatchProcessor with ThreadPoolExecutor
├── reporter.py     # Rich table, CSV, and JSON Lines output
├── models.py       # Article, Summary, BatchResult dataclasses
├── ingestion/      # URL fetching and HTML parsing
├── llm/            # LLM client wrappers
├── summarize.py    # Core summarization logic
├── cache.py        # Result caching
├── config.py       # Configuration management
└── exceptions.py   # Custom exception hierarchy
```

---

## Running tests

```bash
pytest tests/
```

Run batch-specific tests:

```bash
pytest tests/test_batch.py -v
```
# Article Summarizer

An AI-powered command-line tool for summarising web articles and local text files, with support for batch processing, concurrent execution, and multiple output formats.

---

## Features

- Summarise single articles from URLs or local `.txt`/`.html` files
- **Batch processing** of multiple sources concurrently
- Multiple summary styles
- Rich terminal output with progress tracking
- Export results to CSV or JSON Lines
- Dry-run mode for source validation without LLM calls
- Token usage tracking and cost estimation

---

## Installation

```bash
pip install -e .
```

---

## Quick Start

### Summarise a single article

```bash
summarize run https://example.com/some-article
summarize run path/to/article.txt --style bullet
summarize run https://example.com/article --output summary.txt
```

### Batch processing

Summarise multiple articles concurrently from a URL list file or a directory of article files.

#### URL list file

Create a plain-text file with one URL (or file path) per line. Lines starting with `#` are treated as comments and ignored.

```text
# urls.txt
https://example.com/article-1
https://example.com/article-2
https://example.com/article-3
```

```bash
summarize batch urls.txt
```

#### Directory of files

```bash
summarize batch articles/
```

---

## Batch Subcommand Reference

```
Usage: summarize batch [OPTIONS] SOURCE_PATH

  Summarise multiple articles concurrently from a URL list file or directory.

Arguments:
  SOURCE_PATH  Path to a .txt file containing one URL per line, or a
               directory of .txt/.html article files.  [required]

Options:
  -w, --workers INTEGER RANGE  Number of concurrent worker threads.
                               [default: 4; 1<=x<=32]
  -o, --output PATH            Write results to this file (format determined
                               by --format).
  -f, --format TEXT            Output format when --output is specified:
                               csv | jsonl.  [default: csv]
  -s, --style TEXT             Summary style for all articles.
                               [default: default]
  -m, --model TEXT             LLM model override.
  --dry-run                    Fetch and validate all sources without calling
                               the LLM.
  --help                       Show this message and exit.
```

### Examples

```bash
# Summarise 10 URLs using 8 worker threads and save results to CSV
summarize batch urls.txt --workers 8 --output results.csv

# Export results as JSON Lines
summarize batch urls.txt --output results.jsonl --format jsonl

# Summarise all .txt and .html files in a directory
summarize batch articles/ --workers 4 --output report.csv

# Validate all sources without calling the LLM (dry run)
summarize batch urls.txt --dry-run

# Use a specific summary style and model
summarize batch urls.txt --style bullet --model gpt-4o --output results.csv
```

---

## Output Formats

### Terminal (always shown)

After a batch run, a Rich table is printed to the terminal showing:

| Column    | Description                        |
|-----------|------------------------------------|
| #         | Item index                         |
| Source    | URL or file path                   |
| Title     | Article title (if available)       |
| Status    | ✓ OK or ✗ FAIL                     |
| Tokens    | Tokens consumed by the LLM         |
| Duration  | Time taken for this item           |

Aggregate statistics are shown below the table:

- Total / succeeded / failed item counts
- Success rate
- Total tokens used
- Estimated cost (USD)
- Wall-clock time

### CSV

```bash
summarize batch urls.txt --output results.csv --format csv
```

Columns: `source, title, status, error, tokens_used, duration_seconds, summary`

### JSON Lines

```bash
summarize batch urls.txt --output results.jsonl --format jsonl
```

Each line is a JSON object with the same fields as the CSV output.

---

## Error Handling

Each item in a batch is processed independently. A failed URL or file does not abort the remaining items. Failed items appear in the results table with `✗ FAIL` status and an error message.

The command exits with code `1` if **any** item failed, and `0` if all items succeeded. This makes it straightforward to use in CI pipelines.

---

## Development

```bash
# Install development dependencies
pip install -e ".[dev]"

# Run tests
pytest tests/

# Run only batch tests
pytest tests/test_batch.py -v
```

---

## Project Structure

```
src/summarizer/
├── cli.py          # Typer CLI (run + batch subcommands)
├── batch.py        # BatchProcessor — concurrent execution
├── reporter.py     # Rich table, CSV, and JSON Lines output
├── models.py       # Data models (ArticleContent, BatchResult, …)
├── summarize.py    # Core summarisation logic
├── ingestion/      # URL fetching and file parsing
├── config.py       # Configuration loading
└── exceptions.py   # Custom exception hierarchy
```
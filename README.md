# Article Summarizer

A command-line tool for fetching and summarizing articles from URLs or local files using LLMs.

## Features

- Summarize individual articles from URLs or local files
- **Batch processing** of multiple articles with concurrent workers
- Multiple summary styles: concise, detailed, bullet points
- Rich terminal output with progress indicators
- Export results to CSV or JSON Lines
- Dry-run mode for validating sources without LLM calls
- Per-item error isolation — one failure never aborts the batch
- Token usage tracking and cost estimation

## Installation

```bash
pip install -e .
```

## Usage

### Summarize a single article

```bash
summarizer summarize https://example.com/article --style concise
summarizer summarize path/to/article.txt --style bullet --format markdown
```

### Batch processing

The `batch` subcommand accepts a `.txt` file of URLs (one per line) or a directory
of `.txt`/`.html` files.

```bash
# Process a list of URLs from a file
summarizer batch urls.txt

# Use 8 concurrent workers
summarizer batch urls.txt --workers 8

# Save results to CSV
summarizer batch urls.txt --output results.csv

# Save results as JSON Lines
summarizer batch urls.txt --output results.jsonl --format jsonl

# Process a directory of article files
summarizer batch articles/

# Dry-run: fetch and validate without calling the LLM
summarizer batch urls.txt --dry-run

# Full example: 8 workers, bullet style, CSV output
summarizer batch urls.txt --workers 8 --style bullet --output results.csv
```

#### Batch options

| Option | Default | Description |
|--------|---------|-------------|
| `--workers` / `-w` | `4` | Number of concurrent worker threads (1–32) |
| `--output` / `-o` | — | Output file path for results |
| `--format` | `csv` | Output format: `csv` or `jsonl` |
| `--style` / `-s` | `concise` | Summary style: `concise`, `detailed`, `bullet` |
| `--model` / `-m` | default | LLM model override |
| `--dry-run` | — | Fetch sources without calling the LLM |

#### URL list file format

```
# Lines starting with '#' are comments and are ignored
# Blank lines are also ignored

https://example.com/article/1
https://example.com/article/2
https://example.com/article/3
```

#### Batch output

After processing, a summary table is printed to the terminal:

```
╭────────────────────────────────────────────────────────────────────────╮
│                    Batch Processing Summary                            │
├────┬──────────────────────────────────────┬──────────┬──────────┬──────┤
│  # │ Source                               │ Status   │ Duration │Tokens│
├────┼──────────────────────────────────────┼──────────┼──────────┼──────┤
│  1 │ https://example.com/article/1        │ ✓ OK     │    1.23s │  342 │
│  2 │ https://example.com/article/2        │ ✗ FAILED │    0.10s │    - │
│  3 │ https://example.com/article/3        │ ✓ OK     │    0.98s │  289 │
╰────┴──────────────────────────────────────┴──────────┴──────────┴──────╯

  Total items:    3
  Successful:     2
  Failed:         1
  Total duration: 2.31s
  Total tokens:   631
  Model:          gpt-4o-mini
  Est. cost:      $0.0001 USD
```

## Output formats

### CSV

Each row corresponds to one source:

```
source,status,duration_seconds,tokens_used,title,word_count,model,summary_preview,error,timestamp
https://example.com/1,success,1.234,342,Article Title,...
```

### JSON Lines (JSONL)

One JSON object per line:

```json
{"source": "https://example.com/1", "status": "success", "tokens_used": 342, ...}
{"source": "https://example.com/2", "status": "failed", "error": "Connection refused", ...}
```

## Configuration

Set your API key via environment variable:

```bash
export OPENAI_API_KEY=sk-...
export ANTHROPIC_API_KEY=sk-ant-...
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
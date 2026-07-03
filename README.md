# Article Summarizer

A CLI tool for summarizing web articles using Large Language Models (LLMs).

## Installation

```bash
pip install -e .
```

## Quick Start

### Summarize a single article

```bash
summarizer summarize https://example.com/article
```

With options:
```bash
summarizer summarize https://example.com/article --style bullets --model gpt-4o
```

---

## Batch Processing

The `batch` subcommand lets you summarize multiple articles concurrently from a list of URLs or a directory of local files.

### Basic usage

```bash
summarizer batch urls.txt
```

### Batch from a directory

```bash
summarizer batch ./articles/
```

This will process all `.txt` and `.html` files found in the directory.

### Options

| Flag | Default | Description |
|------|---------|-------------|
| `--workers N` | `4` | Number of concurrent worker threads (1–32) |
| `--output PATH` | — | Path to write results file |
| `--format csv\|jsonl` | `csv` | Output format when `--output` is set |
| `--style STYLE` | `default` | Summary style for all articles |
| `--model MODEL` | — | LLM model to use for all articles |
| `--dry-run` | — | Fetch and validate sources without calling the LLM |
| `--no-cache` | — | Bypass the response cache |

### URL list file format

Create a plain text file with one URL per line:

```
# Comments start with '#' and are ignored
# Blank lines are also ignored

https://example.com/article-one
https://example.com/article-two
https://anothersite.org/post/interesting-topic
```

### Examples

**Process 5 URLs with 8 workers, save CSV:**
```bash
summarizer batch urls.txt --workers 8 --output results.csv --format csv
```

**Dry-run to validate all sources:**
```bash
summarizer batch urls.txt --dry-run
```

**Process a directory and export JSON Lines:**
```bash
summarizer batch ./my-articles/ --output results.jsonl --format jsonl
```

**Use bullet-point style with a specific model:**
```bash
summarizer batch urls.txt --style bullets --model gpt-4o --workers 6
```

### Output

After the batch completes, a summary table is printed to the console:

```
╭─────────────────────────────── Batch Processing Results ────────────────────────────────╮
│  #  │ Source                                │ Status │ Duration │ Tokens │    Cost      │
├─────┼───────────────────────────────────────┼────────┼──────────┼────────┼──────────────┤
│  1  │ https://example.com/article-one       │  ✓ OK  │   2.3s   │  850   │  $0.0017     │
│  2  │ https://example.com/article-two       │  ✓ OK  │   1.8s   │  720   │  $0.0014     │
│  3  │ https://bad-url.example.com/missing   │ ✗ FAIL │   5.0s   │   -    │    -         │
╰─────────────────────────────────────────────────────────────────────────────────────────╯

Batch Summary
  Total items  : 3
  Successes    : 2
  Failures     : 1
  Success rate : 66.7%
  Total time   : 8.1s
  Total tokens : 1570
  Total cost   : $0.0031
```

### CSV output columns

| Column | Description |
|--------|-------------|
| `index` | Row number |
| `source` | URL or file path |
| `success` | `True` / `False` |
| `duration_seconds` | Processing time |
| `tokens_used` | Tokens consumed |
| `cost_estimate` | Estimated cost in USD |
| `error` | Error message (if failed) |
| `summary_text` | Generated summary |
| `article_title` | Extracted article title |
| `article_word_count` | Word count of article |

### JSON Lines output

Each line is a JSON object:

```json
{"index": 1, "source": "https://example.com/article-one", "success": true, "duration_seconds": 2.3, "tokens_used": 850, "cost_estimate": 0.0017, "error": null, "summary": "...", "article": {"title": "...", "word_count": 1200, "url": "..."}}
```

---

## Configuration

Configuration can be provided via a config file:

```bash
summarizer --config config.yaml summarize https://example.com/article
```

## Debug mode

```bash
summarizer --debug batch urls.txt
```

## License

MIT
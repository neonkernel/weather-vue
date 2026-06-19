# Summarizer CLI

A command-line tool to summarize web pages and local files using AI.

## Overview

`summarize` is a CLI tool that accepts a URL or local file path and returns an AI-generated summary. It supports multiple output styles and formats.

## Installation

### Prerequisites

- Python 3.9+
- pip

### Install from source

```bash
# Clone the repository
git clone <repo-url>
cd <repo-dir>

# Create and activate a virtual environment (recommended)
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install in editable mode
pip install -e .
```

### Configure environment variables

```bash
cp .env.example .env
# Edit .env and add your OpenAI API key
```

## Usage

```bash
# Summarize a URL
summarize --url https://example.com/article

# Summarize a local file
summarize --file /path/to/document.txt

# Specify output style
summarize --url https://example.com/article --style bullet

# Specify output format
summarize --url https://example.com/article --format markdown

# Enable verbose logging
summarize --url https://example.com/article --verbose

# Show help
summarize --help
```

## Options

| Option | Description | Default |
|--------|-------------|---------|
| `--url` | URL of the web page to summarize | — |
| `--file` | Path to a local file to summarize | — |
| `--style` | Summary style: `paragraph`, `bullet`, `tldr` | `paragraph` |
| `--format` | Output format: `plain`, `markdown`, `json` | `plain` |
| `--verbose` | Enable verbose/debug logging | False |

## Development

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run a specific test
pytest tests/test_cli.py -v
```

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `OPENAI_API_KEY` | Your OpenAI API key | Yes |
| `SUMMARIZER_MODEL` | OpenAI model to use | No (default: `gpt-4o-mini`) |
| `SUMMARIZER_MAX_TOKENS` | Maximum tokens in response | No (default: `512`) |
| `SUMMARIZER_TIMEOUT` | HTTP request timeout in seconds | No (default: `30`) |

## License

MIT
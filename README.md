# Summarizer CLI

A command-line tool that summarizes web pages and local files using AI.

## Features

- Summarize content from URLs or local files
- Multiple summarization styles (brief, detailed, bullet points)
- Multiple output formats (text, markdown, JSON)
- Configurable via environment variables

## Installation

### Prerequisites

- Python 3.9+
- pip

### Install from source

```bash
# Clone the repository
git clone <repository-url>
cd summarizer

# Create and activate a virtual environment (recommended)
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install in editable mode
pip install -e .
```

### Configure environment

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

# Choose a summarization style
summarize --url https://example.com/article --style bullet

# Choose an output format
summarize --url https://example.com/article --format markdown

# Enable verbose logging
summarize --url https://example.com/article --verbose
```

## Options

| Option | Description | Default |
|--------|-------------|---------|
| `--url` | URL to summarize | — |
| `--file` | Local file path to summarize | — |
| `--style` | Summarization style: `brief`, `detailed`, `bullet` | `brief` |
| `--format` | Output format: `text`, `markdown`, `json` | `text` |
| `--verbose` | Enable verbose/debug logging | `False` |

## Development

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest tests/
```

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `OPENAI_API_KEY` | Your OpenAI API key | Yes |
| `SUMMARIZER_MODEL` | OpenAI model to use | No (default: `gpt-4o-mini`) |
| `SUMMARIZER_MAX_TOKENS` | Maximum tokens in response | No (default: `512`) |
| `SUMMARIZER_DEFAULT_STYLE` | Default summarization style | No (default: `brief`) |
| `SUMMARIZER_DEFAULT_FORMAT` | Default output format | No (default: `text`) |
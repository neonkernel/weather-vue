# Summarizer

A command-line tool that summarizes web pages and local files using LLMs.

## Installation

### Prerequisites

- Python 3.10+
- pip

### Install from source

```bash
# Clone the repository
git clone <repository-url>
cd <repository-directory>

# Create a virtual environment (recommended)
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install in editable mode
pip install -e .
```

### Configure environment variables

```bash
cp .env.example .env
# Edit .env and add your API keys
```

## Usage

```bash
# Summarize a URL
summarize --url https://example.com/article

# Summarize a local file
summarize --file /path/to/document.txt

# Specify output style
summarize --url https://example.com --style bullet

# Specify output format
summarize --url https://example.com --format markdown

# Enable verbose logging
summarize --url https://example.com --verbose
```

## Options

| Option | Description | Default |
|--------|-------------|---------|
| `--url` | URL of the web page to summarize | - |
| `--file` | Path to a local file to summarize | - |
| `--style` | Summary style: `paragraph`, `bullet`, `tldr` | `paragraph` |
| `--format` | Output format: `plain`, `markdown`, `json` | `plain` |
| `--verbose` | Enable verbose/debug logging | `False` |
| `--help` | Show help message and exit | - |

## Development

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest tests/
```

## Environment Variables

See `.env.example` for all supported environment variables.

| Variable | Description | Required |
|----------|-------------|----------|
| `OPENAI_API_KEY` | Your OpenAI API key | Yes |
| `SUMMARIZER_MODEL` | Model to use for summarization | No (default: `gpt-4o-mini`) |
| `SUMMARIZER_MAX_TOKENS` | Maximum tokens in the summary | No (default: `512`) |
| `SUMMARIZER_DEFAULT_STYLE` | Default summary style | No (default: `paragraph`) |
| `SUMMARIZER_DEFAULT_FORMAT` | Default output format | No (default: `plain`) |
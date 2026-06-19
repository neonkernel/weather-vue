# Summarizer CLI

A command-line tool that summarizes web pages and local files using LLMs.

## Installation

### Prerequisites

- Python 3.9+
- pip

### Setup

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd summarizer
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. Install the package in editable mode:
   ```bash
   pip install -e .
   ```

4. Configure environment variables:
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
| `--file` | Path to local file to summarize | — |
| `--style` | Summary style: `paragraph`, `bullet`, `tldr` | `paragraph` |
| `--format` | Output format: `plain`, `markdown`, `json` | `plain` |
| `--verbose` | Enable debug logging | `False` |

## Development

### Running Tests

```bash
pip install -e ".[dev]"
pytest tests/
```

### Project Structure

```
summarizer/
├── src/
│   └── summarizer/
│       ├── __init__.py     # Package init, version
│       ├── cli.py          # Click CLI entry point
│       ├── config.py       # Environment/config management
│       └── logger.py       # Logging setup
├── tests/
│   ├── __init__.py
│   └── test_cli.py         # CLI smoke tests
├── .env.example            # Environment variable template
├── pyproject.toml          # Package metadata & dependencies
└── README.md
```

## Environment Variables

See `.env.example` for all available configuration options.

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENAI_API_KEY` | Yes | Your OpenAI API key |
| `SUMMARIZER_MODEL` | No | Model to use (default: `gpt-4o-mini`) |
| `SUMMARIZER_MAX_TOKENS` | No | Max tokens for response (default: `512`) |
# Summarizer CLI

A command-line tool that summarizes web pages and local files using AI.

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

4. Copy the environment variables template and fill in your values:
   ```bash
   cp .env.example .env
   # Edit .env with your API keys
   ```

## Usage

```bash
# Summarize a URL
summarize --url https://example.com/article

# Summarize a local file
summarize --file /path/to/document.txt

# Choose output style
summarize --url https://example.com --style bullet
summarize --url https://example.com --style narrative
summarize --url https://example.com --style tldr

# Choose output format
summarize --url https://example.com --format plain
summarize --url https://example.com --format markdown
summarize --url https://example.com --format json

# Enable verbose logging
summarize --url https://example.com --verbose

# Show help
summarize --help
```

## Options

| Option | Description | Default |
|--------|-------------|---------|
| `--url` | URL of the web page to summarize | — |
| `--file` | Path to a local file to summarize | — |
| `--style` | Summary style: `bullet`, `narrative`, `tldr` | `narrative` |
| `--format` | Output format: `plain`, `markdown`, `json` | `plain` |
| `--verbose` | Enable verbose/debug logging | False |

## Environment Variables

See `.env.example` for all available configuration options.

| Variable | Description | Required |
|----------|-------------|----------|
| `OPENAI_API_KEY` | Your OpenAI API key | Yes |
| `SUMMARIZER_MODEL` | OpenAI model to use | No (default: `gpt-4o-mini`) |
| `SUMMARIZER_MAX_TOKENS` | Maximum tokens in summary | No (default: `512`) |
| `SUMMARIZER_TEMPERATURE` | Sampling temperature | No (default: `0.3`) |

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
│       ├── __init__.py     # Package init & version
│       ├── cli.py          # Click CLI entry point
│       ├── config.py       # Configuration management
│       └── logger.py       # Logging setup
├── tests/
│   ├── __init__.py
│   └── test_cli.py
├── .env.example
├── pyproject.toml
└── README.md
```
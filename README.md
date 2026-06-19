# Summarizer CLI

A command-line tool that summarizes web pages and local files using AI.

## Features

- Summarize content from URLs or local files
- Multiple summary styles (brief, detailed, bullet points)
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
summarize --file path/to/document.txt

# Choose summary style
summarize --url https://example.com/article --style brief
summarize --url https://example.com/article --style detailed
summarize --url https://example.com/article --style bullets

# Choose output format
summarize --url https://example.com/article --format markdown
summarize --url https://example.com/article --format json

# Enable verbose logging
summarize --url https://example.com/article --verbose

# Show help
summarize --help
```

## Configuration

Copy `.env.example` to `.env` and fill in your values:

| Variable            | Description                          | Default         |
|---------------------|--------------------------------------|-----------------|
| `OPENAI_API_KEY`    | Your OpenAI API key                  | *(required)*    |
| `SUMMARIZER_MODEL`  | OpenAI model to use                  | `gpt-4o-mini`   |
| `MAX_TOKENS`        | Maximum tokens for the summary       | `512`           |
| `LOG_LEVEL`         | Logging level (DEBUG/INFO/WARNING)   | `INFO`          |

## Development

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run tests with coverage
pytest --cov=summarizer
```

## Project Structure

```
summarizer/
├── src/
│   └── summarizer/
│       ├── __init__.py     # Package init & version
│       ├── cli.py          # CLI entry point (click)
│       ├── config.py       # Configuration management
│       └── logger.py       # Logging setup
├── tests/
│   ├── __init__.py
│   └── test_cli.py
├── .env.example
├── .gitignore
├── pyproject.toml
└── README.md
```

## License

MIT
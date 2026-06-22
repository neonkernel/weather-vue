# Web Summarizer CLI

A command-line tool that summarizes web pages and local files using AI.

## Features

- Summarize web pages by URL
- Summarize local text files
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
cd <repository-directory>

# Create and activate a virtual environment (recommended)
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install in editable mode
pip install -e .
```

### Configure environment variables

```bash
cp .env.example .env
# Edit .env and add your API key
```

## Usage

```bash
# Summarize a web page
summarize --url https://example.com/article

# Summarize a local file
summarize --file path/to/document.txt

# Choose summary style
summarize --url https://example.com --style brief
summarize --url https://example.com --style detailed
summarize --url https://example.com --style bullets

# Choose output format
summarize --url https://example.com --format markdown
summarize --url https://example.com --format json

# Verbose output for debugging
summarize --url https://example.com --verbose

# Show help
summarize --help
```

## Configuration

Copy `.env.example` to `.env` and fill in the required values:

| Variable            | Description                          | Default         |
|---------------------|--------------------------------------|-----------------|
| `OPENAI_API_KEY`    | Your OpenAI API key (required)       | —               |
| `SUMMARIZER_MODEL`  | Model to use for summarization       | `gpt-4o-mini`   |
| `SUMMARIZER_MAX_TOKENS` | Maximum tokens in the response   | `512`           |
| `SUMMARIZER_TEMPERATURE` | Sampling temperature            | `0.3`           |

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run tests with coverage
pytest --cov=summarizer
```

## Project Structure

```
.
├── src/
│   └── summarizer/
│       ├── __init__.py   # Package init, version string
│       ├── cli.py        # Click-based CLI entry point
│       ├── config.py     # Configuration management
│       └── logger.py     # Logging setup
├── tests/
│   ├── __init__.py
│   └── test_cli.py       # CLI smoke tests
├── .env.example          # Environment variable template
├── pyproject.toml        # Package metadata and dependencies
└── README.md
```

## License

MIT
# AI Content Summarizer

A command-line tool that summarizes web pages and local files using AI (OpenAI GPT models).

## Features

- Summarize content from URLs or local files
- Multiple summary styles (brief, detailed, bullet points)
- Multiple output formats (text, markdown, JSON)
- Configurable AI model and parameters
- Verbose logging support

## Installation

### Prerequisites

- Python 3.9 or higher
- An OpenAI API key

### Install from source

```bash
# Clone the repository
git clone <repository-url>
cd ai-summarizer

# Create and activate a virtual environment (recommended)
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install in editable mode
pip install -e .
```

### Configure environment variables

```bash
# Copy the example environment file
cp .env.example .env

# Edit .env and add your OpenAI API key
nano .env
```

## Usage

```bash
# Summarize a URL
summarize --url https://example.com/article

# Summarize a local file
summarize --file /path/to/document.txt

# Choose summary style (brief, detailed, bullets)
summarize --url https://example.com --style detailed

# Choose output format (text, markdown, json)
summarize --url https://example.com --format markdown

# Enable verbose logging
summarize --url https://example.com --verbose

# Show help
summarize --help
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENAI_API_KEY` | Your OpenAI API key (required) | — |
| `SUMMARIZER_MODEL` | OpenAI model to use | `gpt-4o-mini` |
| `SUMMARIZER_MAX_TOKENS` | Maximum tokens for summary | `1024` |
| `SUMMARIZER_TEMPERATURE` | Model temperature (0.0–2.0) | `0.7` |

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
.
├── src/
│   └── summarizer/
│       ├── __init__.py      # Package init & version
│       ├── cli.py           # Click CLI entry point
│       ├── config.py        # Configuration management
│       └── logger.py        # Logging setup
├── tests/
│   ├── __init__.py
│   └── test_cli.py          # CLI smoke tests
├── .env.example             # Environment variable template
├── pyproject.toml           # Package metadata & dependencies
└── README.md
```

## License

MIT
# Web Summarizer CLI

A command-line tool that summarizes web pages and local files using OpenAI's language models.

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
cd <repository-directory>

# Create and activate a virtual environment (recommended)
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install in editable mode
pip install -e .
```

### Configuration

Copy the example environment file and fill in your credentials:

```bash
cp .env.example .env
```

Edit `.env` with your OpenAI API key:

```
OPENAI_API_KEY=your-api-key-here
```

## Usage

```bash
# Summarize a URL
summarize --url https://example.com/article

# Summarize a local file
summarize --file path/to/document.txt

# Choose a summary style
summarize --url https://example.com --style brief
summarize --url https://example.com --style detailed
summarize --url https://example.com --style bullets

# Choose an output format
summarize --url https://example.com --format text
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
| `--url` | URL to summarize | - |
| `--file` | Local file path to summarize | - |
| `--style` | Summary style: `brief`, `detailed`, `bullets` | `brief` |
| `--format` | Output format: `text`, `markdown`, `json` | `text` |
| `--verbose` | Enable verbose/debug logging | `False` |

## Development

### Running Tests

```bash
pip install -e ".[dev]"
pytest tests/
```

### Project Structure

```
.
├── src/
│   └── summarizer/
│       ├── __init__.py   # Package init and version
│       ├── cli.py        # CLI entry point (Click)
│       ├── config.py     # Configuration management
│       └── logger.py     # Logging setup
├── tests/
│   ├── __init__.py
│   └── test_cli.py
├── pyproject.toml
├── .env.example
└── README.md
```

## License

MIT
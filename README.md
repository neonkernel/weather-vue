# Summarizer

AI-powered text summarization tool with support for multiple LLM providers, configurable styles, and named configuration profiles.

---

## Table of Contents

- [Installation](#installation)
- [Quick Start](#quick-start)
- [Configuration Profiles](#configuration-profiles)
  - [Config File Format](#config-file-format)
  - [Profile Commands](#profile-commands)
  - [Common Profile Recipes](#common-profile-recipes)
  - [Configuration Priority](#configuration-priority)
  - [Environment Variables](#environment-variables)
- [Usage](#usage)
- [Development](#development)

---

## Installation

```bash
pip install summarizer
```

For Python < 3.11, also install `tomli` and `tomli-w`:

```bash
pip install tomli tomli-w
```

---

## Quick Start

```bash
# Summarize a URL
summarize summarize https://example.com/article

# Summarize a file
summarize summarize ./document.txt

# Summarize stdin
echo "Long text here..." | summarize summarize -

# Use a specific provider and style
summarize --provider anthropic --style detailed summarize https://example.com
```

---

## Configuration Profiles

Named profiles let you define and switch between different summarization setups. Profiles are stored in `~/.config/summarizer/config.toml` (following the [XDG Base Directory Specification](https://specifications.freedesktop.org/basedir-spec/basedir-spec-latest.html)).

### Config File Format

```toml
# ~/.config/summarizer/config.toml

[default]
# The active profile name ("default" means no profile, use built-in defaults)
profile = "work"

# Top-level defaults applied before any profile
# provider = "openai"

[profiles.quick]
provider = "openai"
model = "gpt-3.5-turbo"
style = "concise"
format = "text"
max_length = 200

[profiles.quick.cache]
enabled = true
ttl_hours = 48

[profiles.quick.rate_limit]
requests_per_minute = 60
retry_attempts = 3

[profiles.work]
provider = "openai"
model = "gpt-4"
style = "bullet"
format = "markdown"
max_length = 500

[profiles.research]
provider = "anthropic"
model = "claude-3-opus-20240229"
style = "detailed"
format = "markdown"
max_length = 2000
temperature = 0.3

[profiles.research.cache]
enabled = true
ttl_hours = 168  # One week

[profiles.local]
provider = "ollama"
model = "llama3"
style = "concise"
format = "text"
```

### Profile Commands

#### Initialize config with example profiles

```bash
summarize config init
```

#### List all profiles

```bash
summarize config list

# With details
summarize config list --verbose
```

Output:
```
Active profile: work

Profiles:
* work
  quick
  research
  local
```

#### Create a profile

```bash
summarize config create work \
  --provider openai \
  --model gpt-4 \
  --style bullet \
  --format markdown \
  --max-length 500
```

Options:
- `--provider` — LLM provider (`openai`, `anthropic`, `ollama`, `openrouter`)
- `--model` — Model name
- `--style` — Style (`concise`, `detailed`, `bullet`, `academic`, `casual`)
- `--format` — Output format (`text`, `markdown`, `json`, `html`)
- `--max-length` — Maximum summary length (tokens/words)
- `--temperature` — LLM temperature (0.0–2.0)
- `--cache` / `--no-cache` — Enable/disable cache
- `--cache-ttl` — Cache TTL in hours
- `--rpm` — Rate limit: requests per minute
- `--use` — Set as active profile immediately after creating

#### Switch to a profile

```bash
summarize config use work
# ✓ Now using profile 'work'.

# Reset to built-in defaults
summarize config use default
```

#### Show a profile's settings

```bash
summarize config show
summarize config show research
summarize config show --resolved  # Show fully merged config with sources
```

#### Get/set individual settings

```bash
# Get a setting
summarize config get provider
# provider = openai

summarize config get style --profile research
# style = detailed

# Set a setting
summarize config set provider anthropic
summarize config set model gpt-4o --profile work
```

#### Delete a profile

```bash
summarize config delete research
summarize config delete research --yes  # Skip confirmation
```

#### Show config file path

```bash
summarize config path
# /home/user/.config/summarizer/config.toml
```

### Common Profile Recipes

#### Quick summarization (cheap & fast)

```bash
summarize config create quick \
  --provider openai \
  --model gpt-3.5-turbo \
  --style concise \
  --max-length 150 \
  --use
```

#### Work (structured bullet points)

```bash
summarize config create work \
  --provider openai \
  --model gpt-4 \
  --style bullet \
  --format markdown \
  --max-length 500
```

#### Research (deep analysis)

```bash
summarize config create research \
  --provider anthropic \
  --model claude-3-opus-20240229 \
  --style detailed \
  --format markdown \
  --max-length 2000 \
  --temperature 0.3 \
  --cache-ttl 168
```

#### Local (offline with Ollama)

```bash
summarize config create local \
  --provider ollama \
  --model llama3 \
  --style concise \
  --no-cache
```

#### Academic writing

```bash
summarize config create academic \
  --provider anthropic \
  --model claude-3-sonnet-20240229 \
  --style academic \
  --format markdown \
  --temperature 0.2
```

### Configuration Priority

Settings are resolved in the following order (highest priority wins):

```
CLI flags          ← highest priority
    ↑
Environment vars
    ↑
Config file profile
    ↑
Built-in defaults  ← lowest priority
```

Example:

```bash
# Profile sets provider=anthropic, env sets style=detailed, CLI sets model=gpt-4
SUMMARIZER_STYLE=detailed summarize --profile research --model gpt-4 summarize https://example.com
```

To see exactly where each value is coming from:

```bash
summarize config show --resolved
```

### Environment Variables

All settings can be overridden via environment variables:

| Variable                   | Config Key                      | Example Value       |
|----------------------------|---------------------------------|---------------------|
| `SUMMARIZER_PROVIDER`      | `provider`                      | `anthropic`         |
| `SUMMARIZER_MODEL`         | `model`                         | `claude-3-sonnet`   |
| `SUMMARIZER_STYLE`         | `style`                         | `detailed`          |
| `SUMMARIZER_FORMAT`        | `format`                        | `markdown`          |
| `SUMMARIZER_MAX_LENGTH`    | `max_length`                    | `500`               |
| `SUMMARIZER_TEMPERATURE`   | `temperature`                   | `0.7`               |
| `SUMMARIZER_CACHE_ENABLED` | `cache_enabled`                 | `true`              |
| `SUMMARIZER_CACHE_TTL_HOURS` | `cache_ttl_hours`             | `48`                |
| `SUMMARIZER_CACHE_MAX_SIZE_MB` | `cache_max_size_mb`         | `200`               |
| `SUMMARIZER_RATE_LIMIT_RPM` | `rate_limit_requests_per_minute` | `30`            |
| `SUMMARIZER_RATE_LIMIT_RPD` | `rate_limit_requests_per_day` | `1000`              |
| `SUMMARIZER_RETRY_ATTEMPTS` | `rate_limit_retry_attempts`   | `5`                 |
| `SUMMARIZER_RETRY_DELAY`   | `rate_limit_retry_delay_seconds` | `2.0`             |
| `SUMMARIZER_PROFILE`       | `profile`                       | `work`              |

---

## Usage

```
Usage: summarize [OPTIONS] COMMAND [ARGS]...

  Summarizer - AI-powered text summarization tool.

Options:
  --profile NAME          Use a specific configuration profile.
  --provider TEXT         LLM provider (openai, anthropic, ollama, openrouter).
  --model TEXT            Model name to use.
  --style [concise|detailed|bullet|academic|casual]
                          Summarization style.
  --format [text|markdown|json|html]
                          Output format.
  --config-dir PATH       Override config directory path.
  --help                  Show this message and exit.

Commands:
  summarize  Summarize text from SOURCE.
  config     Manage configuration profiles and settings.
    list     List all configuration profiles.
    create   Create a new configuration profile.
    use      Set the active configuration profile.
    show     Show configuration for a profile.
    get      Get a configuration setting value.
    set      Set a configuration setting value.
    delete   Delete a configuration profile.
    path     Show the path to the config file.
    init     Initialize config file with example profiles.
```

---

## Development

### Setup

```bash
git clone <repo>
cd summarizer
pip install -e ".[dev]"
```

### Run Tests

```bash
pytest tests/ -v
pytest tests/test_config.py tests/test_profile.py -v  # Profile tests only
```

### Config File Schema

The config file is validated using Pydantic models defined in `src/summarizer/schemas.py`.

Valid values:
- **provider**: `openai`, `anthropic`, `ollama`, `openrouter`
- **style**: `concise`, `detailed`, `bullet`, `academic`, `casual`
- **format**: `text`, `markdown`, `json`, `html`
- **temperature**: 0.0–2.0
- **max_length**: 1–100,000
- **cache.ttl_hours**: 1–8,760 (1 hour – 1 year)
- **rate_limit.requests_per_minute**: 1–10,000
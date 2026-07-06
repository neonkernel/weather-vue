# Summarizer

AI-powered text summarization tool with support for multiple LLM providers, configurable styles, and named configuration profiles.

---

## Table of Contents

- [Installation](#installation)
- [Quick Start](#quick-start)
- [Configuration Profiles](#configuration-profiles)
  - [Config File Location](#config-file-location)
  - [Example config.toml](#example-configtoml)
  - [Profile Fields](#profile-fields)
  - [Managing Profiles](#managing-profiles)
  - [Common Profile Recipes](#common-profile-recipes)
- [Configuration Priority](#configuration-priority)
- [Environment Variables](#environment-variables)
- [CLI Reference](#cli-reference)

---

## Installation

```bash
pip install summarizer
# For Python < 3.11, also install the TOML library:
pip install tomli
```

---

## Quick Start

```bash
# Summarize a URL using the active profile
summarizer summarize https://example.com/article

# Summarize with a specific profile
summarizer summarize https://example.com/article --profile work

# Summarize with inline overrides (highest priority)
summarizer summarize article.txt --style bullet --format markdown
```

---

## Configuration Profiles

Named profiles let you define and switch between different summarization setups. Common use cases include `work`, `research`, and `quick` presets.

### Config File Location

The configuration file follows the [XDG Base Directory Specification](https://specifications.freedesktop.org/basedir-spec/basedir-spec-latest.html):

```
~/.config/summarizer/config.toml
```

You can override this with the `XDG_CONFIG_HOME` environment variable:

```bash
export XDG_CONFIG_HOME=/custom/config/path
```

To see the exact path being used:

```bash
summarizer config path
```

### Example config.toml

```toml
[default]
profile = "work"   # The active profile used when no --profile flag is given

[work]
description = "Detailed summaries for work documents"
provider    = "openai"
model       = "gpt-4o"
style       = "detailed"
format      = "markdown"

[work.cache]
enabled        = true
ttl_seconds    = 7200
max_size_mb    = 200

[work.rate_limit]
requests_per_minute = 30
max_concurrent      = 3

[quick]
description = "Fast, concise summaries"
provider    = "openai"
model       = "gpt-4o-mini"
style       = "concise"
format      = "text"

[research]
description = "Academic-quality summaries with longer output"
provider    = "anthropic"
model       = "claude-3-5-sonnet-20241022"
style       = "academic"
format      = "markdown"
max_length  = 500
temperature = 0.3

[research.cache]
ttl_seconds = 86400   # Cache research summaries for 24 hours
```

### Profile Fields

| Field | Type | Description | Valid Values |
|-------|------|-------------|--------------|
| `provider` | string | LLM provider | `openai`, `anthropic`, `ollama`, `groq`, `cohere` |
| `model` | string | Model name | Provider-specific (e.g. `gpt-4o`, `claude-3-5-sonnet-20241022`) |
| `style` | string | Summary style | `concise`, `detailed`, `bullet`, `academic`, `casual`, `technical` |
| `format` | string | Output format | `text`, `markdown`, `json`, `html` |
| `max_length` | integer | Max words in summary | Any positive integer |
| `temperature` | float | LLM creativity (0.0–2.0) | `0.0` to `2.0` |
| `description` | string | Human-readable label | Any string |

**`[profile.cache]` sub-table:**

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `enabled` | bool | `true` | Enable/disable result caching |
| `ttl_seconds` | integer | `3600` | Cache time-to-live in seconds |
| `max_size_mb` | integer | `100` | Maximum cache size in MB |

**`[profile.rate_limit]` sub-table:**

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `requests_per_minute` | integer | `60` | API request rate limit |
| `max_concurrent` | integer | `5` | Max parallel requests |

### Managing Profiles

#### List all profiles

```bash
summarizer config list
summarizer config list --verbose    # Show full details
```

#### Create a profile

```bash
summarizer config create work \
  --provider openai \
  --model gpt-4o \
  --style detailed \
  --format markdown \
  --description "Work documents"
```

#### Switch the active profile

```bash
summarizer config use research
```

#### Show profile details

```bash
summarizer config show work
summarizer config show            # Shows active profile
```

#### Set a single value

```bash
summarizer config set model gpt-4o-mini
summarizer config set temperature 0.5 --profile research
summarizer config set provider anthropic --profile work
```

#### Get a single value

```bash
summarizer config get provider
summarizer config get model --profile work
```

#### Delete a profile

```bash
summarizer config delete quick
summarizer config delete quick --yes   # Skip confirmation
```

#### Show resolved configuration

See the final merged config (all sources applied):

```bash
summarizer config resolve
summarizer config resolve --profile research
summarizer config resolve --style bullet   # Preview CLI override effect
```

### Common Profile Recipes

#### `work` — Detailed markdown output for business documents

```toml
[work]
provider = "openai"
model    = "gpt-4o"
style    = "detailed"
format   = "markdown"

[work.rate_limit]
requests_per_minute = 20
```

#### `quick` — Fast summaries for quick reads

```toml
[quick]
provider = "openai"
model    = "gpt-4o-mini"
style    = "concise"
format   = "text"
```

#### `research` — Long-form academic summaries

```toml
[research]
provider    = "anthropic"
model       = "claude-3-5-sonnet-20241022"
style       = "academic"
format      = "markdown"
max_length  = 800
temperature = 0.2

[research.cache]
ttl_seconds = 86400
```

#### `offline` — Local model via Ollama

```toml
[offline]
provider = "ollama"
model    = "llama3"
style    = "concise"
format   = "text"

[offline.cache]
enabled = true
ttl_seconds = 604800   # 1 week
```

#### `technical` — Code-focused summaries

```toml
[technical]
provider    = "openai"
model       = "gpt-4o"
style       = "technical"
format      = "markdown"
temperature = 0.1
max_length  = 400
```

---

## Configuration Priority

Settings are merged from lowest to highest priority:

```
1. Hardcoded defaults  (lowest)
2. Config file profile (~/.config/summarizer/config.toml)
3. Environment variables
4. CLI flags           (highest)
```

Example: if your `work` profile sets `style = "detailed"` but you run with `--style bullet`, the CLI flag wins.

---

## Environment Variables

All settings can be overridden with environment variables:

| Variable | Config Key | Example |
|----------|-----------|---------|
| `SUMMARIZER_PROVIDER` | provider | `openai` |
| `SUMMARIZER_MODEL` | model | `gpt-4o` |
| `SUMMARIZER_STYLE` | style | `bullet` |
| `SUMMARIZER_FORMAT` | format | `markdown` |
| `SUMMARIZER_MAX_LENGTH` | max_length | `300` |
| `SUMMARIZER_TEMPERATURE` | temperature | `0.7` |
| `SUMMARIZER_CACHE_ENABLED` | cache_enabled | `false` |
| `SUMMARIZER_CACHE_TTL` | cache_ttl_seconds | `7200` |
| `SUMMARIZER_CACHE_MAX_SIZE_MB` | cache_max_size_mb | `200` |
| `SUMMARIZER_REQUESTS_PER_MINUTE` | requests_per_minute | `30` |
| `SUMMARIZER_MAX_CONCURRENT` | max_concurrent | `3` |
| `SUMMARIZER_PROFILE` | active_profile | `research` |

---

## CLI Reference

```
summarizer summarize <source> [options]
summarizer config list [--verbose]
summarizer config show [<profile>]
summarizer config use <profile>
summarizer config create <profile> [options]
summarizer config set <key> <value> [--profile <name>]
summarizer config get <key> [--profile <name>]
summarizer config delete <profile> [--yes]
summarizer config path
summarizer config resolve [--profile <name>] [options]
```
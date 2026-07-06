# Summarizer

An AI-powered text summarizer with support for multiple LLM providers, configurable styles, and named configuration profiles.

---

## Features

- 🤖 Multi-provider support: OpenAI, Anthropic, Ollama, OpenRouter
- 🎨 Multiple summary styles: concise, detailed, bullet, academic, casual, technical
- 📄 Output formats: text, markdown, JSON, HTML
- 💾 Result caching with configurable TTL
- ⚡ Rate limiting
- 🗂️ **Named configuration profiles** — define and switch between named setups

---

## Installation

```bash
pip install summarizer
# For Python < 3.11, also install TOML support:
pip install tomli tomli-w
```

---

## Configuration Profiles

Profiles let you define named sets of options and switch between them instantly.

### Config file location

Configuration is stored in `~/.config/summarizer/config.toml` (follows the [XDG Base Directory spec](https://specifications.freedesktop.org/basedir-spec/basedir-spec-latest.html)).

You can override the location by setting `XDG_CONFIG_HOME`.

### Example `config.toml`

```toml
[default]
active_profile = "work"

[work]
description = "Day-to-day work summaries"
provider = "openai"
model = "gpt-4o-mini"
style = "concise"
format = "markdown"
max_length = 300

[work.cache]
enabled = true
ttl_hours = 24

[work.rate_limit]
requests_per_minute = 60

[research]
description = "In-depth research summaries"
provider = "anthropic"
model = "claude-3-5-sonnet-20241022"
style = "academic"
format = "markdown"
max_length = 1000

[research.cache]
enabled = true
ttl_hours = 168  # one week

[quick]
description = "Fast bullet-point summaries"
provider = "openai"
model = "gpt-4o-mini"
style = "bullet"
max_length = 150
format = "text"

[quick.cache]
enabled = false
```

---

## CLI Reference

### `summarize config` subcommands

#### List all profiles
```bash
summarize config list
summarize config list --json   # JSON output
```

#### Create a profile
```bash
summarize config create work \
  --provider openai \
  --model gpt-4o-mini \
  --style concise \
  --format markdown \
  --description "Work profile"

# Create and immediately activate
summarize config create quick --style bullet --activate
```

#### Switch active profile
```bash
summarize config use research
```

#### Clear active profile (revert to defaults)
```bash
summarize config unset
```

#### Get profile settings
```bash
summarize config get work           # show all settings
summarize config get work provider  # show one key
```

#### Set a value on a profile
```bash
summarize config set work style detailed
summarize config set work max_length 500
```

#### Delete a profile
```bash
summarize config delete old-profile
summarize config delete old-profile --yes  # skip confirmation
```

#### Rename a profile
```bash
summarize config rename oldname newname
```

#### Show resolved config (all sources merged)
```bash
summarize config show             # uses active profile
summarize config show --profile research
```

#### Show config file path
```bash
summarize config path
```

---

## Configuration Priority

Settings are resolved in this order (highest priority wins):

```
Built-in defaults
    ↓
Config file profile  (active profile or --profile flag)
    ↓
Environment variables
    ↓
CLI flags  ← highest priority
```

### Environment variables

| Variable | Config key |
|---|---|
| `SUMMARIZER_PROVIDER` | provider |
| `SUMMARIZER_MODEL` | model |
| `SUMMARIZER_STYLE` | style |
| `SUMMARIZER_FORMAT` | format |
| `SUMMARIZER_MAX_LENGTH` | max_length |
| `SUMMARIZER_LANGUAGE` | language |
| `SUMMARIZER_CACHE_ENABLED` | cache_enabled |
| `SUMMARIZER_CACHE_TTL_HOURS` | cache_ttl_hours |
| `SUMMARIZER_CACHE_MAX_ENTRIES` | cache_max_entries |
| `SUMMARIZER_REQUESTS_PER_MINUTE` | requests_per_minute |
| `SUMMARIZER_TOKENS_PER_MINUTE` | tokens_per_minute |

---

## Common Profile Recipes

### Fast & cheap (OpenAI)
```bash
summarize config create quick \
  --provider openai \
  --model gpt-4o-mini \
  --style bullet \
  --max-length 150 \
  --description "Quick bullet summaries"
```

### Deep research (Anthropic)
```bash
summarize config create research \
  --provider anthropic \
  --model claude-3-5-sonnet-20241022 \
  --style academic \
  --format markdown \
  --max-length 1500 \
  --description "Thorough academic summaries"
```

### Local/offline (Ollama)
```bash
summarize config create local \
  --provider ollama \
  --model llama3.2 \
  --style concise \
  --description "Local model, no API key needed"
```

### Work (minimal, fast)
```bash
summarize config create work \
  --provider openai \
  --model gpt-4o-mini \
  --style concise \
  --format markdown \
  --description "Work summaries"

summarize config use work
```

---

## Valid Values

| Setting | Valid values |
|---|---|
| `provider` | `openai`, `anthropic`, `ollama`, `openrouter` |
| `style` | `concise`, `detailed`, `bullet`, `academic`, `casual`, `technical` |
| `format` | `text`, `markdown`, `json`, `html` |

---

## Running Summarizations

```bash
# Use active profile
summarize summarize "https://example.com/article"

# Use a specific profile
summarize --profile research summarize "https://example.com/paper"

# Override a single setting
summarize --style bullet summarize "https://example.com/article"

# CLI flags always win over profile settings
summarize --profile work --provider anthropic summarize "some text"
```

---

## Python API

```python
from summarizer.config import ConfigResolver
from summarizer.profile import ProfileManager

# Use active profile
resolver = ConfigResolver()
config = resolver.resolve()
print(config.provider, config.model, config.style)

# Use a specific profile
config = resolver.resolve(profile_name="research")

# Override with CLI-style flags
config = resolver.resolve(cli_flags={"style": "bullet", "max_length": 200})

# Manage profiles programmatically
manager = ProfileManager()
manager.create_profile("myprofile", provider="anthropic", style="detailed")
manager.set_active_profile("myprofile")
profile = manager.get_profile("myprofile")
```
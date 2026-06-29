"""Command-line interface for the article summariser."""

from __future__ import annotations

import argparse
import sys
from typing import Optional

from .config import Config
from .exceptions import LLMError, SummarizerError
from .llm.factory import SUPPORTED_PROVIDERS
from .logger import get_logger
from .summarize import summarize

logger = get_logger(__name__)


def build_parser() -> argparse.ArgumentParser:
    """Construct and return the CLI argument parser."""
    parser = argparse.ArgumentParser(
        prog="summarizer",
        description="Summarise articles using an LLM backend of your choice.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  summarizer article.txt
  summarizer https://example.com/article --provider anthropic --style bullet
  summarizer article.html --provider ollama --model llama3 --output-format markdown
        """,
    )

    # --- Input ---
    parser.add_argument(
        "input",
        help="Path to a file or a URL to summarise.",
    )

    # --- Provider ---
    parser.add_argument(
        "--provider",
        choices=list(SUPPORTED_PROVIDERS),
        default=None,
        help=(
            "LLM backend to use. "
            f"Choices: {', '.join(SUPPORTED_PROVIDERS)}. "
            "Defaults to the LLM_PROVIDER env var, or 'openai'."
        ),
    )

    # --- Model ---
    parser.add_argument(
        "--model",
        default=None,
        help=(
            "Model identifier to use (provider-specific). "
            "E.g. 'gpt-4o', 'claude-3-5-sonnet', 'llama3'. "
            "Defaults to each provider's built-in default."
        ),
    )

    # --- API keys / connection ---
    parser.add_argument(
        "--openai-api-key",
        default=None,
        metavar="KEY",
        help="OpenAI API key (overrides OPENAI_API_KEY env var).",
    )
    parser.add_argument(
        "--anthropic-api-key",
        default=None,
        metavar="KEY",
        help="Anthropic API key (overrides ANTHROPIC_API_KEY env var).",
    )
    parser.add_argument(
        "--ollama-host",
        default=None,
        metavar="URL",
        help="Ollama server URL (overrides OLLAMA_HOST env var, default: http://localhost:11434).",
    )

    # --- Generation parameters ---
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=None,
        help="Maximum tokens in the completion (default: 4096).",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=None,
        help="Sampling temperature (default: 0.3).",
    )

    # --- Style / format ---
    parser.add_argument(
        "--style",
        default=None,
        help="Summary style (e.g. 'concise', 'detailed', 'bullet'). Default: 'concise'.",
    )
    parser.add_argument(
        "--output-format",
        dest="output_format",
        default=None,
        choices=["text", "markdown", "json"],
        help="Output format for the summary (default: text).",
    )

    # --- Misc ---
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=None,
        dest="chunk_size",
        help="Token chunk size for long documents (default: 3000).",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        default=False,
        help="Enable verbose/debug logging.",
    )

    return parser


def run(argv: Optional[list[str]] = None) -> int:
    """
    Entry point for the CLI.

    Returns:
        Exit code (0 = success, non-zero = error).
    """
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.verbose:
        import logging
        logging.getLogger("summarizer").setLevel(logging.DEBUG)

    # Build config: start from env, then apply CLI overrides
    config = Config.from_env()

    overrides: dict[str, object] = {}
    if args.provider is not None:
        overrides["provider"] = args.provider
    if args.model is not None:
        overrides["model"] = args.model
    if args.openai_api_key is not None:
        overrides["openai_api_key"] = args.openai_api_key
    if args.anthropic_api_key is not None:
        overrides["anthropic_api_key"] = args.anthropic_api_key
    if args.ollama_host is not None:
        overrides["ollama_host"] = args.ollama_host
    if args.max_tokens is not None:
        overrides["max_tokens"] = args.max_tokens
    if args.temperature is not None:
        overrides["temperature"] = args.temperature
    if args.style is not None:
        overrides["style"] = args.style
    if args.output_format is not None:
        overrides["output_format"] = args.output_format
    if args.chunk_size is not None:
        overrides["chunk_size"] = args.chunk_size

    if overrides:
        config = config.with_overrides(**overrides)

    logger.debug("Effective config: provider=%s, model=%s", config.provider, config.model)

    try:
        result = summarize(args.input, config=config)
        print(result)
        return 0
    except LLMError as exc:
        print(f"LLM error: {exc}", file=sys.stderr)
        logger.debug("LLM error details", exc_info=True)
        return 2
    except SummarizerError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        logger.debug("Summarizer error details", exc_info=True)
        return 1
    except KeyboardInterrupt:
        print("\nAborted.", file=sys.stderr)
        return 130


def main() -> None:
    """Console script entry point."""
    sys.exit(run())


if __name__ == "__main__":
    main()
"""Command-line interface for the summarizer."""

from __future__ import annotations

import argparse
import logging
import sys
from typing import NoReturn

from .config import SummarizerConfig
from .exceptions import LLMError, SummarizerError
from .logger import setup_logging


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="summarizer",
        description="Summarize articles and documents using an LLM backend.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  summarizer article.html
  summarizer https://example.com/article --provider anthropic --style bullet
  summarizer article.txt --provider ollama --model llama3
  cat article.txt | summarizer - --provider openai
        """,
    )

    # Positional input
    parser.add_argument(
        "input",
        nargs="?",
        default="-",
        help=(
            "Path to a file, a URL, or '-' to read from stdin "
            "(default: stdin)."
        ),
    )

    # --- Provider selection ---
    parser.add_argument(
        "--provider",
        choices=["openai", "anthropic", "ollama"],
        default=None,
        help=(
            "LLM backend to use. Overrides the LLM_PROVIDER environment variable. "
            "Choices: openai (default), anthropic, ollama."
        ),
    )

    # --- Model ---
    parser.add_argument(
        "--model",
        default=None,
        help=(
            "Model name to use with the selected provider. "
            "Defaults: gpt-4o (openai), claude-3-5-sonnet-20241022 (anthropic), "
            "llama3 (ollama)."
        ),
    )

    # --- Summarization style ---
    parser.add_argument(
        "--style",
        choices=["concise", "detailed", "bullet", "academic"],
        default=None,
        help="Summary style. Defaults to 'concise'.",
    )

    # --- Output format ---
    parser.add_argument(
        "--format",
        dest="output_format",
        choices=["text", "markdown", "json"],
        default=None,
        help="Output format. Defaults to 'text'.",
    )

    # --- Language ---
    parser.add_argument(
        "--language",
        default=None,
        help="Target language for the summary (e.g. 'en', 'fr'). Defaults to 'en'.",
    )

    # --- Token / chunk parameters ---
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=None,
        dest="max_tokens",
        help="Maximum number of tokens in the LLM response.",
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=None,
        dest="chunk_size",
        help="Token budget per text chunk sent to the LLM.",
    )

    # --- Anthropic / Ollama specific ---
    parser.add_argument(
        "--ollama-host",
        default=None,
        dest="ollama_host",
        help=(
            "Base URL for the local Ollama instance "
            "(default: http://localhost:11434). "
            "Overrides the OLLAMA_HOST environment variable."
        ),
    )

    # --- Verbosity ---
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        default=False,
        help="Enable verbose/debug logging.",
    )

    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s 0.1.0",
    )

    return parser


def _apply_cli_overrides(config: SummarizerConfig, args: argparse.Namespace) -> None:
    """Merge CLI argument values into an existing config, overriding where provided."""
    if args.provider is not None:
        config.provider = args.provider  # type: ignore[assignment]
    if args.model is not None:
        config.default_model = args.model
    if args.style is not None:
        config.style = args.style
    if args.output_format is not None:
        config.output_format = args.output_format
    if args.language is not None:
        config.language = args.language
    if args.max_tokens is not None:
        config.max_tokens = args.max_tokens
    if args.chunk_size is not None:
        config.chunk_size = args.chunk_size
    if args.ollama_host is not None:
        config.ollama_host = args.ollama_host
    if args.verbose:
        config.verbose = True


def _read_input(source: str) -> str:
    """Read text from a file path, URL, or stdin ('-')."""
    if source == "-":
        return sys.stdin.read()

    if source.startswith(("http://", "https://")):
        try:
            import requests  # type: ignore

            response = requests.get(source, timeout=30)
            response.raise_for_status()
            return response.text
        except Exception as exc:
            raise SummarizerError(f"Failed to fetch URL '{source}': {exc}") from exc

    try:
        with open(source, "r", encoding="utf-8") as fh:
            return fh.read()
    except OSError as exc:
        raise SummarizerError(f"Could not read file '{source}': {exc}") from exc


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    # Build config from environment, then overlay CLI flags
    config = SummarizerConfig.from_env()
    _apply_cli_overrides(config, args)

    setup_logging(level=logging.DEBUG if config.verbose else logging.WARNING)
    logger = logging.getLogger(__name__)

    try:
        config.validate()
    except ValueError as exc:
        parser.error(str(exc))

    try:
        raw_text = _read_input(args.input)
    except SummarizerError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    if not raw_text.strip():
        print("Error: input is empty.", file=sys.stderr)
        return 1

    from .llm.factory import ProviderFactory
    from .summarize import summarize

    try:
        provider = ProviderFactory.create(config=config)
        logger.info("Using provider: %s", provider.provider_name)

        result = summarize(raw_text, provider=provider, config=config)
        print(result)
        return 0

    except LLMError as exc:
        print(f"LLM error: {exc}", file=sys.stderr)
        return 1
    except SummarizerError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nAborted.", file=sys.stderr)
        return 130


def cli_entry_point() -> NoReturn:
    sys.exit(main())


if __name__ == "__main__":
    cli_entry_point()
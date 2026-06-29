"""Command-line interface for the summarizer."""

from __future__ import annotations

import argparse
import sys

from .config import Config
from .exceptions import LLMError, SummarizerError
from .llm.factory import ProviderFactory, create_provider


def build_parser() -> argparse.ArgumentParser:
    """Construct and return the argument parser."""
    parser = argparse.ArgumentParser(
        prog="summarize",
        description="Summarize articles and documents using an LLM.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  summarize article.html
  summarize https://example.com/article --provider anthropic
  summarize article.txt --provider ollama --model llama3
  summarize article.html --provider openai --model gpt-4o --style bullet
        """,
    )

    # Positional: input
    parser.add_argument(
        "input",
        nargs="?",
        help="Path to a file or URL to summarize. Reads from stdin if omitted.",
    )

    # Provider selection
    parser.add_argument(
        "--provider",
        choices=["openai", "anthropic", "ollama"],
        default=None,
        metavar="PROVIDER",
        help=(
            "LLM provider to use: openai, anthropic, or ollama. "
            "Defaults to the LLM_PROVIDER env var or 'openai'."
        ),
    )

    # Model override
    parser.add_argument(
        "--model",
        default=None,
        help=(
            "Model name override. "
            "Defaults: openai→gpt-4o, anthropic→claude-3-5-sonnet-20241022, ollama→llama3."
        ),
    )

    # Style
    parser.add_argument(
        "--style",
        default=None,
        choices=["concise", "detailed", "bullet"],
        help="Summary style (default: concise).",
    )

    # Language
    parser.add_argument(
        "--language",
        default=None,
        help="Output language for the summary (default: en).",
    )

    # Token limits
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=None,
        dest="max_tokens",
        help="Maximum tokens in the LLM response (default: 1024).",
    )

    parser.add_argument(
        "--max-chunk-tokens",
        type=int,
        default=None,
        dest="max_chunk_tokens",
        help="Maximum tokens per document chunk (default: 3000).",
    )

    # Temperature
    parser.add_argument(
        "--temperature",
        type=float,
        default=None,
        help="Sampling temperature for the LLM (default: 0.3).",
    )

    # Verbose
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        default=False,
        help="Enable verbose output.",
    )

    # List providers
    parser.add_argument(
        "--list-providers",
        action="store_true",
        default=False,
        help="Print available LLM providers and exit.",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    """Entry point for the summarize CLI."""
    parser = build_parser()
    args = parser.parse_args(argv)

    # --list-providers: just print and exit
    if args.list_providers:
        factory = ProviderFactory()
        print("Available LLM providers:")
        for name in factory.available_providers:
            print(f"  {name}")
        return 0

    # Build config: start from env vars, then overlay CLI args
    config = Config.from_env().merge_cli_args(
        provider=args.provider,
        model=args.model,
        style=args.style,
        language=args.language,
        max_tokens=args.max_tokens,
        max_chunk_tokens=args.max_chunk_tokens,
        temperature=args.temperature,
        verbose=True if args.verbose else None,
    )

    if config.verbose:
        print(f"[verbose] Provider : {config.provider}", file=sys.stderr)
        print(f"[verbose] Model    : {config.model or '(provider default)'}", file=sys.stderr)
        print(f"[verbose] Style    : {config.style}", file=sys.stderr)

    # Instantiate the provider early to catch config errors
    try:
        provider = create_provider(config)
    except LLMError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    if config.verbose:
        print(
            f"[verbose] Using model: {config.model or provider.default_model}",
            file=sys.stderr,
        )

    # Read input
    try:
        text = _read_input(args.input)
    except Exception as exc:
        print(f"Error reading input: {exc}", file=sys.stderr)
        return 1

    if not text.strip():
        print("Error: Input is empty.", file=sys.stderr)
        return 1

    # Run summarization
    try:
        from .summarize import summarize

        result = summarize(text, provider=provider, config=config)
        print(result)
        return 0

    except SummarizerError as exc:
        print(f"Summarization failed: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"Unexpected error: {exc}", file=sys.stderr)
        if config.verbose:
            import traceback
            traceback.print_exc()
        return 1


def _read_input(source: str | None) -> str:
    """
    Read text from a file path, URL, or stdin.

    Args:
        source: File path, URL starting with http(s)://, or None for stdin.

    Returns:
        The raw text content.
    """
    if source is None:
        # Read from stdin
        return sys.stdin.read()

    if source.startswith("http://") or source.startswith("https://"):
        try:
            import requests
            response = requests.get(source, timeout=30)
            response.raise_for_status()
            return response.text
        except Exception as exc:
            raise RuntimeError(f"Failed to fetch URL '{source}': {exc}") from exc

    # File path
    try:
        with open(source, encoding="utf-8") as fh:
            return fh.read()
    except OSError as exc:
        raise RuntimeError(f"Cannot read file '{source}': {exc}") from exc


if __name__ == "__main__":
    sys.exit(main())
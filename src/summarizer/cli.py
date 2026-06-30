"""Command-line interface for the summarizer."""

from __future__ import annotations

import argparse
import sys
from typing import Optional

from src.summarizer.config import Config
from src.summarizer.exceptions import LLMError, SummarizerError
from src.summarizer.llm import PROVIDER_NAMES, ProviderFactory
from src.summarizer.logger import get_logger
from src.summarizer.summarize import Summarizer

logger = get_logger(__name__)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="summarizer",
        description="AI-powered text summarizer with multi-provider LLM support.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  summarizer article.txt
  summarizer article.txt --provider anthropic --style bullet
  summarizer article.txt --provider ollama --model llama3
  summarizer https://example.com/article --provider openai --max-length 300
        """,
    )

    # Input
    parser.add_argument(
        "input",
        nargs="?",
        help="Path to a file, URL, or '-' to read from stdin.",
    )

    # Provider selection
    parser.add_argument(
        "--provider",
        choices=list(PROVIDER_NAMES),
        default=None,
        metavar="PROVIDER",
        help=(
            "LLM provider to use. "
            f"Choices: {', '.join(PROVIDER_NAMES)}. "
            "Defaults to the LLM_PROVIDER env var or 'openai'."
        ),
    )

    # Model override
    parser.add_argument(
        "--model",
        default=None,
        metavar="MODEL",
        help=(
            "Override the provider's default model. "
            "Examples: gpt-4o, claude-3-5-sonnet-20241022, llama3."
        ),
    )

    # Summarisation style
    parser.add_argument(
        "--style",
        default=None,
        choices=["paragraph", "bullet", "headline", "tldr"],
        metavar="STYLE",
        help="Summary style: paragraph (default), bullet, headline, tldr.",
    )

    # Length control
    parser.add_argument(
        "--max-length",
        type=int,
        default=None,
        dest="max_length",
        metavar="WORDS",
        help="Approximate maximum word count for the summary.",
    )

    # Generation parameters
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=None,
        dest="max_tokens",
        metavar="N",
        help="Maximum tokens the LLM may generate.",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=None,
        metavar="T",
        help="Sampling temperature (0.0–1.0). Lower = more deterministic.",
    )

    # Chunking
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=None,
        dest="chunk_size",
        metavar="N",
        help="Token budget per chunk when splitting long documents.",
    )

    # Output
    parser.add_argument(
        "--output",
        "-o",
        default=None,
        metavar="FILE",
        help="Write summary to FILE instead of stdout.",
    )

    # Verbosity
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        default=False,
        help="Enable verbose/debug logging.",
    )

    # Ollama helpers
    parser.add_argument(
        "--list-models",
        action="store_true",
        default=False,
        dest="list_models",
        help="List models available on the Ollama instance and exit (requires --provider ollama).",
    )

    return parser


def _build_config(args: argparse.Namespace) -> Config:
    """Merge CLI args on top of environment-based config."""
    overrides: dict[str, object] = {}

    if args.provider is not None:
        overrides["provider"] = args.provider
    if args.model is not None:
        overrides["model"] = args.model
    if args.style is not None:
        overrides["style"] = args.style
    if args.max_length is not None:
        overrides["max_length"] = args.max_length
    if args.max_tokens is not None:
        overrides["max_tokens"] = args.max_tokens
    if args.temperature is not None:
        overrides["temperature"] = args.temperature
    if args.chunk_size is not None:
        overrides["chunk_size"] = args.chunk_size
    if args.verbose:
        overrides["verbose"] = True

    return Config.from_env(**overrides)


def _read_input(source: Optional[str]) -> str:
    """Read text from a file path, URL, or stdin."""
    if source is None or source == "-":
        logger.debug("Reading from stdin.")
        return sys.stdin.read()

    if source.startswith("http://") or source.startswith("https://"):
        logger.debug("Fetching URL: %s", source)
        try:
            import urllib.request
            with urllib.request.urlopen(source, timeout=30) as resp:  # noqa: S310
                raw = resp.read()
                charset = resp.headers.get_content_charset() or "utf-8"
                return raw.decode(charset, errors="replace")
        except Exception as exc:
            print(f"Error fetching URL: {exc}", file=sys.stderr)
            sys.exit(1)

    try:
        with open(source, "r", encoding="utf-8", errors="replace") as fh:
            return fh.read()
    except OSError as exc:
        print(f"Error reading file '{source}': {exc}", file=sys.stderr)
        sys.exit(1)


def main(argv: Optional[list[str]] = None) -> int:
    """Entry point. Returns an exit code."""
    parser = build_parser()
    args = parser.parse_args(argv)

    config = _build_config(args)

    if config.verbose:
        import logging
        logging.getLogger().setLevel(logging.DEBUG)

    # --list-models shortcut (Ollama only)
    if args.list_models:
        if config.provider != "ollama":
            print(
                "Error: --list-models is only supported with --provider ollama.",
                file=sys.stderr,
            )
            return 1
        try:
            provider = ProviderFactory.create(config)
            models = provider.list_models()  # type: ignore[attr-defined]
            if models:
                print("Available Ollama models:")
                for m in models:
                    print(f"  {m}")
            else:
                print("No models found. Pull one with: ollama pull llama3")
            return 0
        except LLMError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 1

    if args.input is None:
        # No input and no special flag – print help
        parser.print_help()
        return 0

    text = _read_input(args.input)
    if not text.strip():
        print("Error: Input is empty.", file=sys.stderr)
        return 1

    logger.debug(
        "Config: provider=%s, model=%s, style=%s",
        config.provider,
        config.model,
        config.style,
    )

    try:
        provider = ProviderFactory.create(config)
        summarizer = Summarizer(provider=provider, config=config)
        summary = summarizer.summarize(text)
    except (LLMError, SummarizerError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    if args.output:
        try:
            with open(args.output, "w", encoding="utf-8") as fh:
                fh.write(summary)
                if not summary.endswith("\n"):
                    fh.write("\n")
            print(f"Summary written to '{args.output}'.")
        except OSError as exc:
            print(f"Error writing output: {exc}", file=sys.stderr)
            return 1
    else:
        print(summary)

    return 0


if __name__ == "__main__":
    sys.exit(main())
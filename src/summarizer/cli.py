"""Command-line interface for the summarizer."""

from __future__ import annotations

import argparse
import sys
from typing import Optional

from .config import SummarizerConfig
from .exceptions import LLMError, SummarizerError
from .llm.factory import SUPPORTED_PROVIDERS, ProviderFactory
from .logger import get_logger
from .summarize import summarize

logger = get_logger(__name__)


def build_parser() -> argparse.ArgumentParser:
    """Build and return the CLI argument parser."""
    parser = argparse.ArgumentParser(
        prog="summarizer",
        description="Summarize articles and documents using an LLM backend.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  summarizer article.html
  summarizer https://example.com/article --provider anthropic
  summarizer article.txt --provider ollama --ollama-model llama3.2
  summarizer article.html --provider openai --style bullet_points
        """,
    )

    # ── Input ─────────────────────────────────────────────────────────────────
    parser.add_argument(
        "source",
        help="Path to a local file or a URL to fetch and summarize.",
    )

    # ── Provider selection ────────────────────────────────────────────────────
    parser.add_argument(
        "--provider",
        choices=SUPPORTED_PROVIDERS,
        default=None,
        help=(
            f"LLM provider to use. Choices: {', '.join(SUPPORTED_PROVIDERS)}. "
            "Overrides the LLM_PROVIDER environment variable. "
            "(default: openai)"
        ),
    )

    # ── OpenAI options ────────────────────────────────────────────────────────
    parser.add_argument(
        "--openai-model",
        default=None,
        metavar="MODEL",
        help="OpenAI model name (e.g. gpt-4o, gpt-4-turbo). "
             "Overrides OPENAI_MODEL env var.",
    )

    # ── Anthropic options ─────────────────────────────────────────────────────
    parser.add_argument(
        "--anthropic-model",
        default=None,
        metavar="MODEL",
        help="Anthropic Claude model name (e.g. claude-3-5-sonnet-20241022). "
             "Overrides ANTHROPIC_MODEL env var.",
    )

    # ── Ollama options ────────────────────────────────────────────────────────
    parser.add_argument(
        "--ollama-host",
        default=None,
        metavar="URL",
        help="Ollama server base URL. Overrides OLLAMA_HOST env var. "
             "(default: http://localhost:11434)",
    )
    parser.add_argument(
        "--ollama-model",
        default=None,
        metavar="MODEL",
        help="Ollama model name (e.g. llama3.2, mistral). "
             "Overrides OLLAMA_MODEL env var.",
    )

    # ── Output options ────────────────────────────────────────────────────────
    parser.add_argument(
        "--style",
        default="paragraph",
        metavar="STYLE",
        help="Summary style (e.g. paragraph, bullet_points, tldr). "
             "(default: paragraph)",
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=None,
        metavar="N",
        help="Maximum tokens in the LLM response. Overrides MAX_TOKENS env var.",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=None,
        metavar="FLOAT",
        help="Sampling temperature (0.0–1.0). Overrides TEMPERATURE env var.",
    )
    parser.add_argument(
        "--output",
        "-o",
        default=None,
        metavar="FILE",
        help="Write the summary to FILE instead of stdout.",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose/debug logging.",
    )

    return parser


def args_to_config(args: argparse.Namespace) -> SummarizerConfig:
    """Merge CLI arguments into a SummarizerConfig (CLI args take priority)."""
    config = SummarizerConfig.from_env()

    if args.provider is not None:
        config.provider = args.provider

    if args.openai_model is not None:
        config.openai_model = args.openai_model

    if args.anthropic_model is not None:
        config.anthropic_model = args.anthropic_model

    if args.ollama_host is not None:
        config.ollama_host = args.ollama_host

    if args.ollama_model is not None:
        config.ollama_model = args.ollama_model

    if args.max_tokens is not None:
        config.max_tokens = args.max_tokens

    if args.temperature is not None:
        config.temperature = args.temperature

    return config


def main(argv: Optional[list[str]] = None) -> int:
    """Entry point for the CLI. Returns an exit code."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.verbose:
        import logging
        logging.basicConfig(level=logging.DEBUG)
        logger.setLevel(logging.DEBUG)

    # Build config from env + CLI overrides
    config = args_to_config(args)

    try:
        config.validate()
    except ValueError as exc:
        parser.error(str(exc))

    # Instantiate the provider
    try:
        provider = ProviderFactory.create(config)
    except LLMError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    logger.debug(
        "Using provider=%s, model=%s", provider.provider_name, provider.default_model
    )

    # Run the summarization
    try:
        summary = summarize(
            source=args.source,
            provider=provider,
            style=args.style,
            config=config,
        )
    except SummarizerError as exc:
        print(f"Summarization error: {exc}", file=sys.stderr)
        return 1
    except LLMError as exc:
        print(f"LLM error: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        logger.exception("Unexpected error during summarization")
        print(f"Unexpected error: {exc}", file=sys.stderr)
        return 1

    # Output
    if args.output:
        try:
            with open(args.output, "w", encoding="utf-8") as fh:
                fh.write(summary)
            print(f"Summary written to {args.output}")
        except OSError as exc:
            print(f"Failed to write output file: {exc}", file=sys.stderr)
            return 1
    else:
        print(summary)

    return 0


if __name__ == "__main__":
    sys.exit(main())
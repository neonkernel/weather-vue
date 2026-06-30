"""Command-line interface for the summarizer."""

from __future__ import annotations

import argparse
import sys
from typing import Optional

from src.summarizer.config import Config
from src.summarizer.exceptions import LLMError, SummarizerError


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="summarizer",
        description="Summarize articles and documents using LLMs.",
    )

    # --- Input ---
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument(
        "url",
        nargs="?",
        help="URL of the article to summarize.",
    )
    input_group.add_argument(
        "--file",
        "-f",
        metavar="PATH",
        help="Path to a local file to summarize.",
    )
    input_group.add_argument(
        "--stdin",
        action="store_true",
        help="Read input text from stdin.",
    )

    # --- Provider selection ---
    parser.add_argument(
        "--provider",
        "-p",
        choices=["openai", "anthropic", "ollama"],
        default=None,
        help=(
            "LLM backend to use. Overrides the LLM_PROVIDER environment variable. "
            "Choices: openai, anthropic, ollama. (default: openai)"
        ),
    )

    # --- Model ---
    parser.add_argument(
        "--model",
        "-m",
        default=None,
        help=(
            "Model name to use with the selected provider. "
            "Defaults: openai=gpt-4o-mini, anthropic=claude-3-5-haiku-20241022, "
            "ollama=llama3.2"
        ),
    )

    # --- Style ---
    parser.add_argument(
        "--style",
        "-s",
        default="default",
        help="Summary style (default, bullet, executive, technical). Default: default",
    )

    # --- Output ---
    parser.add_argument(
        "--format",
        dest="output_format",
        choices=["text", "markdown", "json"],
        default="text",
        help="Output format. Default: text",
    )

    # --- Token limits ---
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=None,
        help="Maximum tokens for the LLM response.",
    )

    # --- Ollama utilities ---
    parser.add_argument(
        "--list-models",
        action="store_true",
        help="List available models for the selected provider (Ollama only) and exit.",
    )

    # --- Verbosity ---
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging.",
    )

    return parser


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    # Build config with CLI overrides
    config = Config.from_env()

    overrides: dict[str, object] = {}
    if args.provider:
        overrides["provider"] = args.provider
    if args.model:
        overrides["model"] = args.model
    if args.max_tokens:
        overrides["max_tokens"] = args.max_tokens
    if args.style:
        overrides["style"] = args.style
    if args.output_format:
        overrides["output_format"] = args.output_format

    if overrides:
        config = config.with_overrides(**overrides)

    # Handle --list-models
    if args.list_models:
        return _handle_list_models(config)

    # Resolve input text
    try:
        text = _resolve_input(args)
    except SummarizerError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    # Run summarization
    try:
        from src.summarizer.llm.factory import ProviderFactory
        from src.summarizer.summarize import summarize

        provider = ProviderFactory.get_provider(config=config)
        result = summarize(text=text, provider=provider, config=config)
        print(result)
        return 0
    except LLMError as exc:
        print(f"LLM Error: {exc}", file=sys.stderr)
        return 1
    except SummarizerError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


def _handle_list_models(config: Config) -> int:
    """List models for providers that support it (Ollama)."""
    provider_name = config.provider.lower()
    if provider_name != "ollama":
        print(
            f"--list-models is currently only supported for the 'ollama' provider "
            f"(selected: '{provider_name}').",
            file=sys.stderr,
        )
        return 1

    try:
        from src.summarizer.llm.factory import ProviderFactory
        from src.summarizer.llm.providers.ollama_provider import OllamaProvider

        provider = ProviderFactory.get_provider(config=config)
        assert isinstance(provider, OllamaProvider)
        models = provider.list_models()
        if models:
            print("Available Ollama models:")
            for m in models:
                print(f"  - {m}")
        else:
            print("No models found. Pull one with: ollama pull <model>")
        return 0
    except LLMError as exc:
        print(f"LLM Error: {exc}", file=sys.stderr)
        return 1


def _resolve_input(args: argparse.Namespace) -> str:
    """Read and return the raw input text from the appropriate source."""
    if args.stdin:
        return sys.stdin.read()

    if args.file:
        try:
            with open(args.file, encoding="utf-8") as fh:
                return fh.read()
        except OSError as exc:
            raise SummarizerError(f"Cannot read file '{args.file}': {exc}") from exc

    if args.url:
        try:
            from src.summarizer.ingestion import fetch_url
            return fetch_url(args.url)
        except Exception as exc:
            raise SummarizerError(f"Cannot fetch URL '{args.url}': {exc}") from exc

    raise SummarizerError("No input source specified.")


if __name__ == "__main__":
    sys.exit(main())
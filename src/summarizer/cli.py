"""Command-line interface for the summarizer."""

import argparse
import sys
from typing import Optional

from .config import Config
from .exceptions import LLMError, SummarizerError
from .llm.factory import ProviderFactory


def build_parser() -> argparse.ArgumentParser:
    """Construct and return the argument parser."""
    parser = argparse.ArgumentParser(
        prog="summarize",
        description="Summarize articles and documents using an LLM backend.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  summarize https://example.com/article
  summarize article.txt --provider anthropic --style bullet
  summarize article.html --provider ollama --model llama3.2
  summarize https://example.com --provider openai --output-format markdown
        """,
    )

    # --- Input ---
    parser.add_argument(
        "input",
        nargs="?",
        help="URL or path to the document to summarize.",
    )

    # --- Provider selection ---
    parser.add_argument(
        "--provider",
        choices=ProviderFactory.available_providers(),
        default=None,
        metavar="PROVIDER",
        help=(
            "LLM backend to use. Choices: "
            + ", ".join(ProviderFactory.available_providers())
            + ". Defaults to the LLM_PROVIDER env var or 'openai'."
        ),
    )

    # --- Model ---
    parser.add_argument(
        "--model",
        default=None,
        help=(
            "Model identifier to use. Defaults to the provider's default model. "
            "Examples: gpt-4o, claude-3-5-sonnet, llama3.2"
        ),
    )

    # --- Generation parameters ---
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=None,
        dest="max_tokens",
        help="Maximum tokens in the completion (default: 4096).",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=None,
        help="Sampling temperature 0–2 (default: 0.3).",
    )

    # --- Summarisation style ---
    parser.add_argument(
        "--style",
        default=None,
        choices=["concise", "detailed", "bullet", "academic"],
        help="Summary style (default: concise).",
    )
    parser.add_argument(
        "--language",
        default=None,
        help="Output language, e.g. 'en', 'fr', 'de' (default: en).",
    )

    # --- Output format ---
    parser.add_argument(
        "--output-format",
        default=None,
        dest="output_format",
        choices=["text", "markdown", "json"],
        help="Output format (default: text).",
    )

    # --- Misc ---
    parser.add_argument(
        "--list-models",
        action="store_true",
        default=False,
        help="List available models for the selected provider and exit.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s 0.1.0",
    )

    return parser


def list_models_for_provider(config: Config) -> None:
    """Print available models for the configured provider and exit."""
    try:
        provider = ProviderFactory.create(config)
        if hasattr(provider, "list_models"):
            models = provider.list_models()
            if models:
                print(f"Available models for provider '{config.provider}':")
                for m in models:
                    print(f"  - {m}")
            else:
                print(f"No models found for provider '{config.provider}'.")
        else:
            print(
                f"Provider '{config.provider}' does not support model listing. "
                f"Default model: {provider.get_default_model()}"
            )
    except LLMError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)


def main(argv: Optional[list] = None) -> int:
    """
    Entry point for the CLI.

    Args:
        argv: Argument list (defaults to sys.argv[1:]).

    Returns:
        Exit code (0 = success, non-zero = error).
    """
    parser = build_parser()
    args = parser.parse_args(argv)

    # Build config: env vars → CLI overrides
    config = Config.from_env()
    config.update_from_cli(args)

    # Handle --list-models
    if args.list_models:
        list_models_for_provider(config)
        return 0

    # Require input when not listing models
    if not args.input:
        parser.print_help()
        return 1

    try:
        # Lazy import to avoid circular dependency at module load
        from .summarize import summarize_document

        result = summarize_document(args.input, config)
        print(result)
        return 0

    except LLMError as exc:
        print(f"LLM Error: {exc}", file=sys.stderr)
        return 2
    except SummarizerError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nAborted.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    sys.exit(main())
"""Command-line interface for the summarizer."""
from __future__ import annotations

import argparse
import sys
from typing import Optional


def build_parser() -> argparse.ArgumentParser:
    """Construct and return the argument parser."""
    parser = argparse.ArgumentParser(
        prog="summarizer",
        description="Summarize articles and documents using LLMs.",
    )

    # Input
    parser.add_argument(
        "input",
        nargs="?",
        help="URL or file path to summarize. Reads from stdin if omitted.",
    )

    # Provider selection
    parser.add_argument(
        "--provider",
        choices=["openai", "anthropic", "ollama"],
        default=None,
        help=(
            "LLM backend to use. Overrides the LLM_PROVIDER environment variable. "
            "Choices: openai (default), anthropic, ollama."
        ),
    )

    # Model override
    parser.add_argument(
        "--model",
        default=None,
        help=(
            "Model name to use. Provider-specific defaults apply when omitted. "
            "Examples: gpt-4o, claude-3-5-sonnet, llama3.2"
        ),
    )

    # Style / output
    parser.add_argument(
        "--style",
        choices=["concise", "detailed", "bullet", "academic"],
        default="concise",
        help="Summary style (default: concise).",
    )
    parser.add_argument(
        "--format",
        dest="output_format",
        choices=["markdown", "plain", "json"],
        default="markdown",
        help="Output format (default: markdown).",
    )
    parser.add_argument(
        "--max-length",
        type=int,
        default=None,
        help="Maximum word count for the summary.",
    )

    # Generation parameters
    parser.add_argument(
        "--temperature",
        type=float,
        default=None,
        help="Sampling temperature (0.0–2.0). Provider default used when omitted.",
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=None,
        help="Maximum tokens in the LLM response.",
    )

    # Ollama-specific
    parser.add_argument(
        "--ollama-host",
        default=None,
        help=(
            "Ollama server URL (default: http://localhost:11434). "
            "Overrides OLLAMA_HOST env var."
        ),
    )

    # Utility flags
    parser.add_argument(
        "--list-models",
        action="store_true",
        help="List available models for the selected provider and exit.",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose/debug output.",
    )

    return parser


def _build_config(args: argparse.Namespace):
    """Construct a Config object from parsed CLI arguments."""
    from src.summarizer.config import Config

    config = Config.from_env()

    # CLI flags override env / defaults
    if args.provider:
        config.provider = args.provider
    if args.model:
        config.model = args.model
    if args.style:
        config.style = args.style
    if args.output_format:
        config.output_format = args.output_format
    if args.max_length is not None:
        config.max_length = args.max_length
    if args.temperature is not None:
        config.temperature = args.temperature
    if args.max_tokens is not None:
        config.max_tokens = args.max_tokens
    if args.ollama_host:
        config.ollama_host = args.ollama_host

    return config


def _list_models(provider_name: str, config) -> None:
    """Print available models for the given provider."""
    from src.summarizer.llm.factory import ProviderFactory

    provider = ProviderFactory.create(provider_name, config)

    if hasattr(provider, "list_models"):
        models = provider.list_models()
        if models:
            print(f"Available {provider_name} models:")
            for m in models:
                print(f"  - {m}")
        else:
            print(f"No models found for provider '{provider_name}'.")
    else:
        print(
            f"Provider '{provider_name}' does not support model listing. "
            f"Default model: {provider.default_model}"
        )


def main(argv: Optional[list[str]] = None) -> int:
    """Entry point. Returns process exit code."""
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        config = _build_config(args)
    except Exception as exc:  # noqa: BLE001
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 1

    # --list-models early exit
    if args.list_models:
        try:
            _list_models(config.provider, config)
        except Exception as exc:  # noqa: BLE001
            print(f"Error listing models: {exc}", file=sys.stderr)
            return 1
        return 0

    # Determine input source
    if args.input:
        input_source = args.input
    elif not sys.stdin.isatty():
        input_source = sys.stdin.read()
    else:
        print("Error: provide an input URL/file or pipe text via stdin.", file=sys.stderr)
        parser.print_help(sys.stderr)
        return 1

    try:
        from src.summarizer.summarize import summarize

        result = summarize(input_source, config=config, verbose=args.verbose)
        print(result)
        return 0

    except Exception as exc:  # noqa: BLE001
        print(f"Error: {exc}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
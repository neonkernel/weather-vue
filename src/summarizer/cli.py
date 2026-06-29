"""Command-line interface for the summarizer."""
from __future__ import annotations

import argparse
import sys
from typing import Optional

from src.summarizer.config import Config
from src.summarizer.exceptions import LLMError, SummarizerError
from src.summarizer.llm.factory import ProviderFactory
from src.summarizer.styles import AVAILABLE_STYLES


def build_parser() -> argparse.ArgumentParser:
    """Construct and return the argument parser."""
    parser = argparse.ArgumentParser(
        prog="summarizer",
        description="Summarize text content using various LLM backends.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  summarizer article.txt
  summarizer article.txt --provider anthropic --style bullet
  summarizer article.txt --provider ollama --model llama3.2
  echo "Some text" | summarizer --provider openai
        """,
    )

    # Input
    parser.add_argument(
        "input",
        nargs="?",
        default="-",
        help="Path to the input file, or '-' to read from stdin (default: stdin)",
    )

    # Provider selection
    parser.add_argument(
        "--provider",
        choices=ProviderFactory.available_providers(),
        default=None,
        metavar="PROVIDER",
        help=(
            f"LLM backend to use. Choices: {', '.join(ProviderFactory.available_providers())}. "
            "Overrides the LLM_PROVIDER env var. (default: openai)"
        ),
    )

    # Model override
    parser.add_argument(
        "--model",
        default=None,
        help=(
            "Model name to use (provider-specific). "
            "Overrides the provider's default model and the OPENAI_MODEL / "
            "ANTHROPIC_MODEL / OLLAMA_MODEL env vars."
        ),
    )

    # Summary style
    parser.add_argument(
        "--style",
        choices=AVAILABLE_STYLES,
        default=None,
        help="Summary style to apply. (default: concise)",
    )

    # Output options
    parser.add_argument(
        "--output",
        "-o",
        default=None,
        help="Write the summary to this file instead of stdout.",
    )

    # Token / chunk settings
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=None,
        help="Maximum number of tokens in the LLM response. (default: 1024)",
    )
    parser.add_argument(
        "--chunk-tokens",
        type=int,
        default=None,
        help="Maximum tokens per chunk when splitting long documents. (default: 3000)",
    )

    # Verbosity
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        default=False,
        help="Enable verbose logging.",
    )

    # List available Ollama models
    parser.add_argument(
        "--list-models",
        action="store_true",
        default=False,
        help="List available models for the selected provider and exit (Ollama only).",
    )

    return parser


def read_input(path: str) -> str:
    """Read text from a file path or stdin ('-')."""
    if path == "-":
        if sys.stdin.isatty():
            print("Reading from stdin (press Ctrl+D when done):", file=sys.stderr)
        return sys.stdin.read()
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return fh.read()
    except FileNotFoundError:
        raise SummarizerError(f"Input file not found: {path}")
    except PermissionError:
        raise SummarizerError(f"Permission denied reading: {path}")


def write_output(text: str, path: Optional[str]) -> None:
    """Write text to a file or stdout."""
    if path:
        try:
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(text)
        except PermissionError:
            raise SummarizerError(f"Permission denied writing to: {path}")
    else:
        print(text)


def main(argv: Optional[list[str]] = None) -> int:
    """
    Entry point for the CLI.

    Returns:
        Exit code (0 = success, non-zero = error).
    """
    parser = build_parser()
    args = parser.parse_args(argv)

    # Build config, allowing CLI args to override env/defaults
    config = Config(
        provider=args.provider or None,  # None means Config picks from env
        style=args.style or None,
        max_output_tokens=args.max_tokens or None,
        max_chunk_tokens=args.chunk_tokens or None,
    )
    # Re-apply provider from CLI (highest priority)
    if args.provider:
        config.provider = args.provider

    try:
        provider = ProviderFactory.create(
            provider_name=args.provider,
            config=config,
        )

        # Handle --list-models (Ollama only for now)
        if args.list_models:
            if hasattr(provider, "list_models"):
                models = provider.list_models()
                if models:
                    print(f"Available models on {provider.provider_name}:")
                    for m in models:
                        print(f"  - {m}")
                else:
                    print(f"No models found for provider '{provider.provider_name}'.")
            else:
                print(
                    f"The '{provider.provider_name}' provider does not support model listing.",
                    file=sys.stderr,
                )
            return 0

        # Read input
        text = read_input(args.input)
        if not text.strip():
            print("Error: Input text is empty.", file=sys.stderr)
            return 1

        if args.verbose:
            print(
                f"[summarizer] Using provider: {provider.provider_name} "
                f"(model: {provider.default_model})",
                file=sys.stderr,
            )

        # Build messages
        style = args.style or config.style or "concise"
        model_override = args.model

        messages = _build_messages(text, style)
        complete_kwargs: dict = {}
        if model_override:
            complete_kwargs["model"] = model_override
        if args.max_tokens:
            complete_kwargs["max_tokens"] = args.max_tokens

        # Call LLM
        summary = provider.complete(messages, **complete_kwargs)

        # Output
        write_output(summary, args.output)
        return 0

    except (LLMError, SummarizerError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nAborted.", file=sys.stderr)
        return 130


def _build_messages(text: str, style: str = "concise") -> list[dict[str, str]]:
    """Construct the messages list for the LLM."""
    style_instructions = {
        "concise": "Provide a concise summary in 2-3 sentences.",
        "detailed": "Provide a detailed summary covering all main points.",
        "bullet": "Summarize the content as a bullet-point list of key takeaways.",
        "eli5": "Explain this content as if the reader is 5 years old.",
        "executive": (
            "Write an executive summary suitable for senior stakeholders: "
            "key decisions, outcomes, and action items only."
        ),
    }
    instruction = style_instructions.get(style, style_instructions["concise"])

    return [
        {
            "role": "system",
            "content": (
                "You are an expert summarizer. Your task is to summarize the provided text "
                f"accurately and concisely. {instruction}"
            ),
        },
        {
            "role": "user",
            "content": f"Please summarize the following text:\n\n{text}",
        },
    ]


if __name__ == "__main__":
    sys.exit(main())
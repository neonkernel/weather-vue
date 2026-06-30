"""Command-line interface for the summarizer."""

from __future__ import annotations

import argparse
import sys
from typing import Optional

from summarizer.config import SummarizerConfig
from summarizer.exceptions import LLMError, SummarizerError
from summarizer.llm.factory import ProviderFactory


def build_parser() -> argparse.ArgumentParser:
    """Construct and return the argument parser."""
    parser = argparse.ArgumentParser(
        prog="summarizer",
        description="Summarize articles and documents using an LLM backend.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  summarizer article.txt
  summarizer https://example.com/article --provider anthropic --style bullet
  summarizer doc.pdf --provider ollama --model llama3.2
  cat article.txt | summarizer -
        """,
    )

    # Input
    parser.add_argument(
        "input",
        nargs="?",
        default="-",
        metavar="INPUT",
        help="File path, URL, or '-' to read from stdin (default: stdin).",
    )

    # Provider selection
    parser.add_argument(
        "--provider",
        choices=ProviderFactory.list_providers(),
        default=None,
        metavar="PROVIDER",
        help=(
            "LLM provider to use. Choices: %(choices)s. "
            "Defaults to the LLM_PROVIDER environment variable or 'openai'."
        ),
    )

    # Model override
    parser.add_argument(
        "--model",
        default=None,
        metavar="MODEL",
        help=(
            "Model name override (e.g. 'gpt-4o', 'claude-3-5-sonnet', 'llama3.2'). "
            "Each provider has its own default when not specified."
        ),
    )

    # Summary style
    parser.add_argument(
        "--style",
        default="concise",
        choices=["concise", "detailed", "bullet", "technical", "eli5"],
        metavar="STYLE",
        help="Summary style. Choices: %(choices)s. (default: %(default)s)",
    )

    # Output control
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=None,
        metavar="N",
        help="Maximum tokens in the LLM response (default: 4096).",
    )

    parser.add_argument(
        "--output",
        "-o",
        default=None,
        metavar="FILE",
        help="Write the summary to FILE instead of stdout.",
    )

    # Verbosity
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging.",
    )

    parser.add_argument(
        "--list-models",
        action="store_true",
        help="List available models for the selected provider and exit (Ollama only).",
    )

    return parser


def build_config(args: argparse.Namespace) -> SummarizerConfig:
    """Build a SummarizerConfig from parsed CLI arguments."""
    kwargs: dict = {}

    if args.provider is not None:
        kwargs["provider"] = args.provider
    if args.model is not None:
        kwargs["model"] = args.model
    if args.max_tokens is not None:
        kwargs["max_tokens"] = args.max_tokens

    kwargs["style"] = args.style

    return SummarizerConfig(**kwargs)


def main(argv: Optional[list[str]] = None) -> int:
    """Entry point for the CLI. Returns an exit code."""
    parser = build_parser()
    args = parser.parse_args(argv)

    config = build_config(args)

    try:
        config.validate()
    except ValueError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 2

    try:
        provider = ProviderFactory.create(config)
    except LLMError as exc:
        print(f"Provider error: {exc}", file=sys.stderr)
        return 1

    # --list-models is only meaningful for Ollama
    if args.list_models:
        if config.provider != "ollama":
            print(
                "Note: --list-models is currently only supported for the 'ollama' provider.",
                file=sys.stderr,
            )
            return 0
        from summarizer.llm.providers.ollama_provider import OllamaProvider
        if isinstance(provider, OllamaProvider):
            try:
                models = provider.list_models()
                if models:
                    print("Available Ollama models:")
                    for m in models:
                        print(f"  {m}")
                else:
                    print("No models found. Pull a model with: ollama pull llama3.2")
            except LLMError as exc:
                print(f"Error listing models: {exc}", file=sys.stderr)
                return 1
        return 0

    if args.verbose:
        print(
            f"Using provider: {provider.get_provider_name()} "
            f"(model: {provider.get_default_model()})",
            file=sys.stderr,
        )

    # Read input
    try:
        if args.input == "-":
            text = sys.stdin.read()
        elif args.input.startswith(("http://", "https://")):
            text = _fetch_url(args.input)
        else:
            with open(args.input, "r", encoding="utf-8") as fh:
                text = fh.read()
    except (OSError, IOError) as exc:
        print(f"Failed to read input: {exc}", file=sys.stderr)
        return 1

    if not text.strip():
        print("Input is empty. Nothing to summarize.", file=sys.stderr)
        return 1

    # Build prompt
    system_prompt = _build_system_prompt(args.style)
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Please summarize the following text:\n\n{text}"},
    ]

    try:
        summary = provider.complete(messages)
    except LLMError as exc:
        print(f"LLM error: {exc}", file=sys.stderr)
        return 1
    except SummarizerError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    # Write output
    if args.output:
        try:
            with open(args.output, "w", encoding="utf-8") as fh:
                fh.write(summary)
                if not summary.endswith("\n"):
                    fh.write("\n")
            if args.verbose:
                print(f"Summary written to {args.output}", file=sys.stderr)
        except OSError as exc:
            print(f"Failed to write output file: {exc}", file=sys.stderr)
            return 1
    else:
        print(summary)

    return 0


def _fetch_url(url: str) -> str:
    """Fetch text content from a URL."""
    try:
        import requests
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        return response.text
    except ImportError:
        raise SummarizerError(
            "requests package is required to fetch URLs. Run: pip install requests"
        )
    except Exception as exc:
        raise SummarizerError(f"Failed to fetch URL '{url}': {exc}") from exc


def _build_system_prompt(style: str) -> str:
    """Return a system prompt appropriate for the requested summary style."""
    prompts = {
        "concise": (
            "You are a helpful assistant that produces concise, accurate summaries. "
            "Capture the key points in a few sentences. Avoid unnecessary detail."
        ),
        "detailed": (
            "You are a helpful assistant that produces thorough, detailed summaries. "
            "Cover all major points, supporting arguments, and conclusions."
        ),
        "bullet": (
            "You are a helpful assistant that summarizes content as a clear, "
            "well-organized bullet-point list. Each bullet should cover one distinct point."
        ),
        "technical": (
            "You are a technical writing assistant. Summarize the content with precision, "
            "preserving technical terminology, methods, and findings."
        ),
        "eli5": (
            "You are a helpful assistant that explains content in very simple language "
            "that a 5-year-old could understand. Use analogies and avoid jargon."
        ),
    }
    return prompts.get(style, prompts["concise"])


if __name__ == "__main__":
    sys.exit(main())
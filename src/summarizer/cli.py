"""Command-line interface for the summarizer."""

import sys
from pathlib import Path

import click

from .formatter import Formatter
from .styles import OutputFormat, SummaryStyle


@click.command()
@click.argument("url_or_file", metavar="URL_OR_FILE")
@click.option(
    "--style",
    type=click.Choice([s.value for s in SummaryStyle], case_sensitive=False),
    default=SummaryStyle.BRIEF.value,
    show_default=True,
    help=(
        "Summary style to use. "
        "'brief' = short executive summary; "
        "'bullets' = bullet-point list; "
        "'detailed' = comprehensive paragraphs; "
        "'eli5' = explain like I'm 5; "
        "'tldr' = one-sentence TL;DR."
    ),
)
@click.option(
    "--format",
    "output_format",
    type=click.Choice([f.value for f in OutputFormat], case_sensitive=False),
    default=OutputFormat.TEXT.value,
    show_default=True,
    help=(
        "Output format. "
        "'text' = plain text; "
        "'markdown' = Markdown with headers and metadata; "
        "'json' = JSON object with full metadata."
    ),
)
@click.option(
    "--output",
    "-o",
    type=click.Path(dir_okay=False, writable=True),
    default=None,
    help="Write output to a file instead of stdout.",
)
@click.option(
    "--model",
    default=None,
    help="LLM model to use for summarization (overrides config default).",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    default=False,
    help="Enable verbose logging.",
)
def main(url_or_file: str, style: str, output_format: str, output: str, model: str, verbose: bool):
    """
    Summarize a URL or local file using an LLM.

    URL_OR_FILE can be an HTTP/HTTPS URL or a path to a local text/HTML file.

    Examples:

    \b
        # Brief summary (default) printed to stdout
        summarize https://example.com/article

    \b
        # Bullet-point summary in Markdown format
        summarize https://example.com/article --style bullets --format markdown

    \b
        # Detailed summary saved to a file
        summarize https://example.com/article --style detailed --output summary.md --format markdown

    \b
        # ELI5 summary as JSON
        summarize https://example.com/article --style eli5 --format json

    \b
        # TL;DR to stdout
        summarize https://example.com/article --style tldr
    """
    # Resolve enums from string values
    summary_style = SummaryStyle(style.lower())
    fmt = OutputFormat(output_format.lower())

    try:
        summary = _run_summarization(url_or_file, summary_style, model, verbose)
    except Exception as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)

    formatter = Formatter()
    result = formatter.format(summary, fmt)

    if output:
        output_path = Path(output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(result, encoding="utf-8")
        click.echo(f"Summary written to {output_path}", err=True)
    else:
        click.echo(result)


def _run_summarization(url_or_file: str, style: SummaryStyle, model: str | None, verbose: bool):
    """
    Orchestrate ingestion → LLM summarization → return Summary object.

    This function wires together the ingestion layer, prompt selection,
    and LLM client. It imports lazily so that missing optional dependencies
    only raise errors when actually needed.
    """
    from .llm.prompts import get_prompt
    from .models import Summary
    from .styles import STYLE_PROMPT_MAP

    # --- Ingestion ---
    text, source_url, title = _ingest(url_or_file, verbose)

    # --- Build prompt ---
    style_key = STYLE_PROMPT_MAP[style]
    prompt = get_prompt(style_key, text)

    # --- Call LLM ---
    body, used_model = _call_llm(prompt, model, verbose)

    # --- Assemble Summary ---
    summary = Summary(
        body=body,
        title=title,
        source_url=source_url,
        model=used_model,
        style=style.value,
    )
    return summary


def _ingest(url_or_file: str, verbose: bool):
    """Ingest content from a URL or local file. Returns (text, source_url, title)."""
    try:
        from .ingestion import ingest  # type: ignore
        result = ingest(url_or_file)
        if isinstance(result, tuple):
            if len(result) == 3:
                return result
            elif len(result) == 2:
                return result[0], result[1], None
        # Plain string returned
        return str(result), url_or_file, None
    except ImportError:
        pass

    # Fallback: read as local file or raise
    path = Path(url_or_file)
    if path.exists():
        if verbose:
            click.echo(f"Reading local file: {path}", err=True)
        return path.read_text(encoding="utf-8"), str(path), path.stem
    else:
        raise FileNotFoundError(
            f"Cannot ingest '{url_or_file}': not a valid file path and ingestion module unavailable."
        )


def _call_llm(prompt: str, model: str | None, verbose: bool):
    """Call the LLM with the prompt. Returns (response_text, model_name)."""
    try:
        from .llm import client as llm_client  # type: ignore
        response = llm_client.complete(prompt, model=model)
        if isinstance(response, tuple):
            return response  # (text, model_name)
        return str(response), model or "unknown"
    except ImportError:
        pass

    try:
        from .llm.client import LLMClient  # type: ignore
        client = LLMClient(model=model)
        response = client.complete(prompt)
        if isinstance(response, tuple):
            return response
        return str(response), model or client.model
    except (ImportError, AttributeError):
        pass

    raise RuntimeError(
        "LLM client is not available. Please ensure the LLM module is properly installed."
    )


if __name__ == "__main__":
    main()
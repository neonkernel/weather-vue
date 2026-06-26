"""Command-line interface for the summarizer."""

import sys
from pathlib import Path

import click

from .styles import OutputFormat, SummaryStyle
from .formatter import Formatter
from .config import Config


@click.command()
@click.argument("source", required=False)
@click.option(
    "--style",
    type=click.Choice([s.value for s in SummaryStyle], case_sensitive=False),
    default=SummaryStyle.BRIEF.value,
    show_default=True,
    help=(
        "Summary style: "
        "'brief' (executive brief), "
        "'bullets' (bullet points), "
        "'detailed' (full analysis), "
        "'eli5' (explain like I'm 5), "
        "'tldr' (one-sentence TL;DR)."
    ),
)
@click.option(
    "--format",
    "output_format",
    type=click.Choice([f.value for f in OutputFormat], case_sensitive=False),
    default=OutputFormat.TEXT.value,
    show_default=True,
    help="Output format: 'text' (plain text), 'markdown', or 'json'.",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(dir_okay=False, writable=True),
    default=None,
    help="Write output to FILE instead of stdout.",
)
@click.option(
    "--model",
    default=None,
    help="Override the LLM model specified in config.",
)
@click.option(
    "--url",
    default=None,
    help="Source URL to attach as metadata (used when SOURCE is a local file or stdin).",
)
@click.option(
    "--mock",
    is_flag=True,
    default=False,
    hidden=True,
    help="Use mock data instead of calling the LLM (for testing).",
)
@click.version_option()
def main(
    source: str | None,
    style: str,
    output_format: str,
    output: str | None,
    model: str | None,
    url: str | None,
    mock: bool,
) -> None:
    """Summarize an article from a URL, local file, or stdin.

    SOURCE can be a URL (https://…), a local file path, or omitted to read from stdin.

    Examples:\n
        summarizer https://example.com/article\n
        summarizer article.txt --style bullets --format markdown\n
        summarizer https://example.com/article --style detailed --format json -o out.json\n
        cat article.txt | summarizer --style eli5\n
        summarizer https://example.com/article --style tldr
    """
    try:
        style_enum = SummaryStyle(style.lower())
        format_enum = OutputFormat(output_format.lower())
    except ValueError as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)

    # Resolve config
    try:
        config = Config.load()
    except Exception as exc:  # noqa: BLE001
        click.echo(f"Configuration error: {exc}", err=True)
        sys.exit(1)

    if model:
        config.model = model

    # Ingest article text
    article_text, source_url = _ingest(source, url)
    if not article_text:
        click.echo("Error: no input text provided.", err=True)
        sys.exit(1)

    # Summarize
    if mock:
        from .data.mockWeather import get_mock_summary  # type: ignore[import]
        summary = get_mock_summary()
    else:
        from .summarize import summarize

        try:
            summary = summarize(
                text=article_text,
                style=style_enum,
                config=config,
                source_url=source_url,
            )
        except Exception as exc:  # noqa: BLE001
            click.echo(f"Summarization failed: {exc}", err=True)
            sys.exit(1)

    # Format output
    formatter = Formatter()
    rendered = formatter.format(summary, format_enum)

    # Write output
    if output:
        out_path = Path(output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(rendered, encoding="utf-8")
        click.echo(f"Output written to {out_path}", err=True)
    else:
        click.echo(rendered)


def _ingest(source: str | None, url_override: str | None) -> tuple[str, str | None]:
    """Read article text from a URL, file path, or stdin.

    Returns:
        A tuple of (article_text, source_url).
    """
    source_url: str | None = url_override

    if source is None:
        # Read from stdin
        if sys.stdin.isatty():
            raise click.UsageError(
                "No SOURCE provided and stdin is a terminal. "
                "Provide a URL, file path, or pipe text via stdin."
            )
        article_text = sys.stdin.read()
        return article_text, source_url

    if source.startswith("http://") or source.startswith("https://"):
        source_url = source_url or source
        article_text = _fetch_url(source)
        return article_text, source_url

    # Local file
    file_path = Path(source)
    if not file_path.exists():
        raise click.BadParameter(f"File not found: {source}", param_hint="SOURCE")
    article_text = file_path.read_text(encoding="utf-8")
    return article_text, source_url


def _fetch_url(url: str) -> str:
    """Fetch and extract text from a URL using the ingestion service."""
    try:
        from .ingestion import fetch_article  # type: ignore[import]
        return fetch_article(url)
    except ImportError:
        # Fallback: plain urllib fetch
        import urllib.request

        with urllib.request.urlopen(url, timeout=15) as response:  # noqa: S310
            raw = response.read().decode("utf-8", errors="replace")
        return raw


if __name__ == "__main__":
    main()
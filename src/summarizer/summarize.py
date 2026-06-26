"""Core summarization logic."""

from .models import Summary
from .styles import SummaryStyle
from .config import Config


def summarize(
    text: str,
    style: SummaryStyle,
    config: "Config",
    source_url: str | None = None,
) -> Summary:
    """Generate a summary for the provided text.

    Args:
        text: The article text to summarize.
        style: The SummaryStyle to use.
        config: Loaded Config instance containing API credentials and model info.
        source_url: Optional source URL to attach as metadata.

    Returns:
        A populated Summary dataclass.
    """
    from .llm.prompts import get_prompt
    from .llm import get_client  # type: ignore[import]

    prompt = get_prompt(style, text)
    client = get_client(config)

    response_text = client.complete(
        system=prompt["system"],
        user=prompt["user"],
        model=config.model,
    )

    # Attempt to extract a title from the first non-empty line if it looks like one
    title = _extract_title(response_text)

    return Summary(
        body=response_text,
        title=title,
        source_url=source_url,
        model=config.model,
        style=style.value,
    )


def _extract_title(text: str) -> str | None:
    """Heuristically extract a title from the first line of a response."""
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    if not lines:
        return None
    first = lines[0]
    # Use as title only if it's short enough to be a heading
    if len(first) <= 120 and not first.endswith("."):
        return first
    return None
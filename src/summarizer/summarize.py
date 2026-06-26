"""Core summarization logic."""

from .config import Config
from .models import Summary
from .styles import SummaryStyle, STYLE_PROMPT_KEYS


def summarize_url(url: str, style: SummaryStyle = SummaryStyle.BRIEF, config: Config = None) -> Summary:
    """
    Fetch the article at `url` and return a Summary.

    Args:
        url: The URL of the article to summarize.
        style: The SummaryStyle to use for the summary.
        config: Optional Config instance; a default is created if omitted.

    Returns:
        A populated Summary dataclass instance.
    """
    if config is None:
        config = Config.load()

    # Import here to avoid circular imports and keep startup fast
    from .ingestion import fetch_article
    from .llm import get_llm_client
    from .llm.prompts import get_prompt, SYSTEM_PROMPT

    # 1. Fetch and extract article text
    article = fetch_article(url)

    # 2. Build the prompt for the requested style
    style_key = STYLE_PROMPT_KEYS[style]
    user_prompt = get_prompt(style_key, article.text)

    # 3. Call the LLM
    client = get_llm_client(config)
    content = client.complete(
        system_prompt=SYSTEM_PROMPT,
        user_prompt=user_prompt,
    )

    # 4. Build and return the Summary
    return Summary(
        content=content,
        title=article.title,
        source_url=url,
        model=config.model,
        style=style.value,
    )
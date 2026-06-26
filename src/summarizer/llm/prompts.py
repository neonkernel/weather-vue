"""Prompt templates for each SummaryStyle."""

from ..styles import SummaryStyle

# ---------------------------------------------------------------------------
# Style-specific system prompts
# ---------------------------------------------------------------------------

_SYSTEM_BASE = (
    "You are an expert summarization assistant. "
    "Your task is to summarize the provided article text accurately and faithfully. "
    "Do not add information that is not present in the source material."
)

STYLE_PROMPTS: dict[SummaryStyle, dict[str, str]] = {
    SummaryStyle.BRIEF: {
        "system": (
            f"{_SYSTEM_BASE} "
            "Produce a concise executive brief of 2–3 short paragraphs. "
            "Lead with the most important finding, then cover key supporting points, "
            "and close with implications or next steps if relevant."
        ),
        "user_prefix": "Write a concise executive brief of the following article:\n\n",
    },
    SummaryStyle.BULLETS: {
        "system": (
            f"{_SYSTEM_BASE} "
            "Produce a bullet-point summary. "
            "Use clear, parallel bullet points (•) that each capture one key fact or idea. "
            "Aim for 5–10 bullets. Do not use sub-bullets unless absolutely necessary."
        ),
        "user_prefix": "Summarize the following article as a bullet-point list of key facts:\n\n",
    },
    SummaryStyle.DETAILED: {
        "system": (
            f"{_SYSTEM_BASE} "
            "Produce a comprehensive, detailed analysis. "
            "Include background context, main arguments, supporting evidence, counterpoints if any, "
            "and a conclusion. Use clear paragraph breaks. "
            "Your response should be thorough — between 400 and 800 words."
        ),
        "user_prefix": "Write a detailed, comprehensive analysis of the following article:\n\n",
    },
    SummaryStyle.ELI5: {
        "system": (
            f"{_SYSTEM_BASE} "
            "Explain the article as if you are talking to a curious 10-year-old child. "
            "Use simple vocabulary, short sentences, and relatable analogies. "
            "Avoid jargon. Make it engaging and easy to understand."
        ),
        "user_prefix": (
            "Explain the following article in very simple terms, "
            "as if explaining to a young child:\n\n"
        ),
    },
    SummaryStyle.TLDR: {
        "system": (
            f"{_SYSTEM_BASE} "
            "Produce a single TL;DR sentence — no more than 30 words — "
            "that captures the single most important takeaway from the article. "
            "Start your response with 'TL;DR:'"
        ),
        "user_prefix": "Write a one-sentence TL;DR for the following article:\n\n",
    },
}


def get_prompt(style: SummaryStyle, article_text: str) -> dict[str, str]:
    """Return system and user messages for the given style.

    Args:
        style: A SummaryStyle enum value.
        article_text: The raw article text to summarize.

    Returns:
        A dict with keys ``system`` and ``user``.
    """
    template = STYLE_PROMPTS.get(style)
    if template is None:
        raise ValueError(f"No prompt template registered for style: {style}")

    return {
        "system": template["system"],
        "user": f"{template['user_prefix']}{article_text}",
    }
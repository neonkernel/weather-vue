"""Prompt templates for each SummaryStyle."""

# Base system prompt used across all styles
SYSTEM_PROMPT = (
    "You are an expert summarizer. Your task is to read the provided text and "
    "produce a high-quality summary according to the requested style. "
    "Be accurate, concise, and faithful to the source material."
)

# Style-specific prompt templates.
# Each template accepts a single `{text}` placeholder.
PROMPT_TEMPLATES = {
    "bullets": (
        "Read the following text and produce a bullet-point list of the key "
        "takeaways. Each bullet should be a concise, self-contained point. "
        "Use plain '-' characters to denote bullets. Aim for 5-10 bullets.\n\n"
        "Text:\n{text}\n\n"
        "Bullet-point summary:"
    ),
    "brief": (
        "Read the following text and write a brief executive summary in 2-3 "
        "short paragraphs. Focus on the most important ideas and conclusions. "
        "Write in clear, professional prose.\n\n"
        "Text:\n{text}\n\n"
        "Executive summary:"
    ),
    "detailed": (
        "Read the following text and produce a comprehensive, detailed summary. "
        "Cover all major points, supporting arguments, evidence, and conclusions. "
        "Organise the summary into clearly labelled sections where appropriate. "
        "Write in clear, formal prose and aim for thoroughness over brevity.\n\n"
        "Text:\n{text}\n\n"
        "Detailed summary:"
    ),
    "eli5": (
        "Read the following text and explain the main ideas as if you were "
        "talking to a 5-year-old child. Use very simple words, short sentences, "
        "and everyday analogies. Avoid jargon entirely.\n\n"
        "Text:\n{text}\n\n"
        "Simple explanation:"
    ),
    "tldr": (
        "Read the following text and write a single-sentence TL;DR summary that "
        "captures the absolute essence of the content. The sentence must be no "
        "longer than 30 words.\n\n"
        "Text:\n{text}\n\n"
        "TL;DR:"
    ),
}


def get_prompt(style_key: str, text: str) -> str:
    """
    Build the user prompt for the given style key and source text.

    Args:
        style_key: One of the keys in PROMPT_TEMPLATES (e.g. 'brief').
        text: The source text to summarize.

    Returns:
        The fully-rendered prompt string.

    Raises:
        KeyError: If style_key is not a recognised style.
    """
    if style_key not in PROMPT_TEMPLATES:
        raise KeyError(
            f"Unknown style key '{style_key}'. "
            f"Valid keys: {list(PROMPT_TEMPLATES.keys())}"
        )
    return PROMPT_TEMPLATES[style_key].format(text=text)
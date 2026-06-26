"""Prompt templates for each SummaryStyle."""

SYSTEM_PROMPT = (
    "You are an expert summarizer. Your task is to summarize the provided text "
    "accurately and concisely, following the specific style instructions given."
)

PROMPT_TEMPLATES = {
    "brief": (
        "Please provide a concise executive brief of the following text. "
        "Write 2-4 sentences that capture the most important points. "
        "Focus on key findings, decisions, or conclusions.\n\n"
        "Text to summarize:\n{text}"
    ),
    "bullets": (
        "Please summarize the following text as a structured bullet-point list. "
        "Use clear, concise bullet points (5-10 points) that highlight the key ideas, "
        "facts, and takeaways. Start each bullet with a dash (-).\n\n"
        "Text to summarize:\n{text}"
    ),
    "detailed": (
        "Please provide a comprehensive and detailed summary of the following text. "
        "Cover all major topics, arguments, evidence, and conclusions. "
        "Organize your summary into logical paragraphs. "
        "Aim for thoroughness while remaining clear and readable.\n\n"
        "Text to summarize:\n{text}"
    ),
    "eli5": (
        "Please explain the following text as if you were talking to a curious 10-year-old. "
        "Use simple words, short sentences, and helpful analogies or examples. "
        "Avoid jargon and technical terms — if you must use them, explain what they mean. "
        "Make it fun and easy to understand.\n\n"
        "Text to summarize:\n{text}"
    ),
    "tldr": (
        "Please provide an ultra-short TL;DR (Too Long; Didn't Read) summary of the following text. "
        "Write exactly 1-2 sentences that capture the absolute essence of the content. "
        "Be as brief as possible while retaining the core message.\n\n"
        "Text to summarize:\n{text}"
    ),
}


def get_prompt(style_key: str, text: str) -> str:
    """
    Get a formatted prompt for the given style and text.

    Args:
        style_key: The prompt template key (e.g., 'brief', 'bullets').
        text: The text to summarize.

    Returns:
        A formatted prompt string ready to send to the LLM.

    Raises:
        KeyError: If the style_key is not recognized.
    """
    if style_key not in PROMPT_TEMPLATES:
        available = ", ".join(PROMPT_TEMPLATES.keys())
        raise KeyError(
            f"Unknown style key '{style_key}'. Available styles: {available}"
        )
    template = PROMPT_TEMPLATES[style_key]
    return template.format(text=text)
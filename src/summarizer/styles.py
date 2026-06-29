"""Available summary styles."""

AVAILABLE_STYLES: list[str] = [
    "concise",
    "detailed",
    "bullet",
    "eli5",
    "executive",
]

STYLE_DESCRIPTIONS: dict[str, str] = {
    "concise": "A brief 2-3 sentence summary of the main points.",
    "detailed": "A comprehensive summary covering all key topics and details.",
    "bullet": "Key takeaways presented as a bullet-point list.",
    "eli5": "A simple explanation suitable for a general audience.",
    "executive": "An executive summary focused on decisions, outcomes, and action items.",
}
"""LLM abstraction layer for the summarizer."""

from summarizer.llm.base import BaseLLMProvider
from summarizer.llm.factory import ProviderFactory

__all__ = [
    "BaseLLMProvider",
    "ProviderFactory",
]
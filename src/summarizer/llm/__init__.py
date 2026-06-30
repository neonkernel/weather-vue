"""LLM abstraction layer for the summarizer."""

from src.summarizer.llm.base import BaseLLMProvider
from src.summarizer.llm.factory import ProviderFactory, PROVIDER_NAMES

__all__ = [
    "BaseLLMProvider",
    "ProviderFactory",
    "PROVIDER_NAMES",
]
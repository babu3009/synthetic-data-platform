"""Deprecated re-exports for LLM factory.

Prefer importing from `app.modules.llm.factory`.
"""

from app.modules.llm.factory import LLMClientFactory  # type: ignore F401

__all__ = ["LLMClientFactory"]
"""LLM service adapters and factory."""

from .factory import LLMClientFactory, ModelConfig
from .clients import BaseLLMClient, OpenAIClient, AnthropicClient, OllamaClient, LMStudioClient

__all__ = [
    "LLMClientFactory",
    "ModelConfig",
    "BaseLLMClient",
    "OpenAIClient",
    "AnthropicClient",
    "OllamaClient",
    "LMStudioClient",
]
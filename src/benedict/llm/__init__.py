"""LLM protocol and implementations."""

from typing import Optional

from .llm_claude import ClaudeLLM
from .llm_mock import MockLLM
from .protocol import LLM

__all__ = ["LLM", "ClaudeLLM", "MockLLM", "create_llm"]


def create_llm(provider: str = "claude", model: Optional[str] = None) -> LLM:
    """Factory function to create LLM instance.

    Args:
        provider: Provider name ("claude" or "mock")
        model: Optional model name (for Claude, defaults to ANTHROPIC_MODEL env var or claude-3-5-sonnet-20241022)

    Returns:
        LLM instance

    Raises:
        ValueError: If provider is unknown
    """
    if provider == "claude":
        return ClaudeLLM(model=model)
    if provider == "mock":
        return MockLLM()
    raise ValueError(f"Unknown provider: {provider}")

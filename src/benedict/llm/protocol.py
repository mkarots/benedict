"""LLM Protocol Definition

Defines the interface for Large Language Model providers.
"""

from typing import Protocol, List, Dict, Any, Union, Optional


class LLM(Protocol):
    """Protocol for LLM providers."""

    def generate(
        self,
        messages: List[Dict[str, Any]],
        system: str = "",
        max_tokens: int = 2000,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> Union[str, Dict[str, Any]]:
        """Generate response from conversation messages.

        Args:
            messages: Conversation history as list of {"role": "user|assistant|tool", "content": "..."}
                     Must include at least one "user" message. Last message should be the current user question.
                     Tool responses should have role "tool" with "tool_call_id" and "content".
            system: System message/instructions
            max_tokens: Maximum tokens in response
            tools: Optional list of tool definitions for function calling

        Returns:
            If tools are provided and LLM requests tool use:
                Dict with "tool_calls" key containing list of tool call requests
            Otherwise:
                Generated text response string
        """
        ...

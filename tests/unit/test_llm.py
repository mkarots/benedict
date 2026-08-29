"""Tests for LLM implementations.

Tests the LLM protocol and mock implementation.
"""

from benedict.llm import MockLLM


def _user(text: str):
    return [{"role": "user", "content": text}]


class TestMockLLM:
    """Tests for MockLLM implementation."""

    def test_initialization(self):
        """Test mock LLM initialization."""
        llm = MockLLM()
        assert llm is not None

    def test_generate_default_response(self):
        """Test generating a default response."""
        llm = MockLLM()
        response = llm.generate(
            messages=_user("What is the architecture?"),
            system="You are a helpful assistant.",
        )

        assert response is not None
        assert isinstance(response, str)
        assert len(response) > 0

    def test_generate_with_history(self):
        """Test generating response with conversation history."""
        llm = MockLLM()
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
            {"role": "user", "content": "How are you?"},
        ]

        response = llm.generate(
            messages=messages,
            system="You are a helpful assistant.",
        )

        assert response is not None
        assert isinstance(response, str)

    def test_generate_with_context(self):
        """Test generating response with a system prompt as context."""
        llm = MockLLM()

        response = llm.generate(
            messages=_user("What language is used?"),
            system="Repository: example-org/repo\nLanguage: Python",
        )

        assert response is not None

    def test_set_response(self):
        """Test setting a custom response."""
        llm = MockLLM()
        custom_response = "This is a custom response"
        llm.set_response(custom_response)

        response = llm.generate(
            messages=_user("Message"),
            system="System",
        )

        assert response == custom_response

    def test_multiple_generations(self):
        """Test generating multiple responses."""
        llm = MockLLM()

        response1 = llm.generate(messages=_user("Message 1"), system="System")
        response2 = llm.generate(messages=_user("Message 2"), system="System")

        assert response1 is not None
        assert response2 is not None

    def test_max_tokens_parameter(self):
        """Test that max_tokens parameter is accepted."""
        llm = MockLLM()

        response = llm.generate(
            messages=_user("Message"),
            system="System",
            max_tokens=100,
        )

        assert response is not None

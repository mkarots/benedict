"""Unit tests for mock LLM and repository reader adapters."""

import pytest

from benedict.llm.llm_mock import MockLLM
from benedict.repo_reader.repo_reader_mock import MockRepoReader


def test_mock_llm_uses_predefined_response():
    llm = MockLLM(responses={"hello": "world"})
    result = llm.generate([{"role": "user", "content": "hello"}])
    assert result == "world"


def test_mock_llm_default_response_includes_prompt():
    llm = MockLLM()
    result = llm.generate([{"role": "user", "content": "explain indexing"}])
    assert "explain indexing" in result
    assert result.startswith("[Mock LLM Response")


def test_mock_llm_handles_empty_and_list_content():
    llm = MockLLM()
    assert "No messages" in llm.generate([])
    result = llm.generate([{"role": "user", "content": [{"type": "text", "text": "list form"}]}])
    assert "list form" in result


def test_mock_repo_reader_read_and_list():
    reader = MockRepoReader(repos={"example-org/example-repo": {"a.py": "print(1)"}})
    assert reader.file_exists("example-org/example-repo", "a.py")
    assert reader.read_file("example-org/example-repo", "a.py") == "print(1)"
    assert reader.list_files("example-org/example-repo") == ["a.py"]
    with pytest.raises(FileNotFoundError):
        reader.read_file("example-org/example-repo", "missing.py")
    with pytest.raises(FileNotFoundError):
        reader.read_file("missing/repo", "a.py")

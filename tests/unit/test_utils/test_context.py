"""Unit tests for context building with mock readers."""

from benedict.repo_reader.repo_reader_mock import MockRepoReader
from benedict.utils.context import build_context, extract_keywords


def test_extract_keywords_filters_short_and_stop_words():
    keywords = extract_keywords("what is the authentication flow")
    assert "authentication" in keywords
    assert "flow" in keywords
    assert "what" not in keywords
    assert "the" not in keywords


def test_build_context_includes_readme_and_keyword_matches():
    reader = MockRepoReader(
        repos={
            "example-org/example-repo": {
                "README.md": "# Example repo",
                "src/authentication.py": "def authenticate():\n    pass\n",
                "src/unrelated.py": "print('nope')\n",
            }
        }
    )
    context = build_context(
        repo="example-org/example-repo",
        question="how does authentication work?",
        repo_reader=reader,
    )
    assert "README.md" in context
    assert "authentication.py" in context
    assert "def authenticate" in context


def test_build_context_reads_requested_file():
    reader = MockRepoReader(
        repos={
            "example-org/example-repo": {
                "README.md": "# Example",
                "src/app.py": "APP = True\n",
            }
        }
    )
    context = build_context(
        repo="example-org/example-repo",
        question="please read src/app.py",
        repo_reader=reader,
    )
    assert "src/app.py" in context
    assert "APP = True" in context

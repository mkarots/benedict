"""Tests for repository reader implementations.

Tests the RepoReader protocol and mock implementation.
"""

from pathlib import Path

from benedict.repo_reader import MockRepoReader
from benedict.repo_reader.repo_reader_local import LocalRepoReader
from benedict.repo_reader.repo_reader_mock import DEFAULT_TEST_REPO


class TestMockRepoReader:
    """Tests for MockRepoReader implementation."""

    def test_initialization(self):
        """Test mock repo reader initialization."""
        reader = MockRepoReader()
        assert reader is not None

    def test_add_file(self):
        """Test adding a file to the mock reader."""
        reader = MockRepoReader()
        reader.add_file("README.md", "# Test\nThis is a test file.")

        files = reader.list_files(DEFAULT_TEST_REPO)
        assert "README.md" in files

    def test_read_file(self):
        """Test reading a file."""
        reader = MockRepoReader()
        content = "# Test\nThis is a test file."
        reader.add_file("README.md", content)

        read_content = reader.read_file(DEFAULT_TEST_REPO, "README.md")
        assert read_content == content

    def test_read_nonexistent_file(self):
        """Test reading a file that doesn't exist."""
        reader = MockRepoReader()

        try:
            reader.read_file(DEFAULT_TEST_REPO, "nonexistent.txt")
        except FileNotFoundError:
            return
        raise AssertionError("expected FileNotFoundError for a missing file")

    def test_list_files_empty(self):
        """Test listing files when repository is empty."""
        reader = MockRepoReader()
        files = reader.list_files(DEFAULT_TEST_REPO)

        assert isinstance(files, list)
        assert len(files) == 0

    def test_list_files_with_content(self):
        """Test listing files with content."""
        reader = MockRepoReader()
        reader.add_file("README.md", "Content")
        reader.add_file("src/main.py", "print('hello')")
        reader.add_file("src/utils.py", "def helper(): pass")

        files = reader.list_files(DEFAULT_TEST_REPO)
        assert len(files) == 3
        assert "README.md" in files
        assert "src/main.py" in files
        assert "src/utils.py" in files

    def test_list_files_with_pattern(self):
        """Test listing files and filtering by suffix."""
        reader = MockRepoReader()
        reader.add_file("README.md", "Content")
        reader.add_file("src/main.py", "print('hello')")
        reader.add_file("src/utils.py", "def helper(): pass")
        reader.add_file("test.txt", "test")

        all_files = reader.list_files(DEFAULT_TEST_REPO)
        py_files = [f for f in all_files if f.endswith(".py")]
        assert len(py_files) == 2

    def test_file_exists(self):
        """Test checking if a file exists."""
        reader = MockRepoReader()
        reader.add_file("README.md", "Content")

        assert reader.file_exists(DEFAULT_TEST_REPO, "README.md")
        assert not reader.file_exists(DEFAULT_TEST_REPO, "nonexistent.txt")

    def test_read_multiple_files(self):
        """Test reading multiple files."""
        reader = MockRepoReader()
        reader.add_file("file1.txt", "Content 1")
        reader.add_file("file2.txt", "Content 2")
        reader.add_file("file3.txt", "Content 3")

        assert reader.read_file(DEFAULT_TEST_REPO, "file1.txt") == "Content 1"
        assert reader.read_file(DEFAULT_TEST_REPO, "file2.txt") == "Content 2"
        assert reader.read_file(DEFAULT_TEST_REPO, "file3.txt") == "Content 3"

    def test_overwrite_file(self):
        """Test overwriting an existing file."""
        reader = MockRepoReader()
        reader.add_file("file.txt", "Original content")
        reader.add_file("file.txt", "New content")

        content = reader.read_file(DEFAULT_TEST_REPO, "file.txt")
        assert content == "New content"


class TestLocalRepoReaderWalk:
    """walk helpers must work on Python 3.10 (no Path.walk)."""

    def test_walk_returns_relative_string_paths(self, tmp_path: Path):
        repo = tmp_path / "acme" / "widget"
        (repo / "src").mkdir(parents=True)
        (repo / "README.md").write_text("hi\n", encoding="utf-8")
        (repo / "src" / "main.py").write_text("print(1)\n", encoding="utf-8")

        reader = LocalRepoReader(base_path=str(tmp_path))
        walked = reader.walk("acme/widget")
        files = reader.walk_files("acme/widget")
        dirs = reader.walk_dirs("acme/widget")

        assert "README.md" in walked
        assert "src/main.py" in walked
        assert "README.md" in files
        assert "src/main.py" in files
        assert all(isinstance(path, str) for path in files)
        assert "src" in dirs

    def test_walk_missing_path_is_empty(self, tmp_path: Path):
        reader = LocalRepoReader(base_path=str(tmp_path))
        assert reader.walk("missing") == []
        assert reader.walk_files("missing") == []
        assert reader.walk_dirs("missing") == []

"""[tool.mypy] is configured for the benedict package with reasonable strictness."""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
PYPROJECT = REPO_ROOT / "pyproject.toml"
DOCS_CI = REPO_ROOT / "docs" / "ci.md"

REQUIRED_MYPY_FLAGS = (
    "disallow_untyped_defs",
    "disallow_incomplete_defs",
    "check_untyped_defs",
    "warn_return_any",
    "warn_redundant_casts",
    "warn_unused_ignores",
    "no_implicit_optional",
    "strict_equality",
)


def _mypy_section() -> str:
    text = PYPROJECT.read_text(encoding="utf-8")
    start = text.index("[tool.mypy]\n")
    rest = text[start + len("[tool.mypy]\n") :]
    next_table = rest.find("\n[")
    body = rest if next_table == -1 else rest[:next_table]
    return "[tool.mypy]\n" + body


def test_tool_mypy_section_exists():
    assert "[tool.mypy]" in PYPROJECT.read_text(encoding="utf-8")


def test_mypy_targets_benedict_on_python_3_10():
    section = _mypy_section()
    assert 'python_version = "3.10"' in section
    assert 'mypy_path = "src"' in section
    assert "explicit_package_bases = true" in section


def test_mypy_uses_reasonable_strictness():
    section = _mypy_section()
    missing = [flag for flag in REQUIRED_MYPY_FLAGS if f"{flag} = true" not in section]
    assert missing == [], f"[tool.mypy] is missing strict flags: {missing}"


def test_mypy_does_not_ignore_package_modules():
    text = PYPROJECT.read_text(encoding="utf-8")
    assert "[[tool.mypy.overrides]]" not in text
    assert "ignore_errors = true" not in text


def test_ci_docs_describe_typed_package_not_an_ignore_list():
    text = DOCS_CI.read_text(encoding="utf-8")
    assert "[tool.mypy]" in text
    assert "disallow_untyped_defs" in text
    assert "older modules is ignored" not in text

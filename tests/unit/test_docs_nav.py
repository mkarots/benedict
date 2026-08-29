"""Docs nav follows the published spine; Markdown in docs/ is registered."""

from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
DOCS = REPO_ROOT / "docs"
MKDOCS = REPO_ROOT / "mkdocs.yml"

# In docs/ but not a published page. See docs/PROCESS.md.
NOT_IN_NAV = frozenset(
    {
        "OPEN_SOURCE_GUIDE_INDEX.md",
        "COMMAND_CLASSIFIER_DESIGN.md",
        "COMMAND_CLASSIFIER_API_DESIGN.md",
        "LLM_COMMAND_CLASSIFIER_DESIGN.md",
    }
)

SPINE_TOP = [
    "Home",
    "Get started",
    "Use",
    "How it works",
    "Reference",
    "Maintain",
]


def _nav_paths(items: list) -> set[str]:
    paths: set[str] = set()
    for item in items:
        if isinstance(item, str):
            paths.add(item)
        elif isinstance(item, dict):
            for value in item.values():
                if isinstance(value, str):
                    paths.add(value)
                elif isinstance(value, list):
                    paths.update(_nav_paths(value))
    return paths


def _top_labels(nav: list) -> list[str]:
    labels: list[str] = []
    for item in nav:
        if isinstance(item, dict):
            labels.append(next(iter(item.keys())))
        else:
            labels.append(item)
    return labels


def test_mkdocs_nav_files_exist():
    cfg = yaml.safe_load(MKDOCS.read_text(encoding="utf-8"))
    assert cfg["docs_dir"] == "docs"
    paths = _nav_paths(cfg["nav"])
    assert paths, "mkdocs.yml nav is empty"
    missing = sorted(p for p in paths if not (DOCS / p).is_file())
    assert missing == [], f"nav points at missing files: {missing}"


def test_docs_markdown_is_in_nav_or_excluded():
    cfg = yaml.safe_load(MKDOCS.read_text(encoding="utf-8"))
    listed = _nav_paths(cfg["nav"])
    on_disk = {p.relative_to(DOCS).as_posix() for p in DOCS.rglob("*.md")}
    stray = sorted(
        p for p in on_disk if p not in listed and p not in NOT_IN_NAV and not p.startswith("adr/")
    )
    assert stray == [], f"Markdown in docs/ is not in mkdocs.yml nav: {stray}"


def test_nav_follows_docs_spine():
    cfg = yaml.safe_load(MKDOCS.read_text(encoding="utf-8"))
    assert _top_labels(cfg["nav"]) == SPINE_TOP
    assert cfg["nav"][0] == {"Home": "index.md"}

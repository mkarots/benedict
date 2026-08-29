"""MkDocs hooks: include the repo CHANGELOG inside the docs site.

Root files cannot live in `docs/`. These hooks copy CHANGELOG.md into
`changelog.md` at build time and rewrite in-repo links so they resolve in MkDocs.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# Pages whose body is replaced from a file outside docs/.
INCLUDED_PAGES = {
    "changelog.md": REPO_ROOT / "CHANGELOG.md",
}

# In docs/ but not a published MkDocs page (see exclude_docs in mkdocs.yml).
UNPUBLISHED_DOCS = frozenset(
    {
        "docs/OPEN_SOURCE_GUIDE_INDEX.md",
    }
)

DEFAULT_BLOB_BASE = "https://github.com/mkarots/benedict/blob/main/"

_MD_LINK = re.compile(r"\]\(([^)]+)\)")
_FRONT_MATTER = re.compile(r"\A---\n.*?\n---\n?", re.DOTALL)

# Root README and other root files that now have an in-docs home.
_ROOT_PAGE = {
    "README.md": "index.md",
    "CHANGELOG.md": "changelog.md",
}


def _split_href(href: str) -> tuple[str, str]:
    if "#" in href:
        path, frag = href.split("#", 1)
        return path, "#" + frag
    return href, ""


def rewrite_root_href(href: str, *, blob_base: str = DEFAULT_BLOB_BASE) -> str:
    """Rewrite a Markdown href so a root file works as a docs/ page."""
    if href.startswith(("http://", "https://", "mailto:")):
        return href

    path, frag = _split_href(href)

    if path in UNPUBLISHED_DOCS or path.startswith("docs/adr/"):
        return f"{blob_base}{path}{frag}"

    if path.startswith("docs/"):
        rest = path[len("docs/") :]
        renamed = {
            "README.md": "index.md",
            "CODE_READING_GUIDE.md": "CODE_MAP.md",
        }
        return renamed.get(rest, rest) + frag

    if path in _ROOT_PAGE:
        return _ROOT_PAGE[path] + frag

    return href


def rewrite_root_markdown(text: str, *, blob_base: str = DEFAULT_BLOB_BASE) -> str:
    """Rewrite Markdown links in a repository-root file for the docs site."""

    def _replace(match: re.Match[str]) -> str:
        href = match.group(1)
        return f"]({rewrite_root_href(href, blob_base=blob_base)})"

    return _MD_LINK.sub(_replace, text)


def merge_stub_and_source(stub: str, source: str, *, blob_base: str = DEFAULT_BLOB_BASE) -> str:
    """Keep the stub's YAML front matter; use rewritten source as the body."""
    body = rewrite_root_markdown(source, blob_base=blob_base)
    match = _FRONT_MATTER.match(stub)
    if match is None:
        return body
    return match.group(0).rstrip() + "\n\n" + body


def _blob_base(config: object) -> str:
    repo_url = getattr(config, "repo_url", None) or DEFAULT_BLOB_BASE.removesuffix("blob/main/")
    return str(repo_url).rstrip("/") + "/blob/main/"


def on_page_markdown(markdown: str, page: object, config: object, files: object) -> str:
    """Replace included stubs with the corresponding root file."""
    del files
    src = getattr(getattr(page, "file", None), "src_uri", None)
    source_path = INCLUDED_PAGES.get(src or "")
    if source_path is None:
        return markdown
    source = source_path.read_text(encoding="utf-8")
    return merge_stub_and_source(markdown, source, blob_base=_blob_base(config))


def on_page_context(context: dict, page: object, config: object, nav: object) -> dict:
    """Point Edit at the root file, not the docs/ stub."""
    del nav
    src = getattr(getattr(page, "file", None), "src_uri", None)
    source_path = INCLUDED_PAGES.get(src or "")
    if source_path is not None:
        repo_url = str(getattr(config, "repo_url", "") or "").rstrip("/")
        relative = source_path.relative_to(REPO_ROOT).as_posix()
        page.edit_url = f"{repo_url}/edit/main/{relative}"
    return context

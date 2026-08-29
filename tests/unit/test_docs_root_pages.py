"""Root CHANGELOG is included in the MkDocs site, not GitHub-linked."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace

REPO_ROOT = Path(__file__).resolve().parents[2]
HOOKS_PATH = REPO_ROOT / "docs" / "mkdocs_hooks.py"
DOCS = REPO_ROOT / "docs"


def _hooks():
    spec = importlib.util.spec_from_file_location("mkdocs_hooks", HOOKS_PATH)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_docs_hrefs_become_in_site_paths():
    hooks = _hooks()
    assert hooks.rewrite_root_href("docs/MCP.md") == "MCP.md"
    assert hooks.rewrite_root_href("docs/adr/0001-local-operator-ui.md") == (
        "https://github.com/mkarots/benedict/blob/main/docs/adr/0001-local-operator-ui.md"
    )
    assert hooks.rewrite_root_href("docs/PROGRESS.md#overview") == "PROGRESS.md#overview"
    assert hooks.rewrite_root_href("CHANGELOG.md") == "changelog.md"
    assert hooks.rewrite_root_href("README.md") == "index.md"
    assert hooks.rewrite_root_href("docs/README.md") == "index.md"
    assert hooks.rewrite_root_href("docs/CODE_READING_GUIDE.md") == "CODE_MAP.md"


def test_unpublished_docs_href_stays_on_github():
    hooks = _hooks()
    href = hooks.rewrite_root_href("docs/OPEN_SOURCE_GUIDE_INDEX.md")
    assert href.startswith("https://github.com/mkarots/benedict/blob/main/")
    assert href.endswith("docs/OPEN_SOURCE_GUIDE_INDEX.md")


def test_external_and_passthrough_hrefs_are_unchanged():
    hooks = _hooks()
    assert hooks.rewrite_root_href("https://docs.astral.sh/uv/") == "https://docs.astral.sh/uv/"
    assert hooks.rewrite_root_href("mailto:dev@example.com") == "mailto:dev@example.com"
    assert hooks.rewrite_root_href("MCP.md") == "MCP.md"


def test_rewrite_root_markdown_rewrites_only_links():
    hooks = _hooks()
    src = (
        "See [MCP](docs/MCP.md) and `docs/MCP.md` and "
        "[guide](docs/OPEN_SOURCE_GUIDE_INDEX.md) and [log](CHANGELOG.md)."
    )
    out = hooks.rewrite_root_markdown(src)
    assert "[MCP](MCP.md)" in out
    assert "`docs/MCP.md`" in out
    assert "https://github.com/mkarots/benedict/blob/main/docs/OPEN_SOURCE_GUIDE_INDEX.md" in out
    assert "[log](changelog.md)" in out


def test_merge_stub_keeps_front_matter():
    hooks = _hooks()
    stub = "---\ntitle: Changelog\n---\n\nstale\n"
    source = "# Changelog\n\nSee [setup](docs/SLACK_SETUP.md).\n"
    out = hooks.merge_stub_and_source(stub, source)
    assert out.startswith("---\ntitle: Changelog")
    assert "# Changelog" in out
    assert "[setup](SLACK_SETUP.md)" in out
    assert "stale" not in out


def test_on_page_markdown_replaces_included_stubs(tmp_path, monkeypatch):
    hooks = _hooks()
    changelog = tmp_path / "CHANGELOG.md"
    changelog.write_text("# Log\n\n[MCP](docs/MCP.md)\n", encoding="utf-8")
    monkeypatch.setitem(hooks.INCLUDED_PAGES, "changelog.md", changelog)

    page = SimpleNamespace(file=SimpleNamespace(src_uri="changelog.md"))
    config = SimpleNamespace(repo_url="https://github.com/mkarots/benedict")
    stub = "---\ntitle: Changelog\n---\n\nplaceholder\n"
    out = hooks.on_page_markdown(stub, page, config, files=None)
    assert "# Log" in out
    assert "[MCP](MCP.md)" in out
    assert "placeholder" not in out


def test_on_page_context_points_edit_at_root_file():
    hooks = _hooks()
    page = SimpleNamespace(file=SimpleNamespace(src_uri="changelog.md"), edit_url="stale")
    config = SimpleNamespace(repo_url="https://github.com/mkarots/benedict")
    hooks.on_page_context({}, page, config, nav=None)
    assert page.edit_url == "https://github.com/mkarots/benedict/edit/main/CHANGELOG.md"


def test_on_page_markdown_leaves_other_pages():
    hooks = _hooks()
    page = SimpleNamespace(file=SimpleNamespace(src_uri="PROCESS.md"))
    markdown = "Do not replace me."
    assert hooks.on_page_markdown(markdown, page, config=None, files=None) == markdown


def test_current_docs_do_not_github_link_readme():
    bounce = "github.com/mkarots/benedict/blob/main/README.md"
    setup = (DOCS / "SLACK_SETUP.md").read_text(encoding="utf-8")
    home = (DOCS / "index.md").read_text(encoding="utf-8")
    assert bounce not in setup
    assert bounce not in home
    assert "(commands.md)" in setup
    assert "(install.md)" in home

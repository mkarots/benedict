# Documentation process

One-sentence summary:
How to browse, add, and update Benedict docs so the catalog, sidebar, and pages stay in sync.

## 1. Overview

**What:**
Docs live in `docs/` as Markdown. [MkDocs Material](https://squidfunk.github.io/mkdocs-material/) is the UI. `mkdocs.yml` is the sidebar. [README.md](README.md) is the catalog.

**Why:**
A folder of Markdown files is not a docs system. Readers need a sidebar and search. Writers need one place to register a page. Reviewers need a strict build that fails on missing files and broken in-docs links.

**When to use:**
- You are adding or renaming a doc
- You are recording a decision
- You are marking a design as historical

## 2. Non-Goals

Not responsible for:

- The product README or CHANGELOG (those stay at the repository root)
- Milestone notes in `plans/`
- Publishing to GitBook

Out of scope: a second chat surface or the operator console. Those are product UI.

## 3. Structure

Three layers. Keep them in sync.

| Layer | File | Role |
| --- | --- | --- |
| Catalog | `docs/README.md` | Find a doc by job |
| Sidebar | `mkdocs.yml` `nav` | Browse in the UI |
| Page | one Markdown file | The content |

Each page appears **once** in `nav`. The catalog may link the same page from more than one table.

## 4. Page types

| Type | Where | Rule |
| --- | --- | --- |
| Current | `docs/*.md` | Behavior that ships today |
| Decision | `docs/adr/NNNN-short-title.md` | One accepted choice. Status line at the top |
| Historical | `docs/*.md` with a **Status** line at the top | Design the runtime no longer implements |
| Process | this file | How to change docs |

Do not mix current behavior and historical claims on one page. If the runtime dropped a feature, move the old design to Historical or add a Status line and stop describing it as current.

## 5. Add a page

1. Write Markdown under `docs/` (or `docs/adr/` for a decision).
2. Add the file **once** to `nav` in `mkdocs.yml`.
3. Add a row to the matching table in [README.md](README.md).
4. Preview: `make docs` and open the page.
5. Check: `make docs-build` must pass (strict mode).
6. If the doc describes shipped behavior, mention it in `CHANGELOG.md`.

### Decisions

Next ADR is `docs/adr/0002-short-title.md`. Copy the shape of [ADR 0001](adr/0001-local-operator-ui.md): Status, Date, Context, Decision, Consequences.

### Design pages

Follow the design-document sections in `CLAUDE.md`: overview, non-goals, terms, happy path, failure modes.

## 6. Update a page

Edit the file in place.

If you rename a file, update `mkdocs.yml`, the catalog, and every in-docs link. `make docs-build` fails on broken in-docs links.

If behavior changed, do not leave the old claim in a current doc. Mark the old page Historical or delete the obsolete section.

## 7. Preview and check

```bash
make docs        # UI at http://127.0.0.1:8000
make docs-build  # strict HTML build into site/
```

`make docs` needs the `docs` extra: `uv pip install -e ".[docs]"` or `make sync-dev`.

## 8. Constraints

- Product docs stay in `docs/`. `plans/` is milestone history, not the catalog.
- Files outside `docs/` cannot appear in the MkDocs sidebar. Link them as GitHub URLs from the catalog.
- Do not edit docs in a hosted GitBook UI. This repo is the source.

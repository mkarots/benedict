Status: Process

# Documentation process

How to add or update a Benedict doc. The MkDocs sidebar is the catalog.

## Overview

Docs live in `docs/` as Markdown. [MkDocs Material](https://squidfunk.github.io/mkdocs-material/) is the UI. `mkdocs.yml` `nav` is the reading order.

Use this page when you add, rename, or reclassify a doc.

## Non-goals

Not responsible for:

- The product README at the repository root (GitHub landing card; edit it there)
- Milestone notes in `plans/`
- Publishing to GitBook

## Structure

Two layers. Keep them in sync.

| Layer | File | Role |
| --- | --- | --- |
| Sidebar | `mkdocs.yml` `nav` | Browse order. Each page once |
| Page | one Markdown file | The content |

Home is `docs/index.md`. Do not add a second catalog page.

## Page types

Put a **Status** line at the top: `Current`, `Decision`, `Historical`, or `Process`.

| Type | Where | Rule |
| --- | --- | --- |
| Current | `docs/*.md` | Behavior that ships today |
| Decision | `docs/adr/NNNN-short-title.md` | One accepted choice |
| Historical | `docs/*.md` | Design the runtime no longer implements |
| Process | this file | How to change docs |

Do not mix current behavior and historical claims on one page.

## Add a page

1. Write Markdown under `docs/` (or `docs/adr/` for a decision).
2. Add the file **once** to `nav` in `mkdocs.yml`, in the section that matches the spine (Get started, Use, How it works, Reference, Decisions, Historical, Maintain).
3. Preview: `make docs` and open the page.
4. Check: `make docs-build` must pass (strict mode).
5. If the doc describes shipped behavior, mention it in `CHANGELOG.md`.

### Decisions

Next ADR is `docs/adr/0003-short-title.md`. Copy [ADR 0001](adr/0001-local-operator-ui.md): Status, Date, Context, Decision, Consequences.

### Design pages

Follow the design-document sections in `CLAUDE.md`: overview, non-goals, terms, happy path, failure modes.

## Update a page

Edit the file in place. If you rename it, update `mkdocs.yml` and every in-docs link. `make docs-build` fails on broken in-docs links.

If behavior changed, do not leave the old claim in a current doc. Move the old page to Historical or delete the obsolete section.

## Preview and check

```bash
make docs        # UI at http://127.0.0.1:8000
make docs-build  # strict HTML build into site/
```

If port 8000 is already taken, `make docs` exits with that message. Use another port:

```bash
DOCS_PORT=8001 make docs
```

`make docs` needs the `docs` extra: `uv pip install -e ".[docs]"` or `make sync-dev`.

## Constraints

- Product docs stay in `docs/`. `plans/` is milestone history, not the sidebar.
- CHANGELOG is included in Maintain via `changelog.md`. Edit `CHANGELOG.md` at the repo root. A build hook copies it.
- Files outside `docs/` (except that changelog include) cannot appear in the sidebar.
- Do not GitHub-link in-repo current docs. Link the MkDocs path.
- Do not edit docs in a hosted GitBook UI. This repo is the source.

# Metadata overlay location

One-sentence summary:
Store generated `.metadata.benedict` files in a workspace sidecar keyed by the full repo name, so default symlink workspaces do not write into the user’s git tree.

**Issue:** [#12](https://github.com/mkarots/benedict/issues/12)  
**Status:** Design (rewritten 2026-08-23)  
**Replaces:** the 19 Aug 2026 draft on this PR

## 1. Overview

**What:**
Benedict generates per-directory YAML sidecars named `.metadata.benedict`. They are directory summaries, not a graph. There are no node IDs, no edges, and no traversal API. A parent file lists child directory names. Search finds files with a tree walk.

**Why:**
Default workspace mode is `symlink`. `MetadataGenerator.write_metadata` writes `directory / ".metadata.benedict"`. Indexing does that for every non-skipped directory, so writes go through the symlink into the user’s clone. Users then gitignore a file they did not ask for.

**When to use:**
Use this document to implement the location change. Do not use it to expand overlay content, invent a metadata graph, or add Slack migrate commands.

## 2. Non-Goals

Not responsible for overlay quality (template summaries, docstring scraping, AST names).

Out of scope:

- `.benedict.method.yaml` (removed as a runtime feature)
- Auto-appending `.gitignore` in the user’s repo
- Requiring `BENEDICT_WORKSPACE_COPY_MODE=copy`
- Automatic deletion of existing in-tree `.metadata.benedict` files
- Opt-in “commit overlays into the repo”
- MCP write path
- Changing the `1.2` boost constant, chunk prefixing, or Chroma schema

## 3. Key Concepts & Terminology

| Term | Meaning |
| --- | --- |
| Overlay | Generated `.metadata.benedict` YAML for one directory |
| In-tree | Overlay sitting next to source (`src/foo/.metadata.benedict`) |
| Sidecar | Overlay stored under the workspace, outside the repo symlink |
| Repo name | Workspace resource name. May contain slashes (`mkarots/benedict`) |
| Locator | Single function that maps `(workspace_root, repo, relative_dir)` → sidecar file path |
| Directory boost | After embedding search, multiply a hit’s score by `1.2` if its directory matched a metadata keyword search |

## 4. High-Level Design

### Main components

One locator. Writer and reader call it. Nothing else knows the sidecar layout.

```
workspaces/{channel_id}/
  mkarots/benedict/          # symlink to the user’s clone (unchanged)
  .benedict/metadata/
    mkarots/benedict/
      .metadata.benedict     # repo root
      src/
        .metadata.benedict
        commands/
          .metadata.benedict
```

Path rule:

```
sidecar = workspace_root / ".benedict" / "metadata" / repo / relative_dir / ".metadata.benedict"
```

`repo` is used as a path prefix in full. Do not strip the first path component. `WorkspaceManager.add_resource` already creates nested directories when `name` contains slashes.

### Data flow

Onboard and index still call `generate_and_write(source_dir)`. The writer asks the locator for the sidecar path and creates parent directories. The user’s clone is not opened for write.

Readers ask the locator first. If the sidecar is missing, they read `source_dir / ".metadata.benedict"` (legacy). `search_metadata` walks the sidecar tree and returns **source-relative** directory paths (`src/commands`, not `.benedict/metadata/mkarots/benedict/src/commands`). Directory boost depends on that mapping.

### Key invariants

1. After onboard or index, `git status` in the source clone does not show new `.metadata.benedict` files.
2. Sidecar paths include the full repo name, so two repos in one workspace cannot collide.
3. Boosting and MCP summary still work after the move.
4. Old in-tree files remain readable until the user deletes them.

## 5. API / Interface

### Locator

Input:

- `workspace_root`: workspace directory for the channel
- `repo`: resource name, possibly `org/repo`
- `relative_dir`: directory relative to the repo root (`Path(".")` for root)

Output:

- sidecar file path as above

Pass `workspace_root` and `repo` into each call. Do not store them on a process-wide `MetadataGenerator` and mutate them per index job.

### Writer

`write_metadata(directory, metadata)` writes to the sidecar when workspace and repo are known. It does not write in-tree.

### Reader

`read_metadata(directory)`:

1. Sidecar, if locator can be applied
2. Else `directory / ".metadata.benedict"`
3. Else `None`

`search_metadata(workspace_path, query, repo=...)` walks `workspace_path / ".benedict" / "metadata" / repo` and yields `{path, metadata}` where `path` is relative to the **repo root**.

`BENEDICT_METADATA_FILE` stays as a single-file override for now. Do not add `BENEDICT_METADATA_SIDECAR` or `use_sidecar` flags.

## 6. Happy Path Example

Step 1: User onboards `mkarots/benedict` with default symlink mode.

Step 2: Benedict writes  
`workspaces/C123/.benedict/metadata/mkarots/benedict/.metadata.benedict`.

Step 3: Index walks directories under the symlink but writes sidecars only.

Step 4: `git status` in the clone is unchanged. MCP `get_repository_summary`, Q&A context, and directory boost read the sidecar (or in-tree leftover).

Result: overlays exist; the clone is clean.

## 7. Edge Cases & Failure Modes

| Case | Handling |
| --- | --- |
| Repo name contains slashes | Locator uses the full name as path parts |
| Two repos in one workspace | Separate trees under `.benedict/metadata/{repo}/` |
| Workspace deleted | Overlays go away. Regenerated on next onboard/index |
| In-tree leftovers | Reader falls back. Writer does not delete them |
| User committed overlays | Leave them. Do not unlink through the symlink |
| Copy workspace mode | Still write sidecar. Do not write into the copy either |
| Locator missing workspace/repo | Do not fall back to in-tree writes. Fail the write and log |
| `search_metadata` path remap wrong | Boost attaches to `.benedict/metadata/...` and is a no-op on real files. This is the main regression. Prove it with the ranking tests below |

## 8. Constraints & Assumptions

- Overlay content stays as it is. Location is the only change.
- Metadata is cheap to regenerate. Persistence across offboard is not required.
- Option B (store under `BENEDICT_DATA_DIR` by repo hash) is deferred. Use it later only if overlays must survive workspace deletion.
- No new Slack commands (`migrate metadata`, `clean metadata`).
- Implementation is a small PR: locator + writer + reader + indexer + MCP, with tests.

## 9. Alternatives Considered

**Workspace sidecar keyed by full repo name** — accepted. Matches how workspaces already name resources. Overlays die with the workspace, which is acceptable.

**Sidecar that strips the first path component** — rejected. That is the 19 Aug draft. It maps `mkarots/benedict/src` to `metadata/benedict/src` and collides on the repo basename.

**One sidecar tree per workspace with no repo prefix** — rejected. Multi-repo workspaces share `src/`.

**Data-dir store keyed by repo hash** — rejected for this change. Needs a stable key and orphan cleanup. Revisit if workspaces become ephemeral.

**Auto-gitignore** — rejected. Mutates a user file. This repo already ignores the filename; user repos still get polluted.

**Copy mode as the fix** — rejected. Expensive and not the default.

**Auto-migrate and delete in-tree files** — rejected for v1. In symlink mode, delete walks into the clone. Stop writing first. Cleanup can be a later, explicit step.

## 10. Open Questions

Q1: Later, should Benedict delete leftover in-tree files it wrote? Default no, unless we can tell generated files from user-committed ones.

Q2: Later, should users opt into in-tree overlays they want to commit? Not in this change.

Q3: Should `BENEDICT_METADATA_FILE` be removed in a later major version? Keep it until nothing uses it.

## 11. Implementation plan

1. Add `metadata_location.py` with `sidecar_path(...)` and tests for `org/repo`, root, and nested dirs.
2. Thread `(workspace_root, repo)` into `MetadataGenerator.write_metadata` and `MetadataReader`.
3. Point indexer overlay generation and `_get_file_metadata_text` at the reader/locator. Stop opening `current_dir / ".metadata.benedict"` by hand.
4. Point MCP `get_repository_summary` at `project.workspace_path` + `project.repo`, not only `project.repo_path`.
5. Rewrite `search_metadata` to walk the sidecar tree and return repo-relative paths.
6. Extract directory boost into a pure function and lock it with ranking tests (below).
7. Update README / MCP docs with the sidecar path. Do not require users to gitignore overlays.

Call sites today: onboard in `agent.py`, recursive generate in `semantic_indexer_chromadb.py`, read in `metadata_reader.py`, MCP `service.py`, `build_context`, classifier metadata tools. Tools currently call `read_metadata(workspace_path)` (workspace root, not repo). Fix that to `workspace_path / repo` as part of this work.

## 12. How to prove ranking and retrieval features

The directory boost is `score *= 1.2` for hits whose directory matched a metadata keyword search, then re-sort. There are **no tests** for it today. A location change can break it silently if sidecar paths leak into `relevant_dir_paths`.

When you add a ranking trick, prove three claims separately. Do not mix them in one test.

### Claim 1 — The transform is correct (contract)

Extract a pure function. Do not go through ChromaDB or the embedding model.

```python
def apply_directory_boost(
    hits: list[dict],
    relevant_dirs: set[str],
    factor: float = 1.2,
) -> list[dict]:
    ...
```

Each `hit` has `file_path`, `score` (already converted from distance), and `content`. The function multiplies matching scores and sorts descending.

Fixture (two hits, **equal** base score):

| file_path | base score | metadata dirs | expected rank |
| --- | --- | --- | --- |
| `src/auth/session.py` | 0.50 | `{src/auth}` | 1, score `0.60` |
| `docs/deploy.md` | 0.50 | `{src/auth}` | 2, score `0.50` |

Tests that belong in CI:

- Equal base scores: the file in a matched dir ranks first.
- Unmatched scores are unchanged.
- A parent dir match boosts nested files (`src/auth` boosts `src/auth/jwt.py`).
- A sidecar path in `relevant_dirs` (`.benedict/metadata/mkarots/benedict/src/auth`) does **not** boost `src/auth/session.py`. This is the location-move regression.
- `org/repo` prefixes are stripped before comparison, or never introduced. Pick one and test it.
- `top_k` is applied after sort, not before.

Do not write `assert score == 0.5 * 1.2` as the only assertion. That restates the constant. Assert **order** and **which rows changed**. Order is what the user sees.

### Claim 2 — The transform is wired (ablation)

Same fake search hits, two calls:

1. `metadata_reader=None` → order is embedding order.
2. Reader returns one directory that matches the query → order matches Claim 1.

Stub the vector store. If a test needs a live `SentenceTransformer` to prove a multiplier, the ranking code is not isolated enough.

Also assert `search_metadata` returns `src/auth`, not a sidecar path. That is a reader test, not a Chroma test.

### Claim 3 — The transform helps answers (quality)

Unit tests cannot prove that `1.2` is the right number, or that Slack replies get better. That needs a small labeled set:

1. Freeze 10–20 questions against a fixture repo (this repo is enough).
2. For each question, list the files that should appear in the top 5.
3. Run three conditions: embeddings only, embeddings + boost, embeddings + chunk prefix.
4. Score with recall@5 and MRR. Record the table in the PR, not only “looks better”.

This is a benchmark, not a default unit test. Run it when you change ranking. Fail CI only if a known-good query drops out of the top 5 (regression), not if MRR moves 0.02.

Do not tune `1.2` against the same queries you report. If you change the constant, hold out a few questions.

### Observability (production)

Contract tests prove the function. They do not prove it fired on a real mention.

The operator UI already records search hits and scores (`build_context` → `record_stage("search", detail={query, hits})`). Extend that payload:

- `relevant_dirs`
- `boosted_paths`
- pre-boost order vs post-boost order

Then a real question is inspectable: open the run, see whether boost fired, see whether order changed. That is the sustainable check for any new retrieval trick (prefix, rerank, hybrid search). If you cannot see the feature in a run, you cannot debug it.

### What not to do

- Do not “prove” boost by logging `score *= 1.2`.
- Do not require a full onboard + Chroma index to test a multiplier.
- Do not gate merge on a vague “answers feel better”.
- Do not add Slack commands to exercise ranking.

### Suggested files

| Test | File | Claim |
| --- | --- | --- |
| Locator paths including `org/repo` | `tests/unit/test_metadata_location.py` | Location |
| Reader fallback sidecar → in-tree | `tests/unit/test_metadata_reader.py` | Location |
| Onboard/index does not write into a symlink source | `tests/unit/test_metadata_write_path.py` | Location |
| `search_metadata` returns repo-relative dirs | `tests/unit/test_metadata_reader.py` | Location + Claim 2 |
| `apply_directory_boost` order and sidecar non-match | `tests/unit/test_directory_boost.py` | Claim 1 |
| Search ablation with a stub store | `tests/unit/test_semantic_search_boost.py` | Claim 2 |
| Golden queries (optional job) | `tests/eval/test_search_ranking.py` | Claim 3 |

## 13. Appendix

### Current writers

- Onboard: `RepoAgent` → `generate_and_write(workspace / repo)` (root only)
- Index: `ChromaDBSemanticIndexer._generate_metadata_overlays` (every non-skipped directory)

### Current readers

- `MetadataReader.read_metadata` / `search_metadata`
- MCP `get_repository_summary` (root summary + purpose)
- `build_context` (root summary, purpose, first five files)
- Classifier tools `get_file_metadata`, `list_key_files`, `get_repository_summary`
- Indexer `_get_file_metadata_text` (opens in-tree files itself)

### Overlay contents (unchanged)

- `summary`: template, e.g. “Code directory with N files and M subdirectories”
- `purpose`: template, e.g. “Source code directory: {name}”
- `files[]`: first docstring line or first `#` comment, plus Python AST names
- `subdirectories[]`: child name and “Contains N Python files”

This is a hint layer. Missing files degrade context; they do not take the product down.

### Changelog of this document

| Date | Change |
| --- | --- |
| 2026-08-19 | Original draft: sidecar, auto-migrate, strip first path component |
| 2026-08-23 | Rewrite: locator keyed by full repo name, no auto-delete, ranking proof method |

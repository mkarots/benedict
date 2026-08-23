# Incremental semantic index

One-sentence summary:
How `@benedict update index` deletes old Chroma chunks and reindexes only changed files.

## 1. Overview

What:
Incremental index updates the Chroma collection for one repo. It removes stale chunks for modified and deleted files, then embeds added and modified files.

Why:
A full rebuild is slow. `@benedict update index` is the write path people should use. If it is slow on an ordinary git diff, people force-reindex and the incremental design is wasted.

When to use:
After local commits, rebases, or any change you want in semantic search. Add `force` only when the collection should be rebuilt from scratch.

## 2. Non-Goals

Not responsible for detecting *which* files changed. That is `RepoChangeDetector` (git) or file mtimes.

Out of scope: replacing git change detection, changing chunk size, or changing the embedding model.

## 3. Key Concepts & Terminology

| Term | Meaning |
| --- | --- |
| Collection | One Chroma collection per repo (`repo_{md5[:16]}`) |
| Chunk | Embedded slice of a file. Metadata includes `file_path` |
| `$in` batch | Chroma where-filter over many `file_path` values at once |

## 4. High-Level Design

Main components:

- `GitChangeDetector` (or mtime fallback) lists added, modified, and deleted files
- `delete_chunks_for_files` loads chunk IDs with batched `file_path $in` queries, then one `delete`
- `_update_index_git` and `_update_index_file_mtime` both call that helper
- `_index_files` re-embeds added and modified files

Data flow:
Git (or mtime) returns path lists. The indexer deletes chunks for `deleted + modified`, then indexes `added + modified`. Collections are already per-repo, so the where-filter does not combine `repo` equality with `$in`.

Key invariants:

- One `delete` (or a small constant number) per update, not one `get` per file
- `$in` lists are chunked (`CHROMA_FILE_PATH_IN_BATCH_SIZE`, default 100). `batch_size <= 0` sends all paths in one query.
- Empty change sets do not call Chroma
- Git deletes chunks for `deleted + modified`. Mtime deletes chunks for modified files only.

## 5. API / Interface

`delete_chunks_for_files(collection, file_paths, *, batch_size=100) -> int`

Input:

- `collection`: Chroma collection for this repo
- `file_paths`: modified and/or deleted paths
- `batch_size`: max paths per `$in` query

Output:

- Number of chunk IDs passed to `delete`, or 0 if nothing was removed

## 6. Happy Path Example

Step 1: `@benedict update index` after a commit that edits `a.py`, `b.py`, and deletes `gone.py`.
Step 2: One `collection.get(where={"file_path": {"$in": ["gone.py", "a.py", "b.py"]}})`.
Step 3: One `collection.delete(ids=...)`.
Result: Old chunks for those files are gone. `a.py` and `b.py` are reindexed.

## 7. Edge Cases & Failure Modes

What can fail:

- A single `$in` batch query can fail. The helper logs a warning and continues with the next batch.
- `delete` can fail. The helper logs a warning and returns 0.
- No matching chunk IDs: no `delete` is issued.

What the system guarantees:

- Empty `file_paths` does not call `get` or `delete`.
- Duplicate paths are queried once.

## 8. Constraints & Assumptions

- Each collection holds one repo.
- Chroma `$in` lists must stay bounded; the helper chunks them.
- Tests use a fake collection. Importing the indexer module still loads sentence-transformers.

## 9. Alternatives Considered

Fetch every chunk for the repo and filter `file_path` in Python — rejected because a 5-file commit in a large repo would still load all metadata.

Copy the mtime query (`repo` equality + `$in`) — rejected because that combination is the Chroma limitation the git path already avoided.

`collection.delete(where=...)` — skipped so the helper can log and test a reliable deleted-ID count.

## 10. Open Questions

None for this change. `$in` batch size 100 is a conservative default.

## 11. Appendix

Issue: [Git incremental index deletes chunks with one Chroma get per changed file #42](https://github.com/mkarots/benedict/issues/42)

Code: `src/benedict/semantic_indexer/semantic_indexer_chromadb.py`
Tests: `tests/unit/test_semantic_indexer_chromadb.py`

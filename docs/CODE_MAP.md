Status: Current

# Code map

One-sentence summary:
Where the code lives, how it is wired, and in what order to read it.

## Overview

**What:**
Module map and reading order for `src/benedict/`.

**Why:**
Request behavior is in [Request path](REQUEST_PATH.md). This page is the file map and the composition root.

**When to use:**
- You are opening the repo for the first time
- You need to know which file owns a feature
- You are adding a dependency and must wire it in `main.py`

## Non-goals

Not responsible for:

- Routing, prompts, and tools on a user request ([Request path](REQUEST_PATH.md))
- Env vars ([Configuration](configuration.md))
- Slack command text ([Slack commands](commands.md))

Out of scope: milestone notes in `plans/`.

## Code terms

| Term | Meaning |
| --- | --- |
| Protocol | Python `Protocol` defining a contract without an implementation |
| Composition root | `main.py` (Slack) or `mcp/server.py` (MCP), where concrete classes are created |
| Workspace | Per-channel directory under `BENEDICT_DATA_DIR` |
| Repo reader | Reads files from the local checkout or the workspace |

Product terms (onboard, retrieve-then-stuff, progress loop): [Home](index.md).

## Layers

1. **Entry** — `main.py` (Slack), `mcp/server.py` (MCP)
2. **Protocols** — `protocols/` (no implementations)
3. **Implementations** — `llm/`, `repo_reader/`, `semantic_indexer/`, and the rest
4. **Core logic** — `agent.py`, `slack_app.py`
5. **Features** — `workspace/`, `metadata/`, `commands/`, `progress/`, `operator_ui/`

### Entry and core

| Path | Role |
| --- | --- |
| `main.py` | Slack composition root |
| `slack_app.py` | Slack Bolt handlers |
| `agent.py` | Commands and conversation |
| `paths.py` | Data-dir and `.env` helpers |
| `mcp/` | MCP server (resolver, read-only service, stdio root) |
| `progress/` | Unattended progress loop |
| `operator_ui/` | Local request debugger |
| `architect/` | Cross-project architect prompts |

### Protocols

| Path | Role |
| --- | --- |
| `protocols/llm.py` | LLM |
| `protocols/repo_reader.py` | Repository file access |
| `protocols/semantic_indexer.py` | Semantic search |
| `protocols/conversation_repository.py` | Conversation persistence |
| `protocols/repo_change_detector.py` | Git change detection |
| `protocols/conversation_history_indexer.py` | Slack history indexing |

### Implementations

| Path | Role |
| --- | --- |
| `llm/llm_claude.py` | Claude |
| `llm/llm_mock.py` | Tests |
| `repo_reader/repo_reader_local.py` | Local filesystem |
| `repo_reader/repo_reader_workspace.py` | Workspace-aware reader |
| `semantic_indexer/semantic_indexer_chromadb.py` | ChromaDB + sentence-transformers |
| `conversation_repository/conversation_repository_json.py` | `state.json` |
| `repo_change_detector/git_change_detector.py` | Incremental index |
| `indexers/slack_history_indexer.py` | Slack history into the workspace |

### Features

| Path | Role |
| --- | --- |
| `workspace/` | Per-channel workspace lifecycle and action log |
| `metadata/` | `.metadata.benedict` generate and read |
| `commands/` | Metadata classifier, GitHub tool, tool loop |
| `models/conversation.py` | Conversation and message models |
| `utils/context.py` | Retrieve-then-stuff context |
| `utils/slack_formatter.py` | Slack reply formatting |

Benedict does not have a method-file subsystem. A `.benedict.method.yaml` in a repository is an ordinary file.

## Composition

Concrete classes are created in `main.py` (Slack) or `mcp/server.py` (MCP), then injected.

```
main.py
  ├─ LLM (optional)
  ├─ RepoReader (optional)
  ├─ WorkspaceManager
  ├─ SemanticIndexer (optional; needs metadata + change detector)
  ├─ ConversationRepository
  ├─ ProgressService (optional; needs LLM)
  └─ RepoAgent
       └─ SlackApp → SocketModeHandler
            └─ Operator UI thread (optional)
```

The MCP process does not start Slack. It reads the same `state.json`, workspaces, and index.

### Invariants

- Concrete classes are instantiated at the composition root
- Dependencies are constructor-injected
- Optional pieces (LLM, indexer, Slack history) log a warning and continue if they fail to start

## How to read the tree

1. **`main.py` or `mcp/server.py`** — what is created, what is optional
2. **`agent.py`** — command handlers and `handle_conversation`
3. **`protocols/`** — contracts
4. **One implementation** (for example `llm/llm_claude.py`) plus its mock
5. **A feature module** (`workspace/`, `metadata/`, `progress/`)

For a user request, switch to [Request path](REQUEST_PATH.md) after step 2.

When you open a file: identify protocol vs implementation vs core logic, list constructor dependencies, and find where it is instantiated (should be the composition root for concrete classes).

## Common paths

**Question (Slack).** `slack_app.py` → `RepoAgent.handle_conversation` → optional metadata shortcut → `build_context()` → optional `run_github` tool loop → Slack reply. Canonical write-up: [Request path](REQUEST_PATH.md).

**Onboard.** `slack_app.py` → `handle_onboard` → `workspace_manager` → channel mapping in `state.json`.

**Index.** First search or `@benedict update index` → `semantic_indexer` → `GitChangeDetector` → ChromaDB.

**Progress.** Timer or `@benedict progress` → `progress/` (snapshot, decide, execute). Spec: [Progress loop](PROGRESS.md).

**MCP ask.** `mcp/server.py` → `BenedictMcpService.ask()` → `build_context()` → one `llm.generate()`. No `RepoAgent`, no Slack history, no tools.

## Patterns

**Protocol.** Define the contract in `protocols/`. Implement it in a sibling package. Tests use the mock.

**Dependency injection.** `RepoAgent` receives `llm` and `repo_reader`. It does not construct them.

**Graceful degradation.** If Claude fails to start, `llm` is `None` and Slack still accepts commands in stub mode.

## Debugging

Use the [operator console](OPERATOR_UI_DESIGN.md) first (`http://127.0.0.1:8765`). It records the run: route, search hits, prompt, tools.

If you still need logs, raise the `benedict` logger to DEBUG. Typical failures:

- LLM stub replies — `llm` is `None`; missing `ANTHROPIC_API_KEY`
- Repository not found — onboard path and `BENEDICT_REPO_SOURCE_DIRS`
- Semantic search empty — indexer never started, or index not built

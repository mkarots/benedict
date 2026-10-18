Status: Current

# System design

One-sentence summary:
How Benedict is built today: two processes, four surfaces, one data directory, and one isolated agent per onboarded repo.

## 1. Overview

**What:**
The architecture of the running system. Processes, surfaces, components, data stores, and request paths as they ship.

**Why:**
Invite the bot, connect a local folder, that channel has a brain. The same memory is available from the IDE. This page is the map of how that works, so a change has a home.

**When to use:**
- You are adding a surface, store, or collaborator
- You need to know which process owns a behavior
- You are tracing a Slack mention, MCP call, progress cycle, or chat-API turn

Related pages: [Install and run](install.md), [Slack commands](commands.md), [MCP](MCP.md), [Progress loop](PROGRESS.md), [Configuration](configuration.md). Product decision: `docs/adr/0004-product-shape.md`.

## 2. Non-Goals

This page does not:

- Specify a future container sandbox, coding executor, or rooted `read_file` tool
- Replace [MCP](MCP.md), [Progress loop](PROGRESS.md), or [Configuration](configuration.md)
- Describe Space or any other product
- Treat MCP or the chat API as a second SKU, index, or product name

Benedict does not ship these today:

- Cloning GitHub for the customer
- A general shell, `read_file` tool, or pull-request opener
- A policy language, allowlist UI, or approval queue
- OpenTelemetry export or a golden-set eval runner
- A method-file runtime (a `.benedict.method.yaml` in a checkout is an ordinary file)

## 3. Key Concepts & Terminology

| Term | Meaning |
| --- | --- |
| **Onboarded repo** | A local folder linked to one Slack channel in `state.json`. The unit of memory, index, and action. |
| **Workspace** | Per-channel directory under `BENEDICT_WORKSPACES_DIR`. Holds the repo symlink or copy, metadata sidecar, conversation history files, and `workspace_log.json`. |
| **RepoAgent** | Slack-process domain object. Commands, conversation, architect queries, and the chat API go through it. MCP does not. |
| **Surface** | A way to talk to Benedict: Slack, MCP, localhost chat API, operator UI. |
| **Bound tool** | A tool that runs one host binary (`gh` or `ntn`) with caller argv. Not a general shell. |
| **Run** | One Slack mention, MCP call, chat-API turn, index job, or progress cycle. Recorded in `runs.jsonl`. |
| **Architect channel** | The only cross-project exception. Searches many repo indexes. Does not merge Slack histories into one assistant. |
| **Data directory** | Shared on-disk store (default `~/.benedict`). Slack and MCP must point at the same path. |

## 4. High-Level Design

Two processes share a data directory. They do not share `RepoAgent`.

The Slack process (`benedict` / `main.py`) is the human surface and the only place the progress loop runs. It also serves the operator UI and the localhost chat API. The MCP process (`benedict-mcp` / `mcp/server.py`) is inbound and read-only. Cursor and Claude Code launch it on stdio.

Each onboarded channel gets its own workspace, code collection, conversation collection, and action log.

```
 Slack mention / thread / timer     Cursor / Claude Code      phone / script
        │                                  │                       │
        ▼                                  ▼                       ▼
  main.py  (Bolt + progress         mcp/server.py (stdio)    POST /v1/chat
            + operator UI                                        (loopback)
            + chat API)
        │                                  │                       │
        ├─ route / classify                ├─ resolve repo         └─ RepoAgent
        ├─ build_context()                 ├─ build_context()         handle_conversation
        ├─ run_tool_loop (gh, ntn)         └─ generate (no tools)
        └─ progress: snapshot → decide → act
                       │
                       ▼
              ~/.benedict
              state.json · workspaces/ · .chroma_db · runs.jsonl
```

Invariants:

1. One channel, one repo. Memory and actions stay there.
2. The folder is already on the host. Benedict does not clone GitHub for the customer.
3. The model does not get a general computer. It gets stuffed context and two bound CLIs.
4. Conversation-path GitHub and Notion writes ask the user first. The progress loop may file an issue without that prompt.
5. Recording a run must not crash Slack, MCP, or the chat API.
6. MCP cannot mutate Slack, GitHub, or metadata.

### 4.1 Processes

| Process | Entry | Owns | Does not own |
| --- | --- | --- | --- |
| Slack | `src/benedict/main.py` (`benedict`) | Socket Mode, `RepoAgent`, progress scheduler, operator UI (`127.0.0.1:8765`), chat API (`127.0.0.1:8766`) | MCP stdio |
| MCP | `src/benedict/mcp/server.py` (`benedict-mcp`) | Project resolve, read-only tools, `ask_benedict` | Slack, progress, chat API, operator UI HTTP |

`main.py` is the Slack composition root. It wires LLM, readers, indexers, `RepoAgent`, the progress scheduler, the operator UI, and the chat API, then starts Socket Mode.

`mcp/server.py` is a second composition root. It wires `ProjectResolver` and `BenedictMcpService`. It does not start Slack or the progress loop.

Optional collaborators degrade. No LLM means stub Slack and no progress. No Chroma means keyword file matching. No `gh` or `ntn` means those tools return an install message.

### 4.2 Surfaces

| Surface | Direction | What it can do |
| --- | --- | --- |
| Slack | human ↔ Benedict | Commands, Q&A, progress posts, thread replies |
| MCP | IDE → Benedict | `list_projects`, `get_repository_summary`, `search_code`, `get_recent_actions`, `ask_benedict` |
| Chat API | local client → Benedict | One conversation turn on the same `RepoAgent` (`POST /v1/chat`) |
| Operator UI | operator → localhost | Read-only activity, runs, workspaces. Does not send Slack or onboard repos |
| GitHub | Benedict → host `gh` | Inspect and, with policy, mutate that repo’s GitHub |
| Notion | Benedict → host `ntn` | Walk and, with policy, edit linked pages |

GitHub and Notion are host CLIs, not in-process SDKs. Auth is whatever `gh auth login` or `ntn login` / `NOTION_API_KEY` already did on that machine.

MCP is the same product. It is not a second index. Benedict does not call other MCP servers.

### 4.3 Slack routing

`slack/app.py` handles `app_mention` and `message`.

1. `@mention`, or a thread Benedict already joined, or a message that looks directed at the bot
2. Commands first: progress, architect onboard, onboard, Notion link/unlink, offboard, status, update index
3. Architect channel → `handle_architect_query`
4. Else conversation → `handle_conversation`

Channel messages also trigger background Slack-history indexing. A reply in a progress-question thread acknowledges the pending question.

Conversation orchestration inside `RepoAgent`:

1. Load the thread from `ConversationManager`
2. Optional metadata-tool shortcut for explicit overlay questions (`get_file_metadata`, `list_key_files`, `get_repository_summary`)
3. `build_context()` plus conversation-history search
4. `run_tool_loop()` with `run_github` and `run_notion` (up to 5 rounds)
5. Save the thread and return a Slack payload

GitHub issue and PR questions do not take the metadata shortcut. They stay on the conversation path so `run_github` can run.

### 4.4 Components

Composition happens at the roots. Tests substitute protocols. Concrete classes are created in `main.py` or `mcp/server.py`, not deep in the tree.

| Component | Module | Role |
| --- | --- | --- |
| `RepoAgent` | `agent.py` | Channel commands, conversation, architect, index update |
| Slack Bolt app | `slack/app.py` | Event handlers, routing, run begin/finish |
| Slack payloads | `slack/payloads.py`, `slack/formatter.py`, `slack/messages.py` | Structured replies and Block Kit |
| `WorkspaceManager` | `workspace/workspace_manager.py` | Per-channel directory; symlink or copy the checkout |
| `ActionLogger` | `workspace/action_logger.py` | `workspace_log.json` (onboard, index, progress) |
| `ConversationManager` | `models/conversation.py` | Thread transcripts keyed by `thread_ts` |
| Conversation repository | `conversation_repository/` | JSON persistence in `state.json` |
| LLM | `llm/` | Claude (`llm_claude.py`). Protocol in `llm/protocol.py` |
| Repo reader | `repo_reader/` | Local files; conversation and MCP reads go through `WorkspaceRepoReader` |
| Semantic indexer | `semantic_indexer/` | Chunk, embed (`all-MiniLM-L6-v2`), search. Incremental via git change detection |
| Metadata overlays | `semantic_indexer/metadata/` | Sidecar first, then leftover in-tree `.metadata.benedict`. Directory boost at search |
| Conversation history indexer | `conversation_history_indexer/` | Slack ingest adapter; Chroma `conversation_*` collections |
| Context builder | `context.py` | Prompt pack for Slack, MCP `ask_benedict`, and architect |
| Tool framework | `tools/tool_framework.py` | Schema, `ToolResult`, `ToolRegistry` |
| Tool loop | `tools/tool_loop.py` | Anthropic tool-calling rounds |
| `RunGithubTool` | `tools/github_tools.py` | Bound `gh` in the workspace checkout |
| `RunNotionTool` | `tools/notion_tools.py` | Bound `ntn` in the process environment |
| Metadata tools | `tools/metadata_tools.py`, `tools/tool_registry_factory.py` | Slack shortcut only |
| Progress loop | `progress/` | Snapshot → JSON decision → at most one action |
| Architect prompts | `architect/` | Cross-project system prompt and context |
| MCP resolver / service | `mcp/project.py`, `mcp/service.py` | Map `repo` / cwd to an onboarded project; read-only ops |
| Operator UI | `operator_ui/` | Loopback HTTP + `runs.jsonl` recorder |
| Chat API | `chat_api.py` | Loopback JSON; calls `RepoAgent.handle_conversation` |
| Paths | `paths.py` | `BENEDICT_DATA_DIR`, `.env` load |
| Chroma helper | `lib/chroma.py` | One client, `repo_*` and `conversation_*` names |

### 4.5 Memory and retrieval

Memory is per onboarded repo. The architect channel lists projects and searches many code collections. It does not fuse Slack histories or write a shared brain.

`build_context()` builds the prompt pack: recent actions, metadata summary, README, a directly named file if asked, then semantic hits (full files, truncated) or keyword fallback. Slack also adds `build_conversation_history_context()`. MCP `ask_benedict` reuses `build_context()` and omits Slack history.

The model has no `read_file` tool. The host picks files and stuffs truncated full-file text into the prompt.

Code search uses `all-MiniLM-L6-v2` and Chroma. Incremental updates use git change detection. Directory metadata can boost ranking. Indexing is explicit (`@benedict update index`) after the first index. Slack may index on first query; MCP `search_code` tells you to run update index if the collection is missing.

One Chroma client, two collection prefixes. Code and conversation stay separate.

### 4.6 Execution and policy

Benedict sandboxes by shrinking what can run, not by wrapping a VM around a shell. The host is trusted (`SECURITY.md` at the repo root). Isolation is per workspace.

When something must execute, it is a bound CLI:

| Guard | `run_github` (`gh`) | `run_notion` (`ntn`) |
| --- | --- | --- |
| Binary | host `gh` only | host `ntn` only |
| Working directory | workspace checkout | process environment |
| Timeout | 30s | 45s |
| Output cap | 32k chars | 32k chars |
| Secrets | redact token-shaped strings; refuse `gh auth token` | redact secrets; refuse `login`, `logout`, `workers oauth token` |
| Shell | argv list, no `git` or `bash` | argv list, no general shell |

Hard stops:

- Conversation path: the prompt tells the model to ask before GitHub create/merge/close/comment and before Notion create/edit/trash.
- Progress path: actions are only `skip`, `ask`, `issue`, `implement`. No merge, close, or comment. Duplicate open-issue titles are skipped. Labels must already exist. `ask` blocks further unattended actions until a thread reply or `progress now`.
- Progress decider returns JSON. Unusable output becomes `skip`.
- MCP cannot mutate.
- Operator UI and chat API bind loopback. The operator UI does not send Slack or onboard repos. The chat API talks to the same agent Slack uses.
- Architect queries are rejected unless the channel is the architect channel.

Who may run the process is an operator concern, not an in-app ACL.

### 4.7 Unattended progress

A daemon thread in the Slack process waits, then `ProgressService.run_all()`. Each project is snapshot → JSON decision → at most one action. A lock prevents overlapping cycles on one project. MCP never runs this loop.

`implement` files or points at an issue and tells Slack. It does not open a pull request.

### 4.8 Observability

The primary object is a **run** (`docs/adr/0001-local-operator-ui.md`). Stages include `route`, `classify`, `search`, `conversation_search`, `context`, `llm`, `tool`, `reply`. Child tool calls nest under the LLM stage. The inspector shows retrieved chunks, files stuffed into the prompt, tool argv, and the last prompt.

Slack, MCP, progress, and the chat API append the same `runs.jsonl` (rotated at 2,000 rows). Chat API rows use `source=phone`. The Slack process serves `http://127.0.0.1:8765` and reloads when MCP writes. Recording swallows exceptions so a bad log cannot fail a mention.

Coarser traces: `workspace_log.json`, process logs via `benedict.lib.logging`, progress fields in `state.json`.

Correctness tests live under `tests/unit` and `tests/integration`. They do not score answer quality against a golden set.

### 4.9 Data stores

| Store | Where | Scope |
| --- | --- | --- |
| Channel → repo map, thread transcripts, progress, architect id | `state.json` | Channel / thread / process |
| Checkout symlink or copy | `workspaces/<channel>/<repo>/` | Channel |
| Metadata overlays | `workspaces/<channel>/metadata/…` (then leftover in-tree `.metadata.benedict`) | Repo |
| Action log | `workspaces/<channel>/workspace_log.json` | Channel |
| Slack history JSON | `workspaces/<channel>/conversation_history/` | Channel |
| Code chunks | Chroma collection `repo_<hash>` | Repo |
| Slack history chunks | Chroma collection `conversation_<hash>` | Channel |
| Run log | `runs.jsonl` | Process (Slack + MCP + chat API) |

Default root: `~/.benedict`. Override with `BENEDICT_DATA_DIR`.

## 5. API / Interface

These are the contracts the running system already exposes. Environment knobs are in [Configuration](configuration.md).

### Slack

Mention `@benedict` (or `@agent`). Commands: onboard, offboard, status, update index, link/unlink Notion, onboard architect, progress. Anything else is repo-scoped conversation. Full table: [Slack commands](commands.md).

Handlers return `SlackPayload` values. `post_reply` renders Block Kit.

### MCP (stdio)

| Tool | Purpose |
| --- | --- |
| `list_projects` | Onboarded channel → repo mappings |
| `get_repository_summary` | Overlay summary and purpose |
| `search_code` | Semantic search over the code index |
| `get_recent_actions` | Recent `workspace_log.json` entries |
| `ask_benedict` | Question from repo context (no Slack history) |

If `repo` is omitted, the server uses cwd when it matches one onboarded clone.

### Chat API (loopback)

| Method | Path | Body / result |
| --- | --- | --- |
| `POST` | `/v1/chat` | JSON `{channel_id, text, session_id}` → `{ok, text, success}` |
| `GET` | `/health` | `{status: "ok"}` |

`session_id` is the conversation key (`thread_ts` inside `RepoAgent`). Bind: `127.0.0.1:8766`. Disable with `BENEDICT_CHAT_API=0`.

### Operator UI (loopback)

| Method | Path | Result |
| --- | --- | --- |
| `GET` | `/` | HTML console |
| `GET` | `/api/status` | Process, model, channels, component health |
| `GET` | `/api/runs` | Recent run summaries (`limit`, `source`, `status`) |
| `GET` | `/api/runs/<id>` | Full run including stages |
| `GET` | `/api/workspaces` | Onboarded workspaces |

Bind: `127.0.0.1:8765`. Disable with `BENEDICT_OPERATOR_UI=0`.

### Tools (Anthropic shape)

`ToolRegistry.to_anthropic_tools()` is what the model may call. Conversation registers `run_github` and `run_notion`. The metadata shortcut registers overlay tools only. MCP tools are the service methods above, not that registry.

## 6. Happy Path Example

Step 1: On a machine that already has `acme/widget`, start `make run`. Invite `@benedict` and run `@benedict onboard repo acme/widget`.

Step 2: Ask in the channel, “How does checkout work?” Slack routes to conversation. Search returns Chroma chunks. `build_context()` stuffs those files. The tool loop may call `run_github` if you asked about a PR. The reply stays in the thread.

Step 3: Open `http://127.0.0.1:8765`. The run shows the route, hits, stuffed files, and prompt.

Step 4: In Cursor, `ask_benedict` answers from the same index. No Slack history. Same `runs.jsonl` with `source=mcp`.

Step 5: A local client posts `POST http://127.0.0.1:8766/v1/chat` with that channel id. `RepoAgent.handle_conversation` runs. The row is `source=phone`.

Step 6: Hours later the progress loop snapshots the repo, files one issue or asks one question, and records `source=progress`.

Result: one repo, one memory, four surfaces, a visible trace. Nothing left the workspace except `gh` / `ntn` / Slack as those tools allow.

## 7. Edge Cases & Failure Modes

| Case | Behavior |
| --- | --- |
| Channel not onboarded | Conversation refuses. Progress skips. MCP lists no match. Chat API returns the not-onboarded payload. |
| Checkout missing | File reads fail. Progress skips with a workspace-missing summary. |
| No Chroma | Keyword filename matching. `search_code` errors if the indexer is absent. |
| Repo not indexed | Slack may index on first query. MCP `search_code` tells you to run `@benedict update index`. |
| `gh` / `ntn` missing or unauthenticated | Tool result explains the host setup. Progress that needs GitHub skips. |
| Model returns prose instead of progress JSON | Decision becomes `skip`. |
| Pending progress question | Further unattended actions wait, unless `progress now`. |
| Architect query in a normal channel | Rejected. |
| Several onboarded repos and MCP omits `repo` | Resolver errors unless cwd matches one clone. |
| Operator UI or chat API port in use | Warning; Slack still runs. |
| Corrupt `runs.jsonl` | Warning; Slack still replies. |
| Tool loop hits the iteration cap | User-facing “try a more specific question.” |
| No `ANTHROPIC_API_KEY` | Slack stub mode. No progress. MCP `ask_benedict` unavailable. |

Guarantees: one project cannot run two progress cycles at once. A recording failure does not fail the user-visible path. Optional collaborators can be absent.

## 8. Constraints & Assumptions

- The Slack process must stay up for mentions, progress, the operator UI, and the chat API. MCP can run alone against the same data dir.
- Workspace symlinks must resolve on the MCP host.
- Claude is the shipped LLM. Tools use Anthropic tool-calling shape.
- Slack history is not on MCP.
- Default progress interval is hours, to avoid issue spam.
- Loopback HTTP has no auth. Do not bind it to a public interface.
- Python 3.10+. Package install from this clone (`benedict`, `benedict-mcp`).

## 9. Alternatives Considered

**Container sandbox + general shell** — rejected for the Slack product. Bound `gh` / `ntn` and stuffed context match “maintain this repo.”

**One shared assistant for the Slack workspace** — rejected in ADR 0004. Isolation is the unit of value.

**MCP as a second product or a second index** — rejected. MCP reads the same data directory.

**Seat-priced IDE SKU** — rejected. Price by Slack workspace or onboarded repo.

**Hosted clone from GitHub** — rejected. Local-folder-first is why enterprise can run the same agent in a VPC.

**Jaeger / OpenTelemetry as the first debugger** — deferred in ADR 0001. A local run log answers “why this reply” the same day.

**Method-file runtime** — removed. Overlay metadata and repo Q&A remain. The YAML file is not consumed as policy.

## 10. Open Questions

Q1: Should `implement` invoke a coding executor (Cursor SDK or a container `run_command`) to open a PR? That would be the first real coding executor and would force a new sandbox story. Current claim: there is no coding executor.

Q2: Should repo readers reject paths that resolve outside the checkout?

Q3: Should there be a golden-set eval for `ask_benedict` and progress decisions, or is the operator UI enough?

Q4: Should the architect channel get a digest of every project’s progress action?

Q5: Should the model get rooted filesystem tools (`read_file`, list, grep) instead of only stuffed context? Current claim: no `read_file` tool.

Q6: Should the chat API stay a Slack-process sidecar, or become a third composition root that does not require Socket Mode tokens?

## Appendix

### Module map

```
src/benedict/
  main.py                 Slack composition root
  agent.py                RepoAgent
  chat_api.py             Loopback JSON conversation
  context.py              Prompt packing
  paths.py                Data dir and .env
  architect/              Cross-project prompt
  conversation_history_indexer/
  conversation_repository/
  llm/                    Claude + mock
  mcp/                    stdio server, resolver, read-only service
  models/                 Conversation, Message
  operator_ui/            Recorder + loopback console
  progress/               snapshot, decide, execute, cycle, scheduler, store
  repo_reader/
  semantic_indexer/       Chroma, metadata, git change detection
  slack/                  Bolt app, payloads, Block Kit
  tools/                  registry, loop, gh, ntn, metadata shortcut
  workspace/              manager, action log
  lib/                    logging, chroma names, dates
```

### Tests

`tests/unit/` for collaborators. `tests/integration/` for wired paths. Progress: `tests/unit/test_progress.py`. Chat API: `tests/unit/test_chat_api.py`. MCP: `tests/unit/test_mcp/`.

Status: Current

# Request path

One-sentence summary:
What Benedict does with a user request, from entry point through routing, prompt building, and tool calls, to the reply — and why each step exists.

## 1. Overview

**What:**
This document traces a Benedict request. It covers Slack mentions, Slack thread replies, and MCP `ask_benedict`. It names the code that runs, what the model sees, and which tools (if any) the model may call. The unattended progress loop is a separate path: [PROGRESS.md](PROGRESS.md).

**Why:**
Slack and MCP share data (state, workspaces, index) but they do **not** share one request handler. Existing architecture docs list modules. They do not say which path a request takes, or why two LLM tool mechanisms exist.

**When to use:**
- You need to change prompt, tools, routing, or context
- You are debugging a wrong or missing answer
- You are deciding whether a new capability belongs on Slack, MCP, or both

## 2. Non-Goals

Not responsible for:

- Onboarding, indexing, or workspace lifecycle internals
- Operator UI rendering (it *records* this path; see [OPERATOR_UI_DESIGN.md](OPERATOR_UI_DESIGN.md))
- Incremental index mechanics (git-based reindex; not a separate design page)

Out of scope: a single unified agent that Slack and MCP both call. That is a possible future, not the current design.

## 3. Key Concepts & Terminology

| Term | Meaning |
|------|---------|
| **Route** | Deterministic branch chosen before any conversational LLM call |
| **Retrieve-then-stuff** | Search/read files first, then put the text in the system prompt. The model does not have a `read_file` tool |
| **Metadata shortcut** | One-shot classifier + metadata tools. Returns YAML to the user. Does not loop |
| **Tool loop** | Call the model, run requested tools, feed results back, repeat until text |
| **Conversation path** | Slack Q&A for one onboarded repo. Has thread history and `run_github` |
| **Architect path** | Slack Q&A across all onboarded repos. No tools |
| **MCP ask** | Single-turn Q&A from indexed repo context. No Slack history, no tools |

## 4. High-Level Design

Two processes, one data directory.

```
Slack process (main.py)                    MCP process (benedict-mcp)
        │                                          │
        ▼                                          ▼
  slack_app.py                               mcp/server.py
        │                                          │
        ▼                                          ▼
    RepoAgent                              BenedictMcpService
        │                                          │
        └──────────────┬───────────────────────────┘
                       ▼
              Shared read-only memory
              state.json · workspaces · Chroma · .metadata.benedict
                       │
                       ▼
                 build_context()
```

**Main components**

- `slack_app.py` — Slack events, command routing, reply formatting
- `RepoAgent` — Slack command handlers, conversation, architect
- `BenedictMcpService` — MCP tools; `ask()` is the only LLM path
- `build_context()` — retrieve-then-stuff for a single repo
- `LLMCommandClassifier` — metadata-only intent, one shot
- `run_tool_loop()` — conversation-path GitHub interpretation
- `ClaudeLLM.generate()` — Anthropic call; returns text or `tool_calls`

**Data flow**

A request is routed first. Commands never call the conversational LLM. Q&A builds a system prompt from retrieved files, then calls the model. Slack conversation may loop on `run_github`. MCP ask and architect do not.

**Key invariants**

- Pattern match routes Slack commands. The LLM does not decide onboard/status/index/progress.
- The metadata classifier never sees `run_github`. GitHub and code Q&A stay on the conversation path.
- MCP `ask_benedict` does not call `RepoAgent`. It does not persist a thread. It does not run tools.
- File reading for Q&A is retrieve-then-stuff. Tools exist only for GitHub (`run_github`) and metadata files (shortcut).
- The progress loop may create GitHub issues without a chat confirmation. Conversation-path `run_github` still asks before mutating.

## 5. API / Interface

### Slack (Bolt events)

**Input:**
- `channel_id`: Slack channel
- `user_id`: Slack user
- `text`: mention stripped of `<@BOTID>`
- `thread_ts`: thread id, or the mention `ts` if not already in a thread

**Output:**
- `(success, message)` from the agent
- Slack mrkdwn / Block Kit posted in the thread

### MCP `ask_benedict`

**Input:**
- `question`: user question
- `repo`: optional onboarded id (`org/name`). If omitted, cwd is resolved to a project

**Output:**
- `{ok, repo, channel_id, answer}` or `{ok: false, error}`
- No Slack formatting. No tool loop.

## 6. Happy Path Example

### Slack: `@benedict how does onboarding create a workspace?`

Step 1: `app_mention` in `slack_app.py`. Mention is stripped.

Step 2: Pattern checks fail (not progress, not architect, not onboard/status/index). Route is `handle_conversation`.

Step 3: Channel maps to a repo in `state.json`. User text is appended to the thread conversation.

Step 4: `is_metadata_command` is false. Classifier is skipped.

Step 5: `build_context()` loads recent actions, root metadata, README, and semantic-search hits (full file text, truncated). Those strings become `## Repository Context` in the system prompt.

Step 6: System prompt adds identity, capability list, Slack formatting rules, and `run_github` instructions. Messages are the last 10 turns.

Step 7: `run_tool_loop()` calls Claude with the `run_github` schema. For this question the model returns text. No tool runs.

Step 8: Assistant text is saved on the conversation and posted to Slack.

### Slack: `@benedict list open PRs`

Same through step 6. At step 7 Claude returns a `tool_use` for `run_github` with `argv=["pr", "list", "--json", ...]`. The loop runs `gh` in the workspace clone, appends a `tool_result`, and calls Claude again. Claude writes the Slack reply from that output.

### MCP: `ask_benedict("how does onboarding create a workspace?")`

Step 1: MCP tool → `BenedictMcpService.ask()`.

Step 2: `ProjectResolver` maps `repo` or cwd to an onboarded project.

Step 3: Same `build_context()` as Slack.

Step 4: A shorter system prompt (no Slack mrkdwn, no GitHub tool instructions, explicit “no Slack history”).

Step 5: One `llm.generate()` with a single user message. No tools. Return `answer`.

## 7. Edge Cases & Failure Modes

### Slack routing

| Condition | What happens | Why |
|-----------|--------------|-----|
| `@benedict progress` (any channel) | `handle_progress` before architect/conversation | Progress is a command, including in the architect channel |
| Architect channel + other mention | `handle_architect_query` | Cross-repo answers must not be scoped to one channel’s repo |
| Channel not onboarded | Error, no LLM | There is no workspace or index to retrieve from |
| Thread reply, bot already in thread | `handle_conversation` without a new mention | Continuations should not require `@benedict` every turn |
| Channel message that “looks like” a question | Heuristic may start a conversation | Convenience; can false-positive |
| Mention that also matches a command | Command wins | Deterministic ops must not go through the model |

### Metadata shortcut (`handle_conversation`)

Wording must include `metadata`, `list files`, `list key files`, `repository summary`, or `repo summary`.

Then a **second** LLM call classifies into `get_file_metadata`, `list_key_files`, or `get_repository_summary`. On success, the tool output is the user reply. On miss, failure, or exception, the request **falls through** to the conversation path.

This gate exists because the classifier registry has no `run_github`. Before the gate, “create a GitHub issue” could be classified as metadata and die with “Metadata file not found”.

### Context building

| Condition | What happens | Why |
|-----------|--------------|-----|
| Index missing | `index_repository()` then search | First question should still work |
| Indexer missing or search fails | Keyword match on file paths | Graceful degradation |
| Question names a file (`show me src/agent.py`) | That file is read first | Semantic search can miss an explicit path |
| Context over ~4000 tokens | Truncated | Prompt budget |

Slack conversation also injects thread conversations from `ConversationRepository` when the text looks like a “summarize today’s chats” request. MCP never does this.

### Tool loop

| Condition | What happens | Why |
|-----------|--------------|-----|
| No workspace | `run_github` is not registered; single `generate()` | `gh` needs a clone cwd |
| 5 tool rounds with no text | Stop; tell the user to narrow the question | Prevents unbounded `gh` loops |
| `gh` missing / unauthenticated | Tool returns an error string; model explains | Host setup is outside Benedict |
| `gh auth token` | Refused | Must not leak credentials |
| Token-shaped strings in stdout | Redacted | Same reason |

The metadata shortcut is **not** a loop. It executes classifier tool calls once and either replies or falls through.

### MCP ask

| Condition | What happens | Why |
|-----------|--------------|-----|
| Empty question / no LLM / no reader | `{ok: false, error}` | Fail closed |
| Ambiguous cwd | Resolution error; client should pass `repo` | Several projects can be onboarded |
| Other MCP tools | No LLM | Summary, search, and actions are direct reads |

## 8. Constraints & Assumptions

**Prompt construction is retrieve-then-stuff.** The model cannot page through the repo. Answer quality is bounded by `build_context()` (top-k files, 1000 lines each, ~4000 tokens).

**Two tool mechanisms, different jobs.**

| Mechanism | Tools | Loop? | Result goes to |
|-----------|-------|-------|----------------|
| `LLMCommandClassifier` | metadata only | No | User (YAML/text) |
| `run_tool_loop` | `run_github` only | Yes (max 5) | Model, then user |

GitHub output must be interpreted. Metadata dumps do not.

**MCP ask is a thin slice of the Slack conversation path.** Shared: `build_context`, workspace reader, indexer, metadata, action log. Not shared: `RepoAgent`, thread persistence, Slack history, command router, architect, tools.

**Security assumptions:**
- `run_github` is `gh` only, cwd locked to the workspace clone, 30s timeout, 32k output cap
- MCP tools are read-only
- Slack commands that mutate state (onboard, offboard, index) never go through the model

**Environment:** Slack needs bot tokens. MCP needs the same `BENEDICT_DATA_DIR`. `ask_benedict` and the Slack conversation path need `ANTHROPIC_API_KEY`.

## 9. Alternatives Considered

**One `RepoAgent` for Slack and MCP** — rejected for now. MCP is read-only, single-turn, and must not pull Slack history. Sharing the agent would drag thread state and Slack formatting into the IDE path. The cost is duplicated system-prompt text.

**Give the conversation model a `read_file` tool** — rejected. Retrieve-then-stuff keeps one predictable prompt and bounds tokens. The trade-off is missed files when search is wrong.

**Put `run_github` on the metadata classifier** — rejected. That classifier is a shortcut that returns tool output as the user reply. GitHub needs a loop so the model can interpret `gh` JSON.

**LLM-classify all Slack commands** — rejected. Onboard, offboard, status, and index are side-effecting. Pattern match is cheaper and safer.

**Always run the metadata classifier** — rejected. Extra LLM call on every question, and the classifier used to steal GitHub/code questions.

## 10. Open Questions

Q1: Should MCP `ask_benedict` grow a tool loop (`run_github`, or a `read_file` tool) now that Cursor is a first-class client?

Q2: Should Slack conversation and MCP ask share one prompt builder so identity and instructions cannot drift?

Q3: Should the metadata shortcut die, and metadata become either retrieve-then-stuff or tools on the conversation loop?

Q4: Is the “message directed at bot” heuristic worth the false positives, or should channel messages require a mention except in existing threads?

## 11. Appendix

### A. Slack route table

Order in `create_slack_app` (`app_mention`):

1. `is_architect_onboard_command` → `handle_onboard_architect`
2. Channel is architect channel → `handle_architect_query`
3. `is_onboard_command` → `handle_onboard`
4. `is_offboard_command` → `handle_offboard`
5. `is_status_command` → `handle_status`
6. `is_update_index_command` → `handle_update_index`
7. Else → `handle_conversation`

`message` events never run commands. They run architect or conversation if the bot is already in the thread, or if `is_message_directed_at_bot` is true. They also trigger background Slack-history indexing.

### B. Conversation-path sequence

```
handle_conversation
  ├─ require channel → repo
  ├─ load/save Conversation (thread_ts)
  ├─ if is_metadata_command:
  │     LLMCommandClassifier + metadata ToolRegistry
  │     success → return tool text
  │     else → fall through
  ├─ build_context(...)                  # retrieve-then-stuff
  ├─ optional conversation_context       # “summarize chats” only
  ├─ assemble system prompt
  └─ if workspace: run_tool_loop(run_github)
     else: llm.generate()
```

### C. What the conversation model sees

**System (assembled in `RepoAgent.handle_conversation`):**
1. Identity: Benedict for `{repo}`
2. Capability bullets (files, search, metadata, `run_github`, conversation history)
3. `build_context()` output (actions, metadata summary, README, search files)
4. Optional dumped thread conversations
5. Instructions (answer from context; GitHub usage rules; ask before mutating GitHub)
6. Slack mrkdwn rules

**Messages:** last 10 turns, including the current user text.

**Tools (if workspace exists):** `run_github` schema only.

Architect uses `ARCHITECT_SYSTEM_PROMPT` plus `build_architect_context()` (project list + top-10 cross-repo chunks). No tools.

MCP ask uses a short system prompt plus the same `build_context()` output. One user message. No tools.

### D. Why the model cannot “just read the repo”

`RepoReader` is used by `build_context()` and by tools, not exposed to the model as a generic file API. The conversation system prompt *describes* file access. The actual files in the prompt are whatever retrieval already chose.

### E. Code map

| Step | File |
|------|------|
| Slack events + route | `src/benedict/slack_app.py` |
| Agent + prompts + shortcut | `src/benedict/agent.py` |
| Context retrieval | `src/benedict/utils/context.py` |
| Architect identity | `src/benedict/architect/prompts.py` |
| Metadata classifier | `src/benedict/commands/llm_classifier.py` |
| Metadata tools | `src/benedict/commands/tool_registry_factory.py`, `metadata_tools.py` |
| Tool loop | `src/benedict/commands/tool_loop.py` |
| GitHub tool | `src/benedict/commands/github_tools.py` |
| Tool registry | `src/benedict/commands/tool_framework.py` |
| Claude + tool_use parse | `src/benedict/llm/llm_claude.py` |
| MCP compose | `src/benedict/mcp/server.py` |
| MCP ask | `src/benedict/mcp/service.py` |

### F. Related docs

- [Code map](CODE_MAP.md) — module map and composition root
- [MCP](MCP.md) — MCP tool contract
- [LLM command classifier](LLM_COMMAND_CLASSIFIER_DESIGN.md) — Historical. Classifier internals; metadata-only at runtime

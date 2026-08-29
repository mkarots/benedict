---
title: Home
---

Status: Current

# Benedict

A Slack bot that binds a channel to a **local** git checkout and answers questions about that repo. It uses Claude, semantic search, and `.metadata.benedict` directory summaries. The same memory is available in Cursor and Claude Code through `benedict-mcp`. While the Slack process is running, a progress loop can take one next action per project.

Use Benedict when Slack is the working surface for a codebase and you want an agent that already knows the repo and the thread.

## Who this is for

- Operators who run Benedict on a machine that already has the checkouts
- Engineers who talk to an onboarded repo from Slack or from an IDE
- Contributors who need the request path or the module map

## What ships

- Slack `@mentions` and thread replies
- Channel → repository mapping (onboard, offboard, status)
- Semantic search (ChromaDB) and git-based incremental reindex
- Per-channel workspaces (symlink or copy)
- MCP tools: `list_projects`, `get_repository_summary`, `search_code`, `get_recent_actions`, `ask_benedict`
- Local operator console at `http://127.0.0.1:8765`
- Progress loop: Slack question, GitHub issue, or implement-ready note
- Notion during Slack conversations via the host CLI (`ntn` / `run_notion`), when it is installed and the channel is linked

It does **not** clone from GitHub. Onboard needs a directory on the host. It is not a remote GitHub-hosted reader.

## What it does not do

- Open or merge pull requests from the progress loop
- Read GitHub as the repo source (`RepoReader` is local / workspace only)
- Use Notion as a repo source or put Notion pages in the progress snapshot
- Google Docs or Cursor session logs
- A general shell (`gh` and `ntn` only)

## Terms

| Term | Meaning |
| --- | --- |
| Workspace | Isolated directory per Slack channel: symlink or copy of the repo, plus logs |
| Onboard | Link a channel to a local checkout. Benedict does not clone |
| Retrieve-then-stuff | Search and read files first, then put the text in the prompt. No `read_file` tool |
| Metadata shortcut | One-shot classifier plus metadata tools. Returns YAML. Does not loop |
| Architect channel | Cross-project Slack Q&A. No GitHub tools |
| Progress loop | Unattended cycle in the Slack process. At most one action per project |
| Operator console | Localhost request debugger. Not a second chat surface |

## How the pieces relate

```
Slack process (make run)              MCP process (benedict-mcp)
        │                                      │
        ▼                                      ▼
  mentions, commands, progress           list / search / ask
        │                                      │
        └──────────────┬───────────────────────┘
                       ▼
              ~/.benedict  (shared)
              state.json · workspaces · Chroma · .metadata.benedict
```

Request behavior lives in [Request path](REQUEST_PATH.md). Files and protocols live in [Code map](CODE_MAP.md).

## Reading order

Humans and agents should read in this order:

1. This page (what / not / terms)
2. [Install and run](install.md), then [Slack setup](SLACK_SETUP.md) or [MCP](MCP.md) as needed
3. [Slack commands](commands.md) to use it
4. [Request path](REQUEST_PATH.md) for behavior
5. [Progress loop](PROGRESS.md) if the question is unattended work
6. [Code map](CODE_MAP.md) for file locations

Do not treat **Historical** pages as the current API.

!!! note "For agents"
    Prefer this site over the GitHub README for current behavior. The sidebar is the catalog. `plans/` is milestone history.

# Documentation index

Catalog of Benedict documentation. Browse it in the MkDocs UI (`make docs`). The product overview and run instructions live in the [root README](https://github.com/mkarots/benedict/blob/main/README.md).

Use this page to find a doc by job, not by filename. Current behavior is in **How it works** and **Design**. **Historical** docs describe designs that the runtime no longer implements.

The sidebar comes from `mkdocs.yml`. How to add or change a page: [Process](PROCESS.md).

## Start here

| Doc | When to use |
| --- | --- |
| [Root README](https://github.com/mkarots/benedict/blob/main/README.md) | What Benedict is, how to run it, Slack commands |
| [CHANGELOG](https://github.com/mkarots/benedict/blob/main/CHANGELOG.md) | What changed in each release |
| [Process](PROCESS.md) | Add, update, or classify a doc |
| [Code reading guide](CODE_READING_GUIDE.md) | How to navigate the codebase |
| [Request path](REQUEST_PATH.md) | What happens to a Slack mention or MCP `ask_benedict` |
| [Progress loop](PROGRESS.md) | Unattended cycle: issues, questions, implement-ready notes |

## Setup

| Doc | When to use |
| --- | --- |
| [Slack setup](SLACK_SETUP.md) | Create the Slack app, tokens, and Socket Mode |
| [MCP](MCP.md) | Run `benedict-mcp` and connect Cursor or Claude Code |

## How it works

| Doc | When to use |
| --- | --- |
| [Code reading guide](CODE_READING_GUIDE.md) | Protocols, composition root, and where to start reading |
| [Request path](REQUEST_PATH.md) | Routing, retrieve-then-stuff prompts, metadata shortcut vs GitHub tool loop, Slack vs MCP |
| [Progress loop](PROGRESS.md) | Timer in the Slack process: snapshot, decide, ask/issue/implement |
| [Operator UI](OPERATOR_UI_DESIGN.md) | Localhost request debugger: runs, stages, payloads, final prompt |

## Design

| Doc | When to use |
| --- | --- |
| [Architecture](https://github.com/mkarots/benedict/blob/main/plans/ARCHITECTURE.md) | Module map and how pieces wire together |
| [Operator UI](OPERATOR_UI_DESIGN.md) | Spec for the operator console. Layout contract is `src/benedict/operator_ui/static/index.html` |
| [Progress loop](PROGRESS.md) | Spec for the unattended per-project cycle |

## Decisions

Architecture Decision Records. One accepted decision per file. New ADRs go in `docs/adr/` as `NNNN-short-title.md`. Register the file in `mkdocs.yml` (see [Process](PROCESS.md)).

| Doc | Decision |
| --- | --- |
| [ADR 0001](adr/0001-local-operator-ui.md) | Ship a localhost request debugger, not a health dashboard or a second chat surface |
| [ADR 0002](adr/0002-progress-loop.md) | Slack process runs an unattended per-project progress loop |

## Historical

These documents are not current behavior. Read them only to understand why older designs look the way they do.

| Doc | Status |
| --- | --- |
| [Command classifier](COMMAND_CLASSIFIER_DESIGN.md) | Pattern-based classifier. Method-file commands (`read_method`, `update_method`, `create_method`) were removed in v0.4.0 |
| [Command classifier API](COMMAND_CLASSIFIER_API_DESIGN.md) | Multi-agent registry API. Method-file examples are not in the runtime |
| [LLM command classifier](LLM_COMMAND_CLASSIFIER_DESIGN.md) | LLM classifier design. Remaining classifier tools are metadata-only |

## Open source prep

Planning notes for publishing the repo. Not product documentation. They are not in the MkDocs sidebar.

| Doc | When to use |
| --- | --- |
| [Open source guide index](https://github.com/mkarots/benedict/blob/main/docs/OPEN_SOURCE_GUIDE_INDEX.md) | Navigation for the open-source prep set |
| [Summary](https://github.com/mkarots/benedict/blob/main/OPEN_SOURCE_SUMMARY.md) | Executive summary and risks |
| [Quick start](https://github.com/mkarots/benedict/blob/main/OPEN_SOURCE_QUICK_START.md) | Day-to-day checklist |
| [Plan](https://github.com/mkarots/benedict/blob/main/OPEN_SOURCE_PLAN.md) | Full plan and templates |
| [File inventory](https://github.com/mkarots/benedict/blob/main/OPEN_SOURCE_FILE_INVENTORY.md) | File-by-file tasks |
| [Checklist](https://github.com/mkarots/benedict/blob/main/OPEN_SOURCE_CHECKLIST.md) | Launch checklist |

## Elsewhere in the repo

These live outside `docs/`. MkDocs cannot put them in the sidebar. Open them on GitHub.

| Doc | When to use |
| --- | --- |
| [plans/ARCHITECTURE.md](https://github.com/mkarots/benedict/blob/main/plans/ARCHITECTURE.md) | Current architecture overview |
| [plans/MILESTONE_STATUS.md](https://github.com/mkarots/benedict/blob/main/plans/MILESTONE_STATUS.md) | Milestone tracker. Some items are stale; trust the root README and CHANGELOG first |
| [plans/](https://github.com/mkarots/benedict/tree/main/plans) | Older architecture and milestone notes |
| [tests/README.md](https://github.com/mkarots/benedict/blob/main/tests/README.md) | How the test suite is organized |

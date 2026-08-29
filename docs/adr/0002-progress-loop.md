# ADR 0002: Unattended progress loop

Status: Accepted

Date: 2026-08-29

One-sentence summary:
The Slack process runs a timer that, for each onboarded repo, takes at most one next action (ask, GitHub issue, or implement-ready note). It does not wait for an @mention.

## Context

Benedict answered Slack mentions and MCP queries. It did not start work. GitHub mutations on the conversation path were supposed to be confirmed with the user first. MCP is Cursor → Benedict and read-only. Slack conversations can run Notion via `ntn` (`run_notion`); that is not a repo reader and is not in the progress snapshot.

The product gap: after a night of the process running, project channels were unchanged. The original v3 roadmap named “proactive suggestions”; that was never built.

## Decision

1. **Add a progress loop in the Slack process**, not in MCP. Composition stays in `main.py`.
2. **One action per project per cycle.** Actions are `skip`, `ask`, `issue`, `implement`.
3. **Issue create is allowed without a confirmation prompt on this path.** Conversation-path `run_github` still tells the model to ask before mutating.
4. **Ask is blocking.** Unattended actions wait until a human replies in that thread or someone runs `@benedict progress now`.
5. **Do not open pull requests in v1.** `implement` files or points at an issue and posts in Slack. A later executor (Cursor SDK) can replace that step.
6. **On by default** when an LLM is configured. `BENEDICT_PROGRESS=0` disables it.
7. **Record each cycle as an operator-UI run** with `source=progress`.

## Consequences

### What we get

- Overnight, a channel can gain a GitHub issue, a question, or an implement-ready note
- `@benedict progress` / `progress all` runs the same path on demand
- Pending questions prevent issue spam when Benedict is blocked on a decision

### What we give up

- The guarantee that Benedict never writes to GitHub unless a human confirmed that specific create in chat
- Any claim that Benedict “talks to Cursor” to write code. MCP remains inbound

### Follow-up

- Coding executor for `implement` (likely Cursor SDK)
- Notion (and other trackers) in the snapshot
- Optional architect-channel digest

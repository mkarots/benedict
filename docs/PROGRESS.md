Status: Current

# Progress loop

One-sentence summary:
While the Slack process is running, Benedict surveys each onboarded project on a timer and takes at most one next action: ask you a question, open a GitHub issue, or mark work as ready to implement.

## 1. Overview

**What:**
A background cycle in the Slack process. For every onboarded channel it builds a snapshot (README, roadmap, GitHub issues/PRs, recent workspace actions), asks Claude for one next action, and executes it.

**Why:**
Benedict was a reactive Q&A bot. Nothing happened unless you @mentioned it or Cursor called MCP. Projects did not move overnight. This loop is how Benedict spends idle time on the next milestone step.

**When to use:**
- Leave `make run` up. The first cycle runs after a short delay, then on an interval.
- Force a cycle from Slack: `@benedict progress` (this channel) or `@benedict progress all` (every onboarded repo).
- Reply in a progress-question thread when Benedict is blocked on a decision.

## 2. Non-Goals

Not responsible for:

- Opening or merging pull requests (no coding executor yet)
- Calling Cursor. MCP is still Cursor → Benedict (read-only)
- Notion pages, Google Docs, or Slack history in the snapshot (Slack chat can still use `run_notion`)
- Replacing Slack conversation or MCP `ask_benedict`

Out of scope: a general shell, force-push, closing issues, or acting on a repo that is not onboarded.

## 3. Key Concepts & Terminology

| Term | Meaning |
|------|---------|
| Snapshot | Facts for one project: README, roadmap, open issues/PRs, action log |
| Decision | JSON from the model: `skip`, `ask`, `issue`, or `implement` |
| Ask | A blocking Slack question. Further unattended actions wait for a reply in that thread |
| Issue | `gh issue create` in the workspace checkout, then a Slack notice |
| Implement | Ready for a PR. v1 files or points at an issue and tells Slack. It does not open a PR |
| Progress store | `state.json` → `progress.projects` (last action, pending thread) |

## 4. High-Level Design

```
timer / @benedict progress
        │
        ▼
  ProgressService.run_one(channel)
        │
        ├── SnapshotCollector  (workspace files + run_github)
        ├── ActionDecider      (Claude → JSON)
        └── ActionExecutor     (Slack post and/or gh issue create)
                │
                ▼
        Slack channel + operator UI run (source=progress)
```

**Main components** (`src/benedict/progress/`):

- `snapshot.py` — read local files, list GitHub issues/PRs via `RunGithubTool`
- `decide.py` — constrained JSON decision
- `execute.py` — Slack poster + issue create
- `cycle.py` — one action per project, lock, operator-UI run
- `scheduler.py` — daemon thread in `main.py`
- `store.py` — pending-question and last-action fields in `state.json`

**Data flow:**
List onboarded channels from `state.json`. For each, collect a snapshot, skip if a progress question is unanswered, decide, execute, record.

**Key invariants:**

- At most one action per project per cycle
- Conversation-path GitHub mutations still require asking the user. This loop may create issues without a confirmation prompt
- Never merge, close, or comment as the default action
- Duplicate open-issue titles are skipped
- Labels on created issues must already exist on the repo

## 5. API / Interface

### Slack

| Command | Effect |
| --- | --- |
| `@benedict progress` | Run this channel now |
| `@benedict progress now` | Same, and ignore a pending question |
| `@benedict progress all` | Run every onboarded repo |

A human reply in the pending question thread clears the wait (no mention required).

### Environment

| Variable | Default | Purpose |
| --- | --- | --- |
| `BENEDICT_PROGRESS` | `1` | Set `0` to disable the loop |
| `BENEDICT_PROGRESS_INTERVAL_S` | `21600` (6 hours) | Time between full cycles |
| `BENEDICT_PROGRESS_START_DELAY_S` | `120` | Delay before the first cycle |

Requires `ANTHROPIC_API_KEY` and `gh` authenticated on the host. The scheduler starts only when the Slack process has an LLM.

### Decision JSON

Input: snapshot text (repo, purpose, README, roadmap, open issues/PRs, labels, last action).

Output:

- `action`: `skip` \| `ask` \| `issue` \| `implement`
- `reason`: one sentence
- `title` / `body`: required for `ask` and `issue`
- `labels`: optional, filtered to labels that exist
- `issue_number`: optional, for `implement`

## 6. Happy Path Example

Step 1: You onboard `#widget` to `acme/widget` and leave `make run` up.

Step 2: Two minutes later the loop snapshots the repo. Open issues do not cover the next README milestone. Claude returns `issue`.

Step 3: Benedict runs `gh issue create` and posts the URL in `#widget`.

Result: The next morning the channel has a new issue (or a question, or an “ready to implement” note). The operator console shows a run with `source=progress`.

## 7. Edge Cases & Failure Modes

What can fail:

- Missing checkout, missing `gh`, unauthenticated `gh`, LLM error, Slack post error
- Model returns prose instead of JSON
- Issue labels do not exist
- A previous question is still unanswered

How failures are handled:

- Unusable decisions become `skip` and are logged
- Unknown labels are dropped, then `gh issue create` retries with no labels
- Cycle errors are isolated per project; other projects still run
- Operator UI records the run; exceptions do not crash Slack

What the system guarantees:

- One project cannot overlap two cycles (lock)
- A pending ask blocks further unattended actions until a thread reply or `progress now`

## 8. Constraints & Assumptions

- The Slack process must stay running. MCP does not run this loop
- GitHub writes use the host `gh` login
- Cursor cannot be started from Benedict today. MCP does not reverse that
- Notion is not in the snapshot
- Default interval is hours, not minutes, to avoid issue spam

## 9. Alternatives Considered

Option A — Only Slack suggestions, never mutate GitHub — rejected because that is still a chatbot. The goal is a filed issue or a blocking question by morning.

Option B — Benedict calls Cursor MCP as a client — rejected for v1. MCP.md forbids Benedict-as-MCP-client. The coding executor should be a later `PullRequestOpener` (Cursor SDK is the likely implementation).

Option C — Confirm every GitHub create in Slack before executing — rejected for this path. Confirmation is what kept the conversation agent from progressing. Ask is used when a *product* decision is missing, not when the next issue is already clear.

## 10. Open Questions

Q1: Should `implement` invoke the Cursor SDK (local or cloud) to open a PR?

Q2: Should Notion pages join the snapshot? `run_notion` exists on the conversation path; the snapshot still does not include Notion.

Q3: Should the architect channel get a digest of every project’s action?

## 11. Appendix

Code: `src/benedict/progress/`. Tests: `tests/unit/test_progress.py`.

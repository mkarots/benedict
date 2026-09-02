# ADR 0004: Product shape — one agent per repo

Status: Accepted

Date: 2026-09-02

One-sentence summary:
Benedict is a Slack app: invite the bot, connect a repo, that channel has an independent agent whose job is to maintain the repo. MCP in the IDE is the same product. Charge per workspace or per onboarded repo. Enterprise runs the same agent in the customer VPC.

## Context

What ships today is a process you start on a machine that already has the project folders. Invite `@benedict`, onboard a local checkout, and that channel can answer from the code and from Slack talk about it. MCP reads the same data directory. The progress loop already acts per onboarded repo.

The product question is what Benedict is selling, and what it must never become:

- A second IDE product next to the Slack bot
- A seat-priced “Slack AI for the whole workspace”
- A hosted clone of the customer’s GitHub
- One shared assistant that knows every repo at once

The architecture is already local-folder-first. It does not download the project from GitHub. That is the reason an enterprise customer can run the same agent in their VPC.

## Decision

1. **The product is a Slack app.** Invite the bot, connect a repo, the channel has a brain. Hosted is the commercial default. Self-hosted or VPC is the same agent, not a fork.
2. **One independent agent per onboarded repo.** Its goal is to maintain that repo: answer from its code and its channel history, and take the next step for that project. Isolation is the product, not an implementation detail.
3. **MCP in the IDE is included.** Cursor and Claude Code query the same agent and the same memory. MCP is not a second SKU, a second index, or a second product name.
4. **Charge per Slack workspace or per onboarded repo.** Do not price by seat. Seat-based pricing fights Slack AI on their terms and loses.
5. **Enterprise add-on: the same agent in their VPC.** Keep the local-folder-first contract. Do not clone from GitHub for them. The folder must already be on the machine they run.

The architect channel stays the exception: it is cross-project on purpose. It is not the default agent.

## Consequences

### What we get

- A clear unit of value: a repo that has a brain in Slack and in the IDE
- A pricing story that matches how teams onboard work (workspaces and repos), not how Slack sells AI seats
- A path to hosted and VPC without a second architecture: both run the same local-folder-first agent
- A design filter: features that merge repos, share one memory across projects, or treat MCP as a separate product are out of shape

### What we give up

- Competing with Slack AI as a workspace-wide assistant
- Selling MCP, Cursor integration, or “developer seats” as their own product
- A hosted flow that clones GitHub for the customer

### Follow-up

- Keep `RepoAgent` and indexes isolatable per repo even when one process hosts many channels
- Hosted install: invite, connect repo, no operator machine in the happy path
- VPC/enterprise packaging that reuses this process, not a cloud-only rewrite

---
title: Home
---

Status: Current

<p class="hero-mark" align="center">
  <img src="assets/logo.png" alt="Benedict logo" width="320" height="320">
</p>
<p class="hero-tagline" align="center"><em>repo bene(volent)dict(ator) agent</em></p>

# Benedict

Benedict is an agent that knows your code and the Slack conversations you have about it — and can help you plan the work.

Each channel is one project. You point the channel at a local folder. After that, Benedict can answer from the code *and* from what the team already said in Slack: how a feature works, what you decided last week, what to do next.

You can ask the same questions from Cursor or Claude Code. When you want a next step, Benedict can ask a clarifying question, open a GitHub issue, or mark something as ready to implement.

## A normal day

1. Start Benedict on a machine that has the project folders.
2. In Slack: invite `@benedict`, then `@benedict onboard repo …` with the folder for that channel.
3. Ask in the channel. Replies stay in the thread.
4. Optional: connect GitHub or Notion on that machine if you want PRs or a board in the conversation.
5. Optional: `@benedict progress` when you want a next step.

[Install and run](install.md) · [Slack setup](SLACK_SETUP.md) · [Commands](commands.md)

## What it will not do

- Download the project from GitHub for you. The folder must already be on the machine.
- Open or merge pull requests by itself.
- Browse the web, run arbitrary programs, or act as a general computer. GitHub and Notion are optional extras on that host, not a replacement for the folder.
- Read Google Docs or your editor session history.

How a question is answered, and how the pieces are named, is in [Request path](REQUEST_PATH.md) and [Code map](CODE_MAP.md) if you are changing the product — not if you are using it.

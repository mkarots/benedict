# Benedict

A Slack bot that links a channel to a local git repository and answers questions about that repo with Claude, semantic search, and project metadata files.

Use Benedict when a Slack channel is the working surface for a codebase and you want an agent that already knows the repo and the thread history.

Benedict is a working Slack Socket Mode bot (Python 3.10+, version 0.6.2). It is not a remote GitHub-hosted reader. Onboarding resolves a **local** checkout. It does not clone from GitHub. Slack conversations can run GitHub (`gh`) and Notion (`ntn`) on the host; those CLIs are not a general shell and Notion is not the repo source.

**Full documentation** (what ships, install, commands, request path): run `make docs` and open `http://127.0.0.1:8000`.

## Quick start

```bash
git clone https://github.com/mkarots/benedict.git
cd benedict
make setup
source .venv/bin/activate
make sync-dev
```

Put Slack tokens and `ANTHROPIC_API_KEY` in `.env`, then:

```bash
make run
```

Slack app tokens: [docs/SLACK_SETUP.md](docs/SLACK_SETUP.md). MCP (Cursor / Claude Code): [docs/MCP.md](docs/MCP.md).

## Commands

Mention `@benedict` (or `@agent`) in the channel.

| Command | What it does |
| --- | --- |
| `onboard repo org/repo` | Links the channel to a local checkout |
| `offboard` | Removes the channel mapping |
| `status` | Shows the linked repo |
| `update index` | Incremental reindex (`force` for a full rebuild) |
| `onboard architect` | Cross-project architect channel |
| `progress` | Run the progress loop (`all`, `now`) |
| Any other question | Repo-scoped conversation |

## License

MIT License. A `LICENSE` file is not yet in the repository.

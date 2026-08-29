# Benedict

Benedict is an agent that knows your code and the Slack conversations you have about it — and can help you plan the work.

Each channel is one project. You point the channel at a local folder. Benedict answers from the code and from what the team already said in Slack.

You can ask the same questions from Cursor or Claude Code. When you want a next step, it can ask, open a GitHub issue, or mark work as ready to implement.

Python 3.10+. Version 0.6.9. It does not download the project from GitHub for you.

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
| `link notion <url>` | Sets this channel's default Notion page or database |
| `onboard architect` | Cross-project architect channel |
| `progress` | Run the progress loop (`all`, `now`) |
| Any other question | Repo-scoped conversation |

## Community

This project follows the [Contributor Covenant Code of Conduct](CODE_OF_CONDUCT.md). By participating, you agree to uphold that policy. Report unacceptable behavior privately at michael.karotsieris@gmail.com; do not open a public issue for a conduct report.

Report security vulnerabilities privately as described in [SECURITY.md](SECURITY.md). Do not open a public issue for a vulnerability.

## License

Licensed under the Apache License, Version 2.0. See [LICENSE](LICENSE) and [NOTICE](NOTICE). Copyright 2026 Michael Karotsieris.

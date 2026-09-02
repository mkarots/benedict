<p align="center">
  <img src="docs/assets/logo.png" alt="Benedict logo" width="320" height="320">
</p>
<p align="center"><em>repo bene(volent)dict(ator) agent</em></p>

# Benedict

[![CI](https://github.com/mkarots/benedict/actions/workflows/ci.yml/badge.svg)](https://github.com/mkarots/benedict/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![Contributor Covenant](https://img.shields.io/badge/Contributor%20Covenant-2.1-4baaaa.svg)](CODE_OF_CONDUCT.md)
[![Discussions](https://img.shields.io/badge/GitHub-Discussions-blue?logo=github)](https://github.com/mkarots/benedict/discussions)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white)](https://github.com/pre-commit/pre-commit)

Benedict is a Slack app. Invite the bot, connect a repo, that channel has an agent whose job is to maintain the repo.

Each channel is one project. You point the channel at a local folder. Benedict answers from the code and from what the team already said in Slack.

MCP in Cursor or Claude Code is the same agent, not a second product. When you want a next step, it can ask, open a GitHub issue, or mark work as ready to implement.

Python 3.10+. Version 0.8.10. It does not download the project from GitHub for you.

Package name, authors, classifiers, keywords, and project URLs live in [`pyproject.toml`](pyproject.toml).

**Full documentation** (what ships, install, commands, request path): run `make docs` and open `http://127.0.0.1:8000`.

## Quick start

```bash
git clone https://github.com/mkarots/benedict.git
cd benedict
make setup
source .venv/bin/activate
make sync-dev
```

A clone includes `src/benedict/lib` (logging and date helpers used at startup). Git ignores a `/lib/` directory at the repository root only, not that package.

Put Slack tokens and `ANTHROPIC_API_KEY` in `.env`, then:

```bash
make run
```

Slack app tokens: [docs/install.md](docs/install.md). MCP (Cursor / Claude Code): [docs/MCP.md](docs/MCP.md).

## Commands

Mention `@benedict` (or `@agent`) in the channel.

| Command | What it does |
| --- | --- |
| `onboard repo org/repo` | Links the channel to a local checkout |
| `offboard` | Removes the channel mapping |
| `status` | Shows the linked repo |
| `update index` | Incremental reindex (`force` for a full rebuild) |
| `link notion <url>` | Sets this channel's default Notion page or database |
| `unlink notion` | Clears the Notion mapping (repo stays onboarded) |
| `onboard architect` | Cross-project architect channel |
| `progress` | Run the progress loop (`all`, `now`) |
| Any other question | Repo-scoped conversation |

## Community

How to set up a dev environment, run tests, and open a pull request: [CONTRIBUTING.md](CONTRIBUTING.md). Who maintains the project and how decisions are made: [MAINTAINERS.md](MAINTAINERS.md). Cursor and Claude Code writing rules live in [`.cursor/rules/`](.cursor/rules/).

Questions, ideas, and show-and-tell posts: [GitHub Discussions](https://github.com/mkarots/benedict/discussions).

This project follows the [Contributor Covenant Code of Conduct](CODE_OF_CONDUCT.md). By participating, you agree to uphold that policy. Report unacceptable behavior privately at michael.karotsieris@gmail.com; do not open a public issue for a conduct report.

Report bugs with the [Bug report](https://github.com/mkarots/benedict/issues/new?template=bug_report.md) issue template. Request a feature with the [Feature request](https://github.com/mkarots/benedict/issues/new?template=feature_request.md) template.

Report security vulnerabilities privately as described in [SECURITY.md](SECURITY.md). Do not open a public issue for a vulnerability.

## License

Licensed under the Apache License, Version 2.0. See [LICENSE](LICENSE) and [NOTICE](NOTICE). Copyright 2026 Michael Karotsieris.

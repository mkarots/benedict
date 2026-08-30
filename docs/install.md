Status: Current

# Install and run

Clone Benedict, install dependencies, set tokens, and start the Slack process.

## Prerequisites

- Python 3.10 or higher
- [uv](https://docs.astral.sh/uv/) (recommended) or pip
- A Slack workspace where you can create apps
- An Anthropic API key for LLM answers (`ANTHROPIC_API_KEY`)
- Optional: [GitHub CLI](https://cli.github.com/) (`gh`)
- Optional: [Notion CLI](https://ntn.dev) (`ntn`) for Slack `run_notion` (`ntn login` or `NOTION_API_KEY`)
- Optional: Cursor or Claude Code, for `benedict-mcp`
- Optional: local git checkouts of the repos you want to onboard

## Package

Benedict is Apache-2.0. `pyproject.toml` also declares authors, classifiers, keywords, and project URLs (Homepage, Repository, Issues) for GitHub and PyPI. Install from this clone. A PyPI release is not published yet.

## Clone

```bash
git clone https://github.com/mkarots/benedict.git
cd benedict
```

Install uv if needed:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
# or: brew install uv
```

## Install

```bash
make setup
source .venv/bin/activate
make sync-dev
```

Without Make:

```bash
uv venv
source .venv/bin/activate
uv pip install -e ".[dev]"
```

## Environment

Create `.env` in the project directory (or set `BENEDICT_ENV_FILE`):

```bash
SLACK_BOT_TOKEN=xoxb-your-bot-token-here
SLACK_APP_TOKEN=xapp-your-app-token-here
ANTHROPIC_API_KEY=your-anthropic-api-key
```

Slack tokens: [Slack setup](SLACK_SETUP.md). Every variable: [Configuration](configuration.md).

## Run the Slack bot

```bash
make run
```

Or:

```bash
python -m benedict.main
# after install: benedict
```

You should see: `Bot is running! Press Ctrl+C to stop.` and `Operator UI http://127.0.0.1:8765`.

Then invite the bot, onboard a repo, and ask. See [Slack commands](commands.md).

## MCP (Cursor / Claude Code)

After a channel is onboarded, the same data can be queried from an IDE without Slack running:

```bash
benedict-mcp
```

Or `make mcp` / `python -m benedict.mcp`. Setup: [MCP](MCP.md). Slack and MCP must share `BENEDICT_DATA_DIR` (default `~/.benedict`).

## Docs UI

```bash
make docs
```

Serves this site at `http://127.0.0.1:8000`. If that port is busy: `DOCS_PORT=8001 make docs`.

## Checks

Pull requests and pushes to `main` run lint, type check, and tests. See [Continuous integration](ci.md). After `pre-commit install`, the same Black and Ruff versions run on `git commit`. Contributor setup, tests, and pull request expectations are in `CONTRIBUTING.md` at the repository root.

```bash
make lint
make type-check
make test
```

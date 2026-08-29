Status: Current

# Troubleshooting

**Bot does not respond.** Confirm the process is running, the bot is in the channel, and you @mentioned it (or replied in a thread Benedict already joined). Check the terminal log.

**Missing `SLACK_BOT_TOKEN` or `SLACK_APP_TOKEN`.** See [Slack setup](SLACK_SETUP.md).

**Channel is not onboarded.** Run `@benedict onboard repo org/repo` against a directory that exists locally.

**Repository not found.** Set `BENEDICT_REPO_SOURCE_DIRS` to the parent of your checkouts, or pass an absolute path in the onboard command. See [Slack commands](commands.md).

**LLM answers are stubs.** Set `ANTHROPIC_API_KEY`. Without it, Benedict acknowledges the repo but does not call Claude.

**GitHub tool fails.** Install `gh` on the host and run `gh auth login`. Benedict does not ship a GitHub token of its own.

**Corrupt state.** Stop the bot, delete `~/.benedict/state.json`, restart, and re-onboard channels. Conversations in that file are lost.

**Wrong or empty Slack reply.** Open the operator console at `http://127.0.0.1:8765` and inspect the run. Spec: [Operator console](OPERATOR_UI_DESIGN.md). Request routing: [Request path](REQUEST_PATH.md).

All variables: [Configuration](configuration.md).

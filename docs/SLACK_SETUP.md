Status: Current

# Slack setup

You need two tokens from a Slack app. Put them in `.env`, start Benedict, invite the bot.

You need a workspace where you can create and install apps.

## Create the app

At [api.slack.com/apps](https://api.slack.com/apps): **Create New App** → **From scratch**. Name it and pick the workspace.

Then, in that app:

| Page | What to do |
| --- | --- |
| Socket Mode | Turn it on. Create an app-level token with scope `connections:write`. Copy it (`xapp-…`). That is `SLACK_APP_TOKEN`. |
| OAuth & Permissions | Under Bot Token Scopes add `chat:write`, `channels:history`, `channels:read`. |
| Event Subscriptions | Turn events on. Add the bot event `app_mention`. |
| Install App | Install to the workspace. Copy the Bot User OAuth Token (`xoxb-…`). That is `SLACK_BOT_TOKEN`. |

If you add scopes later, install the app again.

Benedict uses Socket Mode. You do not need a public webhook URL.

## Tokens in `.env`

```bash
SLACK_BOT_TOKEN=xoxb-…
SLACK_APP_TOKEN=xapp-…
```

`.env` is gitignored. If a token leaks, regenerate it in the Slack app.

## Invite

Start the process if it is not running: [Install and run](install.md).

```
/invite @benedict
```

Then `@benedict status`. If it answers, the app is fine. Onboard next: [Slack commands](commands.md).

If it does not: [Troubleshooting](troubleshooting.md).

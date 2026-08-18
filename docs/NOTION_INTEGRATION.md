# Notion integration

One-sentence summary:
How Benedict reads and writes Notion from Slack using an internal integration token.

## Setup (operator, once)

1. In Notion: Settings → Connections → develop or manage integrations → New internal integration. Name it Benedict.
2. Copy the secret into the bot host `.env`:

```bash
NOTION_API_KEY=secret_...
```

3. Restart Benedict as the same process that can read that env var.

## Per channel (Slack)

1. In Notion, open the project page or database → Share → invite the Benedict integration.
2. In the onboarded Slack channel:

```
@benedict link notion https://www.notion.so/...
```

Benedict stores the id on the channel and uses it as the default for `run_notion`.

```
@benedict unlink notion
```

forgets that mapping. It does not offboard the git repo and does not revoke the Notion share.

## What the agent can do

Reads: search, get a page (title, properties, text), query a database/board.

Writes (ask first in the thread): create a page or database card, update properties (for example Status to move a card), append paragraphs.

The bot acts as the integration, not as the Slack user.

## Failures

`object_not_found` means the integration cannot see the page. Share it again, then `link notion`.

# Notion (`ntn`)

One-sentence summary:
How Benedict reads and writes Notion from Slack by running the Notion CLI (`ntn`) the same way it runs `gh`.

## Setup (operator, once)

1. Install the CLI: `curl -fsSL https://ntn.dev | bash` then `ntn --version`.
2. Authenticate as a full workspace member:

```bash
ntn login
```

Or put a personal access token in `.env` as `NOTION_API_KEY`. Benedict copies it to `NOTION_API_TOKEN` for `ntn`. Create a token at [Personal access tokens](https://www.notion.so/developers/tokens).

3. Restart Benedict. Confirm `ntn` is on the PATH of that process.

## Per channel (Slack)

```
@benedict link notion https://www.notion.so/your-page-or-database
```

stores the id as the channel default. `unlink notion` forgets it and does not offboard the git repo.

## How the agent navigates

`run_notion` is argv-only, like `run_github`. The model may call it many times in one reply:

1. `datasources resolve DATABASE_ID` or `datasources query DATA_SOURCE_ID`
2. `pages get PAGE_ID` — markdown, properties, nested `<page>` and `<database>` / `collection://` links
3. Query the nested data source, then `pages get` a task card

Ask before mutating (`pages create`, `pages edit`, `pages trash`).

## Failures

If `ntn` is missing, install it on the Benedict host. If a page is not visible, run `ntn login` as the Notion user who can open it, or set `NOTION_API_KEY`. Copy the page/database link (id in the path, before `?v=`).

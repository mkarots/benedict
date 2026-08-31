Status: Current

# Slack commands

Mention `@benedict` (or `@agent`) in the channel.

| Command | What it does |
| --- | --- |
| `onboard repo org/repo` | Links the channel to a local checkout. Also accepts `this channel is for org/repo` or an absolute path. |
| `offboard` | Removes the channel mapping. |
| `status` | Shows the linked repo and when it was onboarded. |
| `update index` | Incremental reindex. Add `force` for a full rebuild. |
| `link notion <url>` | Sets this channel's default Notion page or database for `run_notion`. |
| `unlink notion` | Clears the Notion mapping. Does not offboard the repo. |
| `onboard architect` | Marks the channel as the architect channel for cross-project questions. |
| `progress` | Run the progress loop for this channel. Add `all` for every onboarded repo, `now` to ignore a pending question. |
| Any other question | Repo-scoped conversation with search, LLM, `run_github`, and `run_notion`. |

GitHub issue/PR requests stay on the conversation path. Asking for `.metadata.benedict` contents (file metadata, list key files, repository summary) may use a short metadata-tool shortcut. That shortcut does not run GitHub; if it fails, Benedict falls through to conversation.

There is no method-file command. A `.benedict.method.yaml` in a repository is an ordinary file, not a runtime feature.

MCP is not a Slack command. See [MCP](MCP.md).

## First channel

1. Invite the bot: `/invite @benedict`
2. Onboard: `@benedict onboard repo acme/widget`
3. Confirm: `@benedict status`
4. Ask: `@benedict what's the architecture?`
5. `@benedict progress` picks a next step for this channel. Add `all` for every onboarded repo.

## Onboard a channel

```
@benedict onboard repo acme/widget
```

Benedict looks for the checkout in this order:

1. The text as an absolute path
2. Directories in `BENEDICT_REPO_SOURCE_DIRS` (comma-separated), as `org/repo` and as the repo name alone
3. `~/Projects/<repo>` if `BENEDICT_REPO_SOURCE_DIRS` is unset
4. The current working directory

It does not clone from GitHub. The directory must already exist on the machine that runs the bot.

## Ask a question

```
@benedict what files handle authentication?
```

Benedict embeds the question, retrieves similar chunks from the Chroma index, then reads those files (plus README) from the workspace and sends them to Claude. The model has no `read_file` tool. Later replies in that thread are treated as continuation even without a mention, once Benedict has already participated.

Open `http://127.0.0.1:8765` to see the retrieved chunks and the files that went into the prompt.

How that request is routed: `artifacts/REQUEST_PATH.html`.

## GitHub CLI

If GitHub CLI is installed and authenticated on the host, Benedict can run `gh` in the onboarded workspace repo (list PRs, inspect issues, and similar). Mutating GitHub (create, merge, close, comment) is supposed to be confirmed with you first. This is not a general shell.

## Notion CLI

If [`ntn`](https://ntn.dev) is installed on the host (or `NOTION_API_KEY` is set), Benedict can walk Notion during conversations with `run_notion`, the same argv-only pattern as `run_github`. Link a page or database with `@benedict link notion <url>`. Notion is not a `RepoReader` and is not in the progress-loop snapshot.

## State and workspaces

Channel mappings and thread conversations live in `~/.benedict/state.json`:

```json
{
  "channels": {
    "C12345ABC": {
      "repo": "acme/widget",
      "onboarded_at": "2026-02-01T20:30:00Z",
      "onboarded_by": "U123456"
    }
  },
  "conversations": {},
  "architect": {}
}
```

Each onboarded channel also gets a directory under `~/.benedict/workspaces/<channel_id>/` containing a symlink (or copy) of the repo plus action logs and indexed Slack history. If you previously ran Benedict from the git checkout, move `state.json`, `workspaces/`, `.chroma_db/`, and `runs.jsonl` into `~/.benedict`, or set `BENEDICT_DATA_DIR` to the old location.

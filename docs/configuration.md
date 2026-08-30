Status: Current

# Configuration

Environment variables. Set them in `.env` in the project directory, or point `BENEDICT_ENV_FILE` at another file.

```bash
SLACK_BOT_TOKEN=xoxb-your-bot-token-here
SLACK_APP_TOKEN=xapp-your-app-token-here
ANTHROPIC_API_KEY=your-anthropic-api-key
# Optional
# ANTHROPIC_MODEL=claude-3-5-sonnet-20241022
# BENEDICT_REPO_SOURCE_DIRS=/Users/you/Projects,/opt/repos
```

| Variable | Default | Purpose |
| --- | --- | --- |
| `SLACK_BOT_TOKEN` | required | Slack bot token |
| `SLACK_APP_TOKEN` | required | Slack Socket Mode token |
| `ANTHROPIC_API_KEY` | optional | Claude. Without it, Slack runs in stub mode and MCP `ask_benedict` is unavailable. |
| `ANTHROPIC_MODEL` | `claude-3-5-sonnet-20241022` | Claude model id |
| `BENEDICT_DATA_DIR` | `~/.benedict` | Root for state, workspaces, and ChromaDB. Slack bot and `benedict-mcp` must share this. |
| `BENEDICT_WORKSPACES_DIR` | `{data_dir}/workspaces` | Per-channel workspaces |
| `BENEDICT_WORKSPACE_COPY_MODE` | `symlink` | `symlink` or `copy` |
| `BENEDICT_CHROMA_DB_DIR` | `{data_dir}/.chroma_db` | Vector index |
| `BENEDICT_STATE_FILE` | `{data_dir}/state.json` | Channel mappings and conversations |
| `BENEDICT_ENV_FILE` | `{repo}/.env` | dotenv path |
| `BENEDICT_REPO_SOURCE_DIRS` | `~/Projects` | Comma-separated roots used during onboard |
| `BENEDICT_CHUNK_SIZE` | `2000` | Index chunk size in characters |
| `BENEDICT_METADATA_FILE` | `.metadata.benedict` | Override metadata file name/path |
| `BENEDICT_OPERATOR_UI` | `1` | Local debug console. Set `0` to disable. |
| `BENEDICT_OPERATOR_UI_HOST` | `127.0.0.1` | Bind address |
| `BENEDICT_OPERATOR_UI_PORT` | `8765` | Console port |
| `BENEDICT_PROGRESS` | `1` | Unattended progress loop. Set `0` to disable. |
| `BENEDICT_PROGRESS_INTERVAL_S` | `21600` | Seconds between full progress cycles |
| `BENEDICT_PROGRESS_START_DELAY_S` | `120` | Seconds to wait after startup before the first cycle |
| `NOTION_API_KEY` | unset | Optional. Copied to `NOTION_API_TOKEN` for `ntn` if that var is unset. `ntn login` also works. |

Install and start: [Install and run](install.md).

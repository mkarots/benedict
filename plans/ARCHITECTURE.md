# Architecture Overview

Status: Historical pointer. This file is milestone archaeology and may lag the code.


## Entry Point

**`src/benedict/main.py`** is the Slack application entry point. Run with:
```bash
python -m benedict.main
```

**`src/benedict/mcp/server.py`** is the MCP server entry point (Cursor / Claude Code). Run with:
```bash
benedict-mcp
```
or:
```bash
python -m benedict.mcp
```

**`src/benedict/mcp/server.py`** is the MCP server entry point (Cursor / Claude Code). Run with:
```bash
benedict-mcp
```
or:
```bash
python -m benedict.mcp
```

The MCP process does not start Slack. It reads the same `state.json`, workspaces, and index. See [docs/MCP.md](../docs/MCP.md). The unattended progress loop runs only in the Slack process. See [docs/PROGRESS.md](../docs/PROGRESS.md).

For what happens on a user request (routing, prompt building, tool calls, Slack vs MCP), see `artifacts/REQUEST_PATH.html`. Slack and MCP share that data directory. They do not share `RepoAgent`.

## File Structure

### Core Application
- **`main.py`** - Composition root (wires all dependencies together)
- **`slack/`** - Slack Bolt app, message delivery, and Block Kit formatting
  - **`app.py`** - Bolt event handlers
  - **`messages.py`** - message types, parsing, chunking, and `say()`
  - **`formatter.py`** - mrkdwn and Block Kit construction
- **`agent.py`** - Main agent logic (handles commands and conversations)
- **`paths.py`** - Shared data-dir and `.env` path helpers
- **`mcp/`** - MCP server (project resolver, read-only service, stdio composition root)
- **`progress/`** - Unattended progress loop (snapshot, decide, execute, scheduler)

### Domain Models
- **`models/conversation.py`** - Conversation and Message models, ConversationManager

### Protocols (Interfaces)
- **`protocols/llm.py`** - LLM protocol definition
- **`protocols/repo_reader.py`** - Repository reader protocol
- **`protocols/semantic_indexer.py`** - Semantic code search protocol
- **`protocols/conversation_repository.py`** - Conversation persistence protocol
- **`protocols/repo_change_detector.py`** - Repository change detection protocol
- **`protocols/conversation_history_indexer.py`** - Conversation history indexing protocol

### Implementations

#### LLM
- **`llm/llm_claude.py`** - Claude 3.5 Sonnet implementation
- **`llm/llm_mock.py`** - Mock LLM for testing

#### Repository Reader
- **`repo_reader/repo_reader_local.py`** - Local filesystem implementation
- **`repo_reader/repo_reader_workspace.py`** - Workspace-aware repository reader
- **`repo_reader/repo_reader_workspace_adapter.py`** - Adapter for workspace reader
- **`repo_reader/repo_reader_mock.py`** - Mock repository reader for testing

#### Semantic Indexer
- **`semantic_indexer/semantic_indexer_chromadb.py`** - ChromaDB + sentence-transformers implementation
- **`semantic_indexer/semantic_indexer_mock.py`** - Mock semantic indexer for testing

#### Conversation Repository
- **`conversation_repository/conversation_repository_json.py`** - JSON file persistence
- **`conversation_repository/conversation_repository_mock.py`** - In-memory mock for testing

#### Repository Change Detection
- **`repo_change_detector/git_change_detector.py`** - Git-based change detection

#### Conversation History Indexing
- **`indexers/slack_history_indexer.py`** - Slack conversation history indexer

### Workspace System
- **`workspace/workspace_manager.py`** - Manages workspace lifecycle and resources
- **`workspace/action_logger.py`** - Logs workspace actions and operations

### Metadata System
- **`metadata/metadata_location.py`** - Sidecar path: `workspaces/<channel>/metadata/<org>/<repo>/…`
- **`metadata/metadata_generator.py`** - Writes overlays to the sidecar only (never through the repo symlink)
- **`metadata/metadata_reader.py`** - Sidecar first, then leftover in-tree `.metadata.benedict`
- **`metadata/source_dir_skip.py`** - Skip venv/cache under the repo root only
- **`metadata/content_handlers.py`** - Content-specific handlers for metadata generation

Benedict does not have a method-file subsystem. A `.benedict.method.yaml` in a repository is an ordinary file, not a runtime feature.

### Utilities
- **`lib/logging.py`** - Process-wide logging setup (`setup_logging`, `get_logger`)
- **`lib/dateutil.py`** - UTC normalization for incremental indexers
- **`utils/context.py`** - Context building functions (uses semantic search when available)

## Dependency Flow

```
main.py (entry point)
  ├─> Creates: LLM (optional)
  ├─> Creates: RepoReader (optional)
  ├─> Creates: WorkspaceManager (required)
  ├─> Creates: MetadataGenerator (for semantic indexer)
  ├─> Creates: RepoChangeDetector (for semantic indexer)
  ├─> Creates: SemanticIndexer (optional, with MetadataGenerator and RepoChangeDetector)
  ├─> Creates: ConversationRepository (required)
  ├─> Creates: ProgressService (optional, needs LLM)
  └─> Creates: RepoAgent (with all dependencies)
       ├─> Creates: ConversationManager (with ConversationRepository)
       └─> Creates: MetadataGenerator (if workspace_manager available)
            └─> Creates: SlackApp (with RepoAgent)
                 └─> Starts: SocketModeHandler
```

## Component Interactions

### Workspace System
- Each Slack channel gets its own workspace directory
- Repositories are symlinked (or copied) into workspace on onboarding
- Workspace paths are used for:
  - Repository access (via WorkspaceRepoReader)
  - Metadata generation and reading
  - Action logging
  - Conversation history indexing

### Context Building Flow

Full request lifecycle (routes, prompts, tools): `artifacts/REQUEST_PATH.html`.

1. User asks a question in a Slack thread
2. `RepoAgent.handle_conversation()` is called
3. If the text is an explicit metadata-file request (e.g. "show metadata", "list files", "repository summary") and `.metadata.benedict` exists, a metadata-tool shortcut may run. GitHub issue/PR requests do not enter that shortcut. Tool failure falls through.
4. Gets workspace path and creates ActionLogger
5. Creates WorkspaceRepoReader adapter (if workspace available)
6. Calls `build_context()` which:
   - Includes recent actions from action log
   - Includes repository metadata (if available)
   - Includes README.md
   - Uses semantic search (if available) or keyword matching
   - Reads relevant files via RepoReader
7. Conversation-path LLM call may use `run_github` via `run_tool_loop`

MCP `ask_benedict` reuses `build_context()` and a single `llm.generate()`. It does not use `RepoAgent`, thread history, or tools.

### Semantic Indexing Flow
1. On first query, repository is indexed if not already indexed
2. Uses RepoChangeDetector to detect changes for incremental updates
3. MetadataGenerator creates METADATA files for directories
4. Files are chunked and embedded into ChromaDB
5. Search queries use semantic similarity to find relevant files

### Conversation Management
- Each Slack thread has a unique `thread_ts` identifier
- Conversations are persisted via ConversationRepository
- ConversationManager handles conversation lifecycle
- Message history is maintained for context in LLM calls

## Design Principles

- **SOLID**: All components follow SOLID principles
- **Dependency Injection**: Dependencies injected, not created internally
- **Protocol-Based**: Uses Python Protocols for interfaces
- **Root Composition**: All concrete classes instantiated in `main.py`
- **Graceful Degradation**: Works even if optional components unavailable
- **Workspace Isolation**: Each channel has isolated workspace for resources
- **Incremental Updates**: Change detection enables efficient index updates

## Configuration

Environment variables:
- `SLACK_BOT_TOKEN` - Slack bot token (required)
- `SLACK_APP_TOKEN` - Slack app token (required)
- `BENEDICT_DATA_DIR` - Data directory (default: `~/.benedict`)
- `BENEDICT_WORKSPACES_DIR` - Workspaces directory (default: `{data_dir}/workspaces`)
- `BENEDICT_WORKSPACE_COPY_MODE` - "symlink" or "copy" (default: "symlink")
- `BENEDICT_CHROMA_DB_DIR` - ChromaDB directory (default: `{data_dir}/.chroma_db`)
- `BENEDICT_STATE_FILE` - State file path (default: `{data_dir}/state.json`)
- `BENEDICT_OPERATOR_UI_PORT` - Operator console port (default: `8765`)
- `BENEDICT_PROGRESS` - Unattended progress loop (default: on; set `0` to disable)
- `BENEDICT_PROGRESS_INTERVAL_S` - Seconds between progress cycles (default: `21600`)
- `BENEDICT_PROGRESS_START_DELAY_S` - Delay before first cycle (default: `120`)

## Commands

- `@agent onboard repo <repo>` - Link channel to repository
- `@agent offboard` - Unlink the channel from its repository
- `@agent status` - Show channel status and repository info
- `@agent update index` - Update semantic index (incremental)
- `@agent update index force` - Force full reindex
- `@agent progress` / `progress all` / `progress now` - Run the unattended progress loop
- `@agent <question>` - Ask question about repository

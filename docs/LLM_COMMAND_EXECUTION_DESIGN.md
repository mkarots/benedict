# LLM Command Execution Design

**Issue**: [#15 - Clarify how Benedict executes LLM-driven commands](https://github.com/mkarots/benedict/issues/15)

**Status**: Design Document  
**Last Updated**: 2026-08-19

## Overview

This document describes how Benedict executes commands and tool calls that originate from LLM (Claude) interactions. It covers the execution environment, workspace isolation, filesystem access, tool registration, and security boundaries.

## Table of Contents

1. [Execution Environment](#execution-environment)
2. [Working Directory and Filesystem Access](#working-directory-and-filesystem-access)
3. [Tool Selection and Registration](#tool-selection-and-registration)
4. [Security Model](#security-model)
5. [Architecture Details](#architecture-details)
6. [Extension Points](#extension-points)

---

## Execution Environment

### Process Model

All LLM tool calls execute **in-process** within the same Python process as the Benedict Slack bot. There is no sandboxing, containerization, or separate subprocess isolation for tool execution.

```
┌─────────────────────────────────────────────────────┐
│  Benedict Main Process (Python 3.10+)              │
│                                                     │
│  ┌──────────────┐                                  │
│  │  Slack Bot   │ ◄───── Socket Mode Handler       │
│  └──────┬───────┘                                  │
│         │                                           │
│         ▼                                           │
│  ┌──────────────┐                                  │
│  │  RepoAgent   │ ◄───── Handles conversations     │
│  └──────┬───────┘                                  │
│         │                                           │
│         ▼                                           │
│  ┌──────────────────────┐                          │
│  │  Tool Loop/Executor  │ ◄─── Executes LLM tools  │
│  └──────────────────────┘                          │
│         │                                           │
│         ├──► Metadata Tools  (read .metadata files)│
│         ├──► GitHub Tools    (subprocess `gh` CLI) │
│         └──► Future Tools    (TBD)                 │
│                                                     │
└─────────────────────────────────────────────────────┘
```

### Thread Model

Benedict uses the Slack Bolt framework with Socket Mode, which runs event handlers synchronously in the main thread. Each Slack message triggers a handler call that blocks until completion.

**Implications:**
- Tool execution blocks the event handler
- Long-running tools (e.g., `gh` commands) block the bot from processing other messages
- No concurrent tool execution within a single conversation
- The bot is single-threaded per message

### Python Environment

Tools execute with:
- **Python Version**: 3.10+
- **Virtual Environment**: Same virtualenv as the bot (if activated)
- **Environment Variables**: Inherited from the bot process
- **Working Directory**: See [Working Directory](#working-directory-and-filesystem-access) section
- **System User**: Same user account running the bot

---

## Working Directory and Filesystem Access

### Workspace Isolation

Each Slack channel gets its own **workspace directory** when onboarded to a repository. The workspace provides isolation between channels and tracks channel-specific state.

```
BENEDICT_DATA_DIR/
├── state.json                    # Channel mappings, conversations
├── .chroma_db/                   # Semantic index (shared across channels)
└── workspaces/
    ├── C12345ABC/                # Workspace for channel C12345ABC
    │   ├── org-repo/             # Repository (symlink or copy)
    │   ├── actions.jsonl         # Action log
    │   └── conversations/        # Indexed Slack history
    └── C67890DEF/                # Workspace for channel C67890DEF
        └── ...
```

### Working Directory by Tool Type

Different tool types operate in different working directories:

| Tool Type | Working Directory | Notes |
|-----------|------------------|-------|
| **Metadata Tools** | `workspace_path/repo` | Reads `.metadata.benedict` files |
| **GitHub Tools** | `workspace_path/repo` | `gh` runs in the repo directory |
| **Future Shell Tools** | `workspace_path/repo` | If implemented |
| **Conversation Tools** | N/A (in-memory) | No filesystem access |

### Workspace Creation Mode

Workspaces support two creation modes (configured via `BENEDICT_WORKSPACE_COPY_MODE`):

1. **Symlink Mode** (default):
   - Creates symbolic links to the source repository
   - Shares the same on-disk files as the source
   - Changes in workspace affect the source and vice versa
   - Lightweight and disk-efficient

2. **Copy Mode**:
   - Creates a full copy of the source repository
   - Isolated filesystem state
   - Changes in workspace don't affect the source
   - More disk space but better isolation

### Filesystem Access Scope

Tools have **unrestricted filesystem access** within Python's permissions. There are no chroot jails, capability restrictions, or mandatory access controls.

**What tools CAN access:**
- ✅ The workspace directory (`workspaces/<channel_id>/`)
- ✅ The source repository (especially in symlink mode)
- ✅ Any file the bot's user account can read/write
- ✅ Network filesystems if mounted
- ✅ `/tmp`, `/var`, and other system directories

**What tools CANNOT access (by OS permissions only):**
- ❌ Files owned by other users (unless bot runs as root or has sudo)
- ❌ System files protected by OS-level permissions
- ❌ Files in directories without execute permissions

**Security Note**: There is no programmatic restriction preventing tools from accessing files outside the workspace. Tools trust the bot operator to run Benedict as a non-privileged user and to understand that LLM-generated commands execute with full user permissions.

### Repository Resolution

When onboarding a channel, Benedict resolves repository paths in this order:

1. **Absolute path**: If the text contains an absolute path (e.g., `/Users/name/Projects/repo`)
2. **Org/Repo in source dirs**: Searches `BENEDICT_REPO_SOURCE_DIRS` for `org/repo`
3. **Repo name in source dirs**: Searches `BENEDICT_REPO_SOURCE_DIRS` for just `repo`
4. **Default location**: `~/Projects/<repo>` (if `BENEDICT_REPO_SOURCE_DIRS` not set)
5. **Current directory**: `$PWD/<repo>`

**Environment Variable:**
```bash
BENEDICT_REPO_SOURCE_DIRS=/Users/name/Projects,/opt/repos,/workspace/git
```

---

## Tool Selection and Registration

### Two Tool Registration Paths

Benedict uses **two separate tool registries** for different purposes:

#### 1. Metadata Tool Path (Narrow Shortcut)

**When**: Explicit metadata-file requests detected by `is_metadata_command()`

**Tools Available:**
- `get_file_metadata` - Read file metadata from `.metadata.benedict`
- `list_key_files` - List key files from metadata
- `get_repository_summary` - Get repository summary from metadata

**Flow:**
```python
# agent.py:handle_conversation()
if self.llm and self.workspace_manager and self.is_metadata_command(text):
    tool_registry = create_tool_registry(
        metadata_reader=metadata_reader,
        repo_path=repo_path,
    )
    llm_result = self.llm_classifier.classify(text, conversation_history=history)
    if llm_result and llm_result.get("tool_calls"):
        # Execute metadata tools
```

**Scope**: This is a **read-only shortcut** for metadata file operations. It does NOT include:
- ❌ `run_github` tool
- ❌ General conversation/query handling
- ❌ Code search or semantic analysis

**Fallback**: If metadata tools fail or metadata file doesn't exist, Benedict falls through to the conversation path.

#### 2. Conversation Tool Path (GitHub CLI)

**When**: All other conversations (including GitHub issue/PR requests)

**Tools Available:**
- `run_github` - Execute `gh` CLI commands

**Flow:**
```python
# agent.py:handle_conversation() - after metadata shortcut or skip
github_registry = ToolRegistry()
if workspace_path:
    github_registry.register(RunGithubTool())
    tool_context["workspace_path"] = str(workspace_path / repo)

response_text = run_tool_loop(
    llm=self.llm,
    messages=history_messages,
    system=system,
    tool_registry=github_registry,
    context=tool_context,
)
```

**Scope**: This is the **main conversation path** that handles:
- ✅ GitHub issue/PR operations
- ✅ Repository questions (uses context building, not tools)
- ✅ Conversation queries
- ✅ General Q&A

### Tool Classification Decision Tree

```
User Message
    │
    ├─→ Explicit command (onboard, status, update index)
    │   └─→ Direct handler (no LLM tools)
    │
    └─→ Conversation / Question
        │
        ├─→ is_metadata_command(text)?
        │   │   (matches: "metadata", "list files", "repository summary")
        │   │
        │   ├─→ YES → Metadata Tool Path
        │   │   ├─→ Classify with LLM + metadata tools
        │   │   ├─→ Execute metadata tools
        │   │   └─→ Fall through if failure
        │   │
        │   └─→ NO ──┐
        │             │
        └─────────────┘
                      │
                      └─→ Conversation Tool Path
                          ├─→ Build context (semantic search, README, etc.)
                          ├─→ LLM with run_github tool
                          └─→ Tool loop (if tools called)
```

### Tool Registration Conditions

**Metadata Tools** are registered ONLY when:
1. `workspace_manager` is available
2. `is_metadata_command(text)` returns `True`
3. `.metadata.benedict` file exists at `repo_path`

**GitHub Tools** are registered ONLY when:
1. `workspace_path` is available (channel is onboarded)
2. Conversation path is active (not metadata shortcut or explicit command)

### Tool Execution Loop

Tools execute in an **iterative loop** (see `commands/tool_loop.py`):

1. **LLM Call**: Claude generates response, potentially with tool calls
2. **Tool Execution**: Each tool call executes via `ToolRegistry.execute()`
3. **Result Formatting**: Tool results are formatted as text/JSON
4. **Feedback Loop**: Results are added to conversation and sent back to LLM
5. **Iteration**: Loop continues up to `MAX_ITERATIONS` (default: 5)
6. **Termination**: Loop exits when LLM returns text (no tool calls)

```python
# commands/tool_loop.py
for iteration in range(max_iterations):
    response = llm.generate(messages=working_messages, tools=tools)
    if isinstance(response, str):
        return response  # Done - text response
    
    # Execute tool calls
    for call in response["tool_calls"]:
        result = tool_registry.execute(call["name"], call["arguments"], context)
        tool_results.append(format_tool_result(result))
    
    # Feed results back to LLM
    working_messages.append({"role": "user", "content": tool_results})
```

---

## Security Model

### Trust Boundary

Benedict's security model is based on **trust in the Slack workspace and bot operator**:

```
┌─────────────────────────────────────────────────────────┐
│  TRUSTED ZONE                                           │
│                                                         │
│  • Slack workspace members                             │
│  • Bot operator (user running Benedict)                │
│  • Onboarded repositories (local checkouts)            │
│  • Claude API (LLM provider)                           │
│                                                         │
└─────────────────────────────────────────────────────────┘
         │
         ▼
    LLM Tool Calls
         │
         ▼
┌─────────────────────────────────────────────────────────┐
│  UNTRUSTED ZONE                                         │
│                                                         │
│  • External services (GitHub API)                      │
│  • Network endpoints                                    │
│  • User-provided input (Slack messages)                │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### Security Boundaries

#### What IS Prevented

1. **GitHub Token Exposure**
   - `gh auth token` commands are explicitly blocked
   - Token patterns are redacted from tool output via regex: `(ghp_|gho_|ghu_|ghs_|ghr_|github_pat_)[A-Za-z0-9_]+`

   ```python
   # commands/github_tools.py
   if argv[0] == "auth" and argv[1] == "token":
       return ToolResult(success=False, error="Refusing to run `gh auth token`")
   ```

2. **Process Escape Sequences**
   - Null bytes (`\x00`) in `gh` arguments are rejected
   - Shell interpretation is prevented (using `subprocess.run()` with array arguments)

3. **Output Size Limits**
   - `gh` output is truncated to `MAX_OUTPUT_CHARS` (32,000 characters)
   - Prevents memory exhaustion from large outputs

4. **Timeout Protection**
   - `gh` commands timeout after `DEFAULT_TIMEOUT_S` (30 seconds)
   - Prevents indefinite hangs

5. **Binary Restriction**
   - Only the `gh` binary can be executed (hardcoded `GITHUB_BINARY = "gh"`)
   - No arbitrary shell commands or other binaries

#### What IS NOT Prevented

Benedict does **NOT** prevent:

1. **Filesystem Access**
   - Tools can read/write any file the bot user can access
   - No chroot, AppArmor, SELinux, or capability restrictions
   - No programmatic limits on which directories are accessible

2. **Network Access**
   - Tools inherit the bot's network access
   - Can make arbitrary HTTP/HTTPS requests (if Python code allows)
   - `gh` can call GitHub API with host credentials

3. **Credential Usage**
   - `gh` inherits the host's GitHub authentication
   - Tools run with full `gh` permissions (read/write repos, create PRs, etc.)
   - No scope limitation or per-channel credentials

4. **Mutating Operations**
   - LLM can call `gh` to create, merge, close, comment, etc.
   - **Mitigation**: System prompt asks LLM to confirm with user first
   - **Reality**: This is a **policy**, not enforcement. LLM *might* mutate without asking.

5. **Resource Limits**
   - No CPU, memory, or I/O limits on tool execution
   - No rate limiting on tool calls
   - Only iteration count limit (`MAX_ITERATIONS=5`)

6. **Audit Trail**
   - Actions are logged to `actions.jsonl` but not tamper-proof
   - No cryptographic signatures or append-only guarantees
   - Logs are human-readable JSON, not secure audit logs

### GitHub CLI (`run_github`) Security

The `run_github` tool is the **highest-privilege tool** in Benedict. It executes `gh` CLI commands in the workspace repository.

**Execution Model:**
```python
# commands/github_tools.py
def execute(self, arguments, context):
    cwd = Path(context["workspace_path"])  # e.g., /data/workspaces/C123/repo
    command = ["gh", *argv]  # e.g., ["gh", "pr", "list"]
    
    completed = subprocess.run(
        command,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        timeout=self.timeout_s,
        check=False,
    )
```

**Security Properties:**

| Property | Status | Implementation |
|----------|--------|----------------|
| **Authentication** | Host credentials | `gh` uses `~/.config/gh/hosts.yml` |
| **Authorization** | Full GitHub token scope | No scope restriction |
| **Working Directory** | Workspace repo | Locked to `context["workspace_path"]` |
| **Binary** | `gh` only | Hardcoded binary path |
| **Shell Escaping** | Protected | `subprocess.run()` with array args |
| **Output Redaction** | Token patterns | Regex-based token removal |
| **Timeout** | 30 seconds | `timeout=self.timeout_s` |
| **Mutual Operations** | Prompt guidance only | LLM asked to confirm, but not enforced |

**Attack Scenarios:**

❌ **Prevented:**
- Executing arbitrary shell commands (no shell=True)
- Reading GitHub token directly (`gh auth token` blocked)
- Null byte injection (rejected by validation)

⚠️ **Possible:**
- Creating unwanted PRs (if LLM ignores prompt)
- Commenting on issues (if LLM ignores prompt)
- Reading private repository data (within token scope)
- Exhausting API rate limits (no rate limiting)

### Recommendations for Production Use

If Benedict is used in production or with untrusted users:

1. **Run as Non-Privileged User**
   - Create dedicated `benedict` user with minimal permissions
   - Use `sudo` restrictions or AppArmor profiles

2. **Scope GitHub Token**
   - Use fine-grained personal access tokens (not classic tokens)
   - Limit scope to read-only or specific repositories
   - Rotate tokens regularly

3. **Enable Audit Logging**
   - Log all `gh` commands and results
   - Monitor for suspicious patterns (mass deletions, token access)
   - Alert on blocked operations (`gh auth token`)

4. **Limit Slack Access**
   - Use private channels or restricted workspaces
   - Implement approval workflows for mutations
   - Consider bot permissions (remove delete, admin scopes)

5. **Containerization**
   - Run Benedict in Docker/Podman with resource limits
   - Use read-only filesystem mounts where possible
   - Apply seccomp/AppArmor profiles

6. **Code Review LLM Outputs**
   - Implement human-in-the-loop for GitHub mutations
   - Add confirmation prompts in Slack UI
   - Log and review all tool calls

---

## Architecture Details

### Component Interaction Diagram

```
┌────────────────────────────────────────────────────────────────┐
│                        Slack Event                             │
│                   (app_mention, message)                       │
└────────────────────────────────┬───────────────────────────────┘
                                 │
                                 ▼
┌────────────────────────────────────────────────────────────────┐
│                      slack_app.py                              │
│                   (Bolt event handlers)                        │
└────────────────────────────────┬───────────────────────────────┘
                                 │
                                 ▼
┌────────────────────────────────────────────────────────────────┐
│                      RepoAgent                                 │
│                    (agent.py)                                  │
│                                                                │
│  ┌──────────────────────────────────────────────────┐         │
│  │  Command Detection                                │         │
│  │  • is_onboard_command()                          │         │
│  │  • is_status_command()                           │         │
│  │  • is_update_index_command()                     │         │
│  │  • is_metadata_command()                         │         │
│  └──────────────────────┬───────────────────────────┘         │
│                         │                                      │
│         ┌───────────────┼───────────────┐                     │
│         │               │               │                     │
│         ▼               ▼               ▼                     │
│   Direct Handler   Metadata Path   Conversation Path         │
│   • onboard        • LLM Classifier • build_context()        │
│   • status         • Metadata Tools • LLM with tools         │
│   • update index   • Fallback       • Tool Loop              │
└─────────────────────────┬──────────────────┬──────────────────┘
                          │                  │
              ┌───────────┴───────┐  ┌──────┴─────────────────┐
              │                   │  │                        │
              ▼                   │  ▼                        │
    ┌──────────────────┐          │  ┌──────────────────┐    │
    │ Metadata Tools   │          │  │  run_github      │    │
    │ • get_file_meta  │          │  │  (GitHub CLI)    │    │
    │ • list_files     │          │  └────────┬─────────┘    │
    │ • repo_summary   │          │           │              │
    └────────┬─────────┘          │           ▼              │
             │                    │  ┌──────────────────┐    │
             ▼                    │  │   subprocess     │    │
    ┌──────────────────┐          │  │   gh [...args]   │    │
    │ MetadataReader   │          │  │   cwd=workspace  │    │
    │ read .metadata   │          │  │   timeout=30s    │    │
    │ files (YAML)     │          │  └──────────────────┘    │
    └──────────────────┘          │                          │
                                  │                          │
                   ┌──────────────▼──────────────┐           │
                   │     Tool Loop (tool_loop.py)│◄──────────┘
                   │  • LLM → tool calls         │
                   │  • Execute via Registry     │
                   │  • Feed results back        │
                   │  • Iterate (max 5 times)    │
                   └─────────────────────────────┘
```

### File Organization

```
src/benedict/
├── agent.py                         # Main agent logic
│   ├── handle_conversation()        # Entry point for Q&A
│   ├── is_metadata_command()        # Metadata path detection
│   └── Tool path selection
│
├── commands/                        # Tool infrastructure
│   ├── tool_framework.py            # Tool/ToolRegistry base classes
│   ├── tool_loop.py                 # Iterative tool execution loop
│   ├── tool_executor.py             # [Legacy] Metadata tool executor
│   ├── tool_registry_factory.py     # Metadata tool registry factory
│   ├── metadata_tools.py            # Metadata tool implementations
│   ├── github_tools.py              # GitHub CLI tool (run_github)
│   └── llm_classifier.py            # LLM-based command classifier
│
├── workspace/                       # Workspace management
│   ├── workspace_manager.py         # Workspace lifecycle
│   └── action_logger.py             # Action logging (actions.jsonl)
│
├── metadata/                        # Metadata file handling
│   ├── metadata_reader.py           # Read .metadata.benedict
│   └── metadata_generator.py        # Generate metadata files
│
└── utils/
    └── context.py                   # Context building (semantic search, README)
```

### Data Flow: User Question to Tool Execution

**Example: "List recent PRs"**

1. **Slack Event**: `app_mention` event received
2. **slack_app.py**: Routes to `agent.handle_conversation()`
3. **agent.py**: 
   - Checks `is_metadata_command("list recent PRs")` → `False`
   - Skips metadata path
   - Builds context (README, semantic search)
   - Registers `run_github` tool
   - Calls `run_tool_loop()`
4. **tool_loop.py**:
   - Calls `llm.generate()` with tools
   - LLM responds with tool call: `{"name": "run_github", "input": {"argv": ["pr", "list", "--json", "title,number"]}}`
   - Executes via `github_registry.execute("run_github", ...)`
5. **github_tools.py**:
   - Validates argv
   - Runs `subprocess.run(["gh", "pr", "list", "--json", "title,number"], cwd=workspace_path)`
   - Captures output, redacts tokens, returns result
6. **tool_loop.py**:
   - Formats result as text/JSON
   - Feeds back to LLM: `{"role": "user", "content": [{"type": "tool_result", "content": "..."}]}`
   - LLM interprets and returns text response
7. **agent.py**: Returns formatted response to Slack

### Workspace Lifecycle

```
1. User: "@benedict onboard repo org/repo"
   │
   ├─→ RepoAgent.handle_onboard()
   │
   ├─→ WorkspaceManager.create_workspace(channel_id)
   │   └─→ Creates: workspaces/C12345ABC/
   │
   ├─→ WorkspaceManager.add_resource()
   │   └─→ Creates: workspaces/C12345ABC/org-repo/ (symlink or copy)
   │
   ├─→ ActionLogger.log_action("symlink_repository")
   │   └─→ Writes: workspaces/C12345ABC/actions.jsonl
   │
   ├─→ MetadataGenerator.generate_and_write()
   │   └─→ Creates: workspaces/C12345ABC/org-repo/.metadata.benedict
   │
   └─→ ConversationHistoryIndexer.index_conversations()
       └─→ Creates: workspaces/C12345ABC/conversations/

2. Later tool calls:
   │
   ├─→ context["workspace_path"] = "workspaces/C12345ABC/org-repo"
   │
   └─→ Tools run in this directory
```

---

## Extension Points

### Adding New Tools

To add a new tool (e.g., `run_docker`, `query_database`):

1. **Define Tool Class** (`commands/new_tools.py`):
   ```python
   from .tool_framework import Tool, ToolResult
   
   class RunDockerTool(Tool):
       def __init__(self):
           super().__init__(
               name="run_docker",
               description="Run docker commands in the workspace",
           )
       
       def get_schema(self):
           return {
               "name": self.name,
               "description": self.description,
               "input_schema": {
                   "type": "object",
                   "properties": {
                       "command": {"type": "string"},
                   },
                   "required": ["command"],
               },
           }
       
       def execute(self, arguments, context):
           # Implement tool logic
           return ToolResult(success=True, message="...")
   ```

2. **Register Tool** (`agent.py:handle_conversation()`):
   ```python
   from benedict.commands.new_tools import RunDockerTool
   
   github_registry = ToolRegistry()
   if workspace_path:
       github_registry.register(RunGithubTool())
       github_registry.register(RunDockerTool())  # <-- Add here
   ```

3. **Update System Prompt** (document new tool in `agent.py` system message)

4. **Test**: Unit test with mock LLM, integration test with real LLM

### Adding New Tool Paths

To add a new tool path (e.g., `database_path`):

1. **Add Detection Method** (`agent.py`):
   ```python
   @staticmethod
   def is_database_command(text: str) -> bool:
       return "database" in text.lower() or "query" in text.lower()
   ```

2. **Add Path in `handle_conversation()`**:
   ```python
   if self.is_database_command(text):
       db_registry = create_database_tool_registry()
       # ... execute database path
   ```

3. **Create Tool Registry Factory** (`commands/database_tools.py`):
   ```python
   def create_database_tool_registry() -> ToolRegistry:
       registry = ToolRegistry()
       registry.register(QueryDatabaseTool())
       return registry
   ```

### Future Considerations

**Potential Enhancements:**

1. **Sandbox Execution**
   - Run tools in containers (Docker, Podman)
   - Use `firejail` or `bubblewrap` for sandboxing
   - Apply seccomp profiles to restrict syscalls

2. **Fine-Grained Permissions**
   - Per-channel tool access control
   - User role-based tool availability
   - Approval workflows for mutations

3. **Audit and Compliance**
   - Structured audit logs (JSON, with signatures)
   - Compliance reporting (SOC2, GDPR)
   - Tamper-evident logs (append-only, checksums)

4. **Resource Limits**
   - CPU/memory limits per tool call
   - Rate limiting (calls per minute)
   - Concurrent execution limits

5. **Tool Marketplace**
   - Plugin system for third-party tools
   - Tool discovery and installation
   - Version management and updates

---

## References

- **Code Files**:
  - `src/benedict/agent.py` - Main agent logic and tool path selection
  - `src/benedict/commands/tool_loop.py` - Tool execution loop
  - `src/benedict/commands/github_tools.py` - GitHub CLI tool implementation
  - `src/benedict/commands/tool_framework.py` - Tool base classes
  - `src/benedict/workspace/workspace_manager.py` - Workspace management

- **Related Documentation**:
  - [ARCHITECTURE.md](../plans/ARCHITECTURE.md) - Overall system architecture
  - [CODE_READING_GUIDE.md](./CODE_READING_GUIDE.md) - Codebase navigation
  - [LLM_COMMAND_CLASSIFIER_DESIGN.md](./LLM_COMMAND_CLASSIFIER_DESIGN.md) - LLM classifier details

- **External**:
  - [GitHub CLI Documentation](https://cli.github.com/manual/)
  - [Anthropic Claude API](https://docs.anthropic.com/)
  - [Slack Bolt Python](https://slack.dev/bolt-python/)

---

**Document Status**: Complete  
**Last Review**: 2026-08-19  
**Reviewers**: TBD  
**Next Review**: When tool system changes significantly

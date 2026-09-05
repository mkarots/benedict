# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.8.12] - 2026-09-01

### Changed
- Code and conversation history share one Chroma client (`.chroma_db`). They stay in separate collections (`repo_*` vs `conversation_*`). The composition root opens the client; neither indexer owns the database.

## [0.8.11] - 2026-09-01

### Changed
- Conversation history has its own Chroma store (`BENEDICT_CONVERSATION_CHROMA_DIR`, default `{data_dir}/.conversation_chroma`). Code search stays in `.chroma_db`. Slack is only the ingest adapter; the agent owns conversation search. Existing channel collections in `.chroma_db` are unused; the next history update backfills from workspace JSON.

## [0.8.10] - 2026-09-01

### Changed
- Slack posts a handler reply with `post_reply(payload, say=say, thread_ts=thread_ts)`. Command vs conversation Block Kit lives on the payload (`command()` vs `markdown()`), not a `message_type` argument.

## [0.8.9] - 2026-09-01

### Changed
- Slack handlers return structured payloads (`StatusPayload`, `ErrorPayload`, `MarkdownPayload`) instead of emoji-prefixed strings. Block Kit rendering no longer regex-parses those strings ([#117](https://github.com/mkarots/benedict/issues/117)).

## [0.8.8] - 2026-09-01

### Changed
- Internal packages group by capability: protocols sit next to implementations, metadata and git change detection live under `semantic_indexer/`, Slack history indexing is `conversation_history_indexer/`, agent tools are `tools/`, and context building sits beside the agent instead of under `utils/`.
- Semantic search returns a `SearchHit` value object instead of ad-hoc `{file_path, content, score}` dicts.

## [0.8.7] - 2026-09-01

### Changed
- Slack lives in `benedict.slack`: `messages` for delivery, `app` for Bolt handlers, `formatter` for Block Kit ([#128](https://github.com/mkarots/benedict/issues/128)).

## [0.8.6] - 2026-08-31

### Fixed
- Slack questions retrieve indexed channel history from the existing `slack_channel_*` Chroma collection. MCP `ask_benedict` still omits Slack ([#120](https://github.com/mkarots/benedict/issues/120)).

### Changed
- Slack channel search lives on the Slack history indexer. The Chroma repo indexer does not mention Slack.

## [0.8.5] - 2026-08-31

### Fixed
- UTC timestamps use timezone-aware `datetime.now(timezone.utc)` instead of deprecated `datetime.utcnow()`.

## [0.8.4] - 2026-08-31

### Changed
- Runtime dependencies declare `numpy` and `slack-sdk` because the package imports them. Unused `rich` is no longer a direct dependency.

### Removed
- Unused `dev` extra packages: Flake8, pytest-asyncio, and pytest-mock. The leftover `make deps` target is gone.

## [0.8.3] - 2026-08-31

### Changed
- CI runs pytest on Python 3.12 only. Pull requests no longer wait on 3.10 and 3.11 test jobs. The package still declares `requires-python = ">=3.10"`.

## [0.8.2] - 2026-08-31

### Fixed
- Operator console pipeline stages collapse when you click an already-open title again.

## [0.8.1] - 2026-08-31

### Fixed
- `.gitignore` no longer treats `src/benedict/lib/` as a virtualenv path. Logging and date helpers are tracked so a fresh clone can import them ([#118](https://github.com/mkarots/benedict/issues/118)).

## [0.8.0] - 2026-08-31

### Added
- Operator console shows the **chunks Chroma returned** for a question (path, score, expandable text), then the files stuffed into the prompt and why each was included (always README, semantic hit, keyword match, or asked-for file). Slack Q&A, architect, MCP `ask_benedict`, and MCP `search_code` all record this. The model still has no `read_file` tool: chunks pick files, then full file text is stuffed.

## [0.7.0] - 2026-08-30

### Added
- Slack conversations can run Notion through `ntn` (`run_notion`), the same argv-only pattern as `run_github`. `@benedict link notion <url>` stores a per-channel default; `unlink notion` clears it without offboarding the repo. Slack always loads missing keys from `.env` so `NOTION_API_KEY` is not skipped when Slack tokens are already set. Replaces the stale implementation on [#8](https://github.com/mkarots/benedict/pull/8).

## [0.6.26] - 2026-08-30

### Changed
- `[tool.mypy]` now enforces typed public and internal signatures on `src/benedict` (`disallow_untyped_defs`, `check_untyped_defs`, and related flags). The previous per-module ignore list is gone. `make type-check` stays the CI type-check command ([#58](https://github.com/mkarots/benedict/issues/58)).

## [0.6.25] - 2026-08-30

### Added
- Pre-commit hooks (`.pre-commit-config.yaml`): Black, Ruff, trailing-whitespace, and end-of-file-fixer. Versions match the `dev` extra. Install with `pre-commit install` after `make sync-dev`. README shows a pre-commit badge ([#59](https://github.com/mkarots/benedict/issues/59)).

## [0.6.24] - 2026-08-29

### Added
- README badges for Contributor Covenant, GitHub Discussions, Ruff, and Black. CI, license, and Python 3.10+ stay.

## [0.6.23] - 2026-08-29

### Changed
- Agent writing, design-doc, architecture, and version-bump rules live in `.cursor/rules/`. README and CONTRIBUTING point there. `CLAUDE.md` is removed. `.gitignore` tracks that folder and still ignores the rest of `.cursor/`.

## [0.6.22] - 2026-08-29

### Removed
- Internal open-source planning notes: `OPEN_SOURCE_PLAN.md`, `OPEN_SOURCE_QUICK_START.md`, `OPEN_SOURCE_FILE_INVENTORY.md`, `OPEN_SOURCE_SUMMARY.md`, and `docs/OPEN_SOURCE_GUIDE_INDEX.md`. `OPEN_SOURCE_CHECKLIST.md` stays.

## [0.6.21] - 2026-08-29

### Added
- **Maintainers**: `MAINTAINERS.md` lists the project lead, how merge decisions are made, and how to become a maintainer. README Community and CONTRIBUTING link to it ([#66](https://github.com/mkarots/benedict/issues/66)).

## [0.6.20] - 2026-08-29

### Changed
- README and docs home show the logo as a centered hero, with the italic line `repo bene(volent)dict(ator) agent` under it.

## [0.6.19] - 2026-08-29

### Added
- Benedict logo at `docs/assets/logo.png`. README shows it. MkDocs uses it as the site logo and favicon.

## [0.6.18] - 2026-08-29

### Added
- README badges for CI, Apache-2.0, and Python 3.10+. Community already links CONTRIBUTING, CODE_OF_CONDUCT, and SECURITY. Clone URL stays the public remote `github.com/mkarots/benedict.git` ([#56](https://github.com/mkarots/benedict/issues/56)).

## [0.6.17] - 2026-08-29

### Added
- GitHub **pull request** template (`.github/PULL_REQUEST_TEMPLATE.md`) with description, related issues, type of change, testing done, and a checklist for tests, docs, and changelog. CONTRIBUTING points contributors at it ([#55](https://github.com/mkarots/benedict/issues/55)).

## [0.6.16] - 2026-08-29

### Added
- GitHub **feature request** issue template (`.github/ISSUE_TEMPLATE/feature_request.md`) with description, use case, proposed solution, and alternatives. README Community and CONTRIBUTING link to it. The existing chooser (`config.yml`) lists it next to the bug report ([#54](https://github.com/mkarots/benedict/issues/54)).

## [0.6.15] - 2026-08-29

### Added
- Shape tests for the CI workflow (`.github/workflows/ci.yml`) and GitHub issue templates (`.github/ISSUE_TEMPLATE/`).

## [0.6.14] - 2026-08-29

### Added
- **GitHub Discussions**: Q&A, Ideas, and Show and tell are enabled on the repository. README Community and CONTRIBUTING send questions there instead of issues ([#67](https://github.com/mkarots/benedict/issues/67)).

## [0.6.13] - 2026-08-29

### Added
- **Contributing guide**: `CONTRIBUTING.md` covers local setup (`make setup` / uv), tests, Ruff/Black/mypy (and optional Pylint), commit messages, issue reporting, and pull requests. README Community links to it ([#52](https://github.com/mkarots/benedict/issues/52)).

## [0.6.12] - 2026-08-29

### Added
- GitHub **bug report** issue template (`.github/ISSUE_TEMPLATE/bug_report.md`) and template chooser (`config.yml`). Blank issues stay enabled. Security and Code of Conduct reports stay on private channels ([#53](https://github.com/mkarots/benedict/issues/53)).

## [0.6.11] - 2026-08-29

### Added
- GitHub Actions CI (`.github/workflows/ci.yml`) runs lint (Ruff, Black), mypy, and pytest with coverage on pull requests and on pushes to `main`. Tests run on Python 3.10, 3.11, and 3.12. Ruff, Black, and mypy versions are pinned so CI matches local `make sync-dev` ([#57](https://github.com/mkarots/benedict/issues/57)).

### Fixed
- Unit and integration tests now call the current conversation, LLM, workspace, and repo-reader APIs instead of removed method names. `make test` and `make lint` / `make type-check` run through `uv` and fail when a check fails.

## [0.6.10] - 2026-08-29

### Added
- Package metadata in `pyproject.toml`: authors, maintainers, classifiers, keywords, and project URLs (Homepage, Repository, Issues). License stays Apache-2.0 to match `LICENSE`. README and [Install](docs/install.md) point at those fields ([#62](https://github.com/mkarots/benedict/issues/62)).

## [0.6.9] - 2026-08-29

### Added
- **Security policy**: `SECURITY.md` documents supported versions, private vulnerability reporting, and response timelines ([#50](https://github.com/mkarots/benedict/issues/50)).

## [0.6.8] - 2026-08-29

### Changed
- Example org/repo names and Slack handles in source, plans, and tests use `example-org` / `example-repo` and `@alice` ([#49](https://github.com/mkarots/benedict/issues/49)). Real GitHub URLs for this remote are unchanged.

## [0.6.7] - 2026-08-29

### Added
- **License**: Apache License 2.0 (`LICENSE`, `NOTICE`). Benedict's own code is Apache-2.0; dependencies keep their own licenses.

## [0.6.6] - 2026-08-29

### Added
- **Code of conduct**: Adopted Contributor Covenant v2.1 in `CODE_OF_CONDUCT.md` and linked it from the README.

## [0.6.5] - 2026-08-29

### Changed
- Slack setup is the two tokens and an invite. Slack’s admin UI is a table, not eight steps plus a checklist. Token and mention failures live on [Troubleshooting](docs/troubleshooting.md).

## [0.6.4] - 2026-08-29

### Changed
- Home and README lead with the product story: Benedict knows your code, knows Slack talk about those projects, and can help you plan. Progress is a next-step command, not “leave the process running.”

## [0.6.3] - 2026-08-29

### Changed
- Sidecar overlays live at `workspaces/<channel>/metadata/<org>/<repo>/`, not `workspaces/<channel>/.benedict/metadata/`.
- ADRs and retired classifier designs stay in the repo but are not published in the MkDocs sidebar.

### Fixed
- Overlay generation no longer skips every directory when the data dir is `~/.benedict`. Skip rules only apply under the repo root, so Slack reindex and onboard can create `workspaces/<channel>/metadata/`.
- Docs no longer list Notion as unimplemented. Slack conversations can run `ntn` (`run_notion`) when the host CLI is installed; Notion is still not a `RepoReader` and is not in the progress snapshot.

## [0.6.2] - 2026-08-29

### Fixed
- Generated `.metadata.benedict` overlays are written to a workspace sidecar instead of through the repo symlink into the user's clone ([#12](https://github.com/mkarots/benedict/issues/12)). Readers try the sidecar first, then leftover in-tree files. The clone is not written.

## [0.6.1] - 2026-08-29

### Changed
- Docs chrome uses charcoal (`#101010`) with gold (`#d4a574`) as the accent. Material `brown` / `amber` is no longer the docs palette.
- Docs follow a top-to-bottom spine: Home, Get started, Use, How it works, Reference, Decisions, Historical, Maintain. The catalog page is gone. [Code map](docs/CODE_MAP.md) replaces `CODE_READING_GUIDE.md` and `plans/ARCHITECTURE.md` as the in-docs module map. The GitHub README is a short landing card; `make docs` is the full story.

### Fixed
- `make docs` reports when port 8000 is already in use instead of a Python traceback. Override with `DOCS_PORT=8001`.
- The docs Index README and Changelog links stay in the MkDocs site. They no longer bounce to GitHub.

## [0.6.0] - 2026-08-29

### Added
- **Progress loop**: while the Slack process is running, Benedict surveys each onboarded repo on a timer and takes at most one next action — a Slack question, a GitHub issue, or an implement-ready note. `@benedict progress` / `progress all` / `progress now` run the same path. Decision: [docs/adr/0002-progress-loop.md](docs/adr/0002-progress-loop.md). Spec: [docs/PROGRESS.md](docs/PROGRESS.md). Disable with `BENEDICT_PROGRESS=0`.

## [0.5.10] - 2026-08-29

### Changed
- Default data directory is `~/.benedict` instead of the git checkout. `state.json`, `workspaces/`, `.chroma_db/`, and `runs.jsonl` live there. `.env` is still loaded from the repo. Set `BENEDICT_DATA_DIR` to keep using an existing in-repo data dir, or move those files into `~/.benedict`.

## [0.5.9] - 2026-08-29

### Added
- Documentation index at [docs/README.md](docs/README.md). Groups setup, how-it-works, design, ADRs, and historical classifier docs.
- Docs UI, sidebar, and process: MkDocs Material (`make docs`), `mkdocs.yml` nav, and [docs/PROCESS.md](docs/PROCESS.md).

## [0.5.8] - 2026-08-29

### Added
- Request-path design: routing, retrieve-then-stuff prompts, metadata shortcut vs GitHub tool loop, and Slack vs MCP. [docs/REQUEST_PATH.md](docs/REQUEST_PATH.md).

## [0.5.7] - 2026-08-23

### Changed
- Operator UI pipeline stages are bordered cards. Child tool calls nest in the same card as the parent `llm` step so a long tool loop is scannable.

## [0.5.6] - 2026-08-23

### Added
- Operator UI **Why this answer** now shows the final prompt sent to the model (`system` + `messages`) from the last `llm` stage. Slack conversation, architect, MCP `ask_benedict`, and the tool loop all record it. Payloads over 32 KiB keep a truncated preview instead of dropping the prompt.

## [0.5.5] - 2026-08-23

### Fixed
- Operator UI inspector keeps the pipeline scrollable when a long reply would otherwise fill the pane. Reply has a capped height and its own scroll.
- Opening a pipeline stage no longer jumps back to the top on the 2s poll. The inspector is not rebuilt when the run is unchanged, and payload scroll is restored when it is.

## [0.5.4] - 2026-08-23

### Fixed
- Operator UI now reloads `runs.jsonl` when the MCP process appends a run. Slack and MCP are separate processes; the Slack-side recorder previously only listed runs it had written itself, so `ask_benedict` never appeared in the debugger. Spec and ADR note the reload.

## [0.5.3] - 2026-08-23

### Added
- **Operator UI**: local debug console at `http://127.0.0.1:8765` (on by default). Slack and MCP writes go to `runs.jsonl`. Set `BENEDICT_OPERATOR_UI=0` to disable. Decision: [docs/adr/0001-local-operator-ui.md](docs/adr/0001-local-operator-ui.md). Spec: [docs/OPERATOR_UI_DESIGN.md](docs/OPERATOR_UI_DESIGN.md).

## [0.5.2] - 2026-08-18

### Fixed
- Slack error Block Kit now parses `⚠️ Type` followed by a single newline and bullet details. The previous regex required a blank line, so messages like `⚠️ Some operations failed:\n- Metadata file not found` were wrapped in a second generic Error header.

## [0.5.1] - 2026-08-18

### Fixed
- Asking Benedict to create a GitHub issue (or any non-metadata request) no longer dies in the metadata classifier with `Metadata file not found`. The metadata-tool shortcut only runs for explicit metadata-file wording, registers tools only when `.metadata.benedict` exists, and falls through to the conversation/`run_github` path on failure.

### Changed
- Gitignore now excludes generated coverage/cache files, watcher state, `.metadata.benedict` sidecars, nested `.worktrees/`, and local Cursor config.

## [0.5.0] - 2026-08-18

### Added
- **MCP server**: Cursor, Claude Code, and other MCP clients can query onboarded Benedict projects over stdio. Tools: `list_projects`, `get_repository_summary`, `search_code`, `get_recent_actions`, `ask_benedict`. Entry point: `benedict-mcp` / `python -m benedict.mcp`. See [docs/MCP.md](docs/MCP.md).

## [0.4.0] - 2026-08-18

### Removed
- **Method subsystem**: Removed `.benedict.method.yaml` reading, writing, Slack create-method command, classifier method tools, prompt rhetoric, and onboard auto-create. The YAML file was not consumed as methodology (rules were never enforced), and the surrounding machinery duplicated create/read/update paths. Metadata tools and repo Q&A are unchanged.

## [0.3.20] - 2026-08-17

### Changed
- **README**: Rewrote the project README to match the current system. It now describes workspaces, method and metadata files, architect channel, semantic indexing, GitHub CLI, configuration, and the real command surface. Removed stale v0 stub checklists, broken root doc links, and the claim that GitHub API integration was the next unstarted milestone without mentioning what already shipped.

### Fixed
- Package `__version__` in `src/benedict/__init__.py` now matches `pyproject.toml`.

## [0.3.19] - 2026-08-17

### Added
- **Design analysis**: Added `plans/PROMPT_FIRST_VS_TOOLS.md` and `plans/PROMPT_FIRST_VS_TOOLS.html` describing how Benedict uses LLM tools today and whether a prompt-first approach would be a better default.

## [0.3.18] - 2026-08-17

### Added
- **GitHub CLI tool (`run_github`)**: Benedict can run `gh` in the onboarded workspace repository during conversations. The model supplies argv; code locks the binary to `gh`, cwd to the repo, timeout, and output size. Results are fed back through a short tool loop so the model can interpret them instead of dumping raw CLI output to Slack. Mutating GitHub (create/merge/close/comment) is left to the prompt (ask first). Requires `gh` installed and authenticated on the host.

## [0.3.17] - 2026-04-28

### Removed
- **`FileWatcherDetector`**: Removed unused mtime-based change detector. It was wired into the `create_repo_change_detector` factory under `detector_type="file_watcher"` but never instantiated at runtime — the `"auto"` branch always returned `GitChangeDetector`. Deleted `src/benedict/repo_change_detector/file_watcher_detector.py`, removed exports from `repo_change_detector/__init__.py`, simplified the factory to only support `"git"`, and updated `main.py` to pass `detector_type="git"` explicitly.

### Changed
- Updated `docs/FILE_AND_GIT_WATCHING.md` and `plans/ARCHITECTURE.md` to reflect that `GitChangeDetector` is now the only `RepoChangeDetector` implementation.

## [0.3.16] - 2026-03-13

### Added
- **Documentation**: Added `docs/FILE_AND_GIT_WATCHING.md` describing how file watching, git watching, and change detection work in Benedict.

## [0.3.15] - 2026-02-09

### Changed
- **Disabled documentation file detection**: The automatic detection and notification of new .md files has been disabled as it was making Slack channels too noisy. Commit detection and notifications remain active.

## [0.3.14] - 2026-02-09

### Fixed
- **Critical Bug Fixes in Slack Formatter:**
  - Fixed placeholder collision vulnerability (Bug #1): Replaced simple numeric placeholders with UUID-based placeholders to prevent collisions with actual code content
  - Fixed infinite loop in `split_message()` (Bug #5): Added progress check and maximum iteration limit to prevent hangs
  - Fixed unsafe string replacement (Bug #3): Replaced `str.replace()` with position-based removal to avoid substring collisions
  - Fixed unclosed code blocks in truncation (Bug #6): Added code block balance verification before truncating
  - Fixed heading detection in code blocks (Bug #4): Headings inside code blocks are now correctly excluded from section splitting
  - Fixed language identifier regex (Bug #2): Now supports language identifiers with hyphens, dots, plus signs, and hash (e.g., `python-3`, `c++`, `c#`, `tsx.js`)
  - Fixed Mermaid/code block overlap (Bug #7): Mermaid blocks are now excluded from code block extraction using negative lookahead
  - Fixed field truncation issue (Bug #8): Field chunks are now used directly instead of being truncated again
- **Edge Case Improvements:**
  - Added handling for very long single-line code blocks: splits at whitespace/punctuation boundaries
  - Added URL length validation for Mermaid rendering: prevents extremely long URLs (>2000 chars)
- **Code Quality:**
  - Extracted magic numbers to named constants: `PARAGRAPH_SEARCH_WINDOW`, `NEWLINE_SEARCH_WINDOW`, `TRUNCATION_THRESHOLD_RATIO`, `CODE_BLOCK_BUFFER`, `MAX_ITERATIONS_SPLIT`
  - Improved error handling and logging throughout the formatter

## [0.3.13] - 2026-02-08

### Added
- Git file watcher that monitors all onboarded repositories for new commits and new .md files
- Background service that periodically checks repositories and sends notifications to Slack channels
- Watcher state persistence to track last checked commit time per repository
- Configurable check interval via `BENEDICT_WATCHER_INTERVAL` environment variable (default: 300 seconds)
- Automatic detection of new commits with file change details (added, modified, deleted files)
- Automatic detection of new documentation files (.md files) in repositories
- Graceful shutdown handling for the watcher service
- Git file watcher now saves git patches to files in `.benedict/patches/` directory
- LLM-based change analysis that understands what changed in commits
- Automatic roadmap linking: changes are analyzed and linked to roadmap items
- Semantic search integration to find related roadmap items based on changed files
- Comprehensive change summaries that connect code changes to project roadmap
- Roadmap file detection (ROADMAP.md, roadmap.md, docs/ROADMAP.md)
- Change analysis includes: summary of changes, roadmap relationships, and affected roadmap items

## [0.3.12] - 2026-02-08

### Added
- Automatic creation of default `.benedict.method.yaml` file when onboarding empty directories
- Method file is automatically created during onboarding if directory is empty or method file doesn't exist
- Helper method `_create_default_method_data()` to generate default method file structure
- Helper method `_is_directory_empty()` to detect empty directories (ignoring system files like .git, .venv, etc.)

### Fixed
- Fixed method file creation failing when repository directory doesn't exist
- `MethodWriter.write_method()` now creates parent directories before writing the method file
- Prevents `FileNotFoundError` when creating method files in new repository paths
- Improved error handling: method file write failures now raise exceptions instead of silently returning
- Added file creation verification to ensure method files are actually written
- Enhanced logging: success messages now use INFO level instead of DEBUG for better visibility

## [0.3.11] - 2026-02-08

### Added
- Comprehensive features overview document (`docs/FEATURES_OVERVIEW.md`) documenting all implemented features
- Complete feature inventory covering commands, LLM integration, semantic search, method files, metadata, and more
- Usage examples and integration points documentation

## [0.3.10] - 2026-02-08

### Added
- Code reading guide (`docs/CODE_READING_GUIDE.md`) explaining how to read and understand the codebase
- Comprehensive documentation covering architecture patterns, reading strategies, and debugging tips
- Guiding questions for engineers to navigate the codebase effectively

## [0.3.9] - 2026-02-08

### Fixed
- Prevented metadata reader from scanning `.metadata.benedict` files in virtual environments and excluded directories
- Added path filtering to exclude common build/cache directories (`.venv`, `venv`, `node_modules`, `site-packages`, etc.) from metadata scanning
- Reduced unnecessary debug log noise from reading metadata files in third-party package directories

## [0.3.8] - 2026-02-08

### Added
- Method file support for reading and updating `.benedict.method.yaml` files
- `MethodReader` class to read and parse method files with project phases, concerns, and rules
- `MethodWriter` class to write and update method files
- Environment variable `BENEDICT_METHOD_FILE` to specify custom method file path
- Automatic detection of missing method files with proactive guidance
- Method file creation handler that generates complete method files with all concern definitions and sequence phases
- Integration of method file information into context building for better project awareness
- System prompt prioritization: method file creation is marked as FIRST PRIORITY when missing
- Method file update detection and confirmation flow for phase, iteration, step, and concern updates
- Support for parsing method file update requests (e.g., "set phase to sprint", "set documentation to complete")

### Changed
- Method file information is now included in repository context when available
- System prompt now instructs LLM to prioritize method file creation when missing (marked as CRITICAL)

## [0.3.7] - 2026-02-08

### Added
- Mermaid diagram rendering support for Slack messages
- Automatic detection and rendering of Mermaid code blocks to images using mermaid.ink API
- Mermaid diagrams are rendered as image blocks in Block Kit messages
- Fallback to code block display if image rendering fails
- Mermaid source code is included below rendered images for editing/copying

## [0.3.6] - 2026-02-08

### Fixed
- Fixed code block truncation and splitting issues in Slack message formatting
- Code blocks are now never split across message chunks or Slack blocks
- Truncation now respects code block boundaries - never truncates inside a code block
- Added code-aware splitting logic that extends to end of code blocks when necessary
- Fixed issue where code blocks would be cut in half, leaving unclosed code fences

## [0.3.5] - 2026-02-08

### Fixed
- Fixed bug where bot wouldn't respond immediately to channel messages without @mentions
- Fixed duplicate responses when @mentioning the bot (message handler now skips messages with bot mentions)
- Fixed threading issue where responses to channel messages weren't properly linked (now uses `conversation_ts` instead of `thread_ts`)

## [0.3.4] - 2026-02-08

### Changed
- Repository source paths are now configurable via `BENEDICT_REPO_SOURCE_DIRS` environment variable
- Format: comma-separated paths, e.g., `BENEDICT_REPO_SOURCE_DIRS=/Users/name/Projects,/opt/repos`
- Defaults to `~/Projects` if not configured
- Error messages now show all tried paths including configured source directories

## [0.3.3] - 2026-02-08

### Added
- Smart message detection - Benedict now responds to messages in channels that appear to be directed at it
- Detects questions, help requests, and messages mentioning "benedict", "agent", or bot-related terms
- Responds to channel messages without requiring @mention when message seems directed at the bot

## [0.3.2] - 2026-02-08

### Fixed
- Fixed ChromaDB metadata error when indexing Slack messages - now filters out `None` values from metadata before indexing
- Messages with missing `thread_ts` or `user` fields now index correctly

## [0.3.1] - 2026-02-08

### Added
- Thread-aware conversation detection - Benedict now responds to messages in threads where it has already participated, without requiring @mention
- Automatic detection of thread context to understand when users are talking to Benedict

## [0.3.0] - 2026-02-08

### Changed
- Removed manual `@agent index slack history` command - indexing now happens automatically in the background
- Slack conversation history indexing is now fully automatic:
  - Indexes from channel start when channel is onboarded
  - Automatically indexes new messages as they arrive via message events
  - Creates embeddings for all messages in ChromaDB for semantic search
- Messages are now indexed with embeddings for semantic search capabilities

### Added
- Automatic background indexing of new Slack messages via message event handler
- Proper embedding generation for Slack messages in semantic indexer
- `index_new_slack_messages()` method for automatic incremental updates

## [0.2.9] - 2026-02-08

### Added
- Automatic Slack conversation history indexing when a channel is onboarded
- Channel history is now indexed from the beginning when `@agent onboard` is run
- Users are notified that conversation history indexing is in progress during onboarding

## [0.2.8] - 2026-02-08

### Changed
- Conversation summarization is now a normal query, not a special command
- When users ask about conversations (e.g., "summarise today's conversations"), the LLM automatically receives conversation history in context
- Removed special command routing for conversation summarization - it's handled naturally by the LLM

## [0.2.7] - 2026-02-08

### Fixed
- Improved command detection for summarize conversations command to handle British spelling ("summarise") and typos
- Command now properly recognizes variations like "summarise todays conversastions"

## [0.2.6] - 2026-02-08

### Added
- Command to gather and summarize today's conversations via `@agent summarize today` or `@agent gather today's conversations`
- Automatic LLM-powered summarization for conversations with 3+ threads or 20+ messages
- Conversation filtering by date (today) and channel
- Support for extracting key topics, decisions, and action items from conversation history

## [0.2.5] - 2026-02-08

### Added
- Slack conversation history indexing via `@agent index slack history` command
- Full implementation of `SlackConversationHistoryIndexer` with Slack API integration
- Support for fetching channel history using `conversations.history` API with pagination
- Support for fetching thread replies using `conversations.replies` API
- Incremental updates for Slack history indexing (only fetches new messages since last index)
- Message filtering to exclude bot messages and system messages
- Conversation history stored as JSON files in workspace `conversation_history/` directory
- Integration with workspace manager and action logger for tracking indexing operations

### Changed
- Updated `create_conversation_history_indexer()` factory to accept `slack_client` parameter
- Enhanced `RepoAgent` to support conversation history indexing via new `conversation_history_indexer` parameter

## [0.2.4] - 2026-02-08

### Changed
- Renamed metadata files from `METADATA` to `.metadata.benedict` for better specificity and to avoid conflicts
- Updated system prompt to include comprehensive documentation on `.metadata.benedict` files
- Enhanced benedict's ability to discover and read `.metadata.benedict` files through the repo_reader interface

### Breaking Changes
- Existing `METADATA` files will no longer be recognized. Regenerate metadata files to create new `.metadata.benedict` files.

## [0.2.3] - 2026-02-07

### Added
- Configurable chunk size via `BENEDICT_CHUNK_SIZE` environment variable (default: 2000 characters)
- Diagnostic logging for chunking statistics showing:
  - Total files indexed
  - Total chunks created
  - Average chunks per file
  - Average file size
  - Top 10 files by chunk count
- Path-based filtering to exclude common build/cache directories from indexing:
  - Virtual environments (`.venv`, `venv`, `env`, etc.)
  - Dependencies (`node_modules`)
  - Build artifacts (`build`, `dist`, `target`)
  - Cache directories (`__pycache__`, `.pytest_cache`, `.mypy_cache`, etc.)
  - Version control directories (`.git`, `.hg`, `.svn`)
  - IDE directories (`.idea`, `.vscode`, `.vs`)
  - And more (see `_filter_code_files` for complete list)

### Changed
- Increased default chunk size from 1000 to 2000 characters for better semantic context
- Improved file filtering to exclude virtual environment and build artifact directories

### Fixed
- Prevented indexing of `.venv` and other virtual environment directories
- Reduced unnecessary chunk generation from third-party dependencies
- Fixed `AttributeError` when accessing `SlackFormatter.MAX_MESSAGE_LENGTH` by adding it as a class attribute

## [0.2.2]

### Added
- Semantic code search using ChromaDB and sentence-transformers
- Workspace management for multi-channel repository access
- Metadata generation and overlays for enhanced context
- Repository change detection (Git-based and file watcher)
- Incremental index updates for changed files only
- Conversation history tracking per thread
- Protocol-based architecture for testability
- Mock implementations for all protocols

### Changed
- Refactored to SOLID principles with dependency injection
- Improved context building with semantic search integration
- Enhanced file filtering for better code indexing

## [0.2.0] - LLM Integration

### Added
- LLM protocol definition with Claude 3.5 Sonnet implementation
- Repository reader protocol with local filesystem implementation
- Context builder that intelligently selects relevant files
- Composition root pattern for dependency management
- Conversation repository pattern for persistence abstraction
- Thread-based conversations with full history tracking

### Changed
- Refactored from monolithic to protocol-based architecture
- Improved error handling and graceful degradation

## [0.1.0] - Initial Release

### Added
- Slack bot with Socket Mode support
- Channel → Repository mapping via `onboard` command
- Status command to show channel mappings
- State persistence across restarts (JSON-based)
- Thread-based conversation handling
- Basic command parsing and routing

## [0.0.1] - Proof of Concept

### Added
- Initial Slack bot infrastructure
- Basic mention handling
- State management

---

## Types of Changes

- **Added** for new features
- **Changed** for changes in existing functionality
- **Deprecated** for soon-to-be removed features
- **Removed** for now removed features
- **Fixed** for any bug fixes
- **Security** for vulnerability fixes

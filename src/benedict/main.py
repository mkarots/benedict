#!/usr/bin/env python3
"""
Slack Repo Agent - Main Entry Point

Composition root where all dependencies are wired together.
"""

import os
from datetime import datetime, timezone
from pathlib import Path
from slack_bolt.adapter.socket_mode import SocketModeHandler

from benedict.agent import RepoAgent
from benedict.paths import get_data_dir, load_runtime_env
from benedict.protocols import (
    create_llm,
    create_repo_reader,
    create_semantic_indexer,
    create_conversation_repository,
    create_conversation_history_indexer,
)
from benedict.slack.app import create_slack_app
from benedict.workspace import WorkspaceManager
from benedict.lib.logging import setup_logging, get_logger
from slack_sdk import WebClient

# Configure logging first
setup_logging()
logger = get_logger(__name__)


# Always load .env for missing keys (process env wins). Slack tokens already in
# the environment must not skip the file, or NOTION_API_KEY in .env is ignored.
_env_path = load_runtime_env()
if _env_path.exists():
    logger.info(f"Loading .env from: {_env_path}")
else:
    logger.warning(f".env file not found at: {_env_path}")
if os.environ.get("NOTION_API_KEY"):
    logger.info("NOTION_API_KEY is set. Process env overrides .env.")
else:
    logger.info("NOTION_API_KEY is not set")


def main() -> None:
    """Root composition - wire everything together."""

    # Validate environment variables
    bot_token = os.environ.get("SLACK_BOT_TOKEN")
    app_token = os.environ.get("SLACK_APP_TOKEN")

    if not bot_token:
        logger.error("SLACK_BOT_TOKEN not found in environment variables")
        raise ValueError("Missing SLACK_BOT_TOKEN")

    if not app_token:
        logger.error("SLACK_APP_TOKEN not found in environment variables")
        raise ValueError("Missing SLACK_APP_TOKEN")

    logger.info("=" * 60)
    logger.info("Starting Slack Repo Agent...")
    logger.info(f"Bot Token: {bot_token[:20]}...")
    logger.info(f"App Token: {app_token[:20]}...")
    logger.info("=" * 60)

    # Create LLM (optional - can be None for stub mode)
    llm = None
    try:
        llm = create_llm(provider="claude")
        logger.info("✅ LLM initialized (Claude)")
    except Exception as e:
        logger.warning(f"⚠️ LLM not available: {e}")
        logger.info("Running in stub mode (no LLM responses)")

    # Create repo reader (optional - can be None for stub mode)
    repo_reader = None
    try:
        repo_reader = create_repo_reader(source="local")
        logger.info("✅ Repo reader initialized (local filesystem)")
    except Exception as e:
        logger.warning(f"⚠️ Repo reader not available: {e}")
        logger.info("Running without repository access")

    # Get data directory (configurable via BENEDICT_DATA_DIR env var)
    data_dir = get_data_dir()
    logger.info(f"Using data directory: {data_dir}")

    # Create workspace manager
    workspaces_dir = os.environ.get("BENEDICT_WORKSPACES_DIR", str(data_dir / "workspaces"))
    copy_mode = os.environ.get("BENEDICT_WORKSPACE_COPY_MODE", "symlink")
    workspace_manager = WorkspaceManager(workspaces_dir=workspaces_dir, copy_mode=copy_mode)
    logger.info(
        f"✅ Workspace manager initialized (workspaces_dir={workspaces_dir}, copy_mode={copy_mode})"
    )

    # Create semantic indexer (optional - falls back to keyword matching if None)
    semantic_indexer = None
    try:
        # Use configurable path for ChromaDB (defaults to data_dir/.chroma_db)
        chroma_db_path = os.environ.get("BENEDICT_CHROMA_DB_DIR", str(data_dir / ".chroma_db"))
        # Create metadata generator for semantic indexer
        from benedict.metadata import MetadataGenerator
        from benedict.protocols.repo_change_detector import create_repo_change_detector

        metadata_generator = MetadataGenerator()
        change_detector = create_repo_change_detector(detector_type="git")
        semantic_indexer = create_semantic_indexer(
            provider="chromadb",
            persist_directory=chroma_db_path,
            metadata_generator=metadata_generator,
            change_detector=change_detector,
        )
        logger.info(f"✅ Semantic indexer initialized (ChromaDB at {chroma_db_path})")
    except Exception as e:
        logger.warning(f"⚠️ Semantic indexer not available: {e}")
        logger.info("Falling back to keyword-based file matching")

    # Create conversation repository
    # Use configurable path for state file (defaults to data_dir/state.json)
    state_file = os.environ.get("BENEDICT_STATE_FILE", str(data_dir / "state.json"))
    conversation_repository = create_conversation_repository(provider="json", state_file=state_file)
    logger.info(f"✅ Conversation repository initialized (JSON at {state_file})")

    # Create Slack WebClient for conversation history indexing
    slack_client = WebClient(token=bot_token)

    # Create conversation history indexer (optional)
    conversation_history_indexer = None
    try:
        conversation_history_indexer = create_conversation_history_indexer(
            platform="slack", slack_client=slack_client
        )
        logger.info("✅ Conversation history indexer initialized (Slack)")
    except Exception as e:
        logger.warning(f"⚠️ Conversation history indexer not available: {e}")
        logger.info("Slack history indexing will not be available")

    from benedict.operator_ui.server import StatusMonitor, create_recorder, start_operator_ui
    from benedict.progress import (
        ActionDecider,
        ActionExecutor,
        ProgressScheduler,
        ProgressService,
        ProgressStore,
        SlackWebClientPoster,
        SnapshotCollector,
        progress_enabled,
    )

    recorder = create_recorder(data_dir)
    chroma_db_path = os.environ.get("BENEDICT_CHROMA_DB_DIR", str(data_dir / ".chroma_db"))

    # Create agent with dependencies
    agent = RepoAgent(
        state_file=state_file,
        llm=llm,
        repo_reader=repo_reader,
        semantic_indexer=semantic_indexer,
        conversation_repository=conversation_repository,
        workspace_manager=workspace_manager,
        conversation_history_indexer=conversation_history_indexer,
        run_recorder=recorder,
    )

    progress_scheduler = None
    if llm is not None and progress_enabled():
        progress_store = ProgressStore(agent.load_state, agent.save_state)
        agent.progress_service = ProgressService(
            load_state=agent.load_state,
            workspace_path_for=workspace_manager.get_workspace_path,
            collector=SnapshotCollector(store=progress_store),
            decider=ActionDecider(llm),
            executor=ActionExecutor(SlackWebClientPoster(slack_client)),
            store=progress_store,
            run_recorder=recorder,
        )
        progress_scheduler = ProgressScheduler(agent.progress_service)
        progress_scheduler.start()
        logger.info("✅ Progress loop enabled")
    elif not progress_enabled():
        logger.info("Progress loop disabled (BENEDICT_PROGRESS=0)")
    else:
        logger.info("Progress loop skipped (no LLM)")

    start_operator_ui(
        StatusMonitor(
            data_dir=data_dir,
            recorder=recorder,
            state_file=Path(state_file),
            workspaces_dir=Path(workspaces_dir),
            chroma_path=Path(chroma_db_path),
            started_at=datetime.now(timezone.utc),
            model=os.environ.get("ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022"),
            copy_mode=copy_mode,
        )
    )

    # Initialize state file if it doesn't exist
    state_path = Path(state_file)
    if not state_path.exists():
        agent.save_state({"channels": {}})
        logger.info(f"Created new state file: {state_path}")

    # Create and configure Slack app
    slack_app = create_slack_app(agent)

    # Start the app
    logger.info("Initializing Socket Mode handler...")
    handler = SocketModeHandler(slack_app, app_token)
    logger.info("✅ Bot is running! Press Ctrl+C to stop.")
    logger.info("Waiting for events...")

    try:
        handler.start()
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        if progress_scheduler is not None:
            progress_scheduler.stop()
        logger.info("Shutdown complete")


if __name__ == "__main__":
    main()

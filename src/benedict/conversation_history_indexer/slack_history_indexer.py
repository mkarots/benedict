"""Slack Conversation History Indexer

Implements ConversationHistoryIndexer protocol for Slack.
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List, Dict, Any

from benedict.lib.dateutil import normalize_to_utc
from benedict.conversation_history_indexer.protocol import (
    ConversationReader,
)
from benedict.conversation_history_indexer.store import ConversationHistoryStore

logger = logging.getLogger(__name__)


class SlackConversationReader:
    """Reader for Slack conversations."""

    def __init__(self, workspace_path: Path):
        """Initialize Slack conversation reader.

        Args:
            workspace_path: Path to workspace directory
        """
        self.workspace_path = Path(workspace_path)
        self.conversation_dir = self.workspace_path / "conversation_history"

    def read_conversations(
        self,
        context_id: str,
        since: Optional[datetime] = None,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Read Slack conversations from workspace.

        Args:
            context_id: Context identifier (not used, conversations are in workspace)
            since: Optional datetime to get conversations since
            limit: Optional limit on number of conversations

        Returns:
            List of conversation dictionaries
        """
        conversations: List[Dict[str, Any]] = []

        if not self.conversation_dir.exists():
            return conversations

        # Read all JSON files in conversation_history directory
        for json_file in self.conversation_dir.glob("*.json"):
            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    data = json.load(f)

                # Handle different JSON structures
                if isinstance(data, list):
                    conversations.extend(data)
                elif isinstance(data, dict) and "messages" in data:
                    conversations.extend(data["messages"])
                elif isinstance(data, dict):
                    conversations.append(data)
            except Exception as e:
                logger.warning(f"Error reading conversation file {json_file}: {e}")
                continue

        # Filter by since date if provided
        if since:
            filtered = []
            for conv in conversations:
                ts = conv.get("ts") or conv.get("timestamp")
                if ts:
                    try:
                        # Parse timestamp (Slack format or ISO)
                        if isinstance(ts, str):
                            if "." in ts:
                                conv_dt = datetime.fromtimestamp(float(ts))
                            else:
                                conv_dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                        else:
                            conv_dt = datetime.fromtimestamp(ts)

                        if conv_dt >= since:
                            filtered.append(conv)
                    except Exception:
                        filtered.append(conv)  # Include if we can't parse
                else:
                    filtered.append(conv)  # Include if no timestamp
            conversations = filtered

        # Apply limit
        if limit:
            conversations = conversations[:limit]

        return conversations


class SlackConversationHistoryIndexer:
    """Slack ingest adapter for the agent's conversation-history store."""

    def __init__(
        self,
        slack_client: Any = None,
        persist_directory: Optional[str] = None,
        store: Optional[ConversationHistoryStore] = None,
        embedding_model: Any = None,
        client: Any = None,
    ):
        """Initialize Slack conversation history indexer.

        Args:
            slack_client: Slack WebClient for fetching channel history
            persist_directory: Fallback Chroma path when ``client`` is omitted
            store: Optional store (tests inject a fake)
            embedding_model: Optional embedder (tests inject a fake; production lazy-loads MiniLM)
            client: Shared Chroma client (same database as code search)
        """
        self.slack_client = slack_client
        self.store = store or ConversationHistoryStore(
            persist_directory=persist_directory,
            embedding_model=embedding_model,
            client=client,
        )
        logger.info("Initialized SlackConversationHistoryIndexer")

    def search(self, context_id: str, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Search this context's conversation embeddings."""
        if not context_id or not str(query).strip():
            return []
        try:
            return self.store.search(context_id, str(query).strip(), top_k=top_k)
        except Exception as exc:
            logger.warning("Conversation history search failed for %s: %s", context_id, exc)
            return []

    def index_conversations(
        self,
        context_id: str,
        workspace_path: Path,
        since: Optional[datetime] = None,
    ) -> None:
        """Index Slack conversations into workspace.

        Args:
            context_id: Context identifier (Slack channel_id)
            workspace_path: Path to workspace directory
            since: Optional datetime to index conversations since
        """
        if not self.slack_client:
            logger.warning("Slack client not available, cannot index conversations")
            return

        workspace_path = Path(workspace_path)
        conversation_dir = workspace_path / "conversation_history"
        conversation_dir.mkdir(parents=True, exist_ok=True)

        logger.info(
            f"Indexing Slack conversations for channel {context_id} into {conversation_dir}"
        )

        # Convert datetime to Slack timestamp format (Unix timestamp as string)
        oldest_ts = None
        if since:
            # Normalize to UTC and convert to timestamp
            since_utc = normalize_to_utc(since)
            oldest_ts = str(since_utc.timestamp())

        # Fetch all messages from the channel
        all_messages = self._fetch_channel_history(context_id, oldest=oldest_ts)

        if not all_messages:
            logger.info(f"No messages found for channel {context_id}")
            return

        logger.info(f"Fetched {len(all_messages)} messages from channel {context_id}")

        # Fetch thread replies for threaded messages
        threaded_messages = {}
        for msg in all_messages:
            if msg.get("thread_ts") and msg.get("thread_ts") != msg.get("ts"):
                # This is a thread reply, fetch full thread
                thread_ts = msg.get("thread_ts")
                if thread_ts and thread_ts not in threaded_messages:
                    thread_replies = self._fetch_thread_replies(context_id, thread_ts)
                    threaded_messages[thread_ts] = thread_replies

        # Store messages in JSON file
        output_file = conversation_dir / f"{context_id}.json"
        conversation_data = {
            "channel_id": context_id,
            "indexed_at": datetime.now(timezone.utc).isoformat(),
            "message_count": len(all_messages),
            "messages": all_messages,
            "threads": threaded_messages,
        }

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(conversation_data, f, indent=2, ensure_ascii=False)

        logger.info(f"Stored {len(all_messages)} messages to {output_file}")

        keyed_threads = {key: replies for key, replies in threaded_messages.items() if key}
        self._index_into_store(context_id, all_messages, keyed_threads)

    def update_index(
        self,
        context_id: str,
        workspace_path: Path,
        since: Optional[datetime] = None,
    ) -> None:
        """Incrementally update conversation index with new messages.

        Args:
            context_id: Context identifier (Slack channel_id)
            workspace_path: Path to workspace directory
            since: Datetime to index conversations since (required for incremental updates)
        """
        if not self.slack_client:
            logger.warning("Slack client not available, cannot update conversation index")
            return

        if not since:
            logger.warning("update_index requires 'since' parameter for incremental updates")
            return

        workspace_path = Path(workspace_path)
        conversation_dir = workspace_path / "conversation_history"
        conversation_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"Updating conversation index for channel {context_id} since {since}")

        output_file = conversation_dir / f"{context_id}.json"

        # Convert datetime to Slack timestamp (normalize to UTC first)
        since_utc = normalize_to_utc(since)
        oldest_ts = str(since_utc.timestamp())

        # Fetch new messages since 'since'
        new_messages = self._fetch_channel_history(context_id, oldest=oldest_ts)

        if not new_messages:
            logger.info(f"No new messages found for channel {context_id} since {since}")
            self._backfill_store_if_empty(context_id, output_file)
            return

        logger.info(f"Fetched {len(new_messages)} new messages from channel {context_id}")

        # Load existing messages if file exists
        existing_messages = []
        existing_threads = {}

        if output_file.exists():
            try:
                with open(output_file, "r", encoding="utf-8") as f:
                    existing_data = json.load(f)
                    existing_messages = existing_data.get("messages", [])
                    existing_threads = existing_data.get("threads", {})
            except Exception as e:
                logger.warning(f"Error reading existing conversation file: {e}")

        # Merge new messages (avoid duplicates by timestamp)
        existing_ts_set = {msg.get("ts") for msg in existing_messages}
        unique_new_messages = [msg for msg in new_messages if msg.get("ts") not in existing_ts_set]

        if not unique_new_messages:
            logger.info("No new unique messages to add")
            self._backfill_store_if_empty(context_id, output_file)
            return

        # Fetch thread replies for new threaded messages
        for msg in unique_new_messages:
            if msg.get("thread_ts") and msg.get("thread_ts") != msg.get("ts"):
                thread_ts = msg.get("thread_ts")
                if thread_ts and thread_ts not in existing_threads:
                    thread_replies = self._fetch_thread_replies(context_id, thread_ts)
                    existing_threads[thread_ts] = thread_replies

        # Combine existing and new messages
        all_messages = existing_messages + unique_new_messages
        # Sort by timestamp (oldest first)
        all_messages.sort(key=lambda x: float(x.get("ts", "0")))

        # Update stored file
        conversation_data = {
            "channel_id": context_id,
            "indexed_at": datetime.now(timezone.utc).isoformat(),
            "message_count": len(all_messages),
            "messages": all_messages,
            "threads": existing_threads,
        }

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(conversation_data, f, indent=2, ensure_ascii=False)

        logger.info(
            f"Updated conversation file with {len(unique_new_messages)} new messages "
            f"(total: {len(all_messages)} messages)"
        )

        # Empty store after the code/conversation split: embed the full JSON, not only new rows.
        if self.store.document_count(context_id) == 0:
            self._index_into_store(context_id, all_messages, existing_threads)
        else:
            self._index_into_store(context_id, unique_new_messages, existing_threads)

    def get_conversation_reader(self, workspace_path: Path) -> ConversationReader:
        """Get reader for accessing conversations.

        Args:
            workspace_path: Path to workspace directory

        Returns:
            ConversationReader instance
        """
        return SlackConversationReader(workspace_path)

    def _fetch_channel_history(
        self, channel_id: str, oldest: Optional[str] = None, limit: int = 1000
    ) -> List[Dict[str, Any]]:
        """Fetch channel history using Slack API with pagination.

        Args:
            channel_id: Slack channel ID
            oldest: Optional oldest timestamp (Unix timestamp as string)
            limit: Maximum number of messages to fetch

        Returns:
            List of message dictionaries
        """
        messages: List[Dict[str, Any]] = []
        cursor = None

        while len(messages) < limit:
            try:
                params = {
                    "channel": channel_id,
                    "limit": min(200, limit - len(messages)),  # Slack max is 200 per request
                }

                if oldest:
                    params["oldest"] = oldest

                if cursor:
                    params["cursor"] = cursor

                response = self.slack_client.conversations_history(**params)

                if not response.get("ok"):
                    error = response.get("error", "unknown error")
                    logger.error(f"Error fetching channel history: {error}")
                    break

                batch = response.get("messages", [])
                if not batch:
                    break

                # Filter out bot messages and system messages
                filtered = [msg for msg in batch if self._should_index_message(msg)]
                messages.extend(filtered)

                # Check for more pages
                response_metadata = response.get("response_metadata", {})
                cursor = response_metadata.get("next_cursor")
                if not cursor:
                    break

            except Exception as e:
                logger.error(f"Error fetching channel history: {e}", exc_info=True)
                break

        logger.debug(f"Fetched {len(messages)} messages from channel {channel_id}")
        return messages[:limit]

    def _fetch_thread_replies(self, channel_id: str, thread_ts: str) -> List[Dict[str, Any]]:
        """Fetch thread replies using Slack API.

        Args:
            channel_id: Slack channel ID
            thread_ts: Thread timestamp

        Returns:
            List of message dictionaries in the thread
        """
        try:
            response = self.slack_client.conversations_replies(channel=channel_id, ts=thread_ts)

            if not response.get("ok"):
                error = response.get("error", "unknown error")
                logger.error(f"Error fetching thread replies: {error}")
                return []

            messages = response.get("messages", [])
            # Filter out bot messages and system messages
            filtered = [msg for msg in messages if self._should_index_message(msg)]
            return filtered

        except Exception as e:
            logger.error(f"Error fetching thread replies: {e}", exc_info=True)
            return []

    def _should_index_message(self, msg: Dict[str, Any]) -> bool:
        """Check if message should be indexed.

        Filters out:
        - Bot messages (subtype='bot_message')
        - System messages (subtype starts with 'channel_')
        - Deleted messages
        - Messages without text

        Args:
            msg: Message dictionary

        Returns:
            True if message should be indexed
        """
        # Skip bot messages
        if msg.get("subtype") == "bot_message":
            return False

        # Skip system messages
        subtype = msg.get("subtype", "")
        if subtype.startswith("channel_"):
            return False

        # Skip deleted messages
        if subtype == "message_deleted":
            return False

        # Must have text
        if not msg.get("text"):
            return False

        return True

    def _backfill_store_if_empty(self, context_id: str, output_file: Path) -> None:
        """Embed existing JSON when the conversation store is empty (post-split)."""
        if self.store.document_count(context_id) > 0 or not output_file.exists():
            return
        try:
            with open(output_file, "r", encoding="utf-8") as handle:
                data = json.load(handle)
        except Exception as exc:
            logger.warning("Error reading conversation file for backfill: %s", exc)
            return
        messages = data.get("messages") or []
        threads = data.get("threads") or {}
        if messages:
            self._index_into_store(context_id, messages, threads)

    def _index_into_store(
        self,
        context_id: str,
        messages: List[Dict[str, Any]],
        threads: Dict[str, List[Dict[str, Any]]],
    ) -> None:
        """Write messages into the conversation embedding store."""
        if not self.store.available:
            return
        try:
            self.store.add_messages(context_id, messages, threads)
        except Exception as e:
            logger.warning(
                "Error indexing conversation messages for %s: %s",
                context_id,
                e,
                exc_info=True,
            )


class MockConversationHistoryIndexer:
    """Mock implementation for testing."""

    def __init__(self) -> None:
        """Initialize mock conversation history indexer."""
        self._hits: List[Dict[str, Any]] = []
        logger.info("Initialized MockConversationHistoryIndexer")

    def add_hit(
        self,
        content: str,
        score: float = 0.9,
        context_id: str = "C1",
        message_ts: str = "1.0",
        user: str = "U1",
        message_type: str = "message",
    ) -> None:
        """Pre-populate a conversation search hit (test helper)."""
        self._hits.append(
            {
                "file_path": f"conversation:{context_id}:{message_ts}",
                "content": content,
                "score": score,
                "channel_id": context_id,
                "context_id": context_id,
                "message_ts": message_ts,
                "user": user,
                "type": message_type,
                "thread_ts": None,
            }
        )

    def index_conversations(
        self,
        context_id: str,
        workspace_path: Path,
        since: Optional[datetime] = None,
    ) -> None:
        """Mock index conversations."""
        logger.debug(f"Mock indexing conversations for context {context_id}")

    def update_index(
        self,
        context_id: str,
        workspace_path: Path,
        since: Optional[datetime] = None,
    ) -> None:
        """Mock incremental update."""
        self.index_conversations(context_id, workspace_path, since)

    def search(self, context_id: str, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Return pre-populated hits, if any."""
        if not context_id or not str(query).strip():
            return []
        return self._hits[:top_k]

    def get_conversation_reader(self, workspace_path: Path) -> ConversationReader:
        """Get mock conversation reader."""

        class MockReader:
            def read_conversations(
                self,
                context_id: str,
                since: Optional[datetime] = None,
                limit: Optional[int] = None,
            ) -> List[Dict[str, Any]]:
                return []

        return MockReader()

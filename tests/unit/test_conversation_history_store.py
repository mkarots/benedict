"""Conversation history store is separate from the code indexer."""

from benedict.conversation_history_indexer import (
    MockConversationHistoryIndexer,
    create_conversation_history_indexer,
)
from benedict.conversation_history_indexer.store import (
    ConversationHistoryStore,
    conversation_collection_name,
    format_conversation_hits,
)


def test_conversation_collection_name_is_stable():
    first = conversation_collection_name("C123")
    second = conversation_collection_name("C123")
    other = conversation_collection_name("C999")

    assert first == second
    assert first.startswith("conversation_")
    assert first != other
    assert len(first) == len("conversation_") + 16


def test_format_conversation_hits():
    results = {
        "documents": [["we decided X"]],
        "metadatas": [
            [
                {
                    "context_id": "C1",
                    "message_ts": "9.8",
                    "user": "U2",
                    "type": "thread_reply",
                }
            ]
        ],
        "distances": [[0.0]],
    }

    hits = format_conversation_hits(results, "C1")

    assert len(hits) == 1
    assert hits[0]["content"] == "we decided X"
    assert hits[0]["score"] == 1.0
    assert hits[0]["file_path"] == "conversation:C1:9.8"
    assert hits[0]["user"] == "U2"
    assert hits[0]["type"] == "thread_reply"


def test_format_conversation_hits_empty():
    assert (
        format_conversation_hits({"documents": [[]], "metadatas": [[]], "distances": [[]]}, "C1")
        == []
    )
    assert format_conversation_hits({}, "C1") == []


def test_mock_conversation_indexer_search():
    indexer = MockConversationHistoryIndexer()
    indexer.add_hit(content="decision lives here", context_id="Cabc")

    hits = indexer.search("Cabc", "what did we decide?")

    assert hits[0]["content"] == "decision lives here"
    assert indexer.search("", "hello") == []
    assert indexer.search("C1", "   ") == []
    assert MockConversationHistoryIndexer().search("C1", "hello") == []


class _FakeCollection:
    def __init__(self, count: int = 1):
        self._count = count
        self.queries = []
        self.added = []

    def count(self) -> int:
        return self._count

    def query(self, query_embeddings, n_results):
        self.queries.append({"query_embeddings": query_embeddings, "n_results": n_results})
        return {
            "documents": [["use the existing token header"]],
            "metadatas": [[{"context_id": "Cchan", "message_ts": "2.2", "user": "Udev"}]],
            "distances": [[1.0]],
        }

    def add(self, **kwargs):
        self.added.append(kwargs)
        self._count += len(kwargs.get("ids") or [])


class _MissingCollectionClient:
    def get_collection(self, name: str):
        raise ValueError(f"missing {name}")


class _FakeClient:
    def __init__(self, collection: _FakeCollection):
        self.collection = collection
        self.requested = []
        self.created = []

    def get_collection(self, name: str):
        self.requested.append(name)
        return self.collection

    def create_collection(self, name: str, metadata=None):
        self.created.append({"name": name, "metadata": metadata})
        return self.collection


class _FakeEncoder:
    def encode(self, texts, show_progress_bar=False):
        del show_progress_bar
        return [[0.1, 0.2, 0.3] for _ in texts]


def test_store_search_queries_own_chroma():
    collection = _FakeCollection()
    client = _FakeClient(collection)
    store = ConversationHistoryStore(client=client, embedding_model=_FakeEncoder())

    hits = store.search("Cchan", "token header", top_k=3)

    assert client.requested == [conversation_collection_name("Cchan")]
    assert collection.queries[0]["n_results"] == 1
    assert hits[0]["content"] == "use the existing token header"
    assert hits[0]["score"] == 0.5


def test_store_search_missing_collection():
    store = ConversationHistoryStore(
        client=_MissingCollectionClient(), embedding_model=_FakeEncoder()
    )
    assert store.search("Cgone", "anything") == []


def test_store_search_does_not_create_collection():
    collection = _FakeCollection(count=2)
    client = _FakeClient(collection)
    store = ConversationHistoryStore(client=client, embedding_model=_FakeEncoder())

    hits = store.search("Cchan", "token header", top_k=5)

    assert client.requested == [conversation_collection_name("Cchan")]
    assert client.created == []
    assert collection.queries[0]["n_results"] == 2
    assert hits[0]["file_path"] == "conversation:Cchan:2.2"


def test_store_search_empty_collection():
    empty = _FakeCollection(count=0)
    store = ConversationHistoryStore(client=_FakeClient(empty), embedding_model=_FakeEncoder())
    assert store.search("Cempty", "anything") == []
    assert empty.queries == []


def test_store_add_messages_uses_conversation_collection():
    collection = _FakeCollection(count=0)
    client = _FakeClient(collection)
    store = ConversationHistoryStore(client=client, embedding_model=_FakeEncoder())

    store.add_messages(
        "Cchan",
        [{"text": "ship Thursday", "ts": "1.0", "user": "U1"}],
        {},
    )

    assert collection.added
    assert collection.added[0]["ids"] == ["Cchan:1.0"]
    assert collection.added[0]["documents"] == ["ship Thursday"]


def test_factory_uses_shared_chroma_client():
    client = _FakeClient(_FakeCollection())
    indexer = create_conversation_history_indexer(
        platform="slack", client=client, embedding_model=_FakeEncoder()
    )
    hits = indexer.search("Cchan", "token header")
    assert client.requested == [conversation_collection_name("Cchan")]
    assert hits[0]["content"] == "use the existing token header"


def test_slack_indexer_search_uses_injected_store():
    store = ConversationHistoryStore(
        client=_FakeClient(_FakeCollection()), embedding_model=_FakeEncoder()
    )
    indexer = create_conversation_history_indexer(platform="slack", store=store)
    hits = indexer.search("Cchan", "token header")
    assert hits[0]["content"] == "use the existing token header"


def test_index_conversations_does_not_accept_semantic_indexer():
    indexer = MockConversationHistoryIndexer()
    assert "semantic_indexer" not in indexer.index_conversations.__code__.co_varnames


def test_chromadb_code_indexer_has_no_conversation_api():
    from pathlib import Path

    source = (
        Path(__file__).resolve().parents[2]
        / "src"
        / "benedict"
        / "semantic_indexer"
        / "semantic_indexer_chromadb.py"
    )
    text = source.read_text(encoding="utf-8")
    assert "search_slack_channel" not in text
    assert "slack" not in text.lower()
    assert "conversation_history" not in text.lower()

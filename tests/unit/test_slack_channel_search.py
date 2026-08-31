"""Tests for Slack channel collection search."""

from types import SimpleNamespace

from benedict.indexers.slack_history_indexer import (
    format_slack_channel_hits,
    search_indexed_slack_channel,
    slack_channel_collection_name,
)
from benedict.semantic_indexer.semantic_indexer_chromadb import ChromaDBSemanticIndexer
from benedict.semantic_indexer.semantic_indexer_mock import MockSemanticIndexer


def test_slack_channel_collection_name_is_stable():
    first = slack_channel_collection_name("C123")
    second = slack_channel_collection_name("C123")
    other = slack_channel_collection_name("C999")

    assert first == second
    assert first.startswith("slack_channel_")
    assert first != other
    assert len(first) == len("slack_channel_") + 16


def test_format_slack_channel_hits():
    results = {
        "documents": [["we decided X"]],
        "metadatas": [
            [{"channel_id": "C1", "message_ts": "9.8", "user": "U2", "type": "thread_reply"}]
        ],
        "distances": [[0.0]],
    }

    hits = format_slack_channel_hits(results, "C1")

    assert len(hits) == 1
    assert hits[0]["content"] == "we decided X"
    assert hits[0]["score"] == 1.0
    assert hits[0]["file_path"] == "slack:C1:9.8"
    assert hits[0]["user"] == "U2"
    assert hits[0]["type"] == "thread_reply"


def test_format_slack_channel_hits_empty():
    assert (
        format_slack_channel_hits({"documents": [[]], "metadatas": [[]], "distances": [[]]}, "C1")
        == []
    )
    assert format_slack_channel_hits({}, "C1") == []


def test_search_indexed_slack_channel_uses_dedicated_method():
    indexer = MockSemanticIndexer()
    indexer.add_slack_hit(content="decision lives here", channel_id="Cabc")

    hits = search_indexed_slack_channel(indexer, "Cabc", "what did we decide?")

    assert hits[0]["content"] == "decision lives here"


def test_search_indexed_slack_channel_skips_missing_indexer():
    assert search_indexed_slack_channel(None, "C1", "hello") == []
    assert search_indexed_slack_channel(object(), "C1", "hello") == []
    assert search_indexed_slack_channel(MockSemanticIndexer(), "", "hello") == []
    assert search_indexed_slack_channel(MockSemanticIndexer(), "C1", "   ") == []


class _FakeCollection:
    def __init__(self, count: int = 1):
        self._count = count
        self.queries = []

    def count(self) -> int:
        return self._count

    def query(self, query_embeddings, n_results):
        self.queries.append({"query_embeddings": query_embeddings, "n_results": n_results})
        return {
            "documents": [["use the existing token header"]],
            "metadatas": [[{"channel_id": "Cchan", "message_ts": "2.2", "user": "Udev"}]],
            "distances": [[1.0]],
        }


class _MissingCollectionClient:
    def get_collection(self, name: str):
        raise ValueError(f"missing {name}")


class _FakeClient:
    def __init__(self, collection: _FakeCollection):
        self.collection = collection
        self.requested = []

    def get_collection(self, name: str):
        self.requested.append(name)
        return self.collection


class _FakeEncoder:
    def encode(self, texts):
        return [[0.1, 0.2, 0.3] for _ in texts]


def test_search_indexed_slack_channel_queries_chroma_without_dedicated_method():
    collection = _FakeCollection()
    client = _FakeClient(collection)
    indexer = SimpleNamespace(client=client, embedding_model=_FakeEncoder())

    hits = search_indexed_slack_channel(indexer, "Cchan", "token header", top_k=3)

    assert client.requested == [slack_channel_collection_name("Cchan")]
    assert collection.queries[0]["n_results"] == 1
    assert hits[0]["content"] == "use the existing token header"
    assert hits[0]["score"] == 0.5


def test_search_indexed_slack_channel_missing_collection():
    indexer = SimpleNamespace(client=_MissingCollectionClient(), embedding_model=_FakeEncoder())
    assert search_indexed_slack_channel(indexer, "Cgone", "anything") == []


def test_chromadb_search_slack_channel_does_not_create_collection():
    collection = _FakeCollection(count=2)
    client = _FakeClient(collection)
    indexer = ChromaDBSemanticIndexer.__new__(ChromaDBSemanticIndexer)
    indexer.client = client
    indexer.embedding_model = _FakeEncoder()

    hits = indexer.search_slack_channel("Cchan", "token header", top_k=5)

    assert client.requested == [slack_channel_collection_name("Cchan")]
    assert collection.queries[0]["n_results"] == 2
    assert hits[0]["file_path"] == "slack:Cchan:2.2"


def test_chromadb_search_slack_channel_missing_or_empty():
    indexer = ChromaDBSemanticIndexer.__new__(ChromaDBSemanticIndexer)
    indexer.client = _MissingCollectionClient()
    indexer.embedding_model = _FakeEncoder()
    assert indexer.search_slack_channel("Cgone", "anything") == []
    assert indexer.search_slack_channel("C1", "") == []

    empty = _FakeCollection(count=0)
    indexer.client = _FakeClient(empty)
    assert indexer.search_slack_channel("Cempty", "anything") == []
    assert empty.queries == []

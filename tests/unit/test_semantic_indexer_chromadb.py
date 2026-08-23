"""Tests for Chroma incremental index chunk deletes."""

from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import Mock

from benedict.semantic_indexer.semantic_indexer_chromadb import (
    ChromaDBSemanticIndexer,
    delete_chunks_for_files,
)


class FakeCollection:
    """In-memory Chroma collection that records get/delete calls."""

    def __init__(self, chunks):
        self.chunks = list(chunks)
        self.get_calls = []
        self.delete_calls = []

    def get(self, where=None):
        self.get_calls.append(where)
        file_filter = (where or {}).get("file_path")
        if isinstance(file_filter, dict) and "$in" in file_filter:
            wanted = set(file_filter["$in"])
            ids = [chunk_id for chunk_id, path in self.chunks if path in wanted]
        elif isinstance(file_filter, str):
            ids = [chunk_id for chunk_id, path in self.chunks if path == file_filter]
        else:
            ids = [chunk_id for chunk_id, _ in self.chunks]
        return {"ids": ids}

    def delete(self, ids=None):
        self.delete_calls.append(list(ids or []))
        idset = set(ids or [])
        self.chunks = [(chunk_id, path) for chunk_id, path in self.chunks if chunk_id not in idset]


def _make_indexer(change_detector=None) -> ChromaDBSemanticIndexer:
    indexer = ChromaDBSemanticIndexer.__new__(ChromaDBSemanticIndexer)
    indexer.change_detector = change_detector
    indexer.max_chunk_size = 2000
    return indexer


def test_delete_chunks_for_files_empty_does_not_hit_chroma():
    collection = FakeCollection([("id-a", "a.py")])

    removed = delete_chunks_for_files(collection, [])

    assert removed == 0
    assert collection.get_calls == []
    assert collection.delete_calls == []


def test_delete_chunks_for_files_batches_in_and_deletes_once():
    collection = FakeCollection(
        [
            ("a0", "a.py"),
            ("a1", "a.py"),
            ("b0", "b.py"),
            ("keep", "other.py"),
        ]
    )

    removed = delete_chunks_for_files(collection, ["a.py", "b.py", "a.py"])

    assert removed == 3
    assert collection.get_calls == [{"file_path": {"$in": ["a.py", "b.py"]}}]
    assert collection.delete_calls == [["a0", "a1", "b0"]]
    assert collection.chunks == [("keep", "other.py")]


def test_delete_chunks_for_files_chunks_in_lists():
    paths = [f"f{i}.py" for i in range(5)]
    collection = FakeCollection([(f"id-{path}", path) for path in paths])

    removed = delete_chunks_for_files(collection, paths, batch_size=2)

    assert removed == 5
    assert len(collection.get_calls) == 3
    assert collection.get_calls[0] == {"file_path": {"$in": ["f0.py", "f1.py"]}}
    assert collection.get_calls[1] == {"file_path": {"$in": ["f2.py", "f3.py"]}}
    assert collection.get_calls[2] == {"file_path": {"$in": ["f4.py"]}}
    assert len(collection.delete_calls) == 1
    assert collection.delete_calls[0] == [f"id-{path}" for path in paths]


def test_delete_chunks_for_files_skips_delete_when_no_ids():
    collection = FakeCollection([("keep", "other.py")])

    removed = delete_chunks_for_files(collection, ["missing.py"])

    assert removed == 0
    assert len(collection.get_calls) == 1
    assert collection.delete_calls == []


def test_delete_chunks_for_files_continues_after_get_error():
    collection = FakeCollection([("a0", "a.py"), ("b0", "b.py")])
    original_get = collection.get

    def flaky_get(where=None):
        batch = ((where or {}).get("file_path") or {}).get("$in") or []
        if "a.py" in batch:
            raise RuntimeError("chroma get failed")
        return original_get(where)

    collection.get = flaky_get

    removed = delete_chunks_for_files(collection, ["a.py", "b.py"], batch_size=1)

    assert removed == 1
    assert collection.delete_calls == [["b0"]]


def test_delete_chunks_for_files_returns_zero_when_delete_fails():
    collection = FakeCollection([("a0", "a.py")])
    collection.delete = Mock(side_effect=RuntimeError("chroma delete failed"))

    removed = delete_chunks_for_files(collection, ["a.py"])

    assert removed == 0


def test_update_index_git_deletes_modified_and_deleted_in_one_round_trip():
    detector = Mock()
    detector.detect_changes.return_value = {
        "added": ["new.py"],
        "modified": ["a.py", "b.py", "c.py"],
        "deleted": ["gone.py"],
    }
    collection = FakeCollection(
        [
            ("a0", "a.py"),
            ("a1", "a.py"),
            ("b0", "b.py"),
            ("c0", "c.py"),
            ("g0", "gone.py"),
            ("keep", "other.py"),
        ]
    )
    indexer = _make_indexer(detector)
    indexer._index_files = Mock()

    indexer._update_index_git(
        "acme/example",
        Mock(),
        collection,
        Path("/tmp/unused"),
        since=None,
    )

    assert collection.get_calls == [{"file_path": {"$in": ["gone.py", "a.py", "b.py", "c.py"]}}]
    assert collection.delete_calls == [["a0", "a1", "b0", "c0", "g0"]]
    assert collection.chunks == [("keep", "other.py")]
    indexer._index_files.assert_called_once()
    indexed_files = indexer._index_files.call_args[0][3]
    assert indexed_files == ["new.py", "a.py", "b.py", "c.py"]


def test_update_index_git_skips_chroma_when_no_changes():
    detector = Mock()
    detector.detect_changes.return_value = {
        "added": [],
        "modified": [],
        "deleted": [],
    }
    collection = FakeCollection([("a0", "a.py")])
    indexer = _make_indexer(detector)
    indexer._index_files = Mock()

    indexer._update_index_git("acme/example", Mock(), collection, Path("/tmp/unused"), None)

    assert collection.get_calls == []
    assert collection.delete_calls == []
    indexer._index_files.assert_not_called()


def test_update_index_file_mtime_uses_batched_delete(tmp_path):
    repo = "acme/example"
    repo_dir = tmp_path / repo
    repo_dir.mkdir(parents=True)
    for name in ("a.py", "b.py", "c.py"):
        (repo_dir / name).write_text("x = 1\n", encoding="utf-8")

    reader = Mock()
    reader.list_files.return_value = ["a.py", "b.py", "c.py"]
    collection = FakeCollection(
        [
            ("a0", "a.py"),
            ("b0", "b.py"),
            ("c0", "c.py"),
            ("keep", "old.py"),
        ]
    )
    indexer = _make_indexer()
    indexer._index_files = Mock()
    since = datetime.now(timezone.utc) - timedelta(hours=1)

    indexer._update_index_file_mtime(repo, reader, collection, repo_dir, since)

    assert collection.get_calls == [{"file_path": {"$in": ["a.py", "b.py", "c.py"]}}]
    assert collection.delete_calls == [["a0", "b0", "c0"]]
    assert collection.chunks == [("keep", "old.py")]
    indexer._index_files.assert_called_once()

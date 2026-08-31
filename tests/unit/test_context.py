"""Tests for context building and search-hit recording."""

from pathlib import Path

from benedict.operator_ui.recorder import JsonlRunRecorder
from benedict.repo_reader.repo_reader_mock import MockRepoReader
from benedict.semantic_indexer.semantic_indexer_mock import MockSemanticIndexer
from benedict.utils.context import build_architect_context, build_context


def test_build_context_records_chunk_hits(tmp_path: Path):
    recorder = JsonlRunRecorder(tmp_path / "runs.jsonl")
    indexer = MockSemanticIndexer()
    indexer.add_relevant_file(
        "src/index.py",
        score=0.91,
        content="def index_repository():\n    chunk = encode(text)\n",
    )
    reader = MockRepoReader(
        repos={
            "acme/x": {
                "README.md": "# Hello\n",
                "src/index.py": "def index_repository():\n    chunk = encode(text)\n",
            }
        }
    )
    run = recorder.begin(query="how does indexing work")
    text = build_context(
        "acme/x",
        "how does indexing work",
        reader,
        semantic_indexer=indexer,
    )
    run.finish(status="ok")

    assert "index_repository" in text
    loaded = recorder.get(run.id)
    search = next(stage for stage in loaded["stages"] if stage["name"] == "search")
    hit = search["detail"]["hits"][0]
    assert search["detail"]["mode"] == "semantic"
    assert search["detail"]["stuffed"] == "full_files"
    assert hit["file_path"] == "src/index.py"
    assert hit["score"] == 0.91
    assert "chunk = encode" in hit["content"]

    context = next(stage for stage in loaded["stages"] if stage["name"] == "context")
    assert "README.md" in context["detail"]["files"]
    assert "src/index.py" in context["detail"]["files"]
    reasons = {item["path"]: item["reason"] for item in context["detail"]["items"]}
    assert reasons["README.md"] == "always included"
    assert reasons["src/index.py"] == "semantic hit"


def test_build_context_records_keyword_hits_without_indexer(tmp_path: Path):
    recorder = JsonlRunRecorder(tmp_path / "runs.jsonl")
    reader = MockRepoReader(
        repos={"acme/x": {"README.md": "# Hello\n", "src/indexing.py": "INDEX = 1\n"}}
    )
    run = recorder.begin(query="where is indexing")
    build_context("acme/x", "where is indexing", reader)
    run.finish(status="ok")
    loaded = recorder.get(run.id)
    search = next(stage for stage in loaded["stages"] if stage["name"] == "search")
    assert search["detail"]["mode"] == "keyword"
    assert search["detail"]["hits"][0]["file_path"] == "src/indexing.py"


def test_build_context_records_skip_without_indexer_or_keywords(tmp_path: Path):
    recorder = JsonlRunRecorder(tmp_path / "runs.jsonl")
    reader = MockRepoReader(repos={"acme/x": {"README.md": "# Hello\n"}})
    run = recorder.begin(query="hi")
    build_context("acme/x", "hi", reader)
    run.finish(status="ok")
    loaded = recorder.get(run.id)
    search = next(stage for stage in loaded["stages"] if stage["name"] == "search")
    assert search["status"] == "skip"
    assert search["label"] == "no indexer"


def test_build_context_records_search_error(tmp_path: Path):
    recorder = JsonlRunRecorder(tmp_path / "runs.jsonl")

    class _BrokenIndexer:
        def is_indexed(self, repo: str) -> bool:
            return True

        def search(self, *args: object, **kwargs: object) -> list:
            raise RuntimeError("chroma down")

    reader = MockRepoReader(repos={"acme/x": {"README.md": "# Hello\n"}})
    run = recorder.begin(query="how does indexing work")
    build_context("acme/x", "how does indexing work", reader, semantic_indexer=_BrokenIndexer())
    run.finish(status="ok")
    loaded = recorder.get(run.id)
    search = next(stage for stage in loaded["stages"] if stage["name"] == "search")
    assert search["status"] == "error"
    assert "chroma down" in search["detail"]["error"]


def test_build_architect_context_records_chunks(tmp_path: Path):
    recorder = JsonlRunRecorder(tmp_path / "runs.jsonl")
    indexer = MockSemanticIndexer()
    indexer.index_repository("acme/one", repo_reader=None)
    indexer.add_relevant_file("src/a.py", score=0.8, content="class Agent:\n    pass\n")

    class _Agent:
        semantic_indexer = indexer

    run = recorder.begin(query="how do agents work")
    text = build_architect_context(
        _Agent(),
        "how do agents work",
        {"channels": {"C1": {"repo": "acme/one"}}},
    )
    run.finish(status="ok")
    assert "src/a.py" in text
    loaded = recorder.get(run.id)
    search = next(stage for stage in loaded["stages"] if stage["name"] == "search")
    assert search["detail"]["stuffed"] == "chunks"
    assert search["detail"]["hits"][0]["file_path"] == "src/a.py"
    assert "class Agent" in search["detail"]["hits"][0]["content"]
    assert search["detail"]["hits"][0]["project"] == "acme/one"


def test_build_architect_context_records_empty_search(tmp_path: Path):
    recorder = JsonlRunRecorder(tmp_path / "runs.jsonl")

    class _Agent:
        semantic_indexer = None

    run = recorder.begin(query="anything")
    text = build_architect_context(_Agent(), "anything", {"channels": {}})
    run.finish(status="ok")
    assert "No relevant code" in text
    loaded = recorder.get(run.id)
    search = next(stage for stage in loaded["stages"] if stage["name"] == "search")
    assert search["status"] == "skip"
    assert search["detail"]["hits"] == []

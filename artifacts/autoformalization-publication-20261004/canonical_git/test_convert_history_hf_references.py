"""Disposable Git fixtures, not genuine artifacts or semantic labels."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

OWNER = Path(__file__).with_name("convert_history_hf_references.py")
SPEC = importlib.util.spec_from_file_location("hf_history_conversion", OWNER)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def fixture(tmp_path):
    repository = tmp_path / "repository"
    repository.mkdir()
    MODULE.git(repository, "init", "-b", "main")
    MODULE.git(repository, "config", "user.name", "Disposable fixture")
    MODULE.git(repository, "config", "user.email", "fixture@example.invalid")
    (repository / "source.py").write_text("value = 1\n")
    MODULE.git(repository, "add", "source.py")
    MODULE.git(repository, "commit", "-m", "published fixture")
    published = MODULE.git(repository, "rev-parse", "HEAD").decode().strip()
    return repository, published


def commit_file(repository, path, data, message):
    destination = repository / path
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(data)
    MODULE.git(repository, "add", "--", path)
    MODULE.git(repository, "commit", "-m", message)
    return MODULE.git(repository, "rev-parse", "HEAD").decode().strip()


def reference(repository, path, payload):
    oid = MODULE.git(repository, "hash-object", "--stdin", data=payload).decode().strip()
    return {path: {"schema": "disposable-hf-reference/v1", "source_git_blob_oid": oid,
                   "sha256": "f" * 64, "bytes": len(payload)}}


def test_hf_conversion_preserves_small_versions_messages_modes_and_original_refs(tmp_path):
    repository, published = fixture(tmp_path)
    path = "data/nested/data.duckdb"
    small = commit_file(repository, path, b"small", "small historical version")
    large = commit_file(repository, path, b"selected oversized fixture", "large historical version")
    tip = commit_file(repository, "source.py", b"value = 2\n", "source descendant")
    before_refs = MODULE.git(repository, "for-each-ref")
    before_head = MODULE.git(repository, "rev-parse", "HEAD")
    before_index = MODULE.git(repository, "diff", "--cached")
    original_source = (repository / "source.py").read_bytes()
    result = MODULE.rewrite_unpublished(repository, tip, [published], reference(repository, path, b"selected oversized fixture"))
    assert result["commit_map"][small] == small
    mapped_large = result["commit_map"][large]
    assert path not in MODULE.tree(repository, mapped_large)
    pointer = MODULE.git(repository, "show", mapped_large + ":" + path + ".hf.json")
    assert json.loads(pointer)["source_git_blob_oid"] == reference(repository, path, b"selected oversized fixture")[path]["source_git_blob_oid"]
    assert MODULE.git(repository, "show", small + ":" + path) == b"small"
    assert MODULE.git(repository, "show", result["tip"] + ":source.py") == original_source
    old_commit = MODULE.git(repository, "cat-file", "commit", large)
    new_commit = MODULE.git(repository, "cat-file", "commit", mapped_large)
    assert old_commit.partition(b"\n\n")[2] == new_commit.partition(b"\n\n")[2]
    assert [line for line in old_commit.splitlines() if line.startswith((b"author ", b"committer "))] == [
        line for line in new_commit.splitlines() if line.startswith((b"author ", b"committer "))]
    assert MODULE.git(repository, "for-each-ref") == before_refs
    assert MODULE.git(repository, "rev-parse", "HEAD") == before_head
    assert MODULE.git(repository, "diff", "--cached") == before_index
    assert (repository / "source.py").read_bytes() == original_source
    MODULE.git(repository, "merge-base", "--is-ancestor", published, result["tip"])


def test_hf_conversion_preserves_merge_geometry_and_final_deleted_tree(tmp_path):
    repository, published = fixture(tmp_path)
    left = commit_file(repository, "data/payload.jsonl", b"selected", "left")
    MODULE.git(repository, "checkout", "-b", "right", published)
    right = commit_file(repository, "right.py", b"side = True\n", "right")
    MODULE.git(repository, "checkout", "main")
    MODULE.git(repository, "merge", "--no-ff", "right", "-m", "merge")
    merge = MODULE.git(repository, "rev-parse", "HEAD").decode().strip()
    MODULE.git(repository, "rm", "--", "data/payload.jsonl")
    MODULE.git(repository, "commit", "-m", "remove raw generated artifact")
    tip = MODULE.git(repository, "rev-parse", "HEAD").decode().strip()
    result = MODULE.rewrite_unpublished(repository, tip, [published], reference(repository, "data/payload.jsonl", b"selected"))
    assert MODULE.tree(repository, result["tip"]) == MODULE.tree(repository, tip)
    for head in [left, right, merge]:
        MODULE.git(repository, "merge-base", "--is-ancestor", result["commit_map"].get(head, head), result["tip"])
    mapped_merge = MODULE.git(repository, "cat-file", "commit", result["commit_map"][merge])
    parents = [line[7:].decode() for line in mapped_merge.splitlines() if line.startswith(b"parent ")]
    assert parents == [result["commit_map"][left], right]
    assert result["commit_map"][right] == right


def test_hf_conversion_rejects_adjacent_collision_and_preserves_published_history(tmp_path):
    repository, published = fixture(tmp_path)
    large = commit_file(repository, "data.bin", b"selected", "published payload")
    MODULE.git(repository, "rm", "--", "data.bin")
    MODULE.git(repository, "commit", "-m", "remove historical payload")
    tip = MODULE.git(repository, "rev-parse", "HEAD").decode().strip()
    refs = reference(repository, "data.bin", b"selected")
    result = MODULE.rewrite_unpublished(repository, tip, [large], refs)
    assert result["tip"] == tip
    assert MODULE.git(repository, "show", large + ":data.bin") == b"selected"
    commit_file(repository, "data.bin.hf.json", b"existing content", "adjacent reference collision")
    collision = commit_file(repository, "data.bin", b"selected", "restore colliding payload")
    with pytest.raises(ValueError, match="overwrite"):
        MODULE.rewrite_unpublished(repository, collision, [published], refs)

#!/usr/bin/env python3
"""Prepare an isolated, genuinely indexed Notes corpus before browser testing.

Search never creates an index. Existing collections and services are never
replaced. This precondition grants no application/task acceptance.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import math
from pathlib import Path
import re
import uuid

try:
    from .common import ROOT, Transport, ReadinessError, atomic_json, confined, endpoint, require, sha, wire
except ImportError:
    from common import ROOT, Transport, ReadinessError, atomic_json, confined, endpoint, require, sha, wire

TITLE = "SVF cedar-ledger note"
BODY = "cedar-ledger semantic phrase for notebook search"
MODEL = "thenlper/gte-small"
COLLECTION = re.compile(r"svf-notes-[0-9a-f]{32}\Z")


def documents(collection: str) -> list[dict]:
    require(bool(COLLECTION.fullmatch(collection)), "fixture collection must be a fresh SVF Notes UUID namespace")
    return [
        {"text": BODY, "metadata": {"title": TITLE, "content": BODY, "fixture_scope": collection, "note_id": "cedar-ledger"}},
        {"text": "Unrelated telescope maintenance and distant stellar observations.",
         "metadata": {"title": "SVF astronomy distractor", "fixture_scope": collection, "note_id": "astronomy"}},
    ]


def verify_search(value: dict, collection: str) -> dict:
    require(isinstance(value, dict) and value.get("collection") == collection and value.get("query") == BODY
            and value.get("model") == MODEL, "native semantic search is not bound to the requested fixture")
    rows = value.get("results")
    require(isinstance(rows, list) and rows, "native semantic search returned no actual rows")
    hit = rows[0]
    require(isinstance(hit, dict) and type(hit.get("score")) in {int, float} and math.isfinite(hit["score"]), "native search omitted a real similarity score")
    doc = hit.get("document")
    require(isinstance(doc, dict) and doc.get("text") == BODY,
            "native search did not return the indexed document bytes; statistics/IDs alone cannot prove Notes search")
    metadata = doc.get("metadata")
    require(isinstance(metadata, dict) and metadata.get("title") == TITLE and metadata.get("content") == BODY
            and metadata.get("fixture_scope") == collection, "native matched row/title/provenance differs from the fixture")
    provenance = hit.get("document_provenance")
    require(isinstance(provenance, dict) and provenance.get("source") == "duckdb_authority"
            and provenance.get("producer_vector_id") == "doc_0"
            and type(provenance.get("generation_id")) is int and provenance["generation_id"] > 0
            and all(isinstance(provenance.get(key), str) and provenance[key] for key in ["collection_id", "document_id", "chunk_id"])
            and provenance.get("payload_digest") == "sha256:" + sha(wire(doc)),
            "native matched document lacks its authoritative published-row binding")
    return hit


def prepare(root: Path, profile: dict, output: Path, *, transport_factory=Transport, nonce=None) -> dict:
    root = root.resolve()
    runtime = confined(root, profile["runtimeRoot"])
    output = confined(root, output)
    require(output.is_relative_to(runtime / "backends" / "notes-fixtures"), "fixture output must remain in campaign-owned Notes preparation state")
    require(not output.exists(), "fixture preparation output already exists; preserve it and use a fresh attempt")
    origin = endpoint(profile["backends"]["ipfs_datasets_py"])
    collection = "svf-notes-" + (nonce or uuid.uuid4().hex)
    docs = documents(collection)
    # The pinned SDK uses ./vector_indexes relative to the verified adapter's
    # workspace cwd. Reserve only this fresh UUID directory; never enumerate,
    # delete, overwrite or reuse another collection (including 'default').
    index_root = confined(root, profile.get("backendReadiness", {}).get("notesIndexesDirectory", "vector_indexes"))
    require(index_root == root / "vector_indexes" or index_root.is_relative_to(runtime / "backends"),
            "configured index directory is outside controlled SDK fixture state")
    index_dir = confined(root, index_root / collection)
    require(not index_dir.exists(), "fixture index already exists; existing data is preserved")
    output.mkdir(parents=True, exist_ok=False)
    client = transport_factory(root, origin, "ipfs_datasets_py", output)
    client.catalog(["vector_index", "semantic_search"])
    fixture_file = output / "documents.json"
    fixture_file.write_bytes(wire(docs) + b"\n")
    index_dir.mkdir(parents=True, exist_ok=False)
    reservation = {"schema": "swissknife.notes-fixture-reservation.v1", "collection": collection,
                   "documents_sha256": sha(wire(docs)), "index_directory": index_dir.relative_to(root).as_posix()}
    atomic_json(output / "reservation.json", reservation)
    try:
        indexed = client.call("vector_index", {"collection": collection, "documents": docs, "backend": "faiss",
            "vector_dim": 384, "distance_metric": "cosine", "dry_run": False, "fixture_scope": collection,
            "index_config": {"document_payload_policy": "matched-only"}})
        require(indexed.get("status") == "success" and indexed.get("index_name") == collection
                and indexed.get("backend") == "faiss" and indexed.get("document_count") == len(docs),
                "native vector-index creation did not acknowledge the exact corpus")
        require((index_dir / "index.faiss").is_file() and not (index_dir / "index.faiss").is_symlink(),
                "native SDK did not persist its real FAISS segment in the reserved namespace")
        result = client.call("semantic_search", {"query": BODY, "collection": collection, "model": MODEL,
            "top_k": 2, "dry_run": False, "fixture_scope": collection})
        hit = verify_search(result, collection)
        report = {"schema": "swissknife.notes-index-fixture.v1", "fixture_ready": True,
            "prepared_at": dt.datetime.now(dt.timezone.utc).isoformat(), "collection": collection,
            "owner": "ipfs_datasets_py", "endpoint": origin, "model": MODEL,
            "expected_note": {"title": TITLE, "content": BODY}, "documents_sha256": sha(wire(docs)),
            "index_directory": index_dir.relative_to(root).as_posix(),
            "faiss_sha256": sha((index_dir / "index.faiss").read_bytes()),
            "verified_hit": hit, "owner_identity": client.identity, "requests": client.records,
            "browser_result_pointer": "/result/result/content/0/json/results/0/document/metadata/title",
            "app_configuration": {"notes_collection": collection, "notes_model": MODEL},
            "boundary": "Pre-existing controlled corpus for read-only semantic search; local editor changes are not automatically indexed.",
            "functional_acceptance": "not_evaluated", "work_complete": False, "completion_authority": False}
        atomic_json(output / "fixture.json", report)
        return report
    except Exception as error:
        atomic_json(output / "failure.json", {"schema": "swissknife.notes-index-fixture-failure.v1",
            "collection": collection, "fixture_ready": False, "error": type(error).__name__ + ": " + str(error)[:1000],
            "owner_identity": client.identity, "requests": client.records,
            "preserved_index_directory": index_dir.relative_to(root).as_posix(), "completion_authority": False})
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", default="config/swissknife_visual_functional_supervisor.json")
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()
    try:
        profile = json.loads(confined(ROOT, args.profile).read_text())
        result = prepare(ROOT, profile, confined(ROOT, args.output_dir))
        print(json.dumps(result)); return 0
    except (ReadinessError, OSError, ValueError) as error:
        print(json.dumps({"fixture_ready": False, "error": str(error), "completion_authority": False})); return 1


if __name__ == "__main__":
    raise SystemExit(main())

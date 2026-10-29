"""Authored transport fixtures test admission/readback only, never live evidence."""
import copy
import json
from pathlib import Path
import tempfile
import unittest

from scripts.svf_backends import notes_fixture as fixture


class UnitClient:
    mode = "valid"
    calls = []

    def __init__(self, root, origin, owner, output):
        self.root, self.origin, self.output = root, origin, output
        self.identity = {"owner": owner, "endpoint": origin, "unit_only": True}
        self.records = []

    def catalog(self, names):
        self.calls.append(("catalog", names))
        if self.mode == "missing_catalog":raise fixture.ReadinessError("native vector_index is unavailable")

    def call(self, tool, args):
        self.calls.append((tool, copy.deepcopy(args)))
        if tool == "vector_index":
            if self.mode == "write_error":raise fixture.ReadinessError("actual owner rejected fixture write")
            (self.root / "vector_indexes" / args["collection"] / "index.faiss").write_bytes(b"authored unit segment, not native evidence")
            return {"status": "success", "backend": "faiss", "index_name": args["collection"], "document_count": len(args["documents"])}
        result = {"query": fixture.BODY, "model": fixture.MODEL, "collection": args["collection"],
                  "results": [{"score": 1.0, "document": fixture.documents(args["collection"])[0]}]}
        result["results"][0]["document_provenance"] = {"source": "duckdb_authority", "producer_vector_id": "doc_0",
            "generation_id": 1, "collection_id": "unit_collection", "document_id": "unit_document", "chunk_id": "unit_chunk",
            "payload_digest": "sha256:" + fixture.sha(fixture.wire(result["results"][0]["document"]))}
        if self.mode == "stats_only":result["results"][0]["document"] = {"id": "doc_0", "source": "duckdb_authority"}
        if self.mode == "wrong_title":result["results"][0]["document"]["metadata"]["title"] = "another real note"
        if self.mode == "wrong_text":result["results"][0]["document"]["text"] = "different content"
        if self.mode == "wrong_scope":result["collection"] = "default"
        return result


class FixtureTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="svf-notes-unit-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.profile = {"runtimeRoot": "campaign", "backends": {"ipfs_datasets_py": "http://127.0.0.1:13002"}}
        self.output = self.root / "campaign/backends/notes-fixtures/owned-attempt"
        self.nonce = "a" * 32
        UnitClient.mode = "valid"; UnitClient.calls = []

    def prepare(self):
        return fixture.prepare(self.root, self.profile, self.output, transport_factory=UnitClient, nonce=self.nonce)

    def test_index_before_search_exact_corpus_and_original_semantic_title(self):
        value = self.prepare()
        self.assertEqual([x[0] for x in UnitClient.calls], ["catalog", "vector_index", "semantic_search"])
        write = UnitClient.calls[1][1]; read = UnitClient.calls[2][1]
        self.assertFalse(write["dry_run"]); self.assertEqual(len(write["documents"]), 2)
        self.assertEqual(write["collection"], "svf-notes-" + self.nonce)
        self.assertEqual(read["collection"], write["collection"])
        self.assertNotIn("texts", read); self.assertNotIn("documents", read)
        self.assertEqual(value["verified_hit"]["document"]["metadata"]["title"], fixture.TITLE)
        self.assertTrue(value["fixture_ready"]); self.assertFalse(value["completion_authority"])
        self.assertEqual(value["functional_acceptance"], "not_evaluated")
        self.assertIn("not automatically indexed", value["boundary"])
        self.assertTrue((self.output / "fixture.json").exists())

    def test_never_reuse_or_replace_existing_index(self):
        index = self.root / "vector_indexes" / ("svf-notes-" + self.nonce)
        index.mkdir(parents=True); sentinel = index / "foreign"; sentinel.write_text("preserved")
        with self.assertRaisesRegex(fixture.ReadinessError, "already exists"):self.prepare()
        self.assertEqual(sentinel.read_text(), "preserved"); self.assertEqual(UnitClient.calls, [])

    def test_existing_output_remains_immutable(self):
        self.prepare(); before = (self.output / "fixture.json").read_bytes()
        with self.assertRaisesRegex(fixture.ReadinessError, "already exists"):self.prepare()
        self.assertEqual((self.output / "fixture.json").read_bytes(), before)

    def test_readback_needs_actual_document_bytes_title_and_scope(self):
        for mode in ["stats_only", "wrong_title", "wrong_text", "wrong_scope"]:
            with self.subTest(mode=mode):
                self.output = self.output.parent / mode; self.nonce = {"stats_only":"b", "wrong_title":"c", "wrong_text":"d", "wrong_scope":"e"}[mode] * 32
                UnitClient.mode = mode
                with self.assertRaises(fixture.ReadinessError):self.prepare()
                self.assertFalse((self.output / "fixture.json").exists())
                self.assertFalse(json.loads((self.output / "failure.json").read_text())["fixture_ready"])

    def test_failed_index_does_not_search_or_manufacture_ready_fixture(self):
        UnitClient.mode = "write_error"
        with self.assertRaisesRegex(fixture.ReadinessError, "rejected"):self.prepare()
        self.assertNotIn("semantic_search", [x[0] for x in UnitClient.calls])
        self.assertFalse((self.output / "fixture.json").exists())
        self.assertTrue((self.output / "failure.json").exists())

    def test_missing_capability_never_mutates_index_namespace(self):
        UnitClient.mode = "missing_catalog"
        with self.assertRaises(fixture.ReadinessError):self.prepare()
        self.assertFalse((self.root / "vector_indexes").exists())

    def test_remote_endpoint_and_non_campaign_output_are_rejected(self):
        self.profile["backends"]["ipfs_datasets_py"] = "http://example.com:13002"
        with self.assertRaises(fixture.ReadinessError):self.prepare()
        self.profile["backends"]["ipfs_datasets_py"] = "http://127.0.0.1:13002"
        self.output = self.root / "user-notes"
        with self.assertRaises(fixture.ReadinessError):self.prepare()
        self.assertEqual(UnitClient.calls, [])

    def test_only_unique_svf_names_and_no_symlink_index_parent(self):
        for value in ["default", "../user", "a"*31, "A"*32]:
            self.nonce = value
            with self.assertRaises(fixture.ReadinessError):self.prepare()
        self.nonce = "a" * 32
        elsewhere = self.root / "elsewhere"; elsewhere.mkdir()
        (self.root / "vector_indexes").symlink_to(elsewhere, target_is_directory=True)
        with self.assertRaises(fixture.ReadinessError):self.prepare()
        self.assertEqual(UnitClient.calls, [])


if __name__ == "__main__":unittest.main()

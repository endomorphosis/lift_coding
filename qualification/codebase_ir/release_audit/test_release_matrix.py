from __future__ import annotations

import copy
import os
import subprocess
import sys
import tempfile
import unittest
import zlib
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import release_matrix as matrix


class ReleaseMatrixTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.repo = self.root / "repo"
        self.repo.mkdir()
        self.git("init", "-q")
        self.git("config", "user.email", "qualification@example.invalid")
        self.git("config", "user.name", "Qualification")
        self.source = b"raise RuntimeError('never execute selected source')\n"
        (self.repo / "pkg").mkdir()
        (self.repo / "pkg/source.py").write_bytes(self.source)
        (self.repo / "docs").mkdir()
        (self.repo / "docs/evidence.json").write_bytes(b'{"retained": true}\n')
        rows = []
        for i in range(1, 33):
            rows.append({"id": f"RPI-{i:03d}", "owners": "Owner", "dependencies": "None" if i == 1 else f"RPI-{i - 1:03d}",
                         "criterion": f"Criterion {i}.", "source_line": i, "production_acceptance": "closed" if i <= 18 else "open",
                         "local_status": "criterion_qualified" if i <= 22 else "pending_verification",
                         "locally_qualified_portions": [], "remaining_work": [], "evidence": ["example"],
                         "criterion_acceptance": "qualified_for_declared_profile" if i <= 22 else "not_yet_qualified"})
        self.ledger = {"schema": "repository-proof-index-backlog-status/v1", "updated_at_utc": "2026-10-02",
                       "scope": "Frozen fixture", "source": {"path": str(self.root / "missing-original.md"), "sha256": "a" * 64,
                           "worktree_head": "b" * 40, "working_source": True, "table_rows": 32},
                       "summary": {"criteria": 32, "production_closed": 18, "production_open": 14,
                                   "criteria_qualified_for_declared_profile": 22},
                       "evidence": {"example": {"path": "docs/evidence.json", "sha256": matrix.sha((self.repo / "docs/evidence.json").read_bytes()),
                                                "retention": "repository_evidence"}},
                       "criteria": rows, "source_revision_observation": {}, "closure_audit": {}}
        (self.root / "local").mkdir()
        self.current = self.root / "local/current.md"
        self.write_table()
        (self.root / "copies").mkdir()
        self.retained = self.root / "copies/retained.py"
        self.retained.write_bytes(self.source)
        self.spec = {"schema": matrix.INPUT_SCHEMA, "repositories": [], "ledger": {},
                     "released_documents": [{"name": "absent_roadmap", "repository": "repo", "path": "docs/roadmap.md", "sha256": None}],
                     "local_documents": [], "selected_evidence": ["example"], "snapshot": None,
                     "source_profiles": [{"name": "historical", "origin_basis": "explicit retained fixture", "files": [
                         {"repository": "repo", "path": "pkg/source.py", "sha256": matrix.sha(self.source),
                          "size_bytes": len(self.source), "retained_path": str(self.retained)}]}]}
        self.manifest = self.root / "spec.json"
        self.commit()

    def git(self, *args):
        return subprocess.check_output(["git", "-C", str(self.repo), *args], stderr=subprocess.DEVNULL).decode().strip()

    def write_table(self, changed: set[int] | None = None):
        lines = []
        for i, row in enumerate(self.ledger["criteria"], 1):
            criterion = "Changed criterion." if i in (changed or set()) else row["criterion"]
            lines.append(f'| {row["id"]} | Owner | {row["dependencies"]} | {criterion} |')
        self.current.write_text("\n".join(lines) + "\n")

    def commit(self):
        raw = matrix.json_bytes(self.ledger)
        (self.repo / "docs/ledger.json").write_bytes(raw)
        self.git("add", ".")
        self.git("commit", "-qm", "retained fixture")
        commit = self.git("rev-parse", "HEAD")
        self.spec["repositories"] = [{"name": "repo", "root": str(self.repo), "commit": commit, "package_roots": ["pkg"]}]
        self.spec["ledger"] = {"repository": "repo", "path": "docs/ledger.json", "sha256": matrix.sha(raw)}

    def write_spec(self):
        raw = self.current.read_bytes()
        self.spec["local_documents"] = [{"name": "current", "path": str(self.current), "sha256": matrix.sha(raw),
                                         "size_bytes": len(raw), "kind": "task_table", "source_basis": "current_working_source",
                                         "observed_path": str(self.current)}]
        self.manifest.write_bytes(matrix.json_bytes(self.spec))

    def run_matrix(self):
        self.write_spec()
        return matrix.reconcile(self.manifest)

    def refused(self):
        with self.assertRaises(ValueError):
            self.run_matrix()

    def test_claims_drift_and_transitive_prerequisites_remain_independent(self):
        self.write_table({3, 29, 32})
        result = self.run_matrix()
        self.assertEqual(result["status"], "passed")
        self.assertEqual(result["criterion_source"]["changed_criteria"], ["RPI-003", "RPI-029", "RPI-032"])
        self.assertEqual(result["reconstructed_claim_counts"]["production_closed"], 18)
        self.assertEqual(result["reconstructed_claim_counts"]["criteria_qualified_for_declared_profile"], 22)
        self.assertEqual(result["criteria"][20]["transitive_open_rpi_dependencies"], ["RPI-019", "RPI-020"])
        self.assertEqual(result["criteria"][20]["disposition"], "own_profile_qualified_prerequisites_open")
        self.assertTrue(result["input_files_unchanged"])
        for field in matrix.FALSE_FLAGS:
            self.assertIs(result[field], False)
        self.assertIs(result["criterion_source"]["frozen_original_document_independently_captured"], False)

    def test_release_evidence_and_source_differences_are_findings(self):
        self.ledger["evidence"]["example"]["sha256"] = "c" * 64
        self.ledger["evidence"]["missing"] = {"path": "docs/missing.json", "sha256": "d" * 64, "retention": "repository_evidence"}
        self.spec["selected_evidence"].append("missing")
        (self.repo / "pkg/source.py").write_bytes(b"VALUE=2\n")
        self.commit()
        result = self.run_matrix()
        self.assertEqual(result["evidence_dispositions"], {"different": 1, "missing": 1})
        self.assertEqual(result["source_dispositions"], {"different": 1})
        self.assertIs(result["portability"]["runtime_dependency_closure_qualified"], False)

    def test_pinned_commit_ignores_moving_head_and_ambient_git_routing(self):
        commit = self.spec["repositories"][0]["commit"]
        (self.repo / "pkg/source.py").write_bytes(b"NEW=3\n")
        self.git("add", ".")
        self.git("commit", "-qm", "later unrelated change")
        with patch.dict(os.environ, {"GIT_DIR": "/missing", "GIT_WORK_TREE": "/missing", "GIT_CONFIG_COUNT": "1", "GIT_CONFIG_KEY_0": "alias.cat-file", "GIT_CONFIG_VALUE_0": "!false"}):
            result = self.run_matrix()
        self.assertEqual(result["repositories"][0]["commit"], commit)
        self.assertEqual(result["source_dispositions"], {"identical": 1})

    def test_corrupt_commit_object_cannot_rebind_an_explicit_pin(self):
        commit = self.spec["repositories"][0]["commit"]
        path = self.repo / ".git/objects" / commit[:2] / commit[2:]
        raw = zlib.decompress(path.read_bytes())
        changed = raw.replace(b"retained fixture", b"retained fixturE")
        self.assertNotEqual(raw, changed)
        path.chmod(0o644)
        path.write_bytes(zlib.compress(changed))
        self.refused()

    def test_corrupt_tree_cannot_rebind_blob_path_to_commit(self):
        commit = self.spec["repositories"][0]["commit"]
        tree = self.git("rev-parse", commit + "^{tree}")
        path = self.repo / ".git/objects" / tree[:2] / tree[2:]
        raw = zlib.decompress(path.read_bytes())
        changed = raw.replace(b"docs\0", b"docx\0")
        self.assertNotEqual(raw, changed)
        path.chmod(0o644)
        path.write_bytes(zlib.compress(changed))
        self.refused()

    def test_exact_population_and_duplicate_rows_refused(self):
        for operation in (lambda rows: rows.pop(), lambda rows: rows.__setitem__(31, copy.deepcopy(rows[0]))):
            original = copy.deepcopy(self.ledger)
            operation(self.ledger["criteria"])
            self.commit()
            self.refused()
            self.ledger = original

    def test_dependency_unknown_cycle_duplicate_suffix_and_self_refused(self):
        for expression in ("RPI-999", "RPI-001, RPI-001", "RPI-001x", "garbage", "RPI-002"):
            original = copy.deepcopy(self.ledger)
            self.ledger["criteria"][1]["dependencies"] = expression
            self.commit()
            self.refused()
            self.ledger = original
        self.ledger["criteria"][0]["dependencies"] = "RPI-032"
        self.commit()
        self.refused()

    def test_conditional_ranges_and_external_scope_preserved(self):
        rpi, external = matrix.dependencies("RPI-011; RPI-029/030/031 for selected profile; TIP-010 and TIP-011 contracts")
        self.assertEqual(rpi, ["RPI-011", "RPI-029", "RPI-030", "RPI-031"])
        self.assertEqual(external, ["TIP-010", "TIP-011"])
        self.assertEqual(matrix.dependencies("RPI-013 through RPI-015")[0], ["RPI-013", "RPI-014", "RPI-015"])

    def test_bad_digest_mutable_revision_and_authority_spec_refused(self):
        original = copy.deepcopy(self.spec)
        for mutate in (lambda: self.spec["ledger"].__setitem__("sha256", "e" * 64),
                       lambda: self.spec["repositories"][0].__setitem__("commit", "origin/main"),
                       lambda: self.spec.__setitem__("production_acceptance_requalified", True)):
            mutate()
            self.refused()
            self.spec = copy.deepcopy(original)

    def test_bool_count_and_unknown_evidence_refused(self):
        self.ledger["source"]["table_rows"] = True
        self.commit()
        self.refused()
        self.ledger["source"]["table_rows"] = 32
        self.ledger["criteria"][0]["evidence"] = ["foreign"]
        self.commit()
        self.refused()

    def test_summary_disagreement_is_recorded_without_upgrading(self):
        self.ledger["summary"]["production_closed"] = 32
        self.ledger["summary"]["production_open"] = 0
        self.ledger["criteria"][20]["production_acceptance"] = "closed"
        self.commit()
        result = self.run_matrix()
        self.assertIs(result["declared_summary_matches"], False)
        self.assertIs(result["criteria"][20]["rpi_declared_closure_consistent"], False)

    def test_current_table_missing_duplicate_and_strict_json_refused(self):
        raw = self.current.read_text()
        self.current.write_text(raw + raw.splitlines()[0] + "\n")
        self.refused()
        for raw_json in (b'{"x":1,"x":2}', b'{"x":1e999}', b'{"x":NaN}'):
            with self.assertRaises(ValueError):
                matrix.document(raw_json)

    def test_retained_observation_does_not_fall_back_to_new_current_document(self):
        self.write_spec()
        retained = self.root / "copies/captured.md"
        retained.write_bytes(self.current.read_bytes())
        row = self.spec["local_documents"][0]
        row.update(path=str(retained), source_basis="retained_working_observation")
        self.current.write_text("new current source is deliberately not reread\n")
        self.manifest.write_bytes(matrix.json_bytes(self.spec))
        report = matrix.reconcile(self.manifest)
        self.assertEqual(report["criterion_source"]["local_document_basis"], "retained_working_observation")
        self.assertIs(report["criterion_source"]["current_live_document_freshness_qualified"], False)
        row["path"] = row["observed_path"]
        self.manifest.write_bytes(matrix.json_bytes(self.spec))
        with self.assertRaises(ValueError):
            matrix.reconcile(self.manifest)

    def test_retained_symlink_fifo_and_live_fallback_refused(self):
        target = self.spec["source_profiles"][0]["files"][0]
        original = target["retained_path"]
        link = self.root / "alias.py"
        link.symlink_to(self.retained)
        fifo = self.root / "pipe.py"
        os.mkfifo(fifo)
        for path in (link, fifo, self.repo / "pkg/source.py"):
            target["retained_path"] = str(path)
            self.refused()
        target["retained_path"] = original

    def test_duplicate_source_and_selected_size_bool_refused(self):
        files = self.spec["source_profiles"][0]["files"]
        files.append(copy.deepcopy(files[0]))
        self.refused()
        files.pop()
        files[0]["size_bytes"] = True
        self.refused()

    def test_git_body_byte_ceiling_precedes_body_allocation(self):
        (self.repo / "pkg/large.py").write_bytes(b"x" * 2048)
        self.git("add", ".")
        self.git("commit", "-qm", "large")
        spec = {**self.spec["repositories"][0], "commit": self.git("rev-parse", "HEAD")}
        capture = matrix.Capture()
        objects = matrix.GitObjects(spec, capture)
        with patch.object(matrix, "MAX_FILE_BYTES", 1024), patch.object(objects, "command", wraps=objects.command) as calls:
            observed, raw = objects.blob("pkg/large.py")
        self.assertIsNone(raw)
        self.assertEqual(observed["disposition"], "unread_byte_limit")
        self.assertFalse(any(call.args[0][:2] == ["cat-file", "blob"] for call in calls.call_args_list))

    def test_input_drift_refused(self):
        original = matrix.Capture.stability
        def mutate(capture):
            self.retained.write_bytes(b"changed")
            return original(capture)
        with patch.object(matrix.Capture, "stability", mutate):
            self.refused()

    def test_cli_fresh_output_and_refusal_receipt(self):
        self.write_spec()
        output = self.root / "output"
        self.assertEqual(matrix.main(["--manifest", str(self.manifest), "--output", str(output)]), 0)
        report = matrix.document((output / "release_matrix.json").read_bytes())
        self.assertEqual(report["manifest_sha256"], matrix.sha(self.manifest.read_bytes()))
        self.assertEqual(matrix.main(["--manifest", str(self.manifest), "--output", str(output)]), 2)
        self.spec["ledger"]["sha256"] = "d" * 64
        self.write_spec()
        refused = self.root / "refused"
        self.assertEqual(matrix.main(["--manifest", str(self.manifest), "--output", str(refused)]), 2)
        self.assertEqual(matrix.document((refused / "release_matrix.json").read_bytes())["status"], "refused")

    def test_output_preflight_never_mutates_input_scopes(self):
        self.write_spec()
        for parent in (self.repo, self.current.parent, self.retained.parent):
            output = parent / "forbidden-output"
            self.assertEqual(matrix.main(["--manifest", str(self.manifest), "--output", str(output)]), 2)
            self.assertFalse(output.exists())

    def make_snapshot(self):
        root = self.root / "snapshot"
        source = root / "repo/pkg/source.py"
        source.parent.mkdir(parents=True)
        source.write_bytes(self.source)
        body = {"schema": "codebase-ir-runtime-demand/v1", "generation": 0,
                "parent_snapshot_sha256": None,
                "files": [{"repository": "repo", "path": "pkg/source.py", "sha256": matrix.sha(self.source), "bytes": len(self.source)}],
                "namespace_directories": []}
        digest = matrix.sha(matrix.json_bytes(body))
        (root / "snapshot.json").write_bytes(matrix.json_bytes({**body, "snapshot_sha256": digest}))
        for path in root.rglob("*"):
            path.chmod(0o555 if path.is_dir() else 0o444)
        root.chmod(0o555)
        def unseal():
            for path in [root, *root.rglob("*")]:
                path.chmod(0o755 if path.is_dir() else 0o644)
        self.addCleanup(unseal)
        self.spec["snapshot"] = {"root": str(root), "sha256": digest}
        self.spec["source_profiles"] = []
        return root, source

    def test_snapshot_exact_generation_and_files_bound_before_after(self):
        root, _source = self.make_snapshot()
        result = self.run_matrix()
        self.assertEqual(result["snapshot_before"], result["snapshot_after"])
        self.assertEqual(result["snapshot_before"]["snapshot_sha256"], self.spec["snapshot"]["sha256"])
        self.assertEqual(result["source_dispositions"], {"identical": 1})
        self.write_spec()
        denied = root / "output"
        self.assertEqual(matrix.main(["--manifest", str(self.manifest), "--output", str(denied)]), 2)
        self.assertFalse(denied.exists())

    def test_snapshot_byte_pin_and_unlisted_files_refused(self):
        root, source = self.make_snapshot()
        source.chmod(0o644)
        source.write_bytes(b"different source")
        source.chmod(0o444)
        self.refused()
        source.chmod(0o644)
        source.write_bytes(self.source)
        source.chmod(0o444)
        root.chmod(0o755)
        extra = root / "unlisted.json"
        extra.write_text("{}")
        extra.chmod(0o444)
        root.chmod(0o555)
        self.refused()

    def test_snapshot_postcapture_drift_refused(self):
        _root, source = self.make_snapshot()
        original = matrix.Capture.stability
        def mutate(capture):
            source.chmod(0o644)
            source.write_bytes(b"later drift")
            source.chmod(0o444)
            return original(capture)
        with patch.object(matrix.Capture, "stability", mutate):
            self.refused()


if __name__ == "__main__":
    unittest.main()

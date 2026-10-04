"""Independent corruption controls for retained worker joins and bounded Git reads."""
from __future__ import annotations

import copy
import hashlib
import json
import os
import tempfile
import unittest
import zlib
from pathlib import Path
from unittest.mock import patch

import codebase_ir_worker_evidence as worker
import codebase_ir_worker_git as git


class WorkerPopulationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        value = json.loads(Path(__file__).with_name("worker_regression_reference.json").read_bytes())
        if value["authority"] != "assertion_reference_only":
            raise AssertionError("public regression copies cannot grant worker authority")
        cls.reference = value["records"]

    def setUp(self):
        self.records = copy.deepcopy(self.reference)

    def sync_lifecycle(self):
        result = self.records["result.json"]
        for key in ("start", "stop", "task", "observed_worker_allocations"):
            self.records["native-lifecycle.json"][key] = copy.deepcopy(result[key])
        result["execution_scope_after_stop"] = copy.deepcopy(self.records["execution-scope.json"])

    def test_genuine_complete_population_and_exact_merge(self):
        result = worker.assert_worker(self.records)
        self.assertEqual(result["preserved_task_population"]["task_keys"], ["FINITE-OFFSET", "FINITE-TYPE"])
        self.assertEqual(set(result["preserved_task_population"]["historical_completed_statuses"].values()), {"completed"})
        self.assertEqual(result["git_publication"]["changed_paths"], ["calc.py"])
        self.assertEqual(result["historical_parent_artifact_count"], 77)

    def test_all_correlated_controls_refuse_without_signature_authority(self):
        controls = worker.worker_controls(self.records)
        self.assertEqual(len(controls), 28)
        self.assertEqual({row["mutation_id"] for row in controls}, set(worker.WORKER_CONTROLS))
        self.assertTrue(all(row["outcome"] == "refused" for row in controls))

    def test_status_alone_cannot_replace_prerequisite_completion_row(self):
        self.records["execution-scope.json"]["payload"]["native_population"]["completion_rows"] = {}
        self.sync_lifecycle()
        with self.assertRaisesRegex(worker.AdmissionEvidenceError, "completion row"):
            worker.assert_worker(self.records)

    def test_exact_worker_uid_cannot_be_relabelled_as_owner(self):
        self.records["result.json"]["stop"]["data"]["isolated_worker_cleanup"]["worker_uid"] = 1000
        self.sync_lifecycle()
        with self.assertRaisesRegex(worker.AdmissionEvidenceError, "UID cleanup"):
            worker.assert_worker(self.records)

    def test_boolean_process_identity_cannot_pass_integer_equality(self):
        result = self.records["result.json"]
        result["start"]["data"]["new_process_identity"]["pid"] = True
        result["observed_worker_allocations"][0]["owner"]["parent_pid"] = True
        self.records["owner-fixture-worktree-cleanup.json"][0]["allocation"] = copy.deepcopy(result["observed_worker_allocations"][0])
        self.sync_lifecycle()
        with self.assertRaisesRegex(worker.AdmissionEvidenceError, "process identity"):
            worker.assert_worker(self.records)

    def test_foreign_module_cannot_retain_same_launch_task_flags(self):
        self.records["result.json"]["start"]["data"]["new_process_identity"]["argv"][3] = "foreign.launcher"
        self.sync_lifecycle()
        with self.assertRaisesRegex(worker.AdmissionEvidenceError, "installed launch"):
            worker.assert_worker(self.records)

    def test_rehashed_foreign_canonical_task_refuses_actual_portal_alias_anchor(self):
        result = self.records["result.json"]
        foreign = worker.cid({"foreign": "canonical task"})
        def replace(row):
            if "canonical_task_cid" in row:
                row["canonical_task_cid"] = foreign
        worker.mutate_tree(result["task"], replace)
        worker.mutate_tree(result["observed_worker_allocations"], replace)
        worker.mutate_tree(self.records["owner-fixture-worktree-cleanup.json"], replace)
        def rehash(row):
            if row.get("schema") == "ipfs_accelerate_py/agent-supervisor/accepted-source-transition@1":
                row["transition_cid"] = "sha256:" + hashlib.sha256(worker.canonical({k: v for k, v in row.items() if k != "transition_cid"})).hexdigest()
        worker.mutate_tree(result["task"], rehash)
        self.sync_lifecycle()
        with self.assertRaisesRegex(worker.AdmissionEvidenceError, "portal alias population"):
            worker.assert_worker(self.records)

    def test_transition_digest_cannot_be_changed_in_both_validation_views(self):
        def replace(row):
            if row.get("schema") == "ipfs_accelerate_py/agent-supervisor/accepted-source-transition@1":
                row["transition_cid"] = "sha256:" + "0" * 64
        worker.mutate_tree(self.records["result.json"]["task"], replace)
        self.sync_lifecycle()
        with self.assertRaisesRegex(worker.AdmissionEvidenceError, "transition content identity"):
            worker.assert_worker(self.records)

    def test_original_parent_population_cannot_be_substituted_at_same_count(self):
        row = self.records["historical-parent-artifact-pins.json"][0]
        old = row["path"]
        row["path"] = "/results/native/cas/source/bafk/foreign"
        self.records["verified_parent_pins"][row["path"]] = self.records["verified_parent_pins"].pop(old)
        with self.assertRaisesRegex(worker.AdmissionEvidenceError, "77-parent-artifact"):
            worker.assert_worker(self.records)

    def test_no_work_successor_cannot_erase_original_completed_population(self):
        replay = self.records["fresh-process-replay.json"]
        replay["task_statuses"].pop("FINITE-TYPE")
        self.records["result.json"]["fresh_process_historical_replay"] = copy.deepcopy(replay)
        with self.assertRaisesRegex(worker.AdmissionEvidenceError, "completed population"):
            worker.assert_worker(self.records)

    def test_selected_source_change_cannot_keep_old_signed_producer_hashes(self):
        module = "ipfs_accelerate_py.agent_supervisor.runtime.finite_repository_admission"
        self.records["verified_execution_sources"][module]["sha256"] = "a" * 64
        self.records["execution-scope.json"]["payload"]["implementation"][module] = "a" * 64
        next(row for row in self.records["result.json"]["execution_sources"] if row["path"].endswith("/finite_repository_admission.py"))["sha256"] = "a" * 64
        self.sync_lifecycle()
        with self.assertRaisesRegex(worker.AdmissionEvidenceError, "signed admission implementation"):
            worker.assert_worker(self.records)


class WorkerReadBoundTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name) / "native"
        self.root.mkdir()
        self.reader = worker.WorkerReader(self.root)
        self.path = self.root / "result.json"

    def test_only_exact_original_root_and_one_handoff_remap(self):
        self.assertEqual(self.reader.path("/results/native/result.json"), self.path)
        self.assertEqual(self.reader.path(worker.ORIGINAL_CANDIDATE), self.root.parent / "handoffs/candidate.json")
        for path in ("/results/native/../private/profile.key", "/results/native//result.json", "/foreign/result.json", "result.json"):
            with self.subTest(path=path), self.assertRaises(ValueError):
                self.reader.path(path)

    def test_task_database_key_and_global_private_state_are_never_read(self):
        for relative in ("private/intent.duckdb", "private/profile/local_dev_profile.key", "private/owner/typed-state-owner.token"):
            with self.subTest(relative=relative), patch.object(worker, "_bounded_document") as read:
                with self.assertRaisesRegex(ValueError, "private-state"):
                    self.reader.read(self.root / relative)
                read.assert_not_called()

    def test_count_and_aggregate_caps_apply_before_read_allocation(self):
        self.path.write_bytes(b'{}')
        with patch.object(worker, "MAX_FILES", 0), patch.object(worker, "_bounded_document") as read:
            with self.assertRaisesRegex(ValueError, "count cap"):
                self.reader.read(self.path)
            read.assert_not_called()
        with patch.object(worker, "MAX_TOTAL_BYTES", 1):
            with self.assertRaises(ValueError):
                self.reader.read(self.path)
        self.assertEqual(self.reader.pins, {})

    def test_alias_fifo_and_between_read_drift_refused(self):
        actual = self.root / "before-admission.json"
        actual.write_bytes(b'{}')
        self.path.symlink_to(actual)
        with self.assertRaises(ValueError):
            self.reader.read(self.path)
        self.path.unlink()
        os.mkfifo(self.path)
        with self.assertRaises(ValueError):
            self.reader.read(self.path)
        self.path.unlink()
        self.path.write_bytes(b'{}')
        self.reader.read(self.path)
        self.path.write_bytes(b'[]')
        with self.assertRaisesRegex(ValueError, "changed"):
            self.reader.recheck()

    def test_incomplete_fixture_reports_refusal_without_native_authority(self):
        self.path.write_bytes(b'{"schema":"foreign"}')
        output = self.root.parent / "audit"
        report = worker.run(self.root, output)
        self.assertEqual(report["status"], "refused")
        self.assertFalse(report["worker_execution_during_audit"])
        self.assertFalse(report["current_launch_permission_claimed"])
        self.assertFalse(report["signature_authentication_performed_by_structural_audit"])
        self.assertFalse(report["historical_native_worker_observed"])
        self.assertEqual(report["production_tasks_closed"], [])


class GitLooseObjectTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name) / "native"
        self.root.mkdir()
        self.repository = self.root / "repository"
        self.reader = worker.WorkerReader(self.root)

    def write_object(self, kind, body):
        raw = kind.encode() + b" " + str(len(body)).encode() + b"\0" + body
        oid = hashlib.sha1(raw).hexdigest()
        path = self.repository / ".git/objects" / oid[:2] / oid[2:]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(zlib.compress(raw))
        return oid, path

    def write_tree(self, entries):
        body = b"".join(mode.encode() + b" " + name.encode() + b"\0" + bytes.fromhex(oid) for mode, name, oid in entries)
        return self.write_object("tree", body)[0]

    def fixture(self, *, after_mode="100644"):
        before, _ = self.write_object("blob", b"before\n")
        after, _ = self.write_object("blob", b"after\n")
        helper, _ = self.write_object("blob", b"helper\n")
        old_tree = self.write_tree([("100644", "calc.py", before), ("100644", "support.py", helper)])
        new_tree = self.write_tree([(after_mode, "calc.py", after), ("100644", "support.py", helper)])
        original, _ = self.write_object("commit", ("tree " + old_tree + "\n\noriginal\n").encode())
        implementation, _ = self.write_object("commit", ("tree " + new_tree + "\nparent " + original + "\n\nimplementation\n").encode())
        published, _ = self.write_object("commit", ("tree " + new_tree + "\nparent " + original + "\nparent " + implementation + "\n\nmerge\n").encode())
        result = {"original_commit": original, "published_commit": published, "published_commit_parents": [original, implementation], "changed_paths": ["calc.py"]}
        sources = {name: {"sha256": hashlib.sha256(raw).hexdigest(), "executable": False} for name, raw in (("calc.py", b"before\n"), ("support.py", b"helper\n"))}
        candidate = {"finite_admission": {"declaration": {"payload": {"manifest": {"payload": {"sources": sources}}}}},
            "edit": {"before_sha256": sources["calc.py"]["sha256"], "after_sha256": hashlib.sha256(b"after\n").hexdigest()}}
        return result, candidate

    def test_complete_loose_object_publication_verified_without_git_process(self):
        result, candidate = self.fixture()
        actual = git.verify_publication(self.repository, self.reader, result, candidate)
        self.assertTrue(actual["git_object_verification_performed"])
        self.assertEqual(actual["changed_paths"], ["calc.py"])
        self.assertEqual(actual["published_commit_parents"], result["published_commit_parents"])

    def test_calc_executable_mode_change_is_not_an_authorized_byte_edit(self):
        result, candidate = self.fixture(after_mode="100755")
        with self.assertRaisesRegex(ValueError, "source bytes/mode"):
            git.verify_publication(self.repository, self.reader, result, candidate)

    def test_reordered_merge_parent_population_refused(self):
        result, candidate = self.fixture()
        result["published_commit_parents"].reverse()
        with self.assertRaisesRegex(ValueError, "two-parent baseline"):
            git.verify_publication(self.repository, self.reader, result, candidate)

    def test_malformed_trailing_and_changed_object_compression_refused(self):
        for compressed in (b"not-zlib", zlib.compress(b"blob 2\0ok") + b"trailing", zlib.compress(b"blob 2\0no")):
            with self.subTest(compressed=compressed[:10]):
                oid, path = self.write_object("blob", b"ok")
                path.write_bytes(compressed)
                with self.assertRaises(ValueError):
                    git.LooseGit(self.repository, worker.WorkerReader(self.root)).object(oid, "blob")

    def test_expansion_byte_limit_before_unbounded_decompression(self):
        oid, _ = self.write_object("blob", b"a" * 10000)
        with patch.object(git, "MAX_OBJECT_BYTES", 32), self.assertRaisesRegex(ValueError, "bounded single Git"):
            git.LooseGit(self.repository, self.reader).object(oid, "blob")

    def test_repeated_empty_subtree_dag_has_global_work_budget(self):
        child = self.write_tree([])
        for _ in range(4):
            child = self.write_tree([("40000", "directory" + str(index), child) for index in range(16)])
        selected = git.LooseGit(self.repository, self.reader)
        with self.assertRaisesRegex(ValueError, "expanded tree.*cap"):
            selected.tree(child)
        self.assertLessEqual(len(selected.objects), 5)

    def test_symlink_tree_and_missing_loose_objects_have_no_fallback(self):
        child, _ = self.write_object("blob", b"/foreign")
        tree = self.write_tree([("120000", "calc.py", child)])
        with self.assertRaisesRegex(ValueError, "symlink/submodule"):
            git.LooseGit(self.repository, self.reader).tree(tree)
        with self.assertRaises(FileNotFoundError):
            git.LooseGit(self.repository, self.reader).object("0" * 40, "commit")


if __name__ == "__main__":
    unittest.main()

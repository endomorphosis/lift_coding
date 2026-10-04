from __future__ import annotations

import copy
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import evidence_children as children
import release_matrix as matrix
import test_release_matrix as fixtures


class ReleasedEvidenceChildrenTests(unittest.TestCase):
    def setUp(self):
        self.factory = fixtures.ReleaseMatrixTests("runTest")
        self.factory.setUp()
        self.root, self.repo = self.factory.root, self.factory.repo
        self.addCleanup(self.cleanup)
        (self.root / "inputs").mkdir()
        self.manifest = self.root / "inputs/manifest.json"
        self.sequence = 0
        self.body = b"raise RuntimeError('public payload must remain inert')\n"
        (self.repo / "docs/public").mkdir()
        (self.repo / "docs/public/body.py").write_bytes(self.body)
        self.child_manifest = {"schema": "repository-evidence-files@1", "files": [self.pin("public/body.py", self.body)]}
        self.selected = ["example"]
        self.spec = {}
        self.commit()

    def cleanup(self):
        for path in self.root.rglob("*"):
            if not path.is_symlink():
                path.chmod(0o755 if path.is_dir() else 0o644)
        self.factory.doCleanups()

    @staticmethod
    def pin(path, raw):
        return {"path": path, "sha256": matrix.sha(raw), "bytes": len(raw)}

    def commit(self):
        raw = matrix.json_bytes(self.child_manifest)
        (self.repo / "docs/evidence.json").write_bytes(raw)
        self.factory.ledger["evidence"]["example"]["sha256"] = matrix.sha(raw)
        self.factory.commit()
        self.spec = {"schema": children.INPUT_SCHEMA, "repositories": self.factory.spec["repositories"],
                     "ledger": self.factory.spec["ledger"], "selected_evidence": self.selected,
                     "expansion_policy": children.POLICY}
        self.write_spec()

    def write_spec(self):
        self.manifest.write_bytes(matrix.json_bytes(self.spec))

    def run_audit(self):
        self.sequence += 1
        return children.audit(self.manifest, self.root / f"result-{self.sequence}")

    def second_manifest(self, value=None):
        value = copy.deepcopy(self.child_manifest) if value is None else value
        raw = matrix.json_bytes(value)
        (self.repo / "docs/second.json").write_bytes(raw)
        self.factory.ledger["evidence"]["second"] = {"path": "docs/second.json", "sha256": matrix.sha(raw),
                                                     "retention": "repository_evidence"}
        self.selected.append("second")

    def test_retained_bytes_stable_inert_and_never_promoted(self):
        report = self.run_audit()
        self.assertTrue(report["all_selected_children_verified"])
        self.assertEqual(report["verified_child_count"], 1)
        self.assertEqual(report["unique_child_body_count"], 1)
        self.assertTrue(report["git_input_stability"]["unchanged"])
        self.assertTrue(report["git_object_verification_performed"])
        self.assertTrue(all(report[key] is False for key in children.FALSE_FLAGS))
        row = report["manifests"][0]["children"][0]
        path = Path(row["retained_copy"]["path"])
        self.assertEqual(path.read_bytes(), self.body)
        self.assertEqual(path.stat().st_mode & 0o777, 0o444)
        self.assertEqual(path.parent.stat().st_mode & 0o777, 0o555)

    def test_missing_and_changed_are_diagnostics_without_working_fallback(self):
        self.child_manifest["files"] += [self.pin("absent.json", b"missing")]
        self.child_manifest["files"][0]["sha256"] = "f" * 64
        self.commit()
        (self.repo / "docs/absent.json").write_bytes(b"missing")
        report = self.run_audit()
        self.assertEqual(report["child_dispositions"], {"different": 1, "missing": 1})
        self.assertFalse(report["all_selected_children_verified"])
        self.assertEqual(report["status"], "passed")

    def test_duplicate_inside_parent_is_preserved_and_cannot_inflate_verified_count(self):
        self.child_manifest["files"].append(copy.deepcopy(self.child_manifest["files"][0]))
        self.commit()
        report = self.run_audit()
        self.assertEqual(report["declared_child_count"], 2)
        self.assertEqual(report["verified_child_count"], 1)
        self.assertEqual(report["child_dispositions"], {"verified": 1, "repeated_entry": 1})
        self.assertFalse(report["all_selected_children_verified"])

    def test_shared_body_preserves_both_memberships_and_one_retained_copy(self):
        self.second_manifest()
        self.commit()
        report = self.run_audit()
        self.assertEqual(report["verified_child_count"], 2)
        self.assertEqual(report["unique_child_body_count"], 1)
        self.assertTrue(report["all_selected_children_verified"])
        self.assertEqual([r["children"][0]["shared_body"] for r in report["manifests"]], [False, True])
        self.assertEqual(report["manifests"][0]["children"][0]["retained_copy"],
                         report["manifests"][1]["children"][0]["retained_copy"])

    def test_conflicting_shared_pin_does_not_change_another_parent_claim(self):
        other = copy.deepcopy(self.child_manifest)
        other["files"][0]["sha256"] = "e" * 64
        self.second_manifest(other)
        self.commit()
        report = self.run_audit()
        self.assertEqual(report["child_dispositions"], {"verified": 1, "different": 1})
        self.assertFalse(report["all_selected_children_verified"])

    def test_selected_manifest_reference_cycle_is_explicit_without_recursive_walk(self):
        self.child_manifest["files"] = [self.pin("second.json", b"claim")]
        self.second_manifest({"schema": "repository-evidence-files@1", "files": [self.pin("evidence.json", b"claim")]})
        self.commit()
        report = self.run_audit()
        self.assertEqual(report["child_dispositions"], {"cyclic_manifest_reference": 2})
        self.assertFalse(report["transitive_child_expansion_performed"])
        self.assertEqual(report["unique_child_body_count"], 0)

    def test_unknown_parent_schema_is_explicit_and_child_json_is_inert(self):
        self.second_manifest({"schema": "future-unreviewed@1", "files": [{"path": "../../secret"}]})
        inert = matrix.json_bytes({"schema": "repository-evidence-files@1", "files": [{"path": "../../secret"}]})
        (self.repo / "docs/public/inert.json").write_bytes(inert)
        self.child_manifest["files"].append(self.pin("public/inert.json", inert))
        self.commit()
        report = self.run_audit()
        self.assertEqual(report["manifest_dispositions"], {"expanded": 1, "unsupported_schema": 1})
        self.assertEqual(report["verified_child_count"], 2)
        self.assertFalse(report["all_selected_children_verified"])
        self.assertIsNone(report["manifests"][1]["children"] or None)

    def test_four_explicit_schema_profiles_have_exact_size_fields(self):
        for schema, field in children.SUPPORTED.items():
            row = {"path": "x.json", "sha256": "a" * 64, field: 12}
            _, pins = children.explicit_files(matrix.json_bytes({"schema": schema, "files": [row]}))
            self.assertEqual(pins[0]["bytes"], 12)
            row["extra"] = True
            with self.assertRaises(ValueError):
                children.explicit_files(matrix.json_bytes({"schema": schema, "files": [row]}))

    def test_correlated_child_body_and_manifest_rehash_remain_bound_to_original_commit(self):
        commit = self.spec["repositories"][0]["commit"]
        changed = b"forged numerical success\n"
        (self.repo / "docs/public/body.py").write_bytes(changed)
        self.child_manifest["files"] = [self.pin("public/body.py", changed)]
        self.commit()
        self.spec["repositories"][0]["commit"] = commit
        self.write_spec()
        with self.assertRaises(ValueError):
            self.run_audit()

    def test_path_traversal_platform_alias_and_private_paths_refused_before_reads(self):
        for path in ("../escape", "/absolute", "public/../body.py", "state/owner.json", "workspace/x",
                     "public\\body.py", "public/C:secret", "public/x\n"):
            value = {"schema": "repository-evidence-files@1", "files": [self.pin(path, self.body)]}
            with self.assertRaises(ValueError):
                children.explicit_files(matrix.json_bytes(value))

    def test_bool_size_duplicate_json_and_nonfinite_values_refused(self):
        self.child_manifest["files"][0]["bytes"] = True
        with self.assertRaises(ValueError):
            children.explicit_files(matrix.json_bytes(self.child_manifest))
        for raw in (b'{"schema":"repository-evidence-files@1","files":[],"files":[]}',
                    b'{"schema":"repository-evidence-files@1","files":[],"x":NaN}',
                    b'{"schema":"repository-evidence-files@1","files":[],"x":1e999}'):
            with self.assertRaises(ValueError):
                children.explicit_files(raw)

    def test_aggregate_bounds_are_enforced_before_any_child_blob_read(self):
        self.child_manifest["files"] *= 2
        self.second_manifest()
        self.commit()
        original = matrix.GitObjects.blob
        def guarded(repo, path):
            if path.endswith("body.py"):
                raise AssertionError("child body allocated before population ceiling")
            return original(repo, path)
        with patch.object(children, "MAX_CHILDREN", 3), patch.object(matrix.GitObjects, "blob", guarded), self.assertRaises(ValueError):
            self.run_audit()
        with patch.object(children, "MAX_DECLARED_BYTES", 1), patch.object(matrix.GitObjects, "blob", guarded), self.assertRaises(ValueError):
            self.run_audit()

    def test_input_manifest_size_ceiling_precedes_json_read(self):
        with patch.object(children, "MAX_MANIFEST_BYTES", 10), self.assertRaises(ValueError):
            self.run_audit()
        self.assertFalse((self.root / "result-1").exists())

    def test_output_input_existing_alias_and_seal_refusals_precede_writes(self):
        for output in (self.repo / "out", self.manifest.parent / "out", self.root):
            with self.assertRaises(ValueError):
                children.audit(self.manifest, output)
        alias = self.root / "alias"
        alias.symlink_to(self.manifest.parent, target_is_directory=True)
        with self.assertRaises(ValueError):
            children.audit(self.manifest, alias / "out")
        sealed = self.root / "sealed"
        sealed.mkdir()
        sealed.chmod(0o555)
        with self.assertRaises(ValueError):
            children.audit(self.manifest, sealed / "out")

    def test_wrong_ledger_pin_unknown_selection_mutable_commit_and_extra_fields_refused(self):
        original = copy.deepcopy(self.spec)
        for mutate in (lambda: self.spec["ledger"].__setitem__("sha256", "a" * 64),
                       lambda: self.spec.__setitem__("selected_evidence", ["absent"]),
                       lambda: self.spec["repositories"][0].__setitem__("commit", "HEAD"),
                       lambda: self.spec.__setitem__("current_authority_claimed", True)):
            mutate()
            self.write_spec()
            with self.assertRaises(ValueError):
                self.run_audit()
            self.spec = copy.deepcopy(original)

    def test_original_input_drift_after_retention_refuses_publication(self):
        original = children.git_stability
        def changed(*args):
            self.manifest.write_bytes(self.manifest.read_bytes() + b" ")
            return original(*args)
        with patch.object(children, "git_stability", changed), self.assertRaises(ValueError):
            self.run_audit()
        self.assertFalse((self.root / "result-1/evidence_children.json").exists())

    def test_late_retained_corruption_repaired_hash_is_not_a_new_input_pin(self):
        original = children.git_stability
        def changed(*args):
            path = next((self.root / "result-1/children").rglob("body.py"))
            path.chmod(0o644)
            path.write_bytes(b"X" * len(self.body))
            path.chmod(0o444)
            return original(*args)
        with patch.object(children, "git_stability", changed), self.assertRaises(ValueError):
            self.run_audit()

    def test_late_retained_fifo_added_directory_and_permission_drift_refused(self):
        original = children.git_stability
        for kind in ("fifo", "directory", "permission"):
            output = self.root / f"result-{self.sequence + 1}"
            def changed(*args, output=output, kind=kind):
                root = output / "children"
                root.chmod(0o755)
                if kind == "fifo":
                    os.mkfifo(root / "extra")
                elif kind == "directory":
                    (root / "extra").mkdir()
                else:
                    next(root.rglob("body.py")).chmod(0o644)
                root.chmod(0o555)
                return original(*args)
            with patch.object(children, "git_stability", changed), self.assertRaises(ValueError):
                self.run_audit()

    def test_late_git_corruption_requires_a_fresh_object_read(self):
        original = children.retained_view
        def changed(*args):
            result = original(*args)
            oid = self.factory.git("rev-parse", self.spec["repositories"][0]["commit"] + ":docs/public/body.py")
            path = self.repo / ".git/objects" / oid[:2] / oid[2:]
            path.chmod(0o644)
            path.write_bytes(b"invalid Git object")
            return result
        with patch.object(children, "retained_view", changed), self.assertRaises(ValueError):
            self.run_audit()

    def test_ambient_git_routing_and_later_head_do_not_change_selected_pin(self):
        (self.repo / "docs/public/body.py").write_bytes(b"later owner change\n")
        self.factory.git("add", ".")
        self.factory.git("commit", "-qm", "later")
        with patch.dict(os.environ, {"GIT_DIR": "/missing", "GIT_WORK_TREE": "/missing",
                                    "GIT_CONFIG_COUNT": "1", "GIT_CONFIG_KEY_0": "alias.cat-file",
                                    "GIT_CONFIG_VALUE_0": "!false"}):
            report = self.run_audit()
        self.assertTrue(report["all_selected_children_verified"])


if __name__ == "__main__":
    unittest.main()

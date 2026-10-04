from __future__ import annotations

import copy
import os
import shutil
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import portable_review as portable
import release_matrix as matrix
import test_release_matrix as fixtures


class PortableReviewTests(unittest.TestCase):
    def setUp(self):
        self.factory = fixtures.ReleaseMatrixTests("runTest")
        self.factory.setUp()
        self.addCleanup(self.factory.doCleanups)
        self.root = self.factory.root
        self.factory.write_spec()
        self.spec = self.factory.manifest
        self.report = self.root / "prior/report.json"
        self.report.parent.mkdir()
        self.previous = matrix.reconcile(self.spec)
        self.report.write_bytes(matrix.json_bytes(self.previous))
        self.sequence = 0

    def build(self):
        self.sequence += 1
        output = self.root / f"build-{self.sequence}"
        result = portable.build(self.spec, matrix.sha(self.spec.read_bytes()), self.report,
                                matrix.sha(self.report.read_bytes()), output)
        root = output / "bundle"
        self.addCleanup(self.unseal, root)
        return root, result["bundle_manifest_sha256"]

    @staticmethod
    def unseal(root):
        if root.exists():
            for path in [root, *root.rglob("*")]:
                if not path.is_symlink():
                    path.chmod(0o755 if path.is_dir() else 0o644)

    def changed_manifest(self, root, mutate):
        path = root / portable.MANIFEST_FILENAME
        value = matrix.document(path.read_bytes())
        mutate(value)
        path.chmod(0o644)
        path.write_bytes(matrix.json_bytes(value))
        path.chmod(0o444)
        return matrix.sha(path.read_bytes())

    def verify(self, root, identity):
        self.sequence += 1
        return portable.verify(root, identity, self.root / f"verify-{self.sequence}")

    def test_relocation_needs_neither_original_paths_nor_git(self):
        root, identity = self.build()
        moved = self.root / "relocated"
        shutil.copytree(root, moved)
        self.addCleanup(self.unseal, moved)
        shutil.rmtree(self.factory.repo)
        shutil.rmtree(self.factory.current.parent)
        shutil.rmtree(self.factory.retained.parent)
        self.spec.unlink()
        self.report.unlink()
        with patch.object(matrix.shutil, "which", side_effect=AssertionError("Git lookup forbidden")), patch.object(subprocess, "Popen", side_effect=AssertionError("process launch forbidden")):
            result = self.verify(moved, identity)
        self.assertEqual(result["source_dispositions"], {"identical": 1})
        self.assertEqual(result["evidence_dispositions"], {"identical": 1})
        self.assertTrue(result["input_files_unchanged"])
        self.assertFalse(result["original_paths_read"])
        self.assertFalse(result["git_executable_invoked"])
        self.assertTrue(all(result[x] is False for x in matrix.FALSE_FLAGS))

    def test_missing_and_different_stay_missing_and_different(self):
        source = self.factory.spec["source_profiles"][0]["files"][0]
        source["path"] = "pkg/missing.py"
        self.factory.write_spec()
        self.previous = matrix.reconcile(self.spec)
        self.report.write_bytes(matrix.json_bytes(self.previous))
        root, identity = self.build()
        self.assertEqual(self.verify(root, identity)["source_dispositions"], {"missing": 1})
        source["path"] = "pkg/source.py"
        self.factory.retained.write_bytes(b"historical differs\n")
        source.update(sha256=matrix.sha(self.factory.retained.read_bytes()), size_bytes=self.factory.retained.stat().st_size)
        self.factory.write_spec()
        self.report.write_bytes(matrix.json_bytes(matrix.reconcile(self.spec)))
        root, identity = self.build()
        self.assertEqual(self.verify(root, identity)["source_dispositions"], {"different": 1})

    def test_wrong_manifest_hash_authority_and_numeric_omissions_refused(self):
        root, identity = self.build()
        with self.assertRaises(ValueError):
            self.verify(root, "a" * 64)
        for key in matrix.FALSE_FLAGS:
            digest = self.changed_manifest(root, lambda value, key=key: value.__setitem__(key, True))
            with self.assertRaises(ValueError):
                self.verify(root, digest)
            self.changed_manifest(root, lambda value, key=key: value.__setitem__(key, False))
        digest = self.changed_manifest(root, lambda value: value["omissions"].__setitem__("runtime_environment", 1))
        with self.assertRaises(ValueError):
            self.verify(root, digest)

    def test_unlisted_files_fifo_symlink_and_directory_refused(self):
        for kind in ("file", "fifo", "symlink", "directory"):
            root, identity = self.build()
            root.chmod(0o755)
            path = root / "unselected"
            if kind == "file":
                path.write_bytes(b"unexpected")
            elif kind == "fifo":
                os.mkfifo(path)
            elif kind == "symlink":
                path.symlink_to(root / portable.MANIFEST_FILENAME)
            else:
                path.mkdir()
            if kind != "symlink":
                path.chmod(0o555 if kind == "directory" else 0o444)
            root.chmod(0o555)
            with self.assertRaises(ValueError):
                self.verify(root, identity)

    def test_corrupt_body_and_claimed_git_object_pin_cannot_pass(self):
        root, identity = self.build()
        bundle = matrix.document((root / portable.MANIFEST_FILENAME).read_bytes())
        row = next(row for row in bundle["objects"] if row["kind"] == "tree")
        body = root / row["path"]
        raw = body.read_bytes()
        body.chmod(0o644)
        body.write_bytes(raw[:-1] + bytes([raw[-1] ^ 1]))
        body.chmod(0o444)
        with self.assertRaises(ValueError):
            self.verify(root, identity)
        changed_sha = matrix.sha(body.read_bytes())
        def rebind(value):
            for item in [*value["objects"], *value["files"]]:
                if item["path"] == row["path"]:
                    item["sha256"] = changed_sha
        digest = self.changed_manifest(root, rebind)
        with self.assertRaises(ValueError):
            self.verify(root, digest)

    def test_population_bool_alias_and_unselected_object_refused(self):
        root, _identity = self.build()
        for mutate in (lambda value: value["objects"].append(copy.deepcopy(value["objects"][0])),
                       lambda value: value["local_documents"][0].__setitem__("size_bytes", True),
                       lambda value: value["directories"].append(value["directories"][0])):
            original = matrix.document((root / portable.MANIFEST_FILENAME).read_bytes())
            digest = self.changed_manifest(root, mutate)
            with self.assertRaises(ValueError):
                self.verify(root, digest)
            self.changed_manifest(root, lambda value, original=original: (value.clear(), value.update(original)))

    def test_output_refusal_happens_before_input_mutation(self):
        root, identity = self.build()
        for output in (root / "output", self.factory.repo / "output", self.factory.retained.parent / "output"):
            with self.assertRaises(ValueError):
                portable.verify(root, identity, output)
            self.assertFalse(output.exists())

    def test_bounds_precede_body_reads(self):
        root, identity = self.build()
        with patch.object(portable, "MAX_FILES", 1), self.assertRaises(ValueError):
            self.verify(root, identity)
        with patch.object(matrix, "MAX_TOTAL_BYTES", 100), self.assertRaises(ValueError):
            self.verify(root, identity)
        with patch.object(portable, "MAX_OBJECTS", 1), self.assertRaises(ValueError):
            self.verify(root, identity)
        with patch.object(portable, "MAX_BYTES", 100), self.assertRaises(ValueError):
            self.verify(root, identity)

    def test_prior_scope_or_hash_cannot_be_silently_changed(self):
        self.previous["criteria"][0]["criterion_changed"] = True
        self.report.write_bytes(matrix.json_bytes(self.previous))
        with self.assertRaises(ValueError):
            self.build()
        with self.assertRaises(ValueError):
            portable.build(self.spec, "a" * 64, self.report, matrix.sha(self.report.read_bytes()), self.root / "denied")

    def test_snapshot_old_source_identity_is_portable(self):
        _old, _source = self.factory.make_snapshot()
        self.factory.write_spec()
        self.report.write_bytes(matrix.json_bytes(matrix.reconcile(self.spec)))
        root, identity = self.build()
        result = self.verify(root, identity)
        self.assertEqual(result["source_dispositions"], {"identical": 1})

    def test_snapshot_manifest_race_cannot_publish_successful_build(self):
        snapshot, _source = self.factory.make_snapshot()
        self.factory.write_spec()
        self.report.write_bytes(matrix.json_bytes(matrix.reconcile(self.spec)))
        original = matrix.reconcile
        def change_after_reconcile(*args, **kwargs):
            result = original(*args, **kwargs)
            path = snapshot / "snapshot.json"
            path.chmod(0o644)
            path.write_bytes(path.read_bytes() + b" ")
            path.chmod(0o444)
            return result
        with patch.object(matrix, "reconcile", change_after_reconcile), self.assertRaises(ValueError):
            self.build()

    def test_late_directory_addition_or_permission_drift_refused(self):
        for operation in ("addition", "permission"):
            root, identity = self.build()
            original = portable.BundleReader.stability
            def mutate(reader, operation=operation, root=root, original=original):
                result = original(reader)
                if operation == "addition":
                    root.chmod(0o755)
                    path = root / "late-empty-directory"
                    path.mkdir()
                    path.chmod(0o555)
                    root.chmod(0o555)
                else:
                    (root / "repository_roots").chmod(0o755)
                return result
            with patch.object(portable.BundleReader, "stability", mutate), self.assertRaises(ValueError):
                self.verify(root, identity)


if __name__ == "__main__":
    unittest.main()

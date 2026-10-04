from __future__ import annotations

import copy
import hashlib
import os
import shutil
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import portable_archive as archive
import portable_evidence_children as capsule
import portable_review as portable
import release_matrix as matrix
import test_evidence_children as fixtures


class PortableEvidenceChildrenTests(unittest.TestCase):
    def setUp(self):
        self.factory = fixtures.ReleasedEvidenceChildrenTests("runTest")
        self.factory.setUp()
        self.addCleanup(self.factory.doCleanups)
        self.root = self.factory.root
        self.sequence = 0

    def next_path(self, name):
        self.sequence += 1
        return self.root / f"{name}-{self.sequence}"

    @staticmethod
    def pin(path):
        raw = path.read_bytes()
        return {"path": str(path), "sha256": matrix.sha(raw), "size_bytes": len(raw)}

    def build(self):
        self.factory.run_audit()
        report = self.root / f"result-{self.factory.sequence}/evidence_children.json"
        folder = self.next_path("build-input")
        folder.mkdir()
        manifest = folder / "manifest.json"
        manifest.write_bytes(matrix.json_bytes({"schema": capsule.BUILD_INPUT_SCHEMA,
            "source_manifest": self.pin(self.factory.manifest), "source_report": self.pin(report)}))
        output = self.next_path("build")
        result = capsule.build(manifest, output)
        return output, result

    def verify(self, build):
        output = self.next_path("verify")
        return capsule.verify(build / "archive_input.json", output), output

    def mutated(self, build, change):
        entries = archive.decode((build / "evidence_children.zip").read_bytes())
        value = matrix.document(entries[capsule.CAPSULE_FILENAME])
        change(value, entries)
        entries[capsule.CAPSULE_FILENAME] = matrix.json_bytes(value)
        folder = self.next_path("mutant-input")
        folder.mkdir()
        zip_path = folder / "evidence_children.zip"
        zip_path.write_bytes(archive.encode(entries))
        manifest = folder / "manifest.json"
        manifest.write_bytes(matrix.json_bytes({"schema": capsule.INPUT_SCHEMA, "archive": self.pin(zip_path),
            "capsule_manifest_sha256": matrix.sha(entries[capsule.CAPSULE_FILENAME])}))
        return manifest

    @staticmethod
    def replace(value, entries, path, raw):
        row = portable.pin(path, raw)
        entries[path] = raw
        for original in value["files"]:
            if original["path"] == path:
                original.update(row)
        for key in ("source_manifest", "source_report"):
            if value[key]["path"] == path:
                value[key].update(row)
        for key in ("objects", "retained_views", "implementation"):
            for original in value[key]:
                if original["path"] == path:
                    original.update(row)

    def refused(self, manifest):
        output = self.next_path("refused")
        with self.assertRaises((ValueError, OSError, KeyError, TypeError)):
            capsule.verify(manifest, output)
        self.assertFalse((output / "portable_evidence_children.json").exists())

    def test_roundtrip_retains_body_git_identity_and_scope(self):
        build, built = self.build()
        report, output = self.verify(build)
        self.assertFalse(built["archive_roundtrip_verified"])
        self.assertTrue(report["archive_roundtrip_verified"])
        self.assertTrue(report["all_selected_children_verified"])
        self.assertEqual(report["verified_child_count"], 1)
        self.assertTrue(all(report[key] is False for key in capsule.FALSE_FLAGS))
        body = next((output / "capsule/retained/children").rglob("body.py"))
        self.assertEqual(body.read_bytes(), self.factory.body)
        self.assertEqual(body.stat().st_mode & 0o777, 0o444)
        replay = matrix.document((output / "restored_verification/recomputed/evidence_children.json").read_bytes())
        self.assertFalse(replay["read_only_git_invoked"])
        self.assertEqual(replay["object_query_backend"], "offline_capsule")
        self.assertEqual(report["source_manifest_sha256"], matrix.sha(self.factory.manifest.read_bytes()))

    def test_same_qualified_inputs_produce_identical_archive(self):
        build, _ = self.build()
        source = next(self.root.glob("build-input-*/manifest.json"))
        other = self.next_path("build")
        capsule.build(source, other)
        self.assertEqual((build / "evidence_children.zip").read_bytes(), (other / "evidence_children.zip").read_bytes())

    def test_relocation_succeeds_after_original_paths_removed_without_git_or_subprocess(self):
        build, _ = self.build()
        relocated = self.next_path("relocated")
        relocated.mkdir()
        archive_path = relocated / "evidence_children.zip"
        shutil.copyfile(build / "evidence_children.zip", archive_path)
        spec = matrix.document((build / "archive_input.json").read_bytes())
        spec["archive"]["path"] = str(archive_path)
        manifest = relocated / "manifest.json"
        manifest.write_bytes(matrix.json_bytes(spec))
        shutil.rmtree(self.factory.repo)
        shutil.rmtree(self.factory.manifest.parent)
        report_folder = self.root / f"result-{self.factory.sequence}"
        report_folder.chmod(0o755)
        for path in report_folder.rglob("*"):
            if not path.is_symlink():
                path.chmod(0o755 if path.is_dir() else 0o644)
        shutil.rmtree(report_folder)
        with patch.object(subprocess, "Popen", side_effect=AssertionError("offline subprocess")), \
             patch.object(shutil, "which", side_effect=AssertionError("offline Git lookup")):
            result = capsule.verify(manifest, self.next_path("verified"))
        self.assertTrue(result["archive_roundtrip_verified"])

    def test_diagnostic_missing_different_repeated_and_unknown_are_preserved(self):
        row = self.factory.child_manifest["files"][0]
        row["sha256"] = "f" * 64
        self.factory.child_manifest["files"] += [copy.deepcopy(row), self.factory.pin("absent.json", b"missing")]
        self.factory.second_manifest({"schema": "future-unreviewed@1", "files": []})
        self.factory.commit()
        build, _ = self.build()
        report, _ = self.verify(build)
        self.assertEqual(report["child_dispositions"], {"different": 1, "repeated_entry": 1, "missing": 1})
        self.assertEqual(report["manifest_dispositions"], {"expanded": 1, "unsupported_schema": 1})
        self.assertFalse(report["all_selected_children_verified"])

    def test_shared_and_cyclic_memberships_are_preserved(self):
        self.factory.second_manifest()
        self.factory.commit()
        build, _ = self.build()
        report, output = self.verify(build)
        self.assertEqual(report["verified_child_count"], 2)
        self.assertEqual(report["unique_child_body_count"], 1)
        replay = matrix.document((output / "restored_verification/recomputed/evidence_children.json").read_bytes())
        self.assertEqual([r["children"][0]["shared_body"] for r in replay["manifests"]], [False, True])
        self.factory.child_manifest["files"] = [self.factory.pin("second.json", b"claim")]
        second = {"schema": "repository-evidence-files@1", "files": [self.factory.pin("evidence.json", b"claim")]}
        (self.factory.repo / "docs/second.json").write_bytes(matrix.json_bytes(second))
        self.factory.factory.ledger["evidence"]["second"]["sha256"] = matrix.sha(matrix.json_bytes(second))
        self.factory.commit()
        build, _ = self.build()
        report, _ = self.verify(build)
        self.assertEqual(report["child_dispositions"], {"cyclic_manifest_reference": 2})
        self.assertFalse(report["transitive_child_expansion_performed"])

    def test_repaired_archive_and_file_hashes_do_not_repair_git_object_identity(self):
        build, _ = self.build()
        for kind in ("blob", "tree", "commit"):
            def change(value, entries, kind=kind):
                row = next(row for row in value["objects"] if row["kind"] == kind)
                raw = entries[row["path"]]
                self.replace(value, entries, row["path"], b"X" + raw[1:])
            with self.subTest(kind=kind):
                self.refused(self.mutated(build, change))

    def test_forged_prior_decisions_with_repaired_outer_pins_are_refused(self):
        build, _ = self.build()
        for field, replacement in (("expected_sha256", "e" * 64), ("expected_size_bytes", 0),
                                   ("size_bytes", 0), ("sha256", "e" * 64), ("git_blob", "f" * 40),
                                   ("commit", "f" * 40), ("path", "docs/forged.py"),
                                   ("shared_body", True), ("disposition", "missing")):
            def change(value, entries, field=field, replacement=replacement):
                path = value["source_report"]["path"]
                report = matrix.document(entries[path])
                child = report["manifests"][0]["children"][0]
                child[field] = replacement
                self.replace(value, entries, path, matrix.json_bytes(report))
            with self.subTest(field=field):
                self.refused(self.mutated(build, change))

    def test_valid_but_unused_object_is_refused_and_missing_object_never_falls_back(self):
        build, _ = self.build()
        def extra(value, entries):
            raw = b"unselected owner state"
            oid = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
            path = "git_objects/repo/" + oid
            pin = portable.pin(path, raw)
            entries[path] = raw
            value["files"].append(pin)
            value["objects"].append({**pin, "repository": "repo", "oid": oid, "kind": "blob"})
        self.refused(self.mutated(build, extra))
        def missing(value, entries):
            row = value["objects"].pop(0)
            value["files"] = [r for r in value["files"] if r["path"] != row["path"]]
            del entries[row["path"]]
        with patch.object(subprocess, "Popen", side_effect=AssertionError("Git fallback")):
            self.refused(self.mutated(build, missing))

    def test_undeclared_file_directory_and_tool_population_are_refused(self):
        build, _ = self.build()
        for kind in ("file", "directory", "tool"):
            def change(value, entries, kind=kind):
                if kind == "file":
                    entries["unselected.txt"] = b"extra"
                elif kind == "directory":
                    entries["unselected/"] = b""
                    value["directories"].append("unselected")
                else:
                    row = value["implementation"].pop()
                    del entries[row["path"]]
                    value["files"] = [r for r in value["files"] if r["path"] != row["path"]]
            with self.subTest(kind=kind):
                self.refused(self.mutated(build, change))

    def test_capsule_bounds_and_authority_are_refused(self):
        build, _ = self.build()
        for change in (lambda v, e: v["files"][0].__setitem__("size_bytes", True),
                       lambda v, e: v.__setitem__("runtime_dependency_closure_qualified", True),
                       lambda v, e: v.__setitem__("extra", True)):
            self.refused(self.mutated(build, change))
        with patch.object(capsule, "MAX_OBJECTS", 1):
            self.refused(build / "archive_input.json")
        with patch.object(capsule, "MAX_CAPSULE_MANIFEST_BYTES", 1):
            self.refused(build / "archive_input.json")

    def test_output_aliases_sealed_ancestry_and_symlink_refused(self):
        build, _ = self.build()
        sealed = self.next_path("sealed")
        sealed.mkdir()
        sealed.chmod(0o555)
        alias = self.next_path("alias")
        alias.symlink_to(build, target_is_directory=True)
        for output in (build / "out", self.factory.repo / "out", self.factory.manifest.parent / "out", sealed / "out", alias / "out"):
            with self.subTest(output=output), self.assertRaises(ValueError):
                capsule.verify(build / "archive_input.json", output)

    def test_late_archive_stability_result_and_restored_body_change_refuse_publication(self):
        build, _ = self.build()
        original = archive.PinnedReader.stability
        count = 0
        def changed(reader):
            nonlocal count
            count += 1
            result = original(reader)
            if count == 3:
                result["unchanged"] = False
            return result
        with patch.object(archive.PinnedReader, "stability", changed):
            self.refused(build / "archive_input.json")
        original_seals = archive.exact_seals
        output = self.next_path("late-body")
        def corrupt(root, selected, directories, reader):
            result = original_seals(root, selected, directories, reader)
            if root == output / "capsule" and any(p.name == "portable_evidence_children.py" for p in reader.cache):
                target = root / "tools/portable_evidence_children.py"
                target.chmod(0o644)
                raw = target.read_bytes()
                target.write_bytes(b"X" + raw[1:])
                target.chmod(0o444)
            return result
        with patch.object(archive, "exact_seals", corrupt), self.assertRaises(ValueError):
            capsule.verify(build / "archive_input.json", output)
        self.assertFalse((output / "portable_evidence_children.json").exists())

    def test_build_rereads_written_archive_before_publishing(self):
        self.factory.run_audit()
        source = self.next_path("build-input")
        source.mkdir()
        manifest = source / "manifest.json"
        manifest.write_bytes(matrix.json_bytes({"schema": capsule.BUILD_INPUT_SCHEMA,
            "source_manifest": self.pin(self.factory.manifest),
            "source_report": self.pin(self.root / "result-1/evidence_children.json")}))
        output = self.next_path("short-archive")
        original = Path.chmod
        def corrupt(path, mode, **kwargs):
            if path == output / "evidence_children.zip":
                path.write_bytes(path.read_bytes()[:-1])
            return original(path, mode, **kwargs)
        with patch.object(Path, "chmod", corrupt), self.assertRaises(ValueError):
            capsule.build(manifest, output)
        self.assertFalse((output / "portable_evidence_children_build.json").exists())

    def test_object_count_ceiling_precedes_new_git_body_read(self):
        self.factory.run_audit()
        source = self.next_path("bounded-input")
        source.mkdir()
        manifest = source / "manifest.json"
        manifest.write_bytes(matrix.json_bytes({"schema": capsule.BUILD_INPUT_SCHEMA,
            "source_manifest": self.pin(self.factory.manifest),
            "source_report": self.pin(self.root / "result-1/evidence_children.json")}))
        original = matrix.GitObjects.command
        def guarded(repo, args, limit):
            if args[:2] == ["cat-file", "commit"]:
                raise AssertionError("body read before count refusal")
            return original(repo, args, limit)
        with patch.object(capsule, "MAX_OBJECTS", 0), patch.object(matrix.GitObjects, "command", guarded), self.assertRaises(ValueError):
            capsule.build(manifest, self.next_path("bounded-build"))

    def test_wrong_archive_pin_and_duplicate_json_refused_before_restore(self):
        build, _ = self.build()
        folder = self.next_path("closed-input")
        folder.mkdir()
        manifest = folder / "manifest.json"
        value = matrix.document((build / "archive_input.json").read_bytes())
        value["archive"]["sha256"] = "f" * 64
        manifest.write_bytes(matrix.json_bytes(value))
        self.refused(manifest)
        manifest.write_bytes(b'{"schema":"x","schema":"x"}')
        self.refused(manifest)
        manifest.write_bytes(b'{"schema":"x","value":NaN}')
        self.refused(manifest)

    def test_restored_fifo_and_permission_drift_refused(self):
        build, _ = self.build()
        for kind in ("fifo", "permission"):
            output = self.next_path("late-population")
            original = capsule.verify_capsule
            def changed(root, digest, review_output, original=original, kind=kind):
                result = original(root, digest, review_output)
                if kind == "fifo":
                    root.chmod(0o755)
                    os.mkfifo(root / "extra")
                    root.chmod(0o555)
                else:
                    (root / "tools/portable_evidence_children.py").chmod(0o644)
                return result
            with patch.object(capsule, "verify_capsule", changed), self.assertRaises(ValueError):
                capsule.verify(build / "archive_input.json", output)
            self.assertFalse((output / "portable_evidence_children.json").exists())


if __name__ == "__main__":
    unittest.main()

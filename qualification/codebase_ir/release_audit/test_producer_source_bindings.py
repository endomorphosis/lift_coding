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
import evidence_children as children
import portable_archive as archive
import portable_evidence_children as child_capsule
import portable_review as portable
import producer_source_bindings as bindings
import release_matrix as matrix
import test_evidence_children as fixtures


class ProducerSourceBindingsTests(unittest.TestCase):
    def setUp(self):
        self.factory = fixtures.ReleasedEvidenceChildrenTests("runTest")
        self.factory.setUp()
        self.addCleanup(self.factory.doCleanups)
        self.root, self.repo = self.factory.root, self.factory.repo
        self.sequence = 0
        self.source = self.factory.factory.source
        (self.repo / "pkg/other.py").write_bytes(b"raise RuntimeError('never import other source')\n")
        (self.repo / "pkg/extra.py").write_bytes(b"raise RuntimeError('never import extra source')\n")
        for name in ("admission", "supervision"):
            (self.repo / "docs" / name).mkdir()
        self.admission = {
            "schema": "repository-behavioral-admission-sources@1",
            "repository": "repo",
            "sources": [self.source_pin("pkg/source.py", True), self.source_pin("pkg/other.py", True)],
        }
        self.supervision = {
            "schema": "qualified-source-inventory@1",
            "files": [self.source_pin("pkg/source.py", False), self.source_pin("pkg/extra.py", False)],
        }

    def next_path(self, name):
        self.sequence += 1
        return self.root / f"{name}-{self.sequence}"

    def source_pin(self, path, sized):
        raw = (self.repo / path).read_bytes()
        result = {"path": path, "sha256": matrix.sha(raw)}
        if sized:
            result["size_bytes"] = len(raw)
        return result

    @staticmethod
    def pin(path):
        raw = path.read_bytes()
        return {"path": str(path), "sha256": matrix.sha(raw), "size_bytes": len(raw)}

    def prior(self):
        choices = []
        for name, eid, value in (
            ("admission", "behavioral-repository-admission", self.admission),
            ("supervision", "behavioral-native-supervision", self.supervision),
        ):
            raw = matrix.json_bytes(value)
            (self.repo / "docs" / name / "producer-sources.json").write_bytes(raw)
            header = matrix.json_bytes(
                {
                    "schema": "repository-evidence-files@1",
                    "files": [{"path": "producer-sources.json", "sha256": matrix.sha(raw), "bytes": len(raw)}],
                }
            )
            (self.repo / "docs" / name / "evidence.json").write_bytes(header)
            self.factory.factory.ledger["evidence"][eid] = {
                "path": f"docs/{name}/evidence.json",
                "sha256": matrix.sha(header),
                "retention": "repository_evidence",
            }
            choices.append(
                {
                    "evidence_id": eid,
                    "receipt_relative_path": "producer-sources.json",
                    "sha256": matrix.sha(raw),
                    "size_bytes": len(raw),
                }
            )
        self.factory.factory.commit()
        self.factory.spec = {
            "schema": children.INPUT_SCHEMA,
            "repositories": self.factory.factory.spec["repositories"],
            "ledger": self.factory.factory.spec["ledger"],
            "selected_evidence": [row["evidence_id"] for row in choices],
            "expansion_policy": children.POLICY,
        }
        self.factory.write_spec()
        self.factory.run_audit()
        report = self.root / f"result-{self.factory.sequence}/evidence_children.json"
        folder = self.next_path("prior-input")
        folder.mkdir()
        spec = folder / "manifest.json"
        spec.write_bytes(
            matrix.json_bytes(
                {
                    "schema": child_capsule.BUILD_INPUT_SCHEMA,
                    "source_manifest": self.pin(self.factory.manifest),
                    "source_report": self.pin(report),
                }
            )
        )
        output = self.next_path("prior-capsule")
        child_capsule.build(spec, output)
        return output, choices

    def build(self):
        prior, choices = self.prior()
        folder = self.next_path("source-input")
        folder.mkdir()
        manifest = folder / "manifest.json"
        manifest.write_bytes(
            matrix.json_bytes(
                {
                    "schema": bindings.BUILD_INPUT_SCHEMA,
                    "custody_capsule_manifest": self.pin(prior / "capsule/capsule_manifest.json"),
                    "selected_receipts": choices,
                }
            )
        )
        output = self.next_path("source-build")
        result = bindings.build(manifest, output)
        return output, result

    def verify(self, build):
        output = self.next_path("verified")
        return bindings.verify(build / "archive_input.json", output), output

    def mutant(self, build, change):
        entries = archive.decode((build / "producer_sources.zip").read_bytes())
        value = matrix.document(entries[bindings.CAPSULE_FILENAME])
        change(value, entries)
        entries[bindings.CAPSULE_FILENAME] = matrix.json_bytes(value)
        folder = self.next_path("mutant-input")
        folder.mkdir()
        zipped = folder / "producer_sources.zip"
        zipped.write_bytes(archive.encode(entries))
        manifest = folder / "manifest.json"
        manifest.write_bytes(
            matrix.json_bytes(
                {
                    "schema": bindings.INPUT_SCHEMA,
                    "archive": self.pin(zipped),
                    "capsule_manifest_sha256": matrix.sha(entries[bindings.CAPSULE_FILENAME]),
                    "custody_capsule_manifest_sha256": value["custody_capsule_manifest_sha256"],
                }
            )
        )
        return manifest

    def refused(self, manifest):
        output = self.next_path("refused")
        with self.assertRaises((ValueError, OSError, KeyError, TypeError)):
            bindings.verify(manifest, output)
        self.assertFalse((output / "producer_source_bindings.json").exists())

    @staticmethod
    def replace(value, entries, path, raw):
        pin = portable.pin(path, raw)
        entries[path] = raw
        for key in ("files", "objects", "source_files", "custody_files", "implementation"):
            for row in value[key]:
                if row["path"] == path:
                    row.update(pin)

    def test_roundtrip_preserves_shared_memberships_and_undeclared_sizes(self):
        built, before = self.build()
        report, output = self.verify(built)
        self.assertFalse(before["archive_roundtrip_verified"])
        self.assertTrue(report["archive_roundtrip_verified"])
        self.assertEqual(
            (report["claim_membership_count"], report["unique_source_path_count"], report["captured_source_count"]),
            (4, 3, 3),
        )
        self.assertEqual((report["declared_size_membership_count"], report["undeclared_size_membership_count"]), (2, 2))
        self.assertEqual(
            [row["size_check_disposition"] for row in report["source_memberships"]],
            ["matching", "matching", "undeclared", "undeclared"],
        )
        self.assertTrue(report["all_selected_sources_verified"])
        self.assertTrue(all(report[flag] is False for flag in bindings.FALSE_FLAGS))
        self.assertEqual(report["source_memberships"][2]["shared_source"], True)
        self.assertEqual((output / "capsule/sources/repo/pkg/source.py").read_bytes(), self.source)

    def test_missing_changed_and_wrong_declared_size_are_explicit_diagnostics(self):
        self.admission["sources"][0]["size_bytes"] += 1
        self.admission["sources"][1]["sha256"] = "f" * 64
        self.supervision["files"].append({"path": "pkg/absent.py", "sha256": matrix.sha(b"missing")})
        built, _ = self.build()
        (self.repo / "pkg/absent.py").write_bytes(b"missing")
        report, _ = self.verify(built)
        self.assertEqual(report["source_dispositions"], {"different": 2, "verified": 2, "missing": 1})
        self.assertFalse(report["all_selected_sources_verified"])
        self.assertEqual(report["source_memberships"][0]["sha_check_disposition"], "matching")
        self.assertEqual(report["source_memberships"][0]["size_check_disposition"], "different")

    def test_repeated_and_conflicting_shared_claims_cannot_inflate_verification(self):
        self.admission["sources"].append(copy.deepcopy(self.admission["sources"][0]))
        self.supervision["files"][0]["sha256"] = "f" * 64
        built, _ = self.build()
        report, _ = self.verify(built)
        self.assertEqual(report["source_dispositions"], {"verified": 3, "repeated_entry": 1, "different": 1})
        self.assertEqual(report["unique_source_path_count"], 3)
        self.assertFalse(report["all_selected_sources_verified"])

    def test_deterministic_archive_from_same_pinned_input(self):
        built, _ = self.build()
        manifest = next(self.root.glob("source-input-*/manifest.json"))
        other = self.next_path("second-build")
        bindings.build(manifest, other)
        self.assertEqual((built / "producer_sources.zip").read_bytes(), (other / "producer_sources.zip").read_bytes())

    def test_relocation_with_original_repository_and_capsule_unavailable(self):
        built, _ = self.build()
        relocated = self.next_path("relocated")
        relocated.mkdir()
        archive_path = relocated / "producer_sources.zip"
        shutil.copyfile(built / "producer_sources.zip", archive_path)
        value = matrix.document((built / "archive_input.json").read_bytes())
        value["archive"]["path"] = str(archive_path)
        manifest = relocated / "manifest.json"
        manifest.write_bytes(matrix.json_bytes(value))
        shutil.rmtree(self.repo)
        original = next(self.root.glob("prior-capsule-*/capsule"))
        original.chmod(0o755)
        for path in original.rglob("*"):
            path.chmod(0o755 if path.is_dir() else 0o644)
        shutil.rmtree(original)
        with (
            patch.object(subprocess, "Popen", side_effect=AssertionError("offline process")),
            patch.object(shutil, "which", side_effect=AssertionError("offline Git lookup")),
        ):
            result = bindings.verify(manifest, self.next_path("offline-output"))
        self.assertTrue(result["archive_roundtrip_verified"])

    def test_correlated_blob_tree_and_commit_rehashes_do_not_repair_git_identity(self):
        built, _ = self.build()
        for kind in ("blob", "tree", "commit"):

            def change(value, entries, kind=kind):
                row = next(row for row in value["objects"] if row["kind"] == kind)
                raw = entries[row["path"]]
                self.replace(value, entries, row["path"], b"X" + raw[1:])

            with self.subTest(kind=kind):
                self.refused(self.mutant(built, change))

    def test_selected_source_parent_and_receipt_forgery_with_repaired_outer_pins(self):
        built, _ = self.build()
        for target in ("source", "parent", "receipt"):

            def change(value, entries, target=target):
                review = value["expected_review"]
                oid = (
                    review["source_memberships"][0]["git_blob"]
                    if target == "source"
                    else review["receipts"][0][target]["git_blob"]
                )
                row = next(row for row in value["objects"] if row["oid"] == oid)
                raw = entries[row["path"]]
                self.replace(value, entries, row["path"], b"X" + raw[1:])

            with self.subTest(target=target):
                self.refused(self.mutant(built, change))

    def test_forged_expected_source_fields_with_repaired_container_hash_are_refused(self):
        built, _ = self.build()
        for field, changed in (
            ("expected_size_bytes", 0),
            ("expected_sha256", "f" * 64),
            ("git_blob", "f" * 40),
            ("shared_source", True),
            ("size_check_disposition", "undeclared"),
        ):

            def change(value, entries, field=field, changed=changed):
                value["expected_review"]["source_memberships"][0][field] = changed

            with self.subTest(field=field):
                self.refused(self.mutant(built, change))

    def test_unused_valid_git_object_missing_proof_and_extra_directory_refused(self):
        built, _ = self.build()

        def extra(value, entries):
            raw = b"unused source"
            oid = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
            path = "git_objects/repo/" + oid
            pin = portable.pin(path, raw)
            entries[path] = raw
            value["files"].append(pin)
            value["objects"].append({**pin, "repository": "repo", "oid": oid, "kind": "blob"})

        self.refused(self.mutant(built, extra))

        def missing(value, entries):
            row = value["objects"].pop(0)
            del entries[row["path"]]
            value["files"] = [r for r in value["files"] if r["path"] != row["path"]]

        self.refused(self.mutant(built, missing))

        def directory(value, entries):
            value["directories"].append("extra")
            entries["extra/"] = b""

        self.refused(self.mutant(built, directory))

    def test_original_custody_and_external_pin_cannot_be_substituted(self):
        built, _ = self.build()
        self.refused(
            self.mutant(built, lambda value, entries: value.__setitem__("custody_capsule_manifest_sha256", "f" * 64))
        )

        def changed(value, entries):
            row = next(
                row for row in value["custody_files"] if row["original_relative_path"].endswith("child_audit.json")
            )
            report = matrix.document(entries[row["path"]])
            report["manifests"][0]["children"][0]["git_blob"] = "f" * 40
            self.replace(value, entries, row["path"], matrix.json_bytes(report))

        self.refused(self.mutant(built, changed))

    def test_claim_schema_type_alias_and_population_refusals(self):
        value = copy.deepcopy(self.admission)
        for path in ("../escape", "state/owner.json", "pkg/x\\y", "pkg/C:secret", "/absolute"):
            value["sources"][0]["path"] = path
            with self.assertRaises(ValueError):
                bindings.source_claims(matrix.json_bytes(value), "repo", "behavioral-repository-admission")
        value = copy.deepcopy(self.admission)
        value["sources"][0]["size_bytes"] = True
        with self.assertRaises(ValueError):
            bindings.source_claims(matrix.json_bytes(value), "repo", "behavioral-repository-admission")
        with self.assertRaises(ValueError):
            bindings.source_claims(matrix.json_bytes(self.supervision), "repo", "behavioral-repository-admission")
        built, _ = self.build()
        with patch.object(bindings, "MAX_OBJECTS", 0):
            self.refused(built / "archive_input.json")

    def test_output_original_scope_symlink_and_sealed_parent_refusals(self):
        built, _ = self.build()
        sealed = self.next_path("sealed")
        sealed.mkdir()
        sealed.chmod(0o555)
        alias = self.next_path("alias")
        alias.symlink_to(built, target_is_directory=True)
        for output in (self.repo / "out", built / "out", alias / "out", sealed / "out"):
            with self.subTest(output=output), self.assertRaises(ValueError):
                bindings.verify(built / "archive_input.json", output)

    def test_final_stability_result_body_and_population_drift_refuse_reports(self):
        built, _ = self.build()
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
            self.refused(built / "archive_input.json")
        for kind in ("body", "fifo", "mode"):
            original_verify = bindings.capsule_verify

            def changed(root, digest, output, kind=kind, original_verify=original_verify):
                result = original_verify(root, digest, output)
                target = root / "sources/repo/pkg/source.py"
                if kind == "body":
                    target.chmod(0o644)
                    target.write_bytes(b"X" * len(self.source))
                    target.chmod(0o444)
                elif kind == "mode":
                    target.chmod(0o644)
                else:
                    root.chmod(0o755)
                    os.mkfifo(root / "extra")
                    root.chmod(0o555)
                return result

            with patch.object(bindings, "capsule_verify", changed):
                self.refused(built / "archive_input.json")

    def test_written_archive_short_copy_is_refused_before_build_report(self):
        prior, choices = self.prior()
        folder = self.next_path("source-input")
        folder.mkdir()
        manifest = folder / "manifest.json"
        manifest.write_bytes(
            matrix.json_bytes(
                {
                    "schema": bindings.BUILD_INPUT_SCHEMA,
                    "custody_capsule_manifest": self.pin(prior / "capsule/capsule_manifest.json"),
                    "selected_receipts": choices,
                }
            )
        )
        output = self.next_path("short-build")
        original = Path.chmod

        def changed(path, mode, **kwargs):
            if path == output / "producer_sources.zip":
                path.write_bytes(path.read_bytes()[:-1])
            return original(path, mode, **kwargs)

        with patch.object(Path, "chmod", changed), self.assertRaises(ValueError):
            bindings.build(manifest, output)
        self.assertFalse((output / "producer_source_bindings_build.json").exists())

    def test_aggregate_claim_and_object_caps_refuse_before_source_body_reads(self):
        prior, choices = self.prior()
        folder = self.next_path("bounded-input")
        folder.mkdir()
        manifest = folder / "manifest.json"
        manifest.write_bytes(
            matrix.json_bytes(
                {
                    "schema": bindings.BUILD_INPUT_SCHEMA,
                    "custody_capsule_manifest": self.pin(prior / "capsule/capsule_manifest.json"),
                    "selected_receipts": choices,
                }
            )
        )
        original_blob = matrix.GitObjects.blob

        def no_source(repo, path):
            if path.startswith("pkg/"):
                raise AssertionError("source body read before aggregate claim ceiling")
            return original_blob(repo, path)

        with (
            patch.object(bindings, "MAX_CLAIMS", 3),
            patch.object(matrix.GitObjects, "blob", no_source),
            self.assertRaises(ValueError),
        ):
            bindings.build(manifest, self.next_path("bounded-build"))
        original_command = matrix.GitObjects.command

        def no_commit(repo, args, limit):
            if args[:2] == ["cat-file", "commit"]:
                raise AssertionError("commit body read before object ceiling")
            return original_command(repo, args, limit)

        with (
            patch.object(bindings, "MAX_OBJECTS", 0),
            patch.object(matrix.GitObjects, "command", no_commit),
            self.assertRaises(ValueError),
        ):
            bindings.build(manifest, self.next_path("bounded-objects"))

    def test_dirty_working_source_is_ignored_and_late_original_receipt_drift_refuses(self):
        prior, choices = self.prior()
        folder = self.next_path("frozen-input")
        folder.mkdir()
        manifest = folder / "manifest.json"
        manifest.write_bytes(
            matrix.json_bytes(
                {
                    "schema": bindings.BUILD_INPUT_SCHEMA,
                    "custody_capsule_manifest": self.pin(prior / "capsule/capsule_manifest.json"),
                    "selected_receipts": choices,
                }
            )
        )
        (self.repo / "pkg/source.py").write_bytes(b"current dirty source")
        output = self.next_path("dirty-build")
        result = bindings.build(manifest, output)
        self.assertTrue(result["all_selected_sources_verified"])
        self.assertEqual((output / "capsule/sources/repo/pkg/source.py").read_bytes(), self.source)
        original_verify = bindings.capsule_verify

        def changed(root, digest, review_output):
            result = original_verify(root, digest, review_output)
            receipt = next((prior / "capsule/retained/children").rglob("producer-sources.json"))
            raw = receipt.read_bytes()
            receipt.chmod(0o644)
            receipt.write_bytes(b"X" + raw[1:])
            receipt.chmod(0o444)
            return result

        late = self.next_path("late-original")
        with patch.object(bindings, "capsule_verify", changed), self.assertRaises(ValueError):
            bindings.build(manifest, late)
        self.assertFalse((late / "producer_source_bindings_build.json").exists())

    def test_actual_late_verification_archive_and_manifest_drift_refuse_publication(self):
        built, _ = self.build()
        original_verify = bindings.capsule_verify
        for name in ("producer_sources.zip", "archive_input.json"):
            path = built / name
            original = path.read_bytes()

            def changed(root, digest, output, path=path):
                result = original_verify(root, digest, output)
                raw = path.read_bytes()
                path.chmod(0o644)
                path.write_bytes(b"X" + raw[1:])
                path.chmod(0o444)
                return result

            with patch.object(bindings, "capsule_verify", changed):
                self.refused(built / "archive_input.json")
            path.chmod(0o644)
            path.write_bytes(original)
            path.chmod(0o444)


if __name__ == "__main__":
    unittest.main()

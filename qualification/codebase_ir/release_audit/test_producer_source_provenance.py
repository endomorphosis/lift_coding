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
import producer_source_provenance as provenance
import release_matrix as matrix
import test_producer_source_bindings as fixtures


class ProducerSourceProvenanceTests(unittest.TestCase):
    def setUp(self):
        self.factory = fixtures.ProducerSourceBindingsTests("runTest")
        self.factory.setUp()
        self.addCleanup(self.factory.doCleanups)
        self.root, self.repo = self.factory.root, self.factory.repo
        self.historical = b"raise RuntimeError('historical source must remain inert')\n"
        self.missing = b"raise RuntimeError('unretained historical preparation')\n"
        self.factory.supervision["files"][0]["sha256"] = matrix.sha(self.historical)
        self.factory.supervision["files"][1]["sha256"] = matrix.sha(self.missing)
        self.extra_children = [{"path": "driver-at-native-01.py.txt", "body": self.historical}]
        self.prior = None

    def next_path(self, label):
        return self.factory.next_path(label)

    pin = staticmethod(fixtures.ProducerSourceBindingsTests.pin)

    def prepare(self):
        if self.prior is not None:
            return self.prior
        choices = []
        for name, eid, value in (
            ("admission", "behavioral-repository-admission", self.factory.admission),
            ("supervision", provenance.EVIDENCE_ID, self.factory.supervision),
        ):
            raw = matrix.json_bytes(value)
            folder = self.repo / "docs" / name
            (folder / "producer-sources.json").write_bytes(raw)
            rows = [{"path": "producer-sources.json", "sha256": matrix.sha(raw), "bytes": len(raw)}]
            if name == "supervision":
                for child in self.extra_children:
                    path = folder / child["path"]
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_bytes(child["body"])
                    rows.append(
                        {
                            "path": child["path"],
                            "sha256": matrix.sha(child["body"]),
                            "bytes": len(child["body"]),
                        }
                    )
            header = matrix.json_bytes({"schema": "repository-evidence-files@1", "files": rows})
            (folder / "evidence.json").write_bytes(header)
            self.factory.factory.factory.ledger["evidence"][eid] = {
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
        self.factory.factory.factory.commit()
        child_factory = self.factory.factory
        child_factory.spec = {
            "schema": children.INPUT_SCHEMA,
            "repositories": child_factory.factory.spec["repositories"],
            "ledger": child_factory.factory.spec["ledger"],
            "selected_evidence": [row["evidence_id"] for row in choices],
            "expansion_policy": children.POLICY,
        }
        child_factory.write_spec()
        child_factory.run_audit()
        report = self.root / f"result-{child_factory.sequence}/evidence_children.json"
        folder = self.next_path("child-build-input")
        folder.mkdir()
        child_input = folder / "manifest.json"
        child_input.write_bytes(
            matrix.json_bytes(
                {
                    "schema": child_capsule.BUILD_INPUT_SCHEMA,
                    "source_manifest": self.pin(child_factory.manifest),
                    "source_report": self.pin(report),
                }
            )
        )
        child_output = self.next_path("child-build")
        child_capsule.build(child_input, child_output)
        folder = self.next_path("producer-build-input")
        folder.mkdir()
        producer_input = folder / "manifest.json"
        producer_input.write_bytes(
            matrix.json_bytes(
                {
                    "schema": bindings.BUILD_INPUT_SCHEMA,
                    "custody_capsule_manifest": self.pin(
                        child_output / "capsule/capsule_manifest.json"
                    ),
                    "selected_receipts": choices,
                }
            )
        )
        producer_output = self.next_path("producer-build")
        bindings.build(producer_input, producer_output)
        producer_verify = self.next_path("producer-restored")
        bindings.verify(producer_output / "archive_input.json", producer_verify)
        folder = self.next_path("provenance-build-input")
        folder.mkdir()
        manifest = folder / "manifest.json"
        manifest.write_bytes(
            matrix.json_bytes(
                {
                    "schema": provenance.BUILD_INPUT_SCHEMA,
                    "producer_source_input": self.pin(producer_output / "archive_input.json"),
                    "producer_source_report": self.pin(
                        producer_verify / "producer_source_bindings.json"
                    ),
                    "producer_capsule_manifest": self.pin(
                        producer_output / "capsule/producer_source_capsule.json"
                    ),
                    "custody_capsule_manifest": self.pin(
                        child_output / "capsule/capsule_manifest.json"
                    ),
                    "selected_source_paths": ["pkg/source.py", "pkg/extra.py"],
                }
            )
        )
        self.prior = manifest, child_output, producer_output, producer_verify
        return self.prior

    def build(self):
        manifest, *_ = self.prepare()
        output = self.next_path("provenance-build")
        report = provenance.build(manifest, output)
        return output, report

    def verify(self, built):
        output = self.next_path("provenance-restored")
        report = provenance.verify(built / "archive_input.json", output)
        return report, output

    @staticmethod
    def replace(cap, entries, path, raw):
        entries[path] = raw
        for key in (
            "files",
            "historical_views",
            "historical_objects",
            "implementation",
            "producer_files",
        ):
            for row in cap[key]:
                if row["path"] == path:
                    row.update(portable.pin(path, raw))
        for key in (
            "source_manifest",
            "producer_source_input",
            "producer_source_report",
            "producer_capsule_manifest",
            "custody_capsule_manifest",
        ):
            if cap[key]["path"] == path:
                cap[key].update(portable.pin(path, raw))

    def mutant(self, built, mutate):
        entries = archive.decode((built / "producer_provenance.zip").read_bytes())
        cap = matrix.document(entries[provenance.CAPSULE_FILENAME])
        mutate(cap, entries)
        entries[provenance.CAPSULE_FILENAME] = matrix.json_bytes(cap)
        folder = self.next_path("mutant")
        folder.mkdir()
        path = folder / "producer_provenance.zip"
        path.write_bytes(archive.encode(entries))
        manifest = folder / "manifest.json"
        spec = matrix.document((built / "archive_input.json").read_bytes())
        spec["archive"] = self.pin(path)
        spec["capsule_manifest_sha256"] = matrix.sha(entries[provenance.CAPSULE_FILENAME])
        for name, key in (
            ("producer_capsule_manifest", "producer_capsule_manifest_sha256"),
            ("custody_capsule_manifest", "custody_capsule_manifest_sha256"),
            ("producer_source_input", "producer_source_input_sha256"),
            ("producer_source_report", "producer_source_report_sha256"),
        ):
            spec[key] = cap[name]["sha256"]
        manifest.write_bytes(matrix.json_bytes(spec))
        return manifest

    def refused(self, manifest):
        output = self.next_path("refused")
        with self.assertRaises((ValueError, OSError, KeyError, TypeError)):
            provenance.verify(manifest, output)
        self.assertFalse((output / "producer_source_provenance.json").exists())

    def test_roundtrip_recovers_one_body_preserves_committed_gaps_and_missing_revision(self):
        built, before = self.build()
        report, output = self.verify(built)
        self.assertFalse(before["archive_roundtrip_verified"])
        self.assertTrue(report["archive_roundtrip_verified"])
        self.assertEqual(
            report["historical_dispositions"],
            {"historical-source-recovered": 1, "historical-source-unavailable": 1},
        )
        self.assertEqual(report["committed_source_dispositions"], {"verified": 2, "different": 2})
        self.assertFalse(report["committed_all_selected_sources_verified"])
        self.assertFalse(report["all_selected_historical_sources_recovered"])
        self.assertTrue(all(report[flag] is False for flag in provenance.FALSE_FLAGS))
        recovered = report["historical_sources"][0]
        self.assertEqual(recovered["expected_size_bytes"], None)
        self.assertEqual(
            recovered["historical_candidates"][0]["declared_size_disposition"], "undeclared"
        )
        self.assertNotEqual(
            recovered["committed_membership"]["sha256"], matrix.sha(self.historical)
        )
        self.assertEqual(
            (
                output / "capsule/historical/docs/supervision/driver-at-native-01.py.txt"
            ).read_bytes(),
            self.historical,
        )
        self.assertEqual(
            (output / "capsule/producer/sources/repo/pkg/source.py").read_bytes(),
            self.factory.source,
        )

    def test_deterministic_archive_does_not_bind_the_new_output_location(self):
        first, first_report = self.build()
        second, second_report = self.build()
        self.assertEqual(
            (first / "producer_provenance.zip").read_bytes(),
            (second / "producer_provenance.zip").read_bytes(),
        )
        self.assertEqual(
            first_report["capsule_manifest_sha256"], second_report["capsule_manifest_sha256"]
        )

    def test_shared_historical_body_keeps_both_claim_memberships_and_unique_retained_bytes(self):
        self.factory.supervision["files"][1]["sha256"] = matrix.sha(self.historical)
        built, _ = self.build()
        report, _output = self.verify(built)
        self.assertEqual(report["recovered_historical_source_count"], 2)
        self.assertEqual(report["historical_candidate_membership_count"], 2)
        self.assertEqual(report["unique_historical_view_count"], 1)
        self.assertEqual(report["retained_historical_source_bytes"], len(self.historical))
        self.assertEqual(report["committed_source_dispositions"]["different"], 2)

    def test_planned_file_budget_refuses_before_historical_payload_reads(self):
        manifest, child_output, *_ = self.prepare()
        calls = 0
        original = portable.BundleReader.body

        def body(reader, pin):
            nonlocal calls
            if reader.root == child_output / "capsule":
                calls += 1
            return original(reader, pin)

        output = self.next_path("planned-budget")
        with (
            patch.object(provenance, "MAX_FILES", 1),
            patch.object(portable.BundleReader, "body", body),
            self.assertRaises(ValueError),
        ):
            provenance.build(manifest, output)
        self.assertEqual(calls, 0)
        self.assertFalse(output.exists())

    def test_missing_claim_is_explicitly_recovered_only_when_same_parent_declares_body(self):
        self.extra_children.append({"path": "preparation.py.txt", "body": self.missing})
        built, _ = self.build()
        report, _output = self.verify(built)
        self.assertEqual(report["recovered_historical_source_count"], 2)
        self.assertEqual(report["unavailable_historical_source_count"], 0)
        self.assertTrue(report["all_selected_historical_sources_recovered"])
        self.assertEqual(report["committed_source_dispositions"]["different"], 2)

    def test_unlisted_working_source_is_never_a_historical_fallback(self):
        manifest, *_ = self.prepare()
        (self.repo / "unlisted-history.py").write_bytes(self.missing)
        output = self.next_path("ignored-working")
        report = provenance.build(manifest, output)
        self.assertEqual(report["unavailable_historical_source_count"], 1)

    def test_repaired_outer_pins_cannot_change_historical_body(self):
        built, _ = self.build()

        def mutate(cap, entries):
            row = cap["historical_views"][0]
            self.replace(cap, entries, row["path"], b"X" + entries[row["path"]][1:])

        self.refused(self.mutant(built, mutate))

    def test_repaired_outer_pins_cannot_forge_historical_git_blob(self):
        built, _ = self.build()

        def mutate(cap, entries):
            row = cap["historical_objects"][0]
            self.replace(cap, entries, row["path"], b"X" + entries[row["path"]][1:])

        self.refused(self.mutant(built, mutate))

    def test_repaired_blob_oid_cannot_escape_committed_tree_binding(self):
        built, _ = self.build()

        def mutate(cap, entries):
            row = cap["historical_objects"][0]
            old = row["path"]
            raw = b"X" + entries[old][1:]
            oid = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
            path = "historical_git_objects/" + row["repository"] + "/" + oid
            entries[path] = raw
            del entries[old]
            for file in cap["files"]:
                if file["path"] == old:
                    file.update(portable.pin(path, raw))
            row.update(oid=oid, **portable.pin(path, raw))

        self.refused(self.mutant(built, mutate))

    def test_repaired_prior_report_and_captured_input_cannot_erase_committed_discrepancies(self):
        built, _ = self.build()

        def mutate(cap, entries):
            report = matrix.document(entries[cap["producer_source_report"]["path"]])
            report["all_selected_sources_verified"] = True
            report["source_dispositions"] = {"verified": 4}
            self.replace(
                cap, entries, cap["producer_source_report"]["path"], matrix.json_bytes(report)
            )
            original = matrix.document(entries[cap["source_manifest"]["path"]])
            original["producer_source_report"].update(
                sha256=cap["producer_source_report"]["sha256"],
                size_bytes=cap["producer_source_report"]["size_bytes"],
            )
            self.replace(cap, entries, cap["source_manifest"]["path"], matrix.json_bytes(original))

        self.refused(self.mutant(built, mutate))

    def test_forged_missing_and_recovered_decisions_are_not_accepted(self):
        built, _ = self.build()
        for field in ("recovered_historical_source_count", "unavailable_historical_source_count"):
            with self.subTest(field=field):
                self.refused(
                    self.mutant(
                        built,
                        lambda cap, entries, key=field: cap["expected_review"].__setitem__(key, 99),
                    )
                )

    def test_historical_body_role_path_and_extra_files_are_refused(self):
        built, _ = self.build()

        def alias(cap, entries):
            cap["historical_views"][0]["evidence_path"] = "docs/supervision/forged.py.txt"

        self.refused(self.mutant(built, alias))

        def extra(cap, entries):
            entries["extra.txt"] = b"unselected"
            cap["files"].append(portable.pin("extra.txt", b"unselected"))

        self.refused(self.mutant(built, extra))

    def test_unused_historical_object_and_missing_proof_are_refused(self):
        built, _ = self.build()

        def extra(cap, entries):
            raw = b"unused historical blob"
            oid = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
            path = "historical_git_objects/repo/" + oid
            row = {"repository": "repo", "oid": oid, "kind": "blob", **portable.pin(path, raw)}
            cap["historical_objects"].append(row)
            cap["files"].append(portable.pin(path, raw))
            entries[path] = raw

        self.refused(self.mutant(built, extra))

        def missing(cap, entries):
            row = cap["historical_objects"].pop()
            cap["files"] = [file for file in cap["files"] if file["path"] != row["path"]]
            del entries[row["path"]]

        self.refused(self.mutant(built, missing))

    def test_authority_escalation_and_independent_pin_changes_refuse(self):
        built, _ = self.build()
        for flag in provenance.FALSE_FLAGS:
            with self.subTest(flag=flag):
                self.refused(
                    self.mutant(built, lambda cap, entries, key=flag: cap.__setitem__(key, True))
                )
        for key in provenance.BINDINGS:
            folder = self.next_path("bad-binding")
            folder.mkdir()
            spec = matrix.document((built / "archive_input.json").read_bytes())
            spec[key] = "f" * 64
            manifest = folder / "manifest.json"
            manifest.write_bytes(matrix.json_bytes(spec))
            self.refused(manifest)

    def test_capsule_count_and_byte_bounds_refuse_before_payload_reads(self):
        built, _ = self.build()
        entries = archive.decode((built / "producer_provenance.zip").read_bytes())
        cap = matrix.document(entries[provenance.CAPSULE_FILENAME])
        for key, limit in (
            ("files", provenance.MAX_FILES),
            ("historical_objects", provenance.MAX_OBJECTS + 1),
            ("directories", provenance.MAX_DIRECTORIES + 1),
        ):
            bad = copy.deepcopy(cap)
            bad[key] = [bad[key][0]] * limit
            raw = matrix.json_bytes(bad)
            with self.subTest(key=key), self.assertRaises(ValueError):
                provenance.inventory(raw, matrix.sha(raw))
        bad = copy.deepcopy(cap)
        bad["files"][0]["size_bytes"] = matrix.MAX_FILE_BYTES + 1
        raw = matrix.json_bytes(bad)
        with self.assertRaises(ValueError):
            provenance.inventory(raw, matrix.sha(raw))

    def test_strict_json_path_selections_and_output_scopes_refuse(self):
        manifest, child_output, producer_output, _report = self.prepare()
        valid = matrix.document(manifest.read_bytes())
        for path in ("../source.py", "/source.py", "pkg\\source.py", "pkg/source.py\x00"):
            bad = copy.deepcopy(valid)
            bad["selected_source_paths"] = [path]
            with self.subTest(path=path), self.assertRaises(ValueError):
                provenance.build_spec(matrix.json_bytes(bad))
        bad = copy.deepcopy(valid)
        bad["selected_source_paths"] *= 2
        with self.assertRaises(ValueError):
            provenance.build_spec(matrix.json_bytes(bad))
        with self.assertRaises(ValueError):
            provenance.build_spec(b'{"schema":"x","schema":"y"}')
        with self.assertRaises(ValueError):
            provenance.build_spec(b'{"schema":NaN}')
        for out in (
            manifest.parent / "nested",
            child_output / "capsule/nested",
            producer_output / "capsule/nested",
            self.repo / "nested",
        ):
            with self.subTest(output=out), self.assertRaises((ValueError, OSError)):
                provenance.build(manifest, out)

    def test_late_written_archive_drift_refuses_build_report(self):
        manifest, *_ = self.prepare()
        output = self.next_path("late-archive")
        original = archive.PinnedReader.read
        changed = False

        def read(reader, path, *args, **kwargs):
            nonlocal changed
            if path.name == "producer_provenance.zip" and not changed:
                raw = path.read_bytes()
                path.write_bytes(raw[:-1] + bytes([raw[-1] ^ 1]))
                changed = True
            return original(reader, path, *args, **kwargs)

        with patch.object(archive.PinnedReader, "read", read), self.assertRaises(ValueError):
            provenance.build(manifest, output)
        self.assertTrue(changed)
        self.assertFalse((output / "producer_source_provenance_build.json").exists())

    def test_late_original_and_retained_copy_drift_refuse_reports(self):
        manifest, *_ = self.prepare()
        output = self.next_path("late-original")
        original = provenance.capsule_verify

        def verify(root, digest, out):
            result = original(root, digest, out)
            raw = manifest.read_bytes()
            manifest.write_bytes(raw + b" ")
            return result

        with patch.object(provenance, "capsule_verify", verify), self.assertRaises(ValueError):
            provenance.build(manifest, output)
        self.assertFalse((output / "producer_source_provenance_build.json").exists())

    def test_final_reread_detected_drift_and_final_population_permission_drift_refuse(self):
        built, _ = self.build()
        original = archive.PinnedReader.stability
        calls = 0

        def stability(reader):
            nonlocal calls
            calls += 1
            if calls == 2:
                return {"unchanged": False}
            return original(reader)

        with patch.object(archive.PinnedReader, "stability", stability):
            self.refused(built / "archive_input.json")
        self.assertEqual(calls, 2)
        original_verify = provenance.capsule_verify

        def mutate(root, digest, output):
            report = original_verify(root, digest, output)
            cap = matrix.document((root / provenance.CAPSULE_FILENAME).read_bytes())
            path = root / cap["historical_views"][0]["path"]
            path.chmod(0o644)
            return report

        with patch.object(provenance, "capsule_verify", mutate):
            self.refused(built / "archive_input.json")

    def test_late_referenced_custody_and_nested_producer_report_drift_refuse_publication(self):
        built, _ = self.build()
        original = portable.BundleReader.stability
        for relative in (
            "producer_source_provenance_custody.json",
            "producer_reverification/producer_source_custody.json",
        ):
            calls = 0
            changed = False

            def stability(reader, selected_relative=relative):
                nonlocal calls, changed
                if reader.root.name == "capsule":
                    calls += 1
                    if calls == 3:
                        path = reader.root.parent / "restored_verification" / selected_relative
                        raw = path.read_bytes()
                        path.write_bytes(bytes([raw[0] ^ 1]) + raw[1:])
                        changed = True
                return original(reader)

            with (
                self.subTest(relative=relative),
                patch.object(portable.BundleReader, "stability", stability),
            ):
                self.refused(built / "archive_input.json")
            self.assertTrue(changed)

    def test_late_original_historical_source_body_drift_refuses_build(self):
        manifest, child_output, *_ = self.prepare()
        cap = matrix.document((child_output / "capsule/capsule_manifest.json").read_bytes())
        pin = next(
            row
            for row in cap["retained_views"]
            if row["path"].endswith("driver-at-native-01.py.txt")
        )
        path = child_output / "capsule" / pin["path"]
        original = provenance.capsule_verify

        def mutate(root, digest, output):
            report = original(root, digest, output)
            raw = path.read_bytes()
            path.chmod(0o644)
            path.write_bytes(bytes([raw[0] ^ 1]) + raw[1:])
            path.chmod(0o444)
            return report

        out = self.next_path("late-historical-original")
        with patch.object(provenance, "capsule_verify", mutate), self.assertRaises(ValueError):
            provenance.build(manifest, out)
        self.assertFalse((out / "producer_source_provenance_build.json").exists())

    def test_relocation_uses_only_packaged_verifier_and_selected_archive(self):
        built, _ = self.build()
        staged = self.next_path("relocated")
        staged.mkdir()
        tools = staged / "tools"
        tools.mkdir()
        for name in provenance.TOOL_FILES:
            shutil.copyfile(built / "capsule" / name, tools / Path(name).name)
        shutil.copyfile(built / "producer_provenance.zip", staged / "producer_provenance.zip")
        spec = matrix.document((built / "archive_input.json").read_bytes())
        spec["archive"]["path"] = str(staged / "producer_provenance.zip")
        manifest = staged / "manifest.json"
        manifest.write_bytes(matrix.json_bytes(spec))
        self.repo.rename(self.root / "original-repository-unavailable")
        for folder in self.prepare()[1:]:
            folder.rename(folder.with_name(folder.name + "-unavailable"))
        self.prepare()[0].unlink()
        output = self.next_path("relocated-restored")
        result = subprocess.run(
            [
                sys.executable,
                "-I",
                "-B",
                str(tools / "producer_source_provenance.py"),
                "verify",
                "--manifest",
                str(manifest),
                "--output",
                str(output),
            ],
            capture_output=True,
            text=True,
            env={**os.environ, "PATH": ""},
            timeout=30,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        report = matrix.document((output / "producer_source_provenance.json").read_bytes())
        self.assertEqual(
            report["historical_dispositions"],
            {"historical-source-recovered": 1, "historical-source-unavailable": 1},
        )
        self.assertEqual(report["committed_source_dispositions"]["different"], 2)
        self.assertTrue(all(report[flag] is False for flag in provenance.FALSE_FLAGS))


if __name__ == "__main__":
    unittest.main()

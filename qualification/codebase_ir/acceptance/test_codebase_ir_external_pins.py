"""External file manifests pin bytes without importing their contents."""
from __future__ import annotations

import copy
import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import codebase_ir_external_pins as pins
import codebase_ir_planning_qualification as planning


class ExternalPinsTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name).resolve()
        self.root = self.base / "site-packages"
        self.root.mkdir()
        self.file = self.root / "authored.py"
        self.file.write_bytes(b"raise AssertionError('must never be imported')\n")
        self.pin = {"sha256": hashlib.sha256(self.file.read_bytes()).hexdigest(), "size_bytes": self.file.stat().st_size}
        self.document = {"schema": pins.SCHEMA, "site_packages_roots": [str(self.root)],
            "source_report_sha256": "a" * 64, "files": [{"path": str(self.file), **self.pin}]}

    def test_before_pin_capture_is_exact_and_does_not_execute_source(self):
        path = self.base / "manifest.json"
        path.write_text(json.dumps(self.document))
        with patch.object(pins, "interpreter_site_roots", return_value=[self.root]):
            observed, metadata = pins.capture_external_manifest(path)
        self.assertEqual(observed, {str(self.file): self.pin})
        self.assertFalse(metadata["imports_performed"])
        self.assertFalse(metadata["runtime_closure_proven"])

    def test_manifest_duplicate_keys_and_nonfinite_json_values_are_refused(self):
        path = self.base / "bad-manifest.json"
        for raw in ('{"schema":"one","schema":"two"}', '{"unexpected":NaN}', '{"unexpected":Infinity}', '{"unexpected":-Infinity}'):
            path.write_text(raw)
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                pins.capture_external_manifest(path)

    def test_report_duplicate_keys_and_nonfinite_json_values_are_refused(self):
        path = self.base / "bad-report.json"
        for raw in ('{"status":"passed","status":"passed"}', '{"unexpected":NaN}'):
            path.write_text(raw)
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                pins.manifest_from_report(path, self.base / "never-created.json")
        self.assertFalse((self.base / "never-created.json").exists())

    def test_document_reads_remain_bounded_when_file_grows_after_fstat(self):
        path = self.base / "growing.json"
        path.write_bytes(b"{}" * 20)
        actual = os.stat(path)
        claimed = SimpleNamespace(st_mode=actual.st_mode, st_size=1, st_dev=actual.st_dev,
            st_ino=actual.st_ino, st_mtime_ns=actual.st_mtime_ns, st_ctime_ns=actual.st_ctime_ns)
        with patch.object(pins.os, "fstat", return_value=claimed), self.assertRaisesRegex(ValueError, "byte cap"):
            pins._bounded_document(path, 10)

    def test_foreign_site_root_and_foreign_file_cannot_expand_allowlist(self):
        foreign = self.base / "foreign" / "site-packages"
        foreign.mkdir(parents=True)
        file = foreign / "foreign.py"
        file.write_bytes(self.file.read_bytes())
        for mutation in ("root", "file"):
            document = copy.deepcopy(self.document)
            if mutation == "root":
                document["site_packages_roots"] = [str(foreign)]
            else:
                document["files"][0]["path"] = str(file)
            with self.assertRaises(ValueError):
                pins.validate_manifest(document, roots=[self.root])

    def test_symlink_file_and_parent_alias_are_refused(self):
        link = self.root / "alias.py"
        link.symlink_to(self.file)
        parent = self.base / "linked-site"
        parent.symlink_to(self.root, target_is_directory=True)
        for path in (link, parent / self.file.name):
            document = copy.deepcopy(self.document)
            document["files"][0]["path"] = str(path)
            with self.assertRaises(ValueError):
                pins.validate_manifest(document, roots=[self.root])

    def test_noncanonical_path_spelling_is_refused(self):
        document = copy.deepcopy(self.document)
        document["files"][0]["path"] = str(self.root) + "/../site-packages/authored.py"
        with self.assertRaises(ValueError):
            pins.validate_manifest(document, roots=[self.root])

    def test_exact_fields_types_digests_and_unique_files_are_required(self):
        for mutation in ("extra", "bool_size", "digest", "duplicate", "unknown_root", "empty"):
            document = copy.deepcopy(self.document)
            if mutation == "extra":
                document["files"][0]["trust_me"] = True
            elif mutation == "bool_size":
                document["files"][0]["size_bytes"] = True
            elif mutation == "digest":
                document["files"][0]["sha256"] = "invalid"
            elif mutation == "duplicate":
                document["files"].append(copy.deepcopy(document["files"][0]))
            elif mutation == "unknown_root":
                document["site_packages_roots"] = []
            else:
                document["files"] = []
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                pins.validate_manifest(document, roots=[self.root])

    def test_digest_drift_refuses_before_execution(self):
        self.file.write_bytes(b"changed bytes\n")
        with self.assertRaisesRegex(ValueError, "digest or size drift"):
            pins.validate_manifest(self.document, roots=[self.root])

    def test_file_count_per_file_and_total_byte_caps_are_enforced(self):
        for name in ("MAX_FILES", "MAX_FILE_BYTES", "MAX_TOTAL_BYTES"):
            limit = 0 if name == "MAX_FILES" else self.pin["size_bytes"] - 1
            with self.subTest(cap=name), patch.object(pins, name, limit), self.assertRaises(ValueError):
                pins.validate_manifest(self.document, roots=[self.root])

    def test_nonregular_fifo_is_refused_without_blocking(self):
        fifo = self.root / "not-a-file"
        os.mkfifo(fifo)
        with self.assertRaisesRegex(ValueError, "regular file"):
            pins.read_file_pin(fifo, roots=[self.root])

    def test_after_compare_uses_bytes_and_preserves_before_for_new_module_names(self):
        after = {str(self.file): {**self.pin, "module_names": ["newly_loaded_module"]}}
        rows = pins.compare_external_pins({str(self.file): self.pin}, after, roots=[self.root])
        self.assertEqual(rows[0]["before"], self.pin)
        self.assertTrue(rows[0]["unchanged"])
        self.assertFalse(rows[0]["late_import"])

    def test_new_unlisted_loaded_file_stays_explicit_late_dependency(self):
        after = {str(self.file): {**self.pin, "module_names": ["late_module"]}}
        rows = pins.compare_external_pins({}, after, roots=[self.root])
        self.assertTrue(rows[0]["late_import"])
        self.assertFalse(rows[0]["unchanged"])

    def test_after_compare_refuses_real_pinned_byte_change(self):
        before = {str(self.file): self.pin}
        self.file.write_bytes(b"mutated after before-read\n")
        after = {str(self.file): {**pins.read_file_pin(self.file, roots=[self.root]), "module_names": ["changed"]}}
        with self.assertRaisesRegex(ValueError, "changed during run"):
            pins.compare_external_pins(before, after, roots=[self.root])

    def test_strict_loaded_module_enumeration_uses_streaming_pin_without_read_bytes(self):
        module = SimpleNamespace(__file__=str(self.file))
        with (patch.object(planning, "sys", SimpleNamespace(modules={"authored_external_test": module})),
                patch.object(Path, "read_bytes", side_effect=AssertionError("unbounded read forbidden"))):
            observed = planning.external_dependency_pins(strict_roots=[self.root])
        self.assertEqual(observed, {str(self.file): {"module_names": ["authored_external_test"], **self.pin}})

    def test_strict_loaded_module_enumeration_enforces_unique_file_and_byte_caps(self):
        module = SimpleNamespace(__file__=str(self.file))
        for name, limit in (("MAX_FILES", 0), ("MAX_TOTAL_BYTES", self.pin["size_bytes"] - 1)):
            with (self.subTest(cap=name), patch.object(planning, name, limit),
                    patch.object(planning, "sys", SimpleNamespace(modules={"authored_external_test": module})),
                    self.assertRaises(ValueError)):
                planning.external_dependency_pins(strict_roots=[self.root])

    def test_strict_loaded_origins_refuse_foreign_site_and_symlink_to_outside_site(self):
        foreign = self.base / "foreign-site" / "site-packages" / "foreign.py"
        foreign.parent.mkdir(parents=True)
        foreign.write_bytes(b"unlisted foreign file\n")
        outside = self.base / "outside.py"
        outside.write_bytes(b"outside current site roots\n")
        link = self.root / "linked.py"
        link.symlink_to(outside)
        for path in (foreign, link):
            module = SimpleNamespace(__file__=str(path))
            with (self.subTest(path=path), patch.object(planning, "sys", SimpleNamespace(modules={"foreign_test": module})),
                    self.assertRaises(ValueError)):
                planning.external_dependency_pins(strict_roots=[self.root])

    def test_initial_imports_cannot_promote_unlisted_files_into_manifest_before_pins(self):
        existing = {str(self.file): {**self.pin, "module_names": ["initial_late_import"]}}
        progress = {"external_dependency_manifest": {"schema": pins.SCHEMA}, "external_dependency_before": {}}
        planning.retain_initial_external_observation(progress, existing)
        self.assertEqual(progress["external_dependency_before"], {})
        self.assertEqual(progress["external_dependency_after_initial_imports"], existing)
        rows = pins.compare_external_pins(progress["external_dependency_before"], existing, roots=[self.root])
        self.assertTrue(rows[0]["late_import"])
        self.assertFalse(rows[0]["unchanged"])
        observed_mode = {}
        planning.retain_initial_external_observation(observed_mode, existing)
        self.assertEqual(observed_mode["external_dependency_before"], existing)

    def test_generator_checks_prior_report_bytes_and_writes_fresh_manifest(self):
        report = self.base / "prior.json"
        report.write_text(json.dumps({"schema": "codebase-ir-finite-planning-qualification@1", "status": "passed",
            "external_dependency_pins": [{"path": str(self.file), "after": self.pin}]}))
        output = self.base / "generated.json"
        with patch.object(pins, "interpreter_site_roots", return_value=[self.root]):
            document = pins.manifest_from_report(report, output)
            with self.assertRaisesRegex(ValueError, "fresh"):
                pins.manifest_from_report(report, output)
        self.assertEqual(document["source_report_sha256"], hashlib.sha256(report.read_bytes()).hexdigest())
        self.assertEqual(json.loads(output.read_bytes()), document)
        self.assertEqual(document["files"], self.document["files"])

    def test_planning_report_keeps_manifest_before_pins_for_actual_late_imports(self):
        manifest = self.base / "run-manifest.json"
        manifest.write_text(json.dumps(self.document))
        loaded = {str(self.file): {**self.pin, "module_names": ["late_actual_import"]}}
        def session(output, *, lean, progress):
            self.assertEqual(progress["external_dependency_before"], {str(self.file): self.pin})
            progress.update({"status": "passed", "final_resource_state": {"active_lease_count": 0, "waiting_request_count": 0}})
            return progress
        with (patch.object(pins, "interpreter_site_roots", return_value=[self.root]),
                patch.object(planning, "interpreter_site_roots", return_value=[self.root]),
                patch.object(planning, "native_source_snapshot", return_value=([], {})),
                patch.object(planning, "imported_native_sources", return_value=[{"unchanged": True}]),
                patch.object(planning, "external_dependency_pins", return_value=loaded),
                patch.object(planning, "native_session", side_effect=session)):
            report = planning.run(self.base / "private-output", lean=self.base / "unused-lean", external_manifest=manifest)
        self.assertEqual(report["status"], "passed")
        self.assertEqual(report["native_planning"]["external_dependency_before"], {str(self.file): self.pin})
        self.assertTrue(report["observed_external_dependency_bytes_stable"])
        self.assertFalse(report["external_dependency_pins"][0]["late_import"])
        self.assertFalse(report["runtime_dependency_closure_proven"])
        self.assertEqual(report["native_planning"]["final_resource_state"]["active_lease_count"], 0)


if __name__ == "__main__":
    unittest.main()

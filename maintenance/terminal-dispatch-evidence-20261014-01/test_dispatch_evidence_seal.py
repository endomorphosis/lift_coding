"""Integrity-only sealer refusal tests using explicit temporary public fixtures.

All fixture writes stay in one temporary child of this successor stage. The
copied sealer keeps its real filesystem logic and source bytes. No supervisor,
database, native claim, process birth, provider or proof API is imported.
"""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


STAGE = Path(__file__).resolve().parent
SOURCE = STAGE / "seal_dispatch_evidence.py"


class DispatchEvidenceSealTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix=".test-dispatch-evidence-seal-", dir=STAGE)
        self.root = Path(self.temporary.name)
        self.program = self.root / "seal_dispatch_evidence.py"
        self.program.write_bytes(SOURCE.read_bytes())
        spec = importlib.util.spec_from_file_location("explicit_public_sealer_fixture", self.program)
        self.sealer = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.sealer)
        self.data = self.root / "public.txt"
        self.data.write_bytes(b"Authored public integrity fixture only.\n")
        self.report = self.root / "report.json"
        self.report.write_text(json.dumps({"qualified": True, "synthetic_fixture_only": True}))
        self.config = self.root / "seal-config.json"
        self.manifest = self.root / "integrity-manifest.json"
        self.configure()

    def tearDown(self):
        self.temporary.cleanup()

    def configure(self, *, files=None, reports=None, sort_files=True):
        files = [str(self.data), str(self.report)] if files is None else files
        reports = [str(self.report)] if reports is None else reports
        value = {"schema": "terminal-dispatch-evidence-seal-config@1",
            "files": sorted(files) if sort_files else files, "qualified_reports": reports}
        self.config.write_bytes(self.sealer.wire(value))
        return value

    def launch(self, *, verify=False):
        argv = [sys.executable, "-B", str(self.program), "--config", str(self.config), "--manifest", str(self.manifest)]
        if verify:
            argv.append("--verify")
        result = subprocess.run(argv, cwd=self.root, capture_output=True, check=False, timeout=10)
        return result, json.loads(result.stdout.splitlines()[-1])

    def assert_refused(self, callback, message):
        with self.assertRaisesRegex(ValueError, message):
            callback()

    def test_valid_seal_and_verify_confer_only_integrity(self):
        result, receipt = self.launch()
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        self.assertIs(receipt["qualified"], True)
        self.assertIs(receipt["verified"], False)
        sealed = json.loads(self.manifest.read_bytes())
        self.assertEqual(sealed["file_count"], 4)
        self.assertEqual({row["path"] for row in sealed["files"]},
            {str(self.data), str(self.report), str(self.config), str(self.program)})
        for key in ("cryptographic_authority_conferred", "native_authority_reconstructed",
                    "loaded_code_or_dependency_closure_attested", "worker_observation_emitter_origin_proved",
                    "source_to_model_equivalence_proved", "convergence_proved", "full_task_satisfaction"):
            self.assertIs(sealed[key], False)
        result, receipt = self.launch(verify=True)
        self.assertEqual(result.returncode, 0)
        self.assertIs(receipt["verified"], True)

    def test_changed_public_pin_after_seal_refuses_verify(self):
        self.assertEqual(self.launch()[0].returncode, 0)
        sealed = self.manifest.read_bytes()
        self.data.write_bytes(b"Changed authored public fixture.\n")
        result, receipt = self.launch(verify=True)
        self.assertEqual(result.returncode, 1)
        self.assertIs(receipt["qualified"], False)
        self.assertEqual(receipt["error"], "sealed inventory changed")
        self.assertEqual(self.manifest.read_bytes(), sealed)

    def test_existing_manifest_is_never_overwritten(self):
        self.assertEqual(self.launch()[0].returncode, 0)
        sealed = self.manifest.read_bytes()
        result, receipt = self.launch()
        self.assertEqual(result.returncode, 1)
        self.assertEqual(receipt["error_type"], "FileExistsError")
        self.assertEqual(self.manifest.read_bytes(), sealed)

    def test_same_byte_replacement_during_primary_read_refuses_original_custody(self):
        raw = b"same original public bytes\n" * 5000
        self.data.write_bytes(raw)
        original = self.data.stat()
        replacement = self.root / "replacement.txt"
        replacement.write_bytes(raw)
        os.utime(replacement, ns=(original.st_atime_ns, original.st_mtime_ns))
        real_read = self.sealer.os.read
        replaced = False

        def replace_after_actual_read(fd, count):
            nonlocal replaced
            block = real_read(fd, count)
            actual = os.fstat(fd)
            if block and not replaced and (actual.st_dev, actual.st_ino) == (original.st_dev, original.st_ino):
                os.replace(replacement, self.data)
                replaced = True
            return block

        with patch.object(self.sealer.os, "read", side_effect=replace_after_actual_read):
            self.assert_refused(lambda: self.sealer.capture(str(self.data)), "original public file changed during capture")
        self.assertTrue(replaced)
        self.assertEqual(self.data.read_bytes(), raw)
        self.assertNotEqual(self.data.stat().st_ino, original.st_ino)

    def test_same_byte_replacement_at_fresh_reopen_refuses_identity(self):
        raw = self.data.read_bytes()
        original = self.data.stat()
        replacement = self.root / "replacement.txt"
        replacement.write_bytes(raw)
        os.utime(replacement, ns=(original.st_atime_ns, original.st_mtime_ns))
        real_open = self.sealer.os.open
        opens = 0

        def replace_before_actual_fresh_open(path, *args, **kwargs):
            nonlocal opens
            if os.fspath(path) == str(self.data):
                opens += 1
                if opens == 2:
                    os.replace(replacement, self.data)
            return real_open(path, *args, **kwargs)

        with patch.object(self.sealer.os, "open", side_effect=replace_before_actual_fresh_open):
            self.assert_refused(lambda: self.sealer.capture(str(self.data)), "fresh public file identity differs")
        self.assertEqual(opens, 2)
        self.assertEqual(self.data.read_bytes(), raw)

    def test_growth_during_fresh_read_refuses_before_another_read(self):
        self.data.write_bytes(b"original bounded public bytes")
        real_read = self.sealer.os.read
        nonempty_descriptors = []
        fresh_read_calls = 0
        grew = False

        def grow_after_actual_fresh_read(fd, count):
            nonlocal fresh_read_calls, grew
            block = real_read(fd, count)
            if block and fd not in nonempty_descriptors:
                nonempty_descriptors.append(fd)
            if len(nonempty_descriptors) == 2 and fd == nonempty_descriptors[1]:
                fresh_read_calls += 1
                if block and not grew:
                    with self.data.open("ab") as stream:
                        stream.write(b"concurrent public growth" * 4096)
                        stream.flush()
                        os.fsync(stream.fileno())
                    grew = True
            return block

        with patch.object(self.sealer.os, "read", side_effect=grow_after_actual_fresh_read):
            self.assert_refused(lambda: self.sealer.capture(str(self.data)), "fresh public file exceeds original byte bound")
        self.assertTrue(grew)
        # The second fresh read exceeds the known original count. Refusal must
        # precede an EOF read or an indefinitely growing stream.
        self.assertEqual(fresh_read_calls, 2)

    def test_symlink_is_not_a_named_public_artifact(self):
        link = self.root / "linked-public.txt"
        link.symlink_to(self.data)
        self.assert_refused(lambda: self.sealer.capture(str(link)), "canonical named successor public path")

    def test_hardlink_and_directory_are_not_public_regular_single_links(self):
        hardlink = self.root / "hardlinked-public.txt"
        os.link(self.data, hardlink)
        self.assert_refused(lambda: self.sealer.capture(str(hardlink)), "single-link public regular file")
        directory = self.root / "public-directory"
        directory.mkdir()
        self.assert_refused(lambda: self.sealer.capture(str(directory)), "single-link public regular file")

    def test_duplicate_inventory_is_refused(self):
        self.configure(files=[str(self.data), str(self.data), str(self.report)])
        self.assert_refused(lambda: self.sealer.manifest_for(str(self.config)), "unique sorted explicit inventory")

    def test_unsorted_inventory_is_refused(self):
        self.configure(files=list(reversed(sorted([str(self.data), str(self.report)]))), sort_files=False)
        self.assert_refused(lambda: self.sealer.manifest_for(str(self.config)), "unique sorted explicit inventory")

    def test_private_database_key_git_and_cache_paths_are_excluded(self):
        relatives = ("private.duckdb", "private.db", "private.parquet", "private.key", "private.pyc",
            ".git/objects/synthetic.txt", "__pycache__/synthetic.json", "checkout/data/synthetic.json")
        for name in relatives:
            with self.subTest(name=name):
                path = self.root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b"Excluded synthetic fixture body; no real private data.\n")
                self.assert_refused(lambda: self.sealer.capture(str(path)), "private database/key/Git/cache bodies")

    def test_false_and_nonboolean_qualification_reports_are_refused(self):
        for value in (False, 1, "true", None, [], {}):
            with self.subTest(value=value):
                self.report.write_text(json.dumps({"qualified": value, "synthetic_fixture_only": True}))
                self.assert_refused(lambda: self.sealer.manifest_for(str(self.config)), "selected report has not qualified")

    def test_duplicate_qualification_report_inventory_is_refused(self):
        self.configure(reports=[str(self.report), str(self.report)])
        self.assert_refused(lambda: self.sealer.manifest_for(str(self.config)), "bounded unique qualification reports")

    def test_unsealed_qualification_report_is_refused(self):
        other = self.root / "unselected-report.json"
        other.write_text('{"qualified":true,"synthetic_fixture_only":true}')
        self.configure(reports=[str(other)])
        self.assert_refused(lambda: self.sealer.manifest_for(str(self.config)), "qualification report absent from sealed inventory")

    def test_false_report_replaced_with_true_after_inventory_does_not_qualify_false_pin(self):
        self.report.write_text('{"qualified":false,"synthetic_fixture_only":true}')
        replacement = self.root / "replacement-report.json"
        replacement.write_text('{"qualified":true,"synthetic_fixture_only":true}')
        real_capture = self.sealer.capture
        replaced = False

        def replace_after_actual_report_pin(path, **kwargs):
            nonlocal replaced
            result = real_capture(path, **kwargs)
            if path == str(self.report) and not kwargs.get("body", False) and not replaced:
                os.replace(replacement, self.report)
                replaced = True
            return result

        with patch.object(self.sealer, "capture", side_effect=replace_after_actual_report_pin):
            self.assert_refused(lambda: self.sealer.manifest_for(str(self.config)), "qualification report changed after inventory capture")
        self.assertTrue(replaced)
        self.assertIs(json.loads(self.report.read_bytes())["qualified"], True)

    def test_configuration_mutated_during_inventory_is_refused(self):
        real_capture = self.sealer.capture
        mutated = False

        def mutate_after_actual_data_pin(path, **kwargs):
            nonlocal mutated
            result = real_capture(path, **kwargs)
            if path == str(self.data) and not mutated:
                self.config.write_bytes(self.config.read_bytes() + b"\n")
                mutated = True
            return result

        with patch.object(self.sealer, "capture", side_effect=mutate_after_actual_data_pin):
            self.assert_refused(lambda: self.sealer.manifest_for(str(self.config)), "configuration changed during seal")
        self.assertTrue(mutated)

    def test_duplicate_configuration_json_field_is_refused(self):
        self.config.write_bytes(b'{"schema":"terminal-dispatch-evidence-seal-config@1","schema":"terminal-dispatch-evidence-seal-config@1","files":[],"qualified_reports":[]}')
        self.assert_refused(lambda: self.sealer.manifest_for(str(self.config)), "duplicate JSON field")

    def test_nonfinite_configuration_json_is_refused(self):
        self.config.write_bytes(b'{"schema":"terminal-dispatch-evidence-seal-config@1","files":NaN,"qualified_reports":[]}')
        self.assert_refused(lambda: self.sealer.manifest_for(str(self.config)), "finite JSON required")

    def test_total_inventory_bound_is_checked_with_real_captures(self):
        baseline = self.sealer.manifest_for(str(self.config))
        with patch.object(self.sealer, "MAX_TOTAL_BYTES", baseline["file_bytes"] - 1):
            self.assert_refused(lambda: self.sealer.manifest_for(str(self.config)), "total explicit file byte bound")

    def test_file_census_includes_configuration_and_sealer(self):
        with patch.object(self.sealer, "MAX_FILES", 3):
            self.assert_refused(lambda: self.sealer.manifest_for(str(self.config)), "file census bound")

    def test_json_body_bound_is_checked_before_loading_large_file(self):
        large = self.root / "large-public.json"
        with large.open("wb") as stream:
            stream.truncate(8 * 1024 * 1024 + 1)
        self.assert_refused(lambda: self.sealer.capture(str(large), body=True), "public JSON body exceeds bound")


if __name__ == "__main__":
    unittest.main()

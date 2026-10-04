from __future__ import annotations

import contextlib
import copy
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from audit import digest, json_bytes
from observed_profile import ObservedProfileError, derive_profile, validate_profile
from runtime_demand import qualify
from snapshot_verify import SnapshotError, verify_snapshot


class ObservedProfileTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="codebase-ir-observed-profile-test-")
        self.base = Path(self.temp.name)
        self.root = self.base / "repo"
        self.root.mkdir()
        subprocess.run(["git", "init", "-q", str(self.root)], check=True)
        self.write("pkg/__init__.py", "")
        self.write("pkg/core.py", "from .leaf import VALUE\n")
        self.write("pkg/leaf.py", "VALUE=1\n")
        self.write("pkg/lazy.py", "VALUE=2\n")
        subprocess.run(["git", "-C", str(self.root), "add", "."], check=True)
        subprocess.run(["git", "-C", str(self.root), "-c", "user.name=Observed Qualification",
                        "-c", "user.email=fixture@example.invalid", "commit", "-qm", "source"], check=True)
        self.config = {"repositories": [{"name": "test", "root": str(self.root), "packages": ["pkg"]}],
                       "seeds": ["pkg.core", "pkg.lazy"], "bounds": {"total_timeout": 10}}

    def tearDown(self):
        self.temp.cleanup()

    def write(self, path, data):
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(data)

    def report(self):
        rows = []
        for path in sorted(self.root.glob("pkg/*.py")):
            raw = path.read_bytes()
            module = "pkg" if path.name == "__init__.py" else "pkg." + path.stem
            pin = {"sha256": digest(raw), "size_bytes": len(raw)}
            rows.append({"path": str(path), "module_names": [module], "before": pin,
                         "after": pin.copy(), "unchanged": True})
        return {"schema": "codebase-ir-finite-planning-qualification@1", "status": "passed",
                "runtime_source_mode": "working_tree_observed", "production_qualified": False,
                "imported_native_source_bytes_stable": True, "imported_native_sources": rows}

    def profile(self, report=None):
        return derive_profile(json_bytes(report or self.report()), self.base / "report.json",
                              self.config["repositories"])

    def execute(self, config=None):
        if config is None:
            config = {**self.config, "observed_profile": self.profile()}
        with contextlib.redirect_stdout(io.StringIO()):
            return qualify(config, self.base / "run", import_timeout=2)

    def test_exact_observed_profile_captures_dormant_invocation_module(self):
        result = self.execute()
        self.assertTrue(result["importability_qualified"], result)
        self.assertEqual(len(result["files"]), 4)
        self.assertEqual(result["observed_invocation_profile"]["source_basis"], "recorded_working_source_bytes")
        self.assertTrue(result["snapshot_verification"]["verified"])
        self.assertFalse(result["runtime_closure_proven"])
        for row in result["files"]:
            self.assertEqual(row["kind"], "recorded_invocation_source")

    def test_source_drift_refuses_before_any_probe_or_generation(self):
        config = {**self.config, "observed_profile": self.profile()}
        self.write("pkg/core.py", "VALUE=9\n")
        result = self.execute(config)
        self.assertEqual(result["disposition"], "source_or_snapshot_refusal")
        self.assertIn("source drift", result["error"])
        self.assertFalse(result["importability_qualified"])
        self.assertEqual(result["snapshot_roots"], [])
        self.assertEqual(result["rounds"], [])

    def test_profile_capture_cannot_exceed_fixed_file_or_byte_ceiling(self):
        config = {**self.config, "observed_profile": self.profile(), "bounds": {"max_files": 2}}
        result = self.execute(config)
        self.assertEqual(result["disposition"], "source_or_snapshot_refusal")
        self.assertLessEqual(len(result["files"]), 2)
        self.assertIn("file_limit", {row["disposition"] for row in result["frontier"]})

    def test_unobserved_runtime_demand_is_refused_without_source_mixing(self):
        report = self.report()
        report["imported_native_sources"] = [row for row in report["imported_native_sources"]
                                             if not row["path"].endswith("/leaf.py")]
        result = self.execute({**self.config, "observed_profile": self.profile(report)})
        self.assertFalse(result["importability_qualified"])
        self.assertNotIn("pkg/leaf.py", {row["path"] for row in result["files"]})
        self.assertIn("unrecorded_invocation_source_refused", {row["disposition"] for row in result["frontier"]})

    def test_exact_initial_generation_adds_only_its_pinned_extra_sources(self):
        previous = self.execute(self.config)
        report = self.report()
        report["imported_native_sources"] = [row for row in report["imported_native_sources"]
                                             if not row["path"].endswith("/leaf.py")]
        config = {**self.config, "observed_profile": self.profile(report)}
        with contextlib.redirect_stdout(io.StringIO()):
            result = qualify(config, self.base / "union", initial_snapshot=Path(previous["snapshot_root"]),
                             initial_snapshot_sha256=previous["snapshot_sha256"], import_timeout=2)
        self.assertTrue(result["importability_qualified"], result)
        self.assertEqual(result["initial_snapshot_verification"]["snapshot_sha256"], previous["snapshot_sha256"])
        self.assertIn("pkg/leaf.py", {row["path"] for row in result["files"]})
        self.write("pkg/extra.py", "VALUE=7\n")
        self.write("pkg/core.py", "from .extra import VALUE\n")
        current_report = self.report()
        current_report["imported_native_sources"] = [row for row in current_report["imported_native_sources"]
                                                     if not row["path"].endswith("/extra.py")]
        with contextlib.redirect_stdout(io.StringIO()):
            refused = qualify({**self.config, "observed_profile": self.profile(current_report)},
                              self.base / "changed-union", initial_snapshot=Path(previous["snapshot_root"]),
                              initial_snapshot_sha256=previous["snapshot_sha256"], import_timeout=2)
        self.assertEqual(refused["disposition"], "source_or_snapshot_refusal")
        self.assertEqual(refused["rounds"], [])
        self.assertEqual(refused["initial_snapshot_sha256"], previous["snapshot_sha256"])

    def test_initial_extra_cannot_authorize_arbitrary_unrecorded_demand(self):
        previous = self.execute(self.config)
        self.write("pkg/unrecorded.py", "VALUE=8\n")
        self.write("pkg/new.py", "from .unrecorded import VALUE\n")
        report = self.report()
        report["imported_native_sources"] = [row for row in report["imported_native_sources"]
                                             if not row["path"].endswith("/unrecorded.py")]
        with contextlib.redirect_stdout(io.StringIO()):
            result = qualify({**self.config, "seeds": ["pkg.new"], "observed_profile": self.profile(report)},
                             self.base / "restricted-union", initial_snapshot=Path(previous["snapshot_root"]),
                             initial_snapshot_sha256=previous["snapshot_sha256"], import_timeout=2)
        self.assertFalse(result["importability_qualified"])
        self.assertNotIn("pkg/unrecorded.py", {row["path"] for row in result["files"]})
        self.assertIn("unrecorded_invocation_source_refused", {row["disposition"] for row in result["frontier"]})

    def test_duplicate_paths_keys_invalid_pin_types_and_changed_records_refuse(self):
        for mutation in ("duplicate", "size_bool", "changed", "extra", "module_alias"):
            with self.subTest(mutation=mutation):
                report = self.report()
                row = report["imported_native_sources"][0]
                if mutation == "duplicate":
                    report["imported_native_sources"].append(copy.deepcopy(row))
                elif mutation == "size_bool":
                    row["before"]["size_bytes"] = True
                elif mutation == "changed":
                    row["after"]["sha256"] = "0" * 64
                elif mutation == "extra":
                    row["unexpected"] = "payload"
                else:
                    report["imported_native_sources"][1]["module_names"].append(row["module_names"][0])
                with self.assertRaises(ObservedProfileError):
                    self.profile(report)
        with self.assertRaisesRegex(ObservedProfileError, "duplicate observation JSON key"):
            derive_profile(b'{"schema":1,"schema":2}', self.base / "report.json", self.config["repositories"])

    def test_foreign_and_symlinked_source_and_forged_normalization_refuse(self):
        report = self.report()
        report["imported_native_sources"][0]["path"] = str(self.base / "foreign.py")
        with self.assertRaisesRegex(ObservedProfileError, "package owner"):
            self.profile(report)
        profile = self.profile()
        profile["files"][0]["repository"] = "foreign"
        profile["profile_sha256"] = digest(json_bytes({k: v for k, v in profile.items() if k != "profile_sha256"}))
        with self.assertRaisesRegex(ObservedProfileError, "ownership or population"):
            validate_profile(profile, self.config["repositories"])
        (self.root / "pkg/alias.py").symlink_to(self.root / "pkg/core.py")
        with self.assertRaisesRegex(ObservedProfileError, "canonical"):
            self.profile()

    def test_late_import_has_no_before_pin_and_remains_explicitly_unqualified(self):
        report = self.report()
        report["imported_native_sources"][0]["before"] = None
        report["imported_native_sources"][0]["unchanged"] = False
        profile = self.profile(report)
        self.assertEqual(len(profile["late_imports_unqualified"]), 1)
        self.assertEqual(len(validate_profile(profile, self.config["repositories"])), 3)
        self.assertFalse(profile["function_invocation_closure_proven"])

    def test_snapshot_verifier_rejects_wrong_roots_identity_bytes_and_extra_files(self):
        result = self.execute()
        root = Path(result["snapshot_root"])
        identity = result["snapshot_sha256"]
        verified = verify_snapshot(root, identity, expected_roots=[root / "test"])
        self.assertEqual(verified["file_count"], 4)
        with self.assertRaises(SnapshotError):
            verify_snapshot(root, "0" * 64)
        with self.assertRaises(SnapshotError):
            verify_snapshot(root, identity, expected_roots=[self.root])
        with self.assertRaisesRegex(SnapshotError, "aggregate byte"):
            verify_snapshot(root, identity, max_bytes=1)
        module = root / "test/pkg/leaf.py"
        module.chmod(0o644)
        module.write_text("VALUE=9\n")
        module.chmod(0o444)
        with self.assertRaisesRegex(SnapshotError, "exact pin"):
            verify_snapshot(root, identity)

    def test_snapshot_verifier_rejects_extra_directory_symlink_and_bool_generation(self):
        result = self.execute()
        root = Path(result["snapshot_root"])
        identity = result["snapshot_sha256"]
        root.chmod(0o755)
        extra = root / "empty"
        extra.mkdir(mode=0o555)
        root.chmod(0o555)
        with self.assertRaises(SnapshotError):
            verify_snapshot(root, identity, expected_roots=[root / "test"])
        root.chmod(0o755)
        extra.rmdir()
        alias = root / "alias"
        alias.symlink_to(root / "test", target_is_directory=True)
        root.chmod(0o555)
        with self.assertRaises(SnapshotError):
            verify_snapshot(root, identity)
        root.chmod(0o755)
        alias.unlink()
        manifest = json.loads((root / "snapshot.json").read_bytes())
        manifest["generation"] = True
        identity = digest(json_bytes({k: v for k, v in manifest.items() if k != "snapshot_sha256"}))
        manifest["snapshot_sha256"] = identity
        (root / "snapshot.json").chmod(0o644)
        (root / "snapshot.json").write_bytes(json_bytes(manifest))
        (root / "snapshot.json").chmod(0o444)
        root.chmod(0o555)
        with self.assertRaisesRegex(SnapshotError, "schema"):
            verify_snapshot(root, identity)

    def test_snapshot_verifier_rejects_sealed_unlisted_fifo_without_opening(self):
        result = self.execute()
        root = Path(result["snapshot_root"])
        root.chmod(0o755)
        os.mkfifo(root / "unexpected-fifo", 0o444)
        root.chmod(0o555)
        with self.assertRaisesRegex(SnapshotError, "non-regular"):
            verify_snapshot(root, result["snapshot_sha256"])


if __name__ == "__main__":
    unittest.main()

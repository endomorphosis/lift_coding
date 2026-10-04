from __future__ import annotations

import copy
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import retained_snapshot as snapshot
from audit import digest, json_bytes
from snapshot_verify import verify_snapshot


class RetainedSnapshotTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="codebase-ir-retained-snapshot-test-")
        self.workspace = Path(self.temp.name).resolve()
        self.root = self.workspace / "external/repo"
        self.root.mkdir(parents=True)
        self.config = {"repositories": [{"name": "test", "root": str(self.root), "packages": ["pkg"]}]}
        self.fixture = self.workspace / "artifacts/fixture"
        self.fixture.mkdir(parents=True)
        (self.fixture / "result.json").write_bytes(json_bytes({"schema": "finite-repository-admission-qualification@1", "status": "completed"}))
        self.source_before = self.workspace / "artifacts/tests/critical-source-before.json"
        self.source_after = self.source_before.with_name("critical-source-after.json")
        self.source_before.parent.mkdir(parents=True)
        self.original = {"pkg/__init__.py": b"", "pkg/core.py": b"VALUE='original'\n"}
        critical = []
        for path, raw in self.original.items():
            live = self.root / path
            live.parent.mkdir(parents=True, exist_ok=True)
            live.write_bytes(raw)
            retained = self.source_before.parent / "sources" / live.relative_to(self.workspace)
            retained.parent.mkdir(parents=True, exist_ok=True)
            retained.write_bytes(raw)
            critical.append({"path": str(live), "sha256": digest(raw), "size_bytes": len(raw), "retained_source": str(retained)})
        self.before = {"schema": "finite-admission-critical-producer-snapshot@1", "scope": "exact original copies",
                       "source_count": 2, "sources": critical}
        self.after = {**self.before, "sources": [{key: value for key, value in row.items() if key != "retained_source"}
                                                for row in critical], "changed_paths": []}
        self.prior = self.workspace / "prior"
        (self.prior / "test").mkdir(parents=True)
        prior_files = []
        for path, raw in {**self.original, "pkg/prior_extra.py": b"VALUE=2\n"}.items():
            target = self.prior / "test" / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(raw)
            target.chmod(0o444)
            prior_files.append({"repository": "test", "path": path, "sha256": digest(raw), "bytes": len(raw)})
        self.prior_manifest = {"schema": "codebase-ir-runtime-demand/v1", "generation": 0,
                               "parent_snapshot_sha256": None, "files": prior_files, "namespace_directories": []}
        self.prior_sha = digest(json_bytes(self.prior_manifest))
        self.prior_manifest["snapshot_sha256"] = self.prior_sha
        (self.prior / "snapshot.json").write_bytes(json_bytes(self.prior_manifest))
        (self.prior / "snapshot.json").chmod(0o444)
        for directory in sorted((path for path in self.prior.rglob("*") if path.is_dir()), reverse=True):
            directory.chmod(0o555)
        self.prior.chmod(0o555)
        (self.root / "pkg/core.py").write_bytes(b"VALUE='changed-current'\n")
        imports = []
        for path in self.original:
            live = self.root / path
            raw = live.read_bytes()
            module = path[:-3].replace("/", ".").removesuffix(".__init__")
            pin = {"sha256": digest(raw), "size_bytes": len(raw)}
            imports.append({"path": str(live), "module_names": [module], "before": pin, "after": pin.copy(), "unchanged": True})
        self.history = {"schema": "codebase-ir-owner-local-historical-replay@1", "status": "refused",
                        "runtime_source_mode": "working_tree_observed_read_only", "read_files_unchanged": True,
                        "observed_current": False, "native_observation_or_proof_invoked": False,
                        "worker_launched": False, "training_steps": 0,
                        "import_observations": {"schema": "codebase-ir-historical-read-only-import-observation@1",
                            "core_package_roots": [str(self.root)], "modules": imports,
                            "source_bytes_total": sum(row["before"]["size_bytes"] for row in imports),
                            "complete_import_closure_claimed": False}}
        self.history_path = self.workspace / "history.json"

    def tearDown(self):
        self.temp.cleanup()

    def execute(self, *, name="run", historical_sha=None):
        self.history_path.write_bytes(json_bytes(self.history))
        self.source_before.write_bytes(json_bytes(self.before))
        self.source_after.write_bytes(json_bytes(self.after))
        return snapshot.seal_retained_sources(historical_report=self.history_path,
                   historical_report_sha256=historical_sha or digest(self.history_path.read_bytes()),
                   fixture=self.fixture, source_before=self.source_before,
                   source_before_sha256=digest(self.source_before.read_bytes()), source_after=self.source_after,
                   source_after_sha256=digest(self.source_after.read_bytes()), initial_snapshot=self.prior,
                   initial_snapshot_sha256=self.prior_sha, workspace=self.workspace,
                   config=self.config, output=self.workspace / name)

    def test_verified_retained_override_repairs_private_copy_without_live_source_write(self):
        current_before = (self.root / "pkg/core.py").read_bytes()
        result = self.execute()
        self.assertEqual(result["disposition"], "snapshot_sealed", result.get("error"))
        root = Path(result["snapshot_root"])
        self.assertEqual((root / "test/pkg/core.py").read_bytes(), self.original["pkg/core.py"])
        self.assertEqual((self.root / "pkg/core.py").read_bytes(), current_before)
        self.assertEqual(result["counts"]["retained_overrides"], 1)
        self.assertEqual(result["counts"]["files"], 3)
        self.assertFalse(result["current_freshness_verified"])
        self.assertFalse(result["native_execution_performed"])
        self.assertTrue(verify_snapshot(root, result["snapshot_sha256"])["verified"])

    def test_input_artifact_sha_duplicate_original_bool_and_late_import_refuse(self):
        wrong = self.execute(name="wrong", historical_sha="0" * 64)
        self.assertEqual(wrong["disposition"], "retained_snapshot_refused")
        original_before, original_history = copy.deepcopy(self.before), copy.deepcopy(self.history)
        for mutation in ("duplicate", "bool", "late"):
            self.before, self.history = copy.deepcopy(original_before), copy.deepcopy(original_history)
            if mutation == "duplicate":
                self.before["sources"].append(copy.deepcopy(self.before["sources"][0]))
                self.before["source_count"] += 1
            elif mutation == "bool":
                self.before["source_count"] = True
            else:
                self.history["import_observations"]["modules"][0]["before"] = None
                self.history["import_observations"]["modules"][0]["unchanged"] = False
            result = self.execute(name=mutation)
            self.assertEqual(result["disposition"], "retained_snapshot_refused", mutation)

    def test_only_actual_historical_trial_statuses_are_accepted(self):
        self.history["status"] = "passed"
        result = self.execute(name="passed-status")
        self.assertEqual(result["disposition"], "snapshot_sealed", result.get("error"))
        self.history["status"] = "verified"
        result = self.execute(name="unrecognized-status")
        self.assertEqual(result["disposition"], "retained_snapshot_refused")

    def test_retained_copy_corruption_live_substitution_and_symlink_refuse(self):
        original = copy.deepcopy(self.before)
        for mutation in ("corruption", "live_substitution", "symlink"):
            self.before = copy.deepcopy(original)
            row = self.before["sources"][1]
            retained = Path(row["retained_source"])
            retained.write_bytes(self.original["pkg/core.py"])
            if mutation == "corruption":
                retained.write_bytes(b"unrecorded payload")
            elif mutation == "live_substitution":
                row["retained_source"] = row["path"]
            else:
                retained.unlink()
                retained.symlink_to(self.root / "pkg/core.py")
            result = self.execute(name=mutation)
            self.assertEqual(result["disposition"], "retained_snapshot_refused", mutation)
            if retained.is_symlink():
                retained.unlink()

    def test_changed_unretained_current_source_cannot_fall_back_to_fresh_bytes(self):
        late = self.root / "pkg/observed_only.py"
        late.write_bytes(b"VALUE='observed'\n")
        pin = {"sha256": digest(late.read_bytes()), "size_bytes": late.stat().st_size}
        self.history["import_observations"]["modules"].append({"path": str(late), "module_names": ["pkg.observed_only"],
                                                              "before": pin, "after": pin.copy(), "unchanged": True})
        self.history["import_observations"]["source_bytes_total"] += pin["size_bytes"]
        late.write_bytes(b"VALUE='fresh-unrecorded'\n")
        result = self.execute()
        self.assertEqual(result["disposition"], "retained_snapshot_refused")
        self.assertIn("declared pin", result["error"])

    def test_conflicting_observed_and_prior_pin_without_original_override_refuses(self):
        extra = self.root / "pkg/prior_extra.py"
        extra.write_bytes(b"VALUE='foreign'\n")
        pin = {"sha256": digest(extra.read_bytes()), "size_bytes": extra.stat().st_size}
        self.history["import_observations"]["modules"].append({"path": str(extra), "module_names": ["pkg.prior_extra"],
                                                              "before": pin, "after": pin.copy(), "unchanged": True})
        self.history["import_observations"]["source_bytes_total"] += pin["size_bytes"]
        result = self.execute()
        self.assertEqual(result["disposition"], "retained_snapshot_refused")
        self.assertIn("conflicting same-original-path", result["error"])

    def test_unrecorded_ancestor_initializer_is_not_silently_captured(self):
        nested = self.root / "pkg/child/core.py"
        nested.parent.mkdir()
        nested.write_bytes(b"VALUE=4\n")
        (nested.parent / "__init__.py").write_bytes(b"UNRECORDED=True\n")
        pin = {"sha256": digest(nested.read_bytes()), "size_bytes": nested.stat().st_size}
        self.history["import_observations"]["modules"].append({"path": str(nested), "module_names": ["pkg.child.core"],
                                                              "before": pin, "after": pin.copy(), "unchanged": True})
        self.history["import_observations"]["source_bytes_total"] += pin["size_bytes"]
        result = self.execute()
        self.assertEqual(result["disposition"], "retained_snapshot_refused")
        self.assertIn("unrecorded ancestor", result["error"])

    def test_fixed_file_byte_ceilings_refuse_before_any_generation(self):
        for variable in ("MAX_FILES", "MAX_BYTES"):
            with patch.object(snapshot, variable, 1):
                result = self.execute(name=variable)
            self.assertEqual(result["disposition"], "retained_snapshot_refused")
            self.assertFalse((self.workspace / variable / "snapshots").exists())

    def test_retained_bytes_changed_after_capture_refuse_sealing(self):
        original = snapshot.Reader.read
        retained_path = Path(self.before["sources"][1]["retained_source"])
        def read_then_change(reader, path, *args, **kwargs):
            raw = original(reader, path, *args, **kwargs)
            if path == retained_path:
                path.write_bytes(b"VALUE='drift-during-capture'\n")
            return raw
        with patch.object(snapshot.Reader, "read", read_then_change):
            result = self.execute()
        self.assertEqual(result["disposition"], "retained_snapshot_refused")
        self.assertFalse(result["source_stability"]["stable"])


if __name__ == "__main__":
    unittest.main()

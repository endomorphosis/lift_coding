from __future__ import annotations

import copy
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import retained_snapshot as sealer
import retained_supplement as supplement
import test_retained_snapshot as retained_controls
from audit import digest, json_bytes
from snapshot_verify import verify_snapshot


class RetainedSupplementTests(unittest.TestCase):
    def setUp(self):
        self.factory = retained_controls.RetainedSnapshotTests("runTest")
        self.factory.setUp()
        self.addCleanup(self.factory.tearDown)
        self.workspace = self.factory.workspace
        self.legacy = self.workspace / "legacy"
        files = {**self.factory.original, "pkg/prior_extra.py": b"VALUE=2\n",
                 "pkg/frontier.py": b"from .sub import leaf\ndef lazy():\n    import pkg.helper\n",
                 "pkg/sub/__init__.py": b"from .leaf import VALUE\n",
                 "pkg/sub/leaf.py": b"from .. import helper\nVALUE=4\n",
                 "pkg/helper.py": b"VALUE=3\n"}
        self.rows = []
        for relative, raw in sorted(files.items()):
            path = self.legacy / "test" / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
            path.chmod(0o444)
            self.rows.append({"repository": "test", "path": relative, "sha256": digest(raw), "bytes": len(raw)})
        self.manifest = {"schema": "codebase-ir-release-audit/v1", "source": "captured_closure_bytes",
                         "files": self.rows, "manifest_sha256": digest(json_bytes(self.rows))}
        (self.legacy / "snapshot.json").write_bytes(json_bytes(self.manifest))
        (self.legacy / "snapshot.json").chmod(0o444)
        for path in sorted((p for p in self.legacy.rglob("*") if p.is_dir()), reverse=True):
            path.chmod(0o555)
        self.legacy.chmod(0o555)
        stable = {"stable": True, "files": [{"repository": row["repository"], "path": row["path"],
                   "before_sha256": row["sha256"], "after_sha256": row["sha256"], "stable": True} for row in self.rows],
                  "heads": [{"repository": "test", "before": "a" * 40, "after": "a" * 40}]}
        self.report = {"schema": self.manifest["schema"], "runtime_closure_proven": False,
                       "static_closure_complete": False, "files": [{**row, "git_status": "tracked_clean"} for row in self.rows],
                       "source_stability": stable, "source_stability_after_probes": copy.deepcopy(stable)}
        self.report_path = self.workspace / "source-report.json"
        prior = verify_snapshot(self.factory.prior, self.factory.prior_sha)
        self.frontier = {"schema": "codebase-ir-owner-local-historical-replay@1", "status": "unavailable",
            "runtime_source_mode": "sealed_snapshot_read_only", "blocker": "ImportError: historical core import unavailable: pkg.frontier",
            "requested_runtime_snapshot_sha256": self.factory.prior_sha, "runtime_snapshot_identity_stable": True,
            "runtime_snapshot_before": prior, "runtime_snapshot_after": copy.deepcopy(prior), "observed_current": False,
            "worker_launched": False, "native_observation_or_proof_invoked": False, "training_steps": 0, "read_files_unchanged": True}
        self.frontier_path = self.workspace / "frontier-report.json"

    def build(self, *, manifest_sha=None, **extra):
        self.report_path.write_bytes(json_bytes(self.report))
        self.frontier_path.write_bytes(json_bytes(self.frontier))
        return supplement.build_profile(snapshot_root=self.legacy,
            snapshot_manifest_sha256=manifest_sha or digest((self.legacy / "snapshot.json").read_bytes()),
            source_report=self.report_path, source_report_sha256=digest(self.report_path.read_bytes()),
            frontier_report=self.frontier_path, frontier_report_sha256=digest(self.frontier_path.read_bytes()), module="pkg.frontier",
            initial_snapshot=self.factory.prior, initial_snapshot_sha256=self.factory.prior_sha, config=self.factory.config, **extra)

    def copied_metadata(self):
        before_path = self.workspace / "copied-source-metadata/source-closure-before.json"
        before_path.parent.mkdir(exist_ok=True)
        sources = []
        for row in self.rows:
            original = self.factory.root / row["path"]
            retained = before_path.parent / "sources" / original.relative_to(self.workspace)
            retained.parent.mkdir(parents=True, exist_ok=True)
            retained.write_bytes((self.legacy / row["repository"] / row["path"]).read_bytes())
            sources.append({"path": str(original), "retained_source": str(retained),
                            "sha256": row["sha256"], "size_bytes": row["bytes"]})
        before = {"schema": "finite-admission-selected-source-snapshot@1", "scope": "selected static original copies",
                  "source_count": len(sources), "sources": sources}
        after = {**before, "sources": [{key: value for key, value in row.items() if key != "retained_source"} for row in sources], "changes": []}
        after_path = before_path.with_name("source-closure-after.json")
        return before_path, after_path, before, after

    def copied_arguments(self, before_path, after_path, before, after):
        before_path.write_bytes(json_bytes(before))
        after_path.write_bytes(json_bytes(after))
        return {"retained_before": before_path, "retained_before_sha256": digest(before_path.read_bytes()),
                "retained_after": after_path, "retained_after_sha256": digest(after_path.read_bytes()), "workspace": self.workspace}

    def test_transitive_lazy_imports_and_new_package_initializer_are_retained_only(self):
        original = supplement.Capture.read_regular
        reads = []
        def read(path, limit):
            reads.append(path)
            return original(path, limit)
        with patch.object(supplement.Capture, "read_regular", staticmethod(read)):
            profile, capture = self.build()
        self.assertEqual({row["module"] for row in profile["selected_files"]}, {"pkg.frontier", "pkg.helper", "pkg.sub", "pkg.sub.leaf"})
        self.assertEqual(profile["counts"]["union_files"], 7)
        self.assertTrue(capture.stability()["stable"])
        self.assertFalse(any(path.is_relative_to(self.factory.root) for path in reads))
        self.assertFalse(profile["runtime_closure_proven"])
        self.assertFalse(profile["original_whole_producer_closure_replayed"])
        supplement.verify_profile(profile, initial_snapshot=self.factory.prior, initial_snapshot_sha256=self.factory.prior_sha,
                                  config=self.factory.config)

    def test_wrong_manifest_pin_duplicate_path_and_boolean_size_refuse(self):
        with self.assertRaises(ValueError):
            self.build(manifest_sha="0" * 64)
        original = copy.deepcopy(self.manifest)
        for mutation in ("duplicate", "bool"):
            self.manifest = copy.deepcopy(original)
            if mutation == "duplicate":
                self.manifest["files"].append(copy.deepcopy(self.manifest["files"][0]))
            else:
                self.manifest["files"][0]["bytes"] = True
            self.manifest["manifest_sha256"] = digest(json_bytes(self.manifest["files"]))
            (self.legacy / "snapshot.json").chmod(0o644)
            (self.legacy / "snapshot.json").write_bytes(json_bytes(self.manifest))
            (self.legacy / "snapshot.json").chmod(0o444)
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                self.build()

    def test_source_report_pin_population_and_before_after_stability_refuse(self):
        original = copy.deepcopy(self.report)
        for mutation in ("missing", "pin", "after", "headbool"):
            self.report = copy.deepcopy(original)
            if mutation == "missing":
                self.report["files"].pop()
            elif mutation == "pin":
                self.report["files"][0]["sha256"] = "0" * 64
            elif mutation == "after":
                self.report["source_stability_after_probes"]["files"][0]["after_sha256"] = "0" * 64
            else:
                self.report["source_stability"]["heads"][0].update(before=True, after=True)
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                self.build()

    def test_exact_sealed_trial_module_and_prior_generation_binding_refuse(self):
        original = copy.deepcopy(self.frontier)
        for mutation in ("module", "identity", "boolgeneration", "unstable", "trainingbool"):
            self.frontier = copy.deepcopy(original)
            if mutation == "module":
                self.frontier["blocker"] += ".foreign"
            elif mutation == "identity":
                self.frontier["requested_runtime_snapshot_sha256"] = "0" * 64
            elif mutation == "boolgeneration":
                self.frontier["runtime_snapshot_before"]["generation"] = False
                self.frontier["runtime_snapshot_after"]["generation"] = False
            elif mutation == "unstable":
                self.frontier["read_files_unchanged"] = False
            else:
                self.frontier["training_steps"] = False
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                self.build()

    def test_unlisted_regular_fifo_symlink_and_writable_legacy_entries_refuse(self):
        path = self.legacy / "test/pkg/unlisted.py"
        for mutation in ("file", "fifo", "symlink", "writable"):
            path.parent.chmod(0o755)
            if mutation == "file":
                path.write_bytes(b"UNRECORDED=True\n")
            elif mutation == "fifo":
                os.mkfifo(path)
            elif mutation == "symlink":
                path.symlink_to(self.factory.root / "pkg/core.py")
            else:
                (self.legacy / "test/pkg/frontier.py").chmod(0o644)
            if not path.is_symlink() and path.exists():
                path.chmod(0o444)
            path.parent.chmod(0o555)
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                self.build()
            path.parent.chmod(0o755)
            if path.exists():
                path.unlink()
            path.parent.chmod(0o555)

    def test_source_byte_corruption_and_changed_after_capture_refuse(self):
        path = self.legacy / "test/pkg/frontier.py"
        original = path.read_bytes()
        path.chmod(0o644)
        path.write_bytes(b"unrecorded source")
        path.chmod(0o444)
        with self.assertRaises(ValueError):
            self.build()
        path.chmod(0o644)
        path.write_bytes(original)
        path.chmod(0o444)
        reader = supplement.Capture.read
        def read_then_change(capture, selected, *args, **kwargs):
            raw = reader(capture, selected, *args, **kwargs)
            if selected == path:
                path.chmod(0o644)
                path.write_bytes(b"changed after pin")
                path.chmod(0o444)
            return raw
        with patch.object(supplement.Capture, "read", read_then_change), self.assertRaises(ValueError):
            self.build()

    def test_union_budgets_and_unrecorded_transitive_source_refuse(self):
        for name in ("MAX_FILES", "MAX_BYTES", "MAX_IMPORTS", "MAX_AST_NODES"):
            with self.subTest(name=name), patch.object(supplement, name, 1), self.assertRaises(ValueError):
                self.build()
        path = self.legacy / "test/pkg/frontier.py"
        path.chmod(0o644)
        raw = b"import pkg.not_retained\n"
        path.write_bytes(raw)
        path.chmod(0o444)
        for row in self.manifest["files"]:
            if row["path"] == "pkg/frontier.py":
                row.update(sha256=digest(raw), bytes=len(raw))
        self.manifest["manifest_sha256"] = digest(json_bytes(self.manifest["files"]))
        (self.legacy / "snapshot.json").chmod(0o644)
        (self.legacy / "snapshot.json").write_bytes(json_bytes(self.manifest))
        (self.legacy / "snapshot.json").chmod(0o444)
        self.report["files"] = copy.deepcopy(self.manifest["files"])
        for field in ("source_stability", "source_stability_after_probes"):
            for row in self.report[field]["files"]:
                if row["path"] == "pkg/frontier.py":
                    row.update(before_sha256=digest(raw), after_sha256=digest(raw))
        with self.assertRaisesRegex(ValueError, "local import frontier"):
            self.build()

    def test_profile_cannot_add_unrelated_source_or_change_exact_types(self):
        profile, _ = self.build()
        for mutation in ("unrelated", "bool", "extra"):
            changed = copy.deepcopy(profile)
            if mutation == "unrelated":
                changed["selected_files"].append({**self.rows[0], "module": "pkg.core", "reason": {}})
            elif mutation == "bool":
                changed["counts"]["selected_files"] = True
            else:
                changed["arbitrary_sources"] = True
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                supplement.verify_profile(changed, initial_snapshot=self.factory.prior,
                    initial_snapshot_sha256=self.factory.prior_sha, config=self.factory.config)

    def test_original_retained_copy_pair_has_separate_exact_provenance(self):
        before_path, after_path, before, after = self.copied_metadata()
        profile, capture = self.build(**self.copied_arguments(before_path, after_path, before, after))
        self.assertEqual(profile["retained_source_pair"]["metadata_source_count"], 7)
        self.assertFalse(profile["retained_source_pair"]["all_metadata_source_bytes_requalified"])
        self.assertTrue(all(row["origin"] == "original_retained_dependency_copy" for row in profile["selected_files"]))
        self.assertTrue(capture.stability()["stable"])
        supplement.verify_profile(profile, initial_snapshot=self.factory.prior, initial_snapshot_sha256=self.factory.prior_sha,
                                  config=self.factory.config)

    def test_original_retained_pair_duplicates_bool_changes_and_alias_mapping_refuse(self):
        before_path, after_path, original_before, original_after = self.copied_metadata()
        for mutation in ("duplicate", "boolcount", "boolsize", "changes", "copy_alias", "after_pin"):
            before, after = copy.deepcopy(original_before), copy.deepcopy(original_after)
            if mutation == "duplicate":
                before["sources"].append(copy.deepcopy(before["sources"][0]))
                after["sources"].append(copy.deepcopy(after["sources"][0]))
                before["source_count"] += 1
                after["source_count"] += 1
            elif mutation == "boolcount":
                before["source_count"] = True
            elif mutation == "boolsize":
                before["sources"][0]["size_bytes"] = True
                after["sources"][0]["size_bytes"] = True
            elif mutation == "changes":
                after["changes"] = [after["sources"][0]["path"]]
            elif mutation == "copy_alias":
                before["sources"][0]["retained_source"] = before["sources"][0]["path"]
            else:
                after["sources"][0]["sha256"] = "0" * 64
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                self.build(**self.copied_arguments(before_path, after_path, before, after))

    def test_selected_original_copy_corruption_symlink_and_stale_artifact_pin_refuse(self):
        before_path, after_path, before, after = self.copied_metadata()
        target = next(row for row in before["sources"] if row["path"].endswith("/frontier.py"))
        path = Path(target["retained_source"])
        original = path.read_bytes()
        args = self.copied_arguments(before_path, after_path, before, after)
        before_path.write_bytes(before_path.read_bytes() + b" ")
        with self.assertRaises(ValueError):
            self.build(**args)
        for mutation in ("bytes", "symlink"):
            args = self.copied_arguments(before_path, after_path, before, after)
            path.write_bytes(original)
            if mutation == "bytes":
                path.write_bytes(b"foreign copy")
            else:
                path.unlink()
                path.symlink_to(self.legacy / "test/pkg/frontier.py")
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                self.build(**args)
            if path.is_symlink():
                path.unlink()

    def test_original_copy_metadata_cap_is_independent_from_selected_body_caps(self):
        before_path, after_path, before, after = self.copied_metadata()
        args = self.copied_arguments(before_path, after_path, before, after)
        with patch.object(supplement, "MAX_RETAINED_METADATA_FILES", 1), self.assertRaises(ValueError):
            self.build(**args)
        profile, _ = self.build(**args)
        altered = copy.deepcopy(profile)
        altered["retained_source_pair"]["metadata_source_count"] = True
        with self.assertRaises(ValueError):
            supplement.verify_profile(altered, initial_snapshot=self.factory.prior, initial_snapshot_sha256=self.factory.prior_sha,
                                      config=self.factory.config)

    def test_sealer_copies_only_verified_supplement_and_records_earlier_basis(self):
        profile, _ = self.build()
        profile_path = self.workspace / "supplement.json"
        profile_path.write_bytes(json_bytes(profile))
        factory = self.factory
        factory.history_path.write_bytes(json_bytes(factory.history))
        factory.source_before.write_bytes(json_bytes(factory.before))
        factory.source_after.write_bytes(json_bytes(factory.after))
        result = sealer.seal_retained_sources(historical_report=factory.history_path,
            historical_report_sha256=digest(factory.history_path.read_bytes()), fixture=factory.fixture,
            source_before=factory.source_before, source_before_sha256=digest(factory.source_before.read_bytes()),
            source_after=factory.source_after, source_after_sha256=digest(factory.source_after.read_bytes()),
            initial_snapshot=factory.prior, initial_snapshot_sha256=factory.prior_sha, workspace=self.workspace,
            config=factory.config, output=self.workspace / "sealed-output", supplemental_profile=profile_path,
            supplemental_profile_sha256=digest(profile_path.read_bytes()))
        self.assertEqual(result["disposition"], "snapshot_sealed", result.get("error"))
        self.assertEqual(result["counts"]["files"], 7)
        self.assertEqual(result["counts"]["supplemental_earlier_static_files"], 4)
        self.assertTrue(result["supplemental_source_stability"]["stable"])
        self.assertEqual(sum(row["selected_origin"] == "verified_earlier_static_capture" for row in result["source_origins"]), 4)


if __name__ == "__main__":
    unittest.main()

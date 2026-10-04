"""Relocated retained native join subsets preserve roles and original unknowns."""
from __future__ import annotations

import copy
import json
import unittest
from dataclasses import replace
from unittest import mock

import codebase_ir_corpus_audit as audit
import codebase_ir_retained_join as join
import test_codebase_ir_closure_requests as closure_controls


class RetainedJoinControls(unittest.TestCase):
    def setUp(self):
        factory = closure_controls.ClosureEvidenceControls("runTest")
        factory.setUp()
        self.addCleanup(factory.doCleanups)
        self.root = factory.root
        self.source = self.root / "relocated"
        self.source.mkdir()
        _, parent, child = factory.inputs()
        checkpoints = {}
        feature = {"schema": "authored-fixed-basis@1", "columns": ["operator:add", "name:n"]}
        for label in ("root", "child"):
            checkpoint = json.loads((self.root / (label + ".json")).read_bytes())
            checkpoint.update(contract={"schema": "authored-contract@1"}, feature_space=feature, state={"not_replayed": True})
            checkpoint["report"].update(contract_sha256="a" * 64, feature_space_sha256=audit._sha(audit._canonical(feature)))
            checkpoint["report"]["codebase_provenance"].update(contract_sha256="a" * 64,
                                                                 feature_space_sha256=checkpoint["report"]["feature_space_sha256"])
            checkpoints[label] = checkpoint
        for path in join.CONTEXT_PATHS:
            label = path.split("-", 1)[0]
            checkpoint, parent_id = checkpoints[label], None if label == "root" else "root"
            raw = audit._canonical(checkpoint)
            lineage = []
            for version in (["root"] if label == "root" else ["child", "root"]):
                item = checkpoints[version]
                data = audit._canonical(item)
                lineage.append({"checkpoint": item, "version": {"version_id": version,
                    "parent_version_id": None if version == "root" else "root", "variant_id": "fixture:variant",
                    "artifact": {"sha256": audit._sha(data), "bytes": len(data)}, "metadata": {}}})
            head = checkpoint["report"]["codebase_provenance"]["head"]
            record = {"schema": "codebase-source-feature-training@1", "version_id": label, "parent_version_id": parent_id,
                      "head": head, "registry_artifact": {"sha256": audit._sha(raw), "bytes": len(raw)},
                      "checkpoint_raw_cid": audit._raw_source_cid(raw), "training_performed_during_load": False,
                      "authority": {"proof_authority": False},
                      "model_head_selected": False, "report_json": audit._canonical(checkpoint["report"]).decode()}
            directory = self.source / path
            directory.mkdir()
            artifacts = {}
            for name, value in (("checkpoint", checkpoint), ("lineage", lineage), ("record", record)):
                data = audit._canonical(value)
                (directory / (name + ".json")).write_bytes(data)
                artifacts[name] = {"schema": "supervisor-codebase-feature-blob@1", "role": name,
                                   "relative_path": name + ".json", "sha256": audit._sha(data), "size_bytes": len(data),
                                   "blob_cid": "claim:opaque"}
            context = {"schema": "supervisor-codebase-feature-context@1", "profile": "codebase_ir/source_bound_feature_v1",
                       "mode": "frozen" if "frozen" in path else "train", "authority": {"proof_authority": False},
                       "version_id": label, "parent_version_id": parent_id, "head": head, "artifacts": artifacts,
                       "candidate_checkpoint_raw_cid": audit._raw_source_cid(raw), "contract_sha256": "a" * 64,
                       "feature_space_sha256": checkpoint["report"]["feature_space_sha256"], "context_cid": "claim:context",
                       "state_sha256": "b" * 64}
            (directory / "context.json").write_bytes(audit._canonical(context))
        result = {"schema": "finite-repository-reviewed-candidate-qualification@1", "status": "completed",
                  "output": "/original/retained-owner-root", "root_measurement": {"version_id": "root"},
                  "child_measurement": {"version_id": "child"}, "original_head": parent["head"], "successor_head": child["head"],
                  "continuation": {"parent_version_id": "root", "child_version_id": "child"},
                  "inventory_paths": ["train.py", "tune.py", "canary.py", "metadata_only.py"]}
        (self.source / "result.json").write_bytes(audit._canonical(result))
        pins = [{"path": path.relative_to(self.source).as_posix(), "sha256": audit._sha(path.read_bytes()),
                 "bytes": path.stat().st_size} for path in sorted(self.source.rglob("*.json"))]
        self.pins = {"schema": "finite-reviewed-candidate-retained-artifact-pins@1", "pins": pins}
        (self.source / "artifact-pins.json").write_bytes(audit._canonical(self.pins))
        report = {"schema": "finite-reviewed-candidate-independent-retained-audit@1", "status": "qualified_snapshot_pass",
                  "output": result["output"], "result_sha256": audit._sha((self.source / "result.json").read_bytes()),
                  "artifact_manifest_sha256": audit._sha((self.source / "artifact-pins.json").read_bytes()), "artifact_pin_count": len(pins)}
        (self.source / "independent-audit.json").write_bytes(audit._canonical(report))
        self.spec = {"schema": join.INPUT_SCHEMA,
                     "path_mapping": {"declared_root": result["output"], "retained_root": str(self.source)},
                     "result_sha256": report["result_sha256"], "artifact_pins_sha256": report["artifact_manifest_sha256"],
                     "independent_audit_sha256": audit._sha((self.source / "independent-audit.json").read_bytes()),
                     "context_paths": join.CONTEXT_PATHS}
        self.input = self.root / "capture-input.json"

    def capture(self, *, name="capture", value=None, **kwargs):
        self.input.write_bytes(audit._canonical(self.spec if value is None else value))
        return join.capture_join(self.input, self.root / name, **kwargs)

    def test_exact_relocated_subset_preserves_native_roles_ancestry_unknowns_and_final_bytes(self):
        report = self.capture()
        self.assertEqual(report["disposition"], "captured_subset_produced")
        self.assertEqual(report["native_version_count"], 2)
        self.assertEqual(report["native_target_membership_count"], 9)
        self.assertEqual(report["ancestral_training_exposure_count"], 1)
        self.assertEqual(report["baseline_issue_count"], 20)
        self.assertEqual(report["reconstructed_issue_count"], 20)
        self.assertEqual(report["recorded_metadata_only_paths"], ["metadata_only.py"])
        self.assertFalse(report["all_primary_artifacts_reverified"])
        self.assertFalse(report["numerical_state_replayed"])
        self.assertEqual(report["path_mapping"]["declared_root"], "/original/retained-owner-root")
        manifest = json.loads((self.root / "capture" / "audit_input.json").read_bytes())
        final = json.loads(join.FINAL_MANIFEST.read_bytes())
        self.assertEqual(manifest["units"], final["units"])
        self.assertTrue(all(unit["role"] == "final" for unit in manifest["units"]))
        self.assertEqual(report["final_connected_group_count"], 0)

    def test_changed_checkpoint_source_and_context_hash_refused(self):
        path = self.source / "child-training-context" / "checkpoint.json"
        path.write_bytes(path.read_bytes() + b" ")
        with self.assertRaises(audit.AuditInputError):
            self.capture()

    def test_original_primary_size_caps_read_before_allocation(self):
        selected = self.source / "child-training-context/checkpoint.json"
        declared_size = selected.stat().st_size
        selected.write_bytes(selected.read_bytes() + b"x" * 100000)
        real, seen = audit._read_bounded, []

        def read(path, maximum):
            if path == selected:
                seen.append(maximum)
            return real(path, maximum)

        with mock.patch.object(audit, "_read_bounded", read), self.assertRaises(audit.AuditInputError):
            self.capture()
        self.assertEqual(seen, [declared_size])

    def test_missing_ancestor_lineage_refused_even_when_all_outer_pins_rebound(self):
        path = self.source / "child-training-context/lineage.json"
        lineage = json.loads(path.read_bytes())
        path.write_bytes(audit._canonical(lineage[:-1]))
        context_path = self.source / "child-training-context/context.json"
        context = json.loads(context_path.read_bytes())
        context["artifacts"]["lineage"].update(sha256=audit._sha(path.read_bytes()), size_bytes=path.stat().st_size)
        context_path.write_bytes(audit._canonical(context))
        self.repin_primary()
        with self.assertRaisesRegex(audit.AuditInputError, "missing terminal ancestor"):
            self.capture()

    def repin_primary(self):
        for row in self.pins["pins"]:
            path = self.source / row["path"]
            row.update(sha256=audit._sha(path.read_bytes()), bytes=path.stat().st_size)
        (self.source / "artifact-pins.json").write_bytes(audit._canonical(self.pins))
        self.spec["artifact_pins_sha256"] = audit._sha((self.source / "artifact-pins.json").read_bytes())
        path = self.source / "independent-audit.json"
        report = json.loads(path.read_bytes())
        report["artifact_manifest_sha256"] = self.spec["artifact_pins_sha256"]
        path.write_bytes(audit._canonical(report))
        self.spec["independent_audit_sha256"] = audit._sha(path.read_bytes())

    def test_declared_origin_and_audit_result_detachment_refused(self):
        changed = copy.deepcopy(self.spec)
        changed["path_mapping"]["declared_root"] = "/wrong/origin"
        with self.assertRaisesRegex(audit.AuditInputError, "relocation origin"):
            self.capture(value=changed)
        path = self.source / "independent-audit.json"
        value = json.loads(path.read_bytes())
        value["result_sha256"] = "0" * 64
        path.write_bytes(audit._canonical(value))
        self.spec["independent_audit_sha256"] = audit._sha(path.read_bytes())
        with self.assertRaisesRegex(audit.AuditInputError, "result/pin inventory"):
            self.capture()

    def test_duplicate_primary_pins_and_malformed_counts_refused(self):
        self.pins["pins"].append(copy.deepcopy(self.pins["pins"][0]))
        self.repin_primary()
        with self.assertRaisesRegex(audit.AuditInputError, "duplicate"):
            self.capture()

    def test_limits_and_strict_spec_prevent_unbounded_work(self):
        for limits in (replace(join.DEFAULT_LIMITS, max_primary_pins=1), replace(join.DEFAULT_LIMITS, max_selected_files=1),
                       replace(join.DEFAULT_LIMITS, max_selected_bytes=32), replace(join.DEFAULT_LIMITS, max_lineage_rows=1)):
            with self.subTest(limits=limits), self.assertRaises(audit.AuditInputError):
                self.capture(limits=limits)
        changed = copy.deepcopy(self.spec)
        changed["context_paths"] = changed["context_paths"][:-1]
        with self.assertRaises(audit.AuditInputError):
            self.capture(value=changed)
        changed = copy.deepcopy(self.spec)
        changed["path_mapping"]["retained_root"] += "/../relocated"
        with self.assertRaises(audit.AuditInputError):
            self.capture(value=changed)

    def test_late_original_result_change_cannot_replace_captured_join(self):
        real = join._Capture.context
        changed = False

        def mutate(captured, path):
            nonlocal changed
            if not changed:
                (self.source / "result.json").write_bytes(b'{}')
                changed = True
            return real(captured, path)

        original = self.spec["result_sha256"]
        with mock.patch.object(join._Capture, "context", mutate):
            report = self.capture()
        self.assertEqual(report["result_sha256"], original)
        self.assertEqual(audit._sha((self.root / "capture/retained/result.json").read_bytes()), original)

    def test_deterministic_private_reports_no_state_execution(self):
        self.capture(name="first")
        self.capture(name="second")
        a = self.root / "first/retained_join_report.json"
        self.assertEqual(a.read_bytes(), (self.root / "second/retained_join_report.json").read_bytes())
        self.assertEqual(a.stat().st_mode & 0o777, 0o600)


if __name__ == "__main__":
    unittest.main()

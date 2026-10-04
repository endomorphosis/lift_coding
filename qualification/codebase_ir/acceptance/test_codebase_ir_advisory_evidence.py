"""Independent retained-stage joins, correlated corruptions and bounded I/O."""

from __future__ import annotations

import copy
import hashlib
import json
import math
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import codebase_ir_advisory_evidence as audit


def selected_spec(root: Path) -> dict:
    attempts = []
    for number in audit.ATTEMPTS:
        directory = root / number
        directory.mkdir(exist_ok=True)
        attempts.append(
            {
                "id": number,
                "root": str(directory),
                "files": [
                    {
                        "role": role,
                        "path": path,
                        "sha256": hashlib.sha256(b"{}").hexdigest(),
                        "bytes": 2,
                    }
                    for role, path in audit.role_paths(number).items()
                ],
            }
        )
    return {"schema": audit.INPUT_SCHEMA, "attempts": attempts}


def authored_training_case() -> dict:
    """Small native-shaped assertion controls, never a native execution receipt."""
    records = {
        "criteria": {"configuration": {"epochs": 16, "learning_rate": 0.01, "seed": 1729}},
        "selections": [
            {"contracts": [], "path": path, "role": role}
            for path, role in (
                ("calc.py", "train"),
                ("known_variant.py", "train"),
                ("tune.py", "tune"),
                ("canary.py", "canary"),
            )
        ],
        "measurements": {"measurements": []},
    }
    case = {"records": records, "pins": {}}
    rows = []
    prior = None
    for number, phase in enumerate(audit.TRAIN_PHASES):
        version = "sha256:" + str(number + 1) * 64
        head = {"schema": "codebase-head@1", "generation": 1 if number < 2 else 2}
        selected = 5 + 14 * number
        provenance = {
            "head": head,
            "selections": records["selections"],
            "tuning_targets": ["fixed-tune"],
            "canary_targets": ["fixed-canary"],
            "replay_targets": ["fixed-replay"],
            "continuation": "exact_frozen_basis_adam_resume",
        }
        state = {
            "latent_width": 8,
            "completed_epochs": selected,
            "adam": [{"step": selected} for _ in range(4)],
            "optimizer_config": {"learning_rate": 0.01},
            "parameters": [number + 0.5],
        }
        checkpoint = {
            "state": state,
            "feature_space": {"atoms": ["fixed"]},
            "contract": {"profile": "authored-assertion-only"},
            "report": {"attempted_epochs": 16, "codebase_provenance": provenance},
        }
        if number:
            checkpoint["report"]["base_state_sha256"] = hashlib.sha256(
                audit.canonical(records[f"train{number - 1}_checkpoint"]["state"])
            ).hexdigest()
        binding = {
            "schema": "supervisor-codebase-feature-context@1",
            "mode": "train",
            "model_enabled": True,
            "profile": "codebase_ir/source_bound_feature_v1",
            "latent_width": 8,
            "parameter_dtype": "float64",
            "authority": dict.fromkeys(audit.CONTEXT_FALSE, False),
            "actual_training_delta": 16,
            "selected_total_epochs": selected,
            "selected_optimizer_steps": [selected] * 4,
            "head": head,
            "version_id": version,
            "parent_version_id": prior,
            "state_sha256": hashlib.sha256(audit.canonical(state)).hexdigest(),
            "feature_space_sha256": hashlib.sha256(
                audit.canonical(checkpoint["feature_space"])
            ).hexdigest(),
            "artifacts": {},
        }
        record = {
            "authority": dict.fromkeys(audit.NATIVE_FEATURE_FALSE, False),
            "head": head,
            "version_id": version,
        }
        inference = {**copy.deepcopy(record), "training_executed": False}
        lineage = [{"version": {"version_id": version}, "checkpoint": copy.deepcopy(checkpoint)}]
        for k in range(number - 1, -1, -1):
            lineage.append(
                {
                    "version": {"version_id": records[f"train{k}_context"]["version_id"]},
                    "checkpoint": copy.deepcopy(records[f"train{k}_checkpoint"]),
                }
            )
        for name, value in (
            ("checkpoint", checkpoint),
            ("lineage", lineage),
            ("record", record),
            ("inference", inference),
            ("invocation", {"mode": "train"}),
            ("metrics", {"diagnostic": 0.1}),
        ):
            role = f"train{number}_{name}"
            records[role] = value
            case["pins"][role] = {"role": role, "path": role + ".json"}
            audit.repin(case, role)
            artifact = {
                "schema": "supervisor-codebase-feature-blob@1",
                "role": name,
                "relative_path": name + ".json",
                "sha256": case["pins"][role]["sha256"],
                "size_bytes": case["pins"][role]["bytes"],
            }
            artifact["blob_cid"] = audit.cid(artifact)
            binding["artifacts"][name] = artifact
        binding["model_record_cid"] = audit.cid(record)
        binding["context_cid"] = audit.cid(binding)
        role = f"train{number}_context"
        records[role] = binding
        case["pins"][role] = {"role": role, "path": role + ".json"}
        audit.repin(case, role)
        rows.append(
            {
                "phase": phase,
                "status": "completed",
                "requested_epochs": 16,
                "actual_attempted_epochs": 16,
                "context_cid": binding["context_cid"],
                "version_id": version,
                "parent_version_id": prior,
            }
        )
        records["measurements"]["measurements"].append(
            {
                **dict.fromkeys(audit.MEASUREMENT_FALSE, False),
                "version_id": version,
                "parent_version_id": prior,
                "context_cid": binding["context_cid"],
                "attempted_epochs": 16,
                "optimizer_steps": [selected] * 4,
            }
        )
        prior = version
    records["epochs"] = {
        "schema": "finite-advisory-observed-training-attempts@1",
        "attempts": rows,
        "known_actual_attempted_epochs": 48,
        "unknown_fitting_attempt_count": 0,
    }
    return case


class AdvisoryStageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        reference = json.loads(
            Path(__file__).with_name("advisory_stage_reference.json").read_bytes()
        )
        cls.case = reference["case"]
        cls.case["records"]["replacement"] = bytes.fromhex(
            cls.case["records"]["replacement"]["bytes_hex"]
        )
        cls.costs = reference["cost_records"]

    def test_genuine_selected_completed_stages(self):
        facts = audit.assert_stages(self.case, "06")
        self.assertEqual(set(facts["original_tasks"]), {"FINITE-TYPE", "FINITE-OFFSET"})
        self.assertEqual(facts["advisory_comparison_fields"], 13)
        self.assertEqual(facts["successor_cold_field_count"], 9)
        self.assertEqual(facts["native_checkpoint_status"], "incomplete")

    def test_correlated_structural_controls_reject_after_unsigned_rebinding(self):
        for name in audit.STAGE_CONTROLS:
            with self.subTest(name=name):
                case = copy.deepcopy(self.case)
                audit.mutate_stage(case, name)
                with self.assertRaises(audit.AdmissionEvidenceError):
                    audit.assert_stages(case, "06")

    def test_bridge_corruption_passes_new_raw_pins_and_still_refuses_task_meaning(self):
        case = copy.deepcopy(self.case)
        audit.mutate_stage(case, "correlated_bridge_task")
        for role in ("bridge", "handoff", "generated", "descriptor", "scope", "outcome"):
            audit.raw_pin(case, role, case["records"][role])
        with self.assertRaisesRegex(
            audit.AdmissionEvidenceError, "bridge admission/task/ready revision"
        ):
            audit.assert_stages(case, "06")

    def test_all_cold_fields_are_compared_independently_of_agreement(self):
        for field in audit.COLD_FIELDS:
            case = copy.deepcopy(self.case)
            semantic = case["records"]["cold"]["receipt"]["payload"]["semantic_context"]
            semantic[field] = "foreign-field-value"
            case["records"]["cold"]["receipt"]["payload"]["semantic_context_cid"] = audit.cid(
                semantic
            )
            with (
                self.subTest(field=field),
                self.assertRaises((audit.AdmissionEvidenceError, TypeError)),
            ):
                audit.assert_stages(case, "06")

    def test_completed_selected_models_and_measurements_refuse_after_repinning(self):
        for field in (
            "selected_initial_model_version_id",
            "selected_successor_model_version_id",
            "training_measurements",
            "continuations",
        ):
            with self.subTest(field=field):
                case = copy.deepcopy(self.case)
                audit.mutate_stage(case, "outcome:" + field)
                audit.raw_pin(case, "outcome", case["records"]["outcome"])
                with self.assertRaisesRegex(
                    audit.AdmissionEvidenceError,
                    "selected model identity|measurements/continuations",
                ):
                    audit.assert_stages(case, "06")

    def test_frozen_selection_refuses_all_rebound_metadata_across_three_models(self):
        for label in ("root-frozen", "initial-child-frozen", "successor-frozen"):
            for field in audit.FROZEN_CORRUPTIONS:
                with self.subTest(label=label, field=field):
                    case = copy.deepcopy(self.case)
                    audit.mutate_stage(case, f"frozen:{label}:{field}")
                    preview = case["records"]["preview_" + label]
                    context = preview["feature_context"]
                    self.assertEqual(
                        context["context_cid"],
                        audit.cid(
                            {key: value for key, value in context.items() if key != "context_cid"}
                        ),
                    )
                    audit.raw_pin(case, "preview_" + label, preview)
                    audit.raw_pin(case, "outcome", case["records"]["outcome"])
                    with self.assertRaisesRegex(
                        audit.AdmissionEvidenceError,
                        "mode/model-enabled/delta|independent trained context|independently pinned",
                    ):
                        audit.assert_stages(case, "06")

    def test_model_off_rejects_fitting_or_selected_state_after_context_rebinding(self):
        changes = (
            {"mode": "train", "model_enabled": True, "actual_training_delta": 999},
            {"version_id": "sha256:" + "0" * 64},
            {"state_sha256": "0" * 64},
            {"selected_total_epochs": True},
            {"selected_optimizer_steps": [1]},
            {"actual_training_delta": False},
        )
        for label in ("initial-off", "successor-off"):
            for change in changes:
                with self.subTest(label=label, change=change):
                    case = copy.deepcopy(self.case)
                    case["records"]["preview_" + label]["feature_context"].update(change)
                    audit.rebind_preview(case, label)
                    audit.raw_pin(case, "preview_" + label, case["records"]["preview_" + label])
                    with self.assertRaisesRegex(
                        audit.AdmissionEvidenceError,
                        "mode/model-enabled/delta|selected numerical state",
                    ):
                        audit.assert_stages(case, "06")

    def test_frozen_checkpoint_self_consistent_blob_cid_cannot_relabel_selected_bytes(self):
        case = copy.deepcopy(self.case)
        audit.mutate_stage(case, "frozen:successor-frozen:checkpoint_descriptor")
        artifact = case["records"]["preview_successor-frozen"]["feature_context"]["artifacts"][
            "checkpoint"
        ]
        self.assertEqual(
            artifact["blob_cid"],
            audit.cid({key: value for key, value in artifact.items() if key != "blob_cid"}),
        )
        audit.raw_pin(case, "preview_successor-frozen", case["records"]["preview_successor-frozen"])
        with self.assertRaisesRegex(
            audit.AdmissionEvidenceError, "independently pinned checkpoint"
        ):
            audit.assert_selected_models(case["records"], completed=True)

    def test_unselected_frozen_auxiliary_descriptors_have_only_bounded_structural_scope(self):
        changes = (
            {"size_bytes": True},
            {"size_bytes": audit.MAX_FILE_BYTES + 1},
            {"sha256": "A" * 64},
            {"unexpected": "field"},
        )
        for role in ("invocation", "inference", "metrics"):
            for change in changes:
                with self.subTest(role=role, change=change):
                    case = copy.deepcopy(self.case)
                    artifact = case["records"]["preview_root-frozen"]["feature_context"][
                        "artifacts"
                    ][role]
                    artifact.update(change)
                    artifact["blob_cid"] = audit.cid(
                        {key: value for key, value in artifact.items() if key != "blob_cid"}
                    )
                    audit.rebind_preview(case, "root-frozen")
                    with self.assertRaisesRegex(
                        audit.AdmissionEvidenceError, "artifact descriptor shape"
                    ):
                        audit.assert_selected_models(case["records"], completed=True)

    def test_correlated_advisory_meaning_rebinds_duplicates_before_signed_meaning_refusal(self):
        case = copy.deepcopy(self.case)
        audit.mutate_stage(case, "correlated_advisory_meaning")
        for role in ("initial_comparison", "bridge", "outcome"):
            audit.raw_pin(case, role, case["records"][role])
        audit.assert_comparison(case["records"], successor=False)
        audit.assert_selected_models(case["records"], completed=True)
        with self.assertRaisesRegex(audit.AdmissionEvidenceError, "detached from signed model-off"):
            audit.assert_stages(case, "06")

    def test_training_counts_returned_work_not_best_selected_epoch(self):
        case = authored_training_case()
        self.assertEqual(audit.assert_training(case, "06"), (48, 0))
        self.assertEqual(
            [case["records"][f"train{i}_context"]["selected_total_epochs"] for i in range(3)],
            [5, 19, 33],
        )

    def test_correlated_epoch_counts_refuse_at_independent_checkpoint(self):
        case = authored_training_case()
        record = case["records"]
        record["epochs"]["attempts"][0]["actual_attempted_epochs"] = 17
        record["epochs"]["known_actual_attempted_epochs"] = 49
        binding = record["train0_context"]
        binding["actual_training_delta"] = 17
        binding["context_cid"] = audit.cid({k: v for k, v in binding.items() if k != "context_cid"})
        record["epochs"]["attempts"][0]["context_cid"] = binding["context_cid"]
        record["measurements"]["measurements"][0] |= {
            "attempted_epochs": 17,
            "context_cid": binding["context_cid"],
        }
        audit.repin(case, "train0_context")
        audit.raw_pin(case, "train0_context", binding)
        with self.assertRaisesRegex(audit.AdmissionEvidenceError, "actual checkpoint"):
            audit.assert_training(case, "06")

    def test_unknown_fitting_is_not_zero_and_bool_epochs_refuse(self):
        ledger = {
            "attempts": [
                {
                    "status": "failed_unknown_actual_fitting",
                    "requested_epochs": 16,
                    "actual_attempted_epochs": None,
                }
            ],
            "known_actual_attempted_epochs": 0,
            "unknown_fitting_attempt_count": 1,
        }
        self.assertEqual(audit.epoch_counts(ledger), (0, 1))
        ledger["attempts"][0] |= {"status": "completed", "actual_attempted_epochs": True}
        with self.assertRaises(audit.AdmissionEvidenceError):
            audit.epoch_counts(ledger)

    def test_changed_fixed_ancestry_refuses_even_when_child_artifact_rehashed(self):
        case = authored_training_case()
        checkpoint = case["records"]["train1_checkpoint"]
        checkpoint["report"]["codebase_provenance"]["canary_targets"] = ["selected-after-training"]
        audit.repin(case, "train1_checkpoint")
        with self.assertRaises(audit.AdmissionEvidenceError):
            audit.assert_training(case, "06")

    def test_phase_calls_and_inclusive_lifetimes_are_separate(self):
        result = audit.phase_accounting(self.costs["06"]["phases"])
        self.assertAlmostEqual(result["disjoint_recorded_call_seconds"], 266.91146167810075)
        self.assertEqual(len(result["inclusive_lifetimes_not_added"]), 2)
        self.assertFalse(result["complete_invocation_wall_time_measured"])

    def test_overlapping_duplicate_nonfinite_or_mislabeled_phase_costs_refuse(self):
        for change in ("overlap", "duplicate", "nan", "overflow", "bool", "inclusive"):
            rows = copy.deepcopy(self.costs["06"]["phases"])
            if change == "overlap":
                rows[1]["started_at"] = rows[0]["started_at"]
            elif change == "duplicate":
                rows.append(copy.deepcopy(rows[0]))
            elif change == "nan":
                rows[0]["wall_seconds"] = math.nan
            elif change == "overflow":
                for row in rows:
                    row["wall_seconds"] = 1e308
            elif change == "bool":
                rows[0]["wall_seconds"] = True
            else:
                next(row for row in rows if row["phase"] in audit.INCLUSIVE)["cost_scope"] = (
                    "disjoint"
                )
            with self.subTest(change=change), self.assertRaises(audit.AdmissionEvidenceError):
                audit.phase_accounting(rows)

    def test_parent_protocol_failure_and_archived_timeout_rows_remain_distinct(self):
        self.assertEqual(self.costs["05"]["outcome"]["error_type"], "JSONDecodeError")
        self.assertEqual(self.costs["05"]["transcript"]["returncode"], 0)
        lines = self.costs["05"]["transcript"]["stdout"].splitlines()
        self.assertEqual(len(lines) - 1, 22)
        audit.assert_replay(audit.parse_document(lines[-1].encode()))
        archived = self.costs["02"]["replay_resources"]
        self.assertEqual((len(archived["leases"]), len(archived["waiters"])), (2, 1))
        self.assertTrue(self.costs["02"]["wrapper"]["container_removed"])


class AdvisoryInputTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.spec = selected_spec(self.root)
        self.manifest = self.root / "input.json"
        self.manifest.write_text(json.dumps(self.spec))

    def test_closed_manifest_accepts_selected_population(self):
        audit.validate_manifest(self.spec)

    def test_foreign_missing_duplicate_or_unbounded_selectors_refuse(self):
        for kind in (
            "foreign",
            "duplicate",
            "missing",
            "bool",
            "uppercase",
            "extra",
            "absolute",
            "dotdot",
            "root_alias",
            "total",
        ):
            spec = copy.deepcopy(self.spec)
            row = spec["attempts"][0]["files"][0]
            if kind == "foreign":
                row["path"] = "private/key.json"
            elif kind == "duplicate":
                spec["attempts"][0]["files"][1] = copy.deepcopy(row)
            elif kind == "missing":
                spec["attempts"].pop()
            elif kind == "bool":
                row["bytes"] = True
            elif kind == "uppercase":
                row["sha256"] = "A" * 64
            elif kind == "extra":
                row["authority"] = True
            elif kind == "absolute":
                row["path"] = "/foreign"
            elif kind == "dotdot":
                spec["attempts"][0]["root"] += "/../01"
            elif kind == "root_alias":
                spec["attempts"][1]["root"] = spec["attempts"][0]["root"]
            else:
                for case in spec["attempts"]:
                    for pin in case["files"]:
                        pin["bytes"] = audit.MAX_FILE_BYTES
            with self.subTest(kind=kind), self.assertRaises(audit.AdmissionEvidenceError):
                audit.validate_manifest(spec)

    def test_existing_output_is_never_overwritten(self):
        output = self.root / "existing"
        output.mkdir()
        retained = output / "advisory_evidence.json"
        retained.write_bytes(b"original report")
        with self.assertRaises(audit.AdmissionEvidenceError):
            audit.run(self.manifest, output)
        self.assertEqual(retained.read_bytes(), b"original report")

    def test_output_inside_retained_root_creates_nothing(self):
        output = self.root / "01" / "new-output"
        with self.assertRaises(audit.AdmissionEvidenceError):
            audit.run(self.manifest, output)
        self.assertFalse(output.exists())

    def test_output_dotdot_alias_creates_nothing(self):
        scratch = self.root / "scratch"
        scratch.mkdir()
        output = scratch / ".." / "01" / "new-output"
        with self.assertRaises(audit.AdmissionEvidenceError):
            audit.run(self.manifest, output)
        self.assertFalse((self.root / "01" / "new-output").exists())

    def test_refused_missing_input_report_keeps_all_execution_claims_false(self):
        report = audit.run(self.manifest, self.root / "report")
        self.assertEqual(report["status"], "refused")
        for field in (
            "native_execution_performed",
            "training_executed",
            "current_authority_claimed",
            "full_join_qualified",
            "signature_authentication_performed",
            "owner_database_opened",
            "profile_keys_read",
        ):
            self.assertIs(report[field], False)
        self.assertEqual(
            report["manifest_sha256"], hashlib.sha256(self.manifest.read_bytes()).hexdigest()
        )

    def test_count_and_aggregate_caps_refuse_before_reader_allocation(self):
        path = self.root / "small.json"
        path.write_bytes(b"{}")
        reader = audit.PinnedReader()
        with (
            mock.patch.object(audit, "MAX_FILES", 0),
            mock.patch.object(audit, "_bounded_document") as read,
        ):
            with self.assertRaises(audit.AdmissionEvidenceError):
                reader.read(path)
            read.assert_not_called()
        reader.total = audit.MAX_TOTAL_BYTES - 1
        with mock.patch.object(audit, "_bounded_document") as read:
            with self.assertRaises(audit.AdmissionEvidenceError):
                reader.read(path, {"sha256": "0" * 64, "bytes": 2})
            read.assert_not_called()

    def test_symlink_fifo_raw_pin_and_postread_drift_refuse(self):
        path = self.root / "public.json"
        path.write_bytes(b"{}")
        alias = self.root / "alias.json"
        alias.symlink_to(path)
        with self.assertRaises(audit.AdmissionEvidenceError):
            audit.PinnedReader().read(alias)
        fifo = self.root / "fifo"
        os.mkfifo(fifo)
        with self.assertRaises(ValueError):
            audit.PinnedReader().read(fifo)
        with self.assertRaises(audit.AdmissionEvidenceError):
            audit.PinnedReader().read(path, {"sha256": "0" * 64, "bytes": 2})
        reader = audit.PinnedReader()
        reader.read(path)
        path.write_bytes(b"[]")
        with self.assertRaises(audit.AdmissionEvidenceError):
            reader.recheck()

    def test_duplicate_json_keys_nonfinite_and_deep_documents_refuse(self):
        for raw in (b'{"a":1,"a":2}', b'{"a":NaN}', b"[" * 80 + b"0" + b"]" * 80):
            with self.subTest(raw=raw[:20]), self.assertRaises(ValueError):
                audit.parse_document(raw)


if __name__ == "__main__":
    unittest.main()

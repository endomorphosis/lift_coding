"""Public inert auxiliary records, correlated rebinding and bounded I/O."""

from __future__ import annotations

import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import codebase_ir_advisory_evidence as advisory
import codebase_ir_frozen_auxiliary as auxiliary


class FrozenAuxiliaryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        reference = json.loads(
            Path(__file__).with_name("frozen_auxiliary_reference.json").read_bytes()
        )
        assert reference["authority"] == "assertion_reference_only"
        cls.models = reference["models"]

    def test_all_three_retained_selections_bind_complete_body_population(self):
        for model in self.models:
            facts = auxiliary.assert_auxiliary(model)
            self.assertEqual(facts["bodies_verified"], list(auxiliary.BODIES))
            self.assertEqual(facts["actual_training_delta"], 0)
            self.assertEqual(facts["copied_training_metrics_attempted_epochs"], 16)
            self.assertEqual(len(facts["inference_source_digests"]), 4)

    def test_all_correlated_controls_refuse_with_regenerated_raw_pins_and_native_cids(self):
        for label, baseline in zip(auxiliary.LABELS, self.models, strict=True):
            for name in auxiliary.CONTROLS:
                with self.subTest(label=label, name=name):
                    model = copy.deepcopy(baseline)
                    auxiliary.mutate(model, name)
                    for body in auxiliary.BODIES:
                        advisory.raw_pin({"pins": model["pins"]}, body, model[body])
                    self.assertEqual(model["context"], model["preview_context"])
                    with self.assertRaises(advisory.AdmissionEvidenceError):
                        auxiliary.assert_auxiliary(model)

    def test_changed_inference_numeric_row_is_consistency_refusal_without_replay(self):
        model = copy.deepcopy(self.models[2])
        auxiliary.mutate(model, "inference_latent")
        with self.assertRaisesRegex(
            advisory.AdmissionEvidenceError, "independently retained selected inference"
        ):
            auxiliary.assert_auxiliary(model)

    def test_metrics_rebinding_cannot_change_independent_checkpoint_report(self):
        model = copy.deepcopy(self.models[1])
        model["metrics"]["after"]["objective"] = 99.0
        model["trained_metrics"] = copy.deepcopy(model["metrics"])
        auxiliary.repin_model(model)
        with self.assertRaisesRegex(
            advisory.AdmissionEvidenceError, "selected checkpoint/native training report"
        ):
            auxiliary.assert_auxiliary(model)

    def test_child_invocation_requested_parent_is_not_selected_model_parent(self):
        model = self.models[1]
        self.assertIsNone(model["invocation"]["parent_version_id"])
        self.assertIsNotNone(model["context"]["parent_version_id"])
        facts = auxiliary.assert_auxiliary(model)
        self.assertIsNone(facts["invocation_requested_parent_version_id"])
        self.assertEqual(facts["parent_version_id"], model["trained_context"]["parent_version_id"])

    def test_sidecar_context_and_native_blob_cids_cannot_disagree(self):
        for kind in ("sidecar", "blob", "size", "relative"):
            with self.subTest(kind=kind):
                model = copy.deepcopy(self.models[0])
                if kind == "sidecar":
                    model["preview_context"]["version_id"] = "sha256:" + "0" * 64
                else:
                    artifact = model["context"]["artifacts"]["inference"]
                    artifact[
                        {"blob": "blob_cid", "size": "size_bytes", "relative": "relative_path"}[
                            kind
                        ]
                    ] = {
                        "blob": advisory.cid({"foreign": True}),
                        "size": True,
                        "relative": "../inference.json",
                    }[kind]
                    model["context"]["context_cid"] = advisory.cid(
                        {k: v for k, v in model["context"].items() if k != "context_cid"}
                    )
                    model["preview_context"] = copy.deepcopy(model["context"])
                    advisory.repin(
                        {"records": {"context": model["context"]}, "pins": model["pins"]}, "context"
                    )
                with self.assertRaises(advisory.AdmissionEvidenceError):
                    auxiliary.assert_auxiliary(model)

    def test_worker_receipt_shape_is_not_promoted_to_execution_attestation(self):
        for change in (
            {"source_execution_attested": True},
            {"returncode": False},
            {"elapsed_ms": True},
            {"elapsed_ms": 90001},
            {"unexpected": "field"},
        ):
            with self.subTest(change=change):
                model = copy.deepcopy(self.models[0])
                model["inference"]["worker_receipt"].update(change)
                auxiliary.repin_model(model)
                with self.assertRaisesRegex(advisory.AdmissionEvidenceError, "worker receipt"):
                    auxiliary.assert_auxiliary(model)

    def test_unknown_extra_missing_inference_fields_refuse_after_rebinding(self):
        for change in ("extra", "missing", "authority"):
            with self.subTest(change=change):
                model = copy.deepcopy(self.models[0])
                if change == "extra":
                    model["inference"]["unexpected"] = "field"
                elif change == "missing":
                    del model["inference"]["training_executed"]
                else:
                    del model["inference"]["authority"]["qualified"]
                auxiliary.repin_model(model)
                with self.assertRaises(advisory.AdmissionEvidenceError):
                    auxiliary.assert_auxiliary(model)


class FrozenAuxiliaryInputTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        base = {"schema": advisory.INPUT_SCHEMA, "attempts": []}
        for number in advisory.ATTEMPTS:
            directory = self.root / number
            directory.mkdir()
            base["attempts"].append(
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
                        for role, path in advisory.role_paths(number).items()
                    ],
                }
            )
        self.base = self.root / "base.json"
        self.base.write_text(json.dumps(base))
        self.prior = self.root / "prior.json"
        self.prior.write_text("{}")

        def pin(path):
            raw = path.read_bytes()
            return {"path": str(path), "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)}

        self.spec = {
            "schema": auxiliary.INPUT_SCHEMA,
            "prior_advisory_manifest": pin(self.base),
            "prior_advisory_report": pin(self.prior),
            "attempts": [
                {
                    "id": number,
                    "root": str(self.root / number),
                    "files": [
                        {
                            "role": role,
                            "path": path,
                            "sha256": hashlib.sha256(b"{}").hexdigest(),
                            "bytes": 2,
                        }
                        for role, path in auxiliary.role_paths().items()
                    ],
                }
                for number in auxiliary.ATTEMPTS
            ],
        }
        self.manifest = self.root / "supplement.json"
        self.save()

    def save(self):
        self.manifest.write_text(json.dumps(self.spec))

    def test_closed_complete_three_attempt_selector_population(self):
        auxiliary.validate_spec(self.spec)

    def test_corrupted_closed_population_pin_and_path_inputs_refuse(self):
        for kind in (
            "missing",
            "duplicate",
            "foreign",
            "upper",
            "boolean",
            "oversize",
            "extra",
            "attempt",
            "alias",
            "dotdot",
        ):
            with self.subTest(kind=kind):
                spec = copy.deepcopy(self.spec)
                files = spec["attempts"][0]["files"]
                if kind == "missing":
                    files.pop()
                elif kind == "duplicate":
                    files[1] = copy.deepcopy(files[0])
                elif kind == "foreign":
                    files[0]["path"] = "native/private/keys.json"
                elif kind == "upper":
                    files[0]["sha256"] = "A" * 64
                elif kind == "boolean":
                    files[0]["bytes"] = True
                elif kind == "oversize":
                    files[0]["bytes"] = advisory.MAX_FILE_BYTES + 1
                elif kind == "extra":
                    spec["unexpected"] = "field"
                elif kind == "attempt":
                    spec["attempts"][0]["id"] = "01"
                elif kind == "alias":
                    spec["attempts"][1]["root"] = spec["attempts"][0]["root"]
                else:
                    spec["attempts"][0]["root"] = str(self.root / "06" / ".." / "02")
                with self.assertRaises(advisory.AdmissionEvidenceError):
                    auxiliary.validate_spec(spec)

    def test_existing_output_report_is_preserved(self):
        output = self.root / "output"
        output.mkdir()
        receipt = output / "frozen_auxiliary_evidence.json"
        receipt.write_bytes(b"original")
        with self.assertRaises(advisory.AdmissionEvidenceError):
            auxiliary.run(self.manifest, output)
        self.assertEqual(receipt.read_bytes(), b"original")

    def test_output_inside_any_prior_attempt_or_supplement_root_creates_nothing(self):
        for directory in (self.root / "01", self.root / "06", self.root / "foreign"):
            with self.subTest(directory=directory):
                if directory.name == "foreign":
                    directory.mkdir()
                    self.spec["attempts"][0]["root"] = str(directory)
                    self.save()
                output = directory / "new"
                with self.assertRaises(advisory.AdmissionEvidenceError):
                    auxiliary.run(self.manifest, output)
                self.assertFalse(output.exists())

    def test_dotdot_and_symlink_output_aliases_create_nothing(self):
        alias = self.root / "alias"
        alias.symlink_to(self.root / "06", target_is_directory=True)
        for output in (self.root / "other" / ".." / "06" / "new", alias / "new"):
            with self.subTest(output=output), self.assertRaises(advisory.AdmissionEvidenceError):
                auxiliary.run(self.manifest, output)
        self.assertFalse((self.root / "06" / "new").exists())

    def test_missing_prior_semantics_yields_safe_refusal_without_execution_claims(self):
        report = auxiliary.run(self.manifest, self.root / "output")
        self.assertEqual(report["status"], "refused")
        self.assertFalse(report["frozen_auxiliary_artifact_bodies_verified"])
        for flag in auxiliary.FLAGS:
            self.assertIs(report[flag], False)

    def test_count_and_byte_caps_are_checked_before_allocation(self):
        source = self.root / "one.json"
        source.write_bytes(b"{}")
        reader = advisory.PinnedReader()
        reader.total = advisory.MAX_TOTAL_BYTES
        with mock.patch.object(advisory, "_bounded_document") as bounded:
            with self.assertRaises(advisory.AdmissionEvidenceError):
                reader.read(source, {"bytes": 2, "sha256": hashlib.sha256(b"{}").hexdigest()})
            bounded.assert_not_called()

    def test_selected_raw_drift_and_postread_changes_refuse(self):
        source = self.root / "one.json"
        source.write_bytes(b"{}")
        reader = advisory.PinnedReader()
        raw = reader.read(source)
        self.assertEqual(raw, b"{}")
        source.write_bytes(b"[]")
        with self.assertRaisesRegex(advisory.AdmissionEvidenceError, "raw pin mismatch"):
            reader.recheck()


if __name__ == "__main__":
    unittest.main()

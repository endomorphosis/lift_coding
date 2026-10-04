"""Exact stdout digest reconstruction and correlated inert protocol controls."""

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
import codebase_ir_worker_protocol as protocol


class WorkerProtocolTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        reference = json.loads(Path(__file__).with_name("frozen_auxiliary_reference.json").read_bytes())
        assert reference["authority"] == "assertion_reference_only"
        cls.models = reference["models"]

    def test_exact_reviewed_response_rederives_all_three_original_output_digests(self):
        for model in self.models:
            raw = protocol.envelope(model)
            facts = protocol.assert_protocol(model, raw, protocol.WORKER_SHA256)
            self.assertEqual(facts["reconstructed_output_sha256"], model["inference"]["worker_receipt"]["output_sha256"])
            self.assertEqual(facts["reconstructed_output_bytes"], len(raw))
            self.assertEqual(facts["input_digest_disposition"], "unknown_exact_stdin_not_retained")
            self.assertFalse(facts["source_execution_attested"])
            self.assertEqual(facts["state_sha256"], model["context"]["state_sha256"])
            self.assertFalse(raw.endswith(b"\n"))

    def test_all_thirty_corruptions_are_refused(self):
        cases = {"06": self.models}
        controls = protocol.controls(cases)
        self.assertEqual(len(controls), 30)
        self.assertTrue(all(row["refused"] for row in controls))

    def test_correlated_numeric_edit_passes_body_rebinding_but_refuses_output_digest(self):
        model = copy.deepcopy(self.models[0])
        raw = protocol.mutate(model, "correlated_numeric_output")
        auxiliary.assert_auxiliary(model)
        for body in auxiliary.BODIES:
            advisory.raw_pin({"pins": model["pins"]}, body, model[body])
        with self.assertRaisesRegex(advisory.AdmissionEvidenceError, "output digest"):
            protocol.assert_protocol(model, raw, protocol.WORKER_SHA256)

    def test_receipt_output_and_worker_identity_cannot_be_changed_by_unsigned_rebinding(self):
        for name in ("receipt_output_digest", "receipt_worker_identity"):
            with self.subTest(control=name):
                model = copy.deepcopy(self.models[1])
                raw = protocol.mutate(model, name)
                auxiliary.assert_auxiliary(model)
                with self.assertRaises(advisory.AdmissionEvidenceError):
                    protocol.assert_protocol(model, raw, protocol.WORKER_SHA256)

    def test_json_semantic_equivalence_does_not_replace_exact_stdout_bytes(self):
        model = self.models[0]
        raw = protocol.envelope(model)
        value = json.loads(raw)
        alternate = [raw + b"\n", json.dumps(value, indent=2).encode(),
                     json.dumps(dict(reversed(list(value.items()))), separators=(",", ":")).encode()]
        for body in alternate:
            with self.subTest(body=body[:30]):
                self.assertEqual(json.loads(body), value)
                with self.assertRaisesRegex(advisory.AdmissionEvidenceError, "canonical stdout"):
                    protocol.assert_protocol(model, body, protocol.WORKER_SHA256)

    def test_closed_protocol_schema_typed_authority_and_training_cannot_widen(self):
        model = self.models[0]
        original = json.loads(protocol.envelope(model))
        for key, value in (("training_executed", 0), ("proof_authority", 0),
                           ("proof_authority", True), ("schema", "foreign@1"),
                           ("unexpected", False)):
            with self.subTest(key=key, value=value):
                changed = copy.deepcopy(original)
                changed[key] = value
                with self.assertRaisesRegex(advisory.AdmissionEvidenceError, "closed inference"):
                    protocol.assert_protocol(model, protocol.wire(changed), protocol.WORKER_SHA256)

    def test_duplicate_json_fields_and_nonfinite_values_refuse(self):
        model = self.models[0]
        for raw in (b'{"schema":"x","schema":"y"}', b'{"schema":NaN}'):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                protocol.assert_protocol(model, raw, protocol.WORKER_SHA256)

    def test_oversized_envelope_refuses_before_json_parsing(self):
        with mock.patch.object(protocol, "parse_document") as parser:
            with self.assertRaisesRegex(advisory.AdmissionEvidenceError, "bounded protocol"):
                protocol.assert_protocol(self.models[0], b" " * (protocol.MAX_ENVELOPE_BYTES + 1), protocol.WORKER_SHA256)
            parser.assert_not_called()

    def test_unknown_contract_cannot_borrow_matching_retained_output(self):
        with self.assertRaisesRegex(advisory.AdmissionEvidenceError, "worker identity"):
            protocol.assert_protocol(self.models[0], protocol.envelope(self.models[0]), "0" * 64)


class WorkerProtocolInputTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        base = {"schema": advisory.INPUT_SCHEMA, "attempts": []}
        for number in advisory.ATTEMPTS:
            directory = self.root / number
            directory.mkdir()
            base["attempts"].append({"id": number, "root": str(directory), "files": [
                {"role": role, "path": path, "sha256": hashlib.sha256(b"{}").hexdigest(), "bytes": 2}
                for role, path in advisory.role_paths(number).items()]})
        self.base = self.root / "base.json"
        self.base.write_text(json.dumps(base))
        self.advisory_report = self.root / "advisory.json"
        self.advisory_report.write_text("{}")
        self.frozen = self.root / "frozen.json"
        self.frozen.write_text(json.dumps({
            "schema": auxiliary.INPUT_SCHEMA, "prior_advisory_manifest": self.pin(self.base),
            "prior_advisory_report": self.pin(self.advisory_report), "attempts": [
                {"id": number, "root": str(self.root / number), "files": [
                    {"role": role, "path": path, "sha256": hashlib.sha256(b"{}").hexdigest(), "bytes": 2}
                    for role, path in auxiliary.role_paths().items()]}
                for number in auxiliary.ATTEMPTS]}))
        self.prior = self.root / "prior.json"
        self.prior.write_text("{}")
        self.source = self.root / "worker.py"
        self.source.write_text("inert placeholder")
        self.spec = {"schema": protocol.INPUT_SCHEMA, "prior_frozen_manifest": self.pin(self.frozen),
                     "prior_frozen_report": self.pin(self.prior), "protocol_worker_source": {
                         "path": str(self.source), "sha256": protocol.WORKER_SHA256,
                         "bytes": protocol.WORKER_BYTES}}
        self.manifest = self.root / "protocol.json"
        self.save()

    def pin(self, path):
        raw = path.read_bytes()
        return {"path": str(path), "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)}

    def save(self):
        self.manifest.write_text(json.dumps(self.spec))

    def test_closed_spec_exact_reviewed_source_and_nonalias_input_paths(self):
        protocol.validate_spec(self.spec)
        for change in ("extra", "digest", "size", "boolean", "alias", "relative", "dotdot"):
            with self.subTest(change=change):
                spec = copy.deepcopy(self.spec)
                if change == "extra":
                    spec["unknown"] = False
                elif change == "digest":
                    spec["protocol_worker_source"]["sha256"] = "0" * 64
                elif change == "size":
                    spec["protocol_worker_source"]["bytes"] += 1
                elif change == "boolean":
                    spec["prior_frozen_report"]["bytes"] = True
                elif change == "alias":
                    spec["prior_frozen_report"]["path"] = spec["prior_frozen_manifest"]["path"]
                elif change == "relative":
                    spec["prior_frozen_report"]["path"] = "prior.json"
                else:
                    spec["prior_frozen_report"]["path"] = str(self.root / "other" / ".." / "prior.json")
                with self.assertRaises(advisory.AdmissionEvidenceError):
                    protocol.validate_spec(spec)

    def test_existing_output_preserves_original_report(self):
        output = self.root / "output"
        output.mkdir()
        target = output / protocol.REPORT_FILE
        target.write_bytes(b"original")
        with self.assertRaises(advisory.AdmissionEvidenceError):
            protocol.run(self.manifest, output)
        self.assertEqual(target.read_bytes(), b"original")

    def test_outputs_inside_all_original_attempt_roots_refuse_before_creation(self):
        for number in advisory.ATTEMPTS:
            output = self.root / number / "new"
            with self.subTest(number=number), self.assertRaises(advisory.AdmissionEvidenceError):
                protocol.run(self.manifest, output)
            self.assertFalse(output.exists())

    def test_symlink_and_dotdot_output_aliases_refuse_before_creation(self):
        alias = self.root / "alias"
        alias.symlink_to(self.root / "06", target_is_directory=True)
        for output in (alias / "new", self.root / "other" / ".." / "06" / "new"):
            with self.subTest(output=output), self.assertRaises(advisory.AdmissionEvidenceError):
                protocol.run(self.manifest, output)
        self.assertFalse((self.root / "06" / "new").exists())

    def test_source_raw_pin_mismatch_records_refusal_without_any_authority_or_digest_claim(self):
        report = protocol.run(self.manifest, self.root / "output")
        self.assertEqual(report["status"], "refused")
        self.assertIn("raw pin mismatch", report["error"])
        self.assertFalse(report["worker_protocol_output_digest_rederived"])
        self.assertFalse(report["frozen_auxiliary_artifact_bodies_verified"])
        for flag in protocol.FALSE_FLAGS:
            self.assertIs(report[flag], False)
        self.assertEqual(report["additional_attempted_training_epochs"], 0)
        self.assertEqual(list((self.root / "output").iterdir()), [self.root / "output" / protocol.REPORT_FILE])

    def test_input_raw_drift_fails_and_bounds_precede_allocations(self):
        reader = advisory.PinnedReader()
        reader.read(self.prior, self.pin(self.prior))
        self.prior.write_bytes(b'{"different": true}')
        with self.assertRaises(ValueError):
            reader.recheck()
        reader.total = advisory.MAX_TOTAL_BYTES
        with mock.patch.object(advisory, "_bounded_document") as bounded:
            with self.assertRaises(advisory.AdmissionEvidenceError):
                reader.read(self.source, self.pin(self.source))
            bounded.assert_not_called()


if __name__ == "__main__":
    unittest.main()

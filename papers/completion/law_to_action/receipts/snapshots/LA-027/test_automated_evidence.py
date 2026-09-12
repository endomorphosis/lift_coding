#!/usr/bin/python3.12
"""Focused automated-admission controls for LA-027. Not held-out scores."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

BENCHMARK = Path(__file__).resolve().parents[1]
if str(BENCHMARK) not in sys.path:
    sys.path.insert(0, str(BENCHMARK))

import automated_evidence as ae  # noqa: E402

PYTHON = "/usr/bin/python3.12"


class AutomatedAdmissionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        ae.write_reference_manifest()
        cls.envelope = ae.build_valid_envelope()

    def test_normal_admission_has_no_reviewer_identities_or_human_labels(self):
        admission = ae.admit(self.envelope)
        self.assertTrue(admission["admitted"])
        self.assertEqual(0, admission["exit_status"])
        self.assertFalse(admission["scored"])
        self.assertFalse(admission["held_out_scored"])
        self.assertFalse(admission["empirical_benchmark_result"])
        self.assertEqual(ae.EVIDENCE_SCOPE, admission["evidence_scope"])
        self.assertEqual("absent", admission["human_fields"]["reviewer_id"])
        self.assertEqual("uncollected", admission["human_fields"]["reviewed_at"])
        self.assertFalse(admission["human_fields"]["independent_human_gold"])
        self.assertFalse(admission["human_fields"]["optional_author_review"]["independent"])
        self.assertFalse(admission["human_fields"]["optional_author_review"]["collected"])
        self.assertEqual("absent", self.envelope["human_fields"]["reviewer_id"])
        populated = ae.populated_human_fields(self.envelope)
        self.assertEqual([], populated)

    def test_failed_admission_has_nonzero_exit_status(self):
        script = BENCHMARK / "automated_evidence.py"
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "bad.json"
            path.write_text("{}\n", encoding="utf-8")
            completed = subprocess.run(
                [PYTHON, str(script), "admit", "--envelope", str(path)],
                cwd=str(ae.ROOT),
                capture_output=True,
                text=True,
                check=False,
                env={**os.environ, "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin"},
            )
        self.assertEqual(ae.FAILED_EXIT, completed.returncode)
        payload = json.loads(completed.stdout)
        self.assertFalse(payload["admitted"])
        self.assertEqual(ae.FAILED_EXIT, payload["exit_status"])

    def _control(self, name: str, reason: str):
        admission = ae.admit(ae.control_envelope(name))
        self.assertFalse(admission["admitted"], name)
        self.assertFalse(admission["scored"], name)
        self.assertEqual(ae.FAILED_EXIT, admission["exit_status"], name)
        self.assertIn(reason, admission["reasons"], name)
        return admission

    def test_reject_missing_runtime_binding(self):
        self._control("missing_runtime_binding", "missing_runtime_binding")

    def test_reject_missing_source_binding(self):
        self._control("missing_source_binding", "missing_source_binding")

    def test_reject_incomplete_case_accounting(self):
        self._control("incomplete_case_accounting", "incomplete_case_accounting")

    def test_reject_invalid_expectation_provenance(self):
        self._control("invalid_expectation_provenance", "invalid_expectation_provenance")

    def test_reject_self_reported_success(self):
        self._control("self_reported_success", "self_reported_success")

    def test_reject_stale_profile(self):
        self._control("stale_profile", "stale_profile")

    def test_reject_stale_budget(self):
        self._control("stale_budget", "stale_budget")

    def test_reject_automated_output_labeled_human_gold(self):
        admission = self._control("automated_output_labeled_human_gold", "automated_output_labeled_human_gold")
        self.assertNotIn("independent human gold", json.dumps(admission.get("human_fields")))

    def test_controls_wrapper_confirms_all_refusals_and_live_admission(self):
        with tempfile.TemporaryDirectory() as raw:
            summary = ae.run_controls(Path(raw))
        self.assertTrue(summary["all_refused"])
        self.assertTrue(summary["normal_admission"]["admitted"])
        self.assertFalse(summary["normal_admission"]["scored"])
        self.assertEqual(len(ae.CONTROL_NAMES), len(summary["controls"]))

    def test_reference_manifest_is_not_human_gold_and_covers_the_frozen_population(self):
        manifest = ae.build_reference_manifest()
        self.assertEqual(60, len(manifest["cases"]))
        self.assertTrue(manifest["inventory"]["complete"])
        self.assertTrue(manifest["producer"]["not_human_gold"])
        self.assertTrue(manifest["frozen_before_evaluated_predictions"])
        self.assertEqual("absent", manifest["human_fields"]["reviewer_id"])
        self.assertEqual("uncollected", manifest["human_fields"]["reviewed_at"])
        self.assertTrue(all(row["policy_polarity"] == "unknown" for row in manifest["cases"]))
        self.assertTrue(all(row["independent_human_gold"] is False for row in manifest["cases"]))
        self.assertFalse(manifest["held_out_result_inferred"])
        self.assertFalse(manifest["useful_work_success_inferred_from_fixtures"])

    def test_original_protocol_hash_is_bound(self):
        amendment = ae.load_amendment()
        self.assertEqual(ae.ORIGINAL_PROTOCOL_SHA256, amendment["original_protocol"]["sha256"])
        self.assertTrue(amendment["original_population_budgets_unchanged"])
        self.assertFalse(amendment["external_human_review_required"])


if __name__ == "__main__":
    unittest.main()

"""Pure completion/typed-byte/full32 failure controls; no neural owners."""
import ast
import hashlib
import importlib.util
import math
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parent


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / (name + ".py"))
    subject = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(subject)
    return subject


TRAIN = load("audit_dual_training")
EVAL = load("audit_dual_evaluation")


def require(name, ok):
    if not ok:
        raise ValueError(name)


class SavedOutputFailures(unittest.TestCase):
    def test_training_completion_required_before_missing_attempt_read(self):
        with self.assertRaisesRegex(ValueError, "Explicit root"):
            TRAIN.audit("/unavailable/training-384-r1", "/unavailable/output.json", False)

    def test_evaluation_completion_required_before_missing_attempt_read(self):
        with self.assertRaisesRegex(ValueError, "Explicit root"):
            EVAL.audit("/unavailable/evaluation-r1", "/unavailable/output.json", False)

    def test_typed_sha_distinguishes_integer_and_float_and_signed_zero(self):
        self.assertNotEqual(TRAIN.typed_tensor_digest({"x": [1]}), TRAIN.typed_tensor_digest({"x": [1.0]}))
        self.assertNotEqual(TRAIN.typed_tensor_digest({"x": [0.0]}), TRAIN.typed_tensor_digest({"x": [-0.0]}))
        self.assertNotEqual(TRAIN.typed_tensor_digest({"x": [True]}), TRAIN.typed_tensor_digest({"x": [1]}))

    def test_ragged_mixed_and_nonfinite_state_refused(self):
        for value in ([[0.0], [0.0, 1.0]], [1, 1.0], [float("nan")]):
            with self.subTest(value=value), self.assertRaises(ValueError):
                TRAIN.typed_tensor_digest({"x": value})

    def test_json_duplicate_key_or_nonfinite_generated_formula_refused(self):
        for text in ('{"rules":[],"rules":[]}', '{"rules":NaN}'):
            with self.subTest(text=text), self.assertRaises(ValueError):
                TRAIN.strict_json(text)

    def receipt(self):
        return dict(full_vocabulary_logits=[[0.0] * 32 for _ in range(6)], target_token_ids=[3] * 6,
                    per_row_cross_entropy=[math.log(32)] * 6, mean_cross_entropy=math.log(32), correct=0,
                    full_vocabulary_size=32, batch_size=6, source_slot=0, loss_field="modality",
                    source_head_forward_calls=1, recurrent_forward_calls=0, count_forward_calls=0,
                    labels_passed_to_model=False, model_copied=False, sampler_state_advanced=False)

    def test_real_full32_uniform_ce_checked(self):
        self.assertEqual(TRAIN.loss_receipt(self.receipt(), require), 6)

    def test_corrupt_ce_and_threeway_logits_refused(self):
        wrong = self.receipt()
        wrong["per_row_cross_entropy"][0] = 0.0
        with self.assertRaises(ValueError):
            TRAIN.loss_receipt(wrong, require)
        wrong = self.receipt()
        wrong["full_vocabulary_logits"][0] = [0.0] * 3
        with self.assertRaises(ValueError):
            TRAIN.loss_receipt(wrong, require)

    def test_extra_source_pass_or_teacher_label_access_refused(self):
        for field, value in (("source_head_forward_calls", 2), ("labels_passed_to_model", True)):
            wrong = self.receipt()
            wrong[field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                TRAIN.loss_receipt(wrong, require)

    def test_unvisited_distribution_denominator_keeps_null_metrics(self):
        empty = EVAL.distribution_summary([])
        self.assertEqual(empty["reference_sites"], 180)
        self.assertEqual(empty["unvisited_or_unavailable_sites"], 180)
        self.assertIsNone(empty["mean_cross_entropy"])
        self.assertEqual(empty["argmax_correct"], 0)

    def test_endpoint_alias_does_not_skip_eight_physical_panels(self):
        source = (ROOT / "audit_dual_evaluation.py").read_text()
        ast.parse(source)
        self.assertIn("1<=distinct_endpoints<=2", source)
        self.assertIn("physical_panels=8,logical_panels=8", source)
        self.assertIn("combined_formula_join_counts=combined_formula", source)


if __name__ == "__main__":
    unittest.main()

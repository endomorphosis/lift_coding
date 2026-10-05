"""Pure toy contract tests; no Torch, models, optimizer steps or network."""
import ast
import copy
import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

PATH = Path(__file__).with_name("evaluate_expanded_reconstruction.py")
SPEC = importlib.util.spec_from_file_location("expanded_evaluation", PATH)
worker = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(worker)


def seal(value):
    return {**value, "content_sha256": worker.digest(value)}


def cohort_fixture():
    rows = []
    for split in ("train", "development"):
        for group in range(8):
            for variant in range(4):
                input_sha = hashlib.sha256(f"{split}/{group}/{variant}".encode()).hexdigest()
                rows.append(dict(id="sha256:" + input_sha, input_sha256=input_sha,
                    source_sha256=hashlib.sha256(f"source/{split}/{group}/{variant}".encode()).hexdigest(),
                    group_id=f"toy-{split}-{group}", split=split, context_role="none_required"))
    rows.sort(key=lambda row: row["id"])
    cohort = seal(dict(schema="source-only-authored-expansion-cohort/v1", rows=rows,
                       contains_formal_targets=False, policy=copy.deepcopy(worker.SOURCE_POLICY)))
    selection = [{key: row[key] for key in ("id", "group_id", "source_sha256", "split")}
                 | {"original_masks": dict.fromkeys(worker.MASKS, 0)}
                 for row in rows if row["split"] == "train"]
    return cohort, selection


def endpoint_fixture():
    rows = []
    for split in ("train", "development"):
        for index in range(32):
            vector = [1., float(index + 1)]
            views = {name: vector.copy() for name in worker.VIEWS}
            views["mean_reconstructed"] = [1., 0.]
            rows.append(dict(id=f"{split}-{index:02}", split=split,
                             group_id=f"{split}-group-{index // 4}",
                             source_sha256=f"{split}-source-{index}",
                             panel_input_sha256=f"{split}-input-{index}", endpoints=views))
    return rows


class ExpandedEvaluationTests(unittest.TestCase):
    def test_complete_cohort_and_all_zero_masks(self):
        cohort, selection = cohort_fixture()
        result = worker.validate_cohort(cohort, selection)
        self.assertEqual(len(result), 64)

    def test_false_boolean_mask_cannot_impersonate_integer_zero(self):
        cohort, selection = cohort_fixture()
        cohort["policy"]["semantic_masks"]["weak_decoder_fit"] = False
        cohort = seal({k: v for k, v in cohort.items() if k != "content_sha256"})
        with self.assertRaisesRegex(ValueError, "policy differs"):
            worker.validate_cohort(cohort, selection)
        cohort, selection = cohort_fixture()
        selection[0]["original_masks"]["weak_decoder_fit"] = False
        with self.assertRaisesRegex(ValueError, "zero masks"):
            worker.validate_cohort(cohort, selection)

    def test_group_and_source_leakage(self):
        for field in ("group_id", "source_sha256", "input_sha256"):
            cohort, selection = cohort_fixture()
            train = next(r for r in cohort["rows"] if r["split"] == "train")
            dev = next(r for r in cohort["rows"] if r["split"] == "development")
            dev[field] = train[field]
            cohort = seal({k: v for k, v in cohort.items() if k != "content_sha256"})
            with self.assertRaises(ValueError):
                worker.validate_cohort(cohort, selection)

    def test_formal_body_or_independent_holdout_promotion_rejected(self):
        cohort, selection = cohort_fixture()
        cohort["reference"] = {"invented": True}
        with self.assertRaisesRegex(ValueError, "closed source"):
            worker.validate_cohort(cohort, selection)
        cohort, selection = cohort_fixture()
        cohort["policy"]["pristine_holdout"] = True
        cohort = seal({k: v for k, v in cohort.items() if k != "content_sha256"})
        with self.assertRaisesRegex(ValueError, "policy differs"):
            worker.validate_cohort(cohort, selection)

    def test_tampered_seal_and_order_rejected(self):
        cohort, selection = cohort_fixture()
        cohort["rows"].reverse()
        with self.assertRaisesRegex(ValueError, "seal differs"):
            worker.validate_cohort(cohort, selection)
        cohort, selection = cohort_fixture()
        selection.reverse()
        with self.assertRaisesRegex(ValueError, "ordered TRAIN"):
            worker.validate_cohort(cohort, selection)

    def test_cosine_ties_deterministic_and_same_bank(self):
        self.assertEqual(worker.cosine_ranking([1., 0.], [("b", [1., 0.]), ("a", [2., 0.])]), ["a", "b"])
        self.assertEqual(worker.cosine_ranking([1., 0.], [("b", [-1., 0.]), ("a", [1., 0.])]), ["a", "b"])

    def test_zero_vectors_not_invented_cosine_scores(self):
        self.assertIsNone(worker.cosine_ranking([0., 0.], [("a", [1., 0.])]))
        self.assertIsNone(worker.cosine_ranking([1., 0.], [("a", [0., 0.])]))

    def test_nonfinite_width_and_duplicate_bank_rejected(self):
        for query, bank in (([float("nan")], [("a", [1.])]),
                            ([1.], [("a", [1., 0.])]),
                            ([1.], [("a", [1.]), ("a", [2.])])):
            with self.assertRaises(ValueError):
                worker.cosine_ranking(query, bank)

    def test_neighborhood_identity_is_exact_and_mean_control_is_weaker(self):
        result = worker.neighborhood_agreement(endpoint_fixture())
        self.assertEqual(result["raw_source"]["mean_top1_agreement_with_raw"], 1.)
        self.assertEqual(result["raw_source"]["mean_top5_set_overlap_fraction_with_raw"], 1.)
        self.assertEqual(result["new_latent"]["mean_top1_agreement_with_raw"], 1.)
        self.assertLess(result["mean_reconstructed"]["mean_top1_agreement_with_raw"], 1.)
        self.assertFalse(result["new_latent"]["semantic_relevance_measured"])
        self.assertEqual(result["new_latent"]["fixed_train_candidates"], 32)

    def test_zero_endpoint_coverage_accounting(self):
        rows = endpoint_fixture()
        rows[32]["endpoints"]["old_latent"] = [0., 0.]
        result = worker.neighborhood_agreement(rows)["old_latent"]
        self.assertEqual(result["fully_defined_queries"], 31)
        self.assertEqual(result["undefined_queries"], 1)

    def test_neighborhood_group_overlap_rejected(self):
        rows = endpoint_fixture()
        rows[32]["group_id"] = rows[0]["group_id"]
        with self.assertRaisesRegex(ValueError, "split overlap"):
            worker.neighborhood_agreement(rows)

    def test_pca_metadata_uses_32_and_actual_rank_without_padding(self):
        class Basis:
            def tolist(self):
                return [[1., 0.], [0., 1.]]
        control = dict(rank=2, retained=2, threshold=1e-5, basis=Basis())
        meta = worker.pca_metadata(control)
        self.assertEqual(meta["fit_rows"], 32)
        self.assertEqual(meta["retained_axes"], 2)
        self.assertEqual(meta["development_rows_read_before_fit"], 0)
        for invalid in ({**control, "rank": 32}, {**control, "retained": 3},
                        {**control, "threshold": 0.}):
            with self.assertRaisesRegex(ValueError, "PCA rank"):
                worker.pca_metadata(invalid)

    def test_checkpoint_local_escape_rejected_before_file_read(self):
        checkpoint = dict(model_file=dict(path="../model.safetensors", bytes=1, sha256="0" * 64))
        with self.assertRaisesRegex(ValueError, "local filename"):
            worker.checkpoint_file_bindings(dict(path="/not/opened/checkpoint.json"), checkpoint)

    def test_captured_source_compilation_uses_checked_bytes_and_no_cli(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "owner.py"
            path.write_text("answer = 42\nif __name__ == '__main__':\n    raise RuntimeError('CLI forbidden')\n")
            reference = worker.binding(path)
            owner = worker.compiled_owner(reference, reference["sha256"], "frozen_toy_owner")
            self.assertEqual(owner["answer"], 42)
            path.write_text("answer = 0\n")
            with self.assertRaisesRegex(ValueError, "pin differs"):
                worker.compiled_owner(reference, reference["sha256"], "frozen_toy_owner")

    def test_duplicate_keys_and_nonfinite_json_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "input.json"
            for text in ('{"a":1,"a":2}', '{"a":NaN}'):
                path.write_text(text)
                with self.assertRaises(ValueError):
                    worker.read(worker.binding(path))

    def test_output_seal_binding_and_fresh_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "report.json"
            reference = worker.write(path, dict(schema="toy/v1", model_calls=0))
            report = json.loads(path.read_bytes())
            worker.seal_check(report)
            self.assertEqual(reference, worker.binding(path))
            with self.assertRaises(FileExistsError):
                worker.write(path, dict(schema="toy/v1"))

    def test_no_training_calls_and_dev_read_occurs_after_controls(self):
        tree = ast.parse(PATH.read_text())
        run = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "run")
        text = ast.get_source_segment(PATH.read_text(), run)
        self.assertNotIn('["fit_steps"]', text)
        self.assertNotIn('["run_arm"]', text)
        self.assertNotIn('["preflight"]', text)
        self.assertLess(text.index('controls_owner["fit_pca_control"]'), text.index('read(selected["development_bundle_binding"])'))
        self.assertLess(text.index('resource.setrlimit(resource.RLIMIT_AS'), text.index('import torch'))


if __name__ == "__main__":
    unittest.main()

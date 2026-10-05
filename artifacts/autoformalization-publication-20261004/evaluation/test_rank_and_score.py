"""Stdlib-only declaration fixtures; no model inference or fitting."""
from __future__ import annotations

import copy
import importlib.util
import json
import math
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

SPEC = importlib.util.spec_from_file_location("reconstruction_rank_and_score", Path(__file__).with_name("rank_and_score.py"))
subject = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(subject)
OLD = subject.ROOT / "artifacts/autoformalization-alignment-20261003"
CAMPAIGN = subject.ROOT / "artifacts/autoformalization-publication-20261004"


def fixture(lane="legacy8"):
    """Use saved AE TRAIN observations and declared synthetic query endpoints.

    Only raw vectors are historical native outputs. Query/linear-control values
    in this unit fixture intentionally make no numerical model-execution claim.
    """
    panel = json.loads((OLD / "richer-01/panel.json").read_text())
    metadata = {"sha256:" + row["input_sha256"]: row for row in panel["rows"]}
    inputs = OLD / "stage-workflow-01/inputs"
    train_path = inputs / (lane + "_raw_train_bundle.json")
    query_path = inputs / (lane + "_raw_query_bundle.json")
    train, query = [json.loads(path.read_text()) for path in (train_path, query_path)]
    report_path = CAMPAIGN / "training/run-01" / (lane + "-seed1729") / "training-report.json"
    report = json.loads(report_path.read_text())
    d, _, z = subject.LANES[lane]
    k = min(z, d, 15)
    mean = [math.fsum(row["vector"][index] for row in train["rows"]) / 16 for index in range(d)]
    rows = []
    for index, row in enumerate(train["rows"] + query["rows"]):
        item = metadata[row["id"]]
        values = row["vector"]
        latent = report["final_observations"]["latent_vectors"][index] if index < 16 else values[:z]
        reconstructed = report["final_observations"]["reconstructed_vectors"][index] if index < 16 else values
        rows.append({"id": row["id"], "group_id": item["group_id"], "split": item["split"],
                     "source_sha256": item["source_sha256"], "panel_input_sha256": item["input_sha256"],
                     "lane_input_sha256": row["input_sha256"], "context_role": item["context"]["role"],
                     "endpoints": {"raw_source": values, "latent": latent, "reconstructed": reconstructed,
                                   "mean_reconstructed": mean, "pca_reconstructed": values, "pca_latent": values[:k]}})
    checkpoint_path = report_path.parent / "step200/checkpoint.json"
    endpoints = subject.seal({"schema": subject.ENDPOINT_SCHEMA, "lane_id": lane, "seed": 1729,
                              "architecture": subject.LANES[lane], "source_profile_sha256": subject.digest(train["profile"]),
                              "checkpoint_binding": subject.binding(checkpoint_path),
                              "model_file_binding": subject.binding(checkpoint_path.parent / "model.safetensors"),
                              "training_report_binding": subject.binding(report_path),
                              "native_train_bundle_binding": subject.binding(train_path),
                              "native_query_bundle_binding": subject.binding(query_path), "rows": rows,
                              "pca_control": {"effective_train_rank": min(d, 15), "retained_axes": k,
                                              "threshold": 1e-5, "basis_sha256": "a" * 64, "fit_rows": 16,
                                              "query_rows_read_before_fit": 0, "recipe": "TRAIN_centered_SVD/v1"},
                              "model_inference_executed": True, "optimizer_updates": 0})
    return endpoints, panel


class MatchedRankingTests(unittest.TestCase):
    def test_original_source_and_model_bindings_join_without_model_imports(self):
        value, _ = fixture()
        subject.verify_bound_inputs(value)
        self.assertNotIn("torch", sys.modules)
        self.assertNotIn("numpy", sys.modules)

    def test_exact_published_checkpoint_bytes_can_relocate_without_original_checkpoint_read(self):
        value, _ = fixture()
        old_path = Path(value["checkpoint_binding"]["path"])
        with tempfile.TemporaryDirectory() as temp:
            relocated = Path(temp) / "checkpoint.json"
            shutil.copyfile(old_path, relocated)
            shutil.copyfile(old_path.parent / "model.safetensors", relocated.parent / "model.safetensors")
            value["checkpoint_binding"] = subject.binding(relocated)
            value["model_file_binding"] = subject.binding(relocated.parent / "model.safetensors")
            subject.seal(value)
            original_read = subject.read_bound
            def guarded(reference, **kwargs):
                self.assertNotEqual(reference["path"], str(old_path))
                return original_read(reference, **kwargs)
            with mock.patch.object(subject, "read_bound", side_effect=guarded):
                subject.verify_bound_inputs(value)
            # Relocation changes no selected byte identity; changed bytes fail.
            content = json.loads(relocated.read_text())
            content["optimizer_steps"] = 100
            subject.seal(content)
            relocated.write_text(json.dumps(content))
            value["checkpoint_binding"] = subject.binding(relocated)
            subject.seal(value)
            with self.assertRaisesRegex(ValueError, "byte identity"):
                subject.verify_bound_inputs(value)

    def test_six_widths_fixed_pool_and_diagnostic_accounting(self):
        value, panel = fixture()
        ranks = subject.rank_endpoints(value)
        scores = subject.score_rankings(ranks, value, panel)
        self.assertEqual(set(ranks["arms"]), set(subject.VIEWS))
        self.assertEqual(len(ranks["candidate_ids"]), 16)
        for view in subject.VIEWS:
            records = ranks["arms"][view]["rows"]
            self.assertEqual(len(records), 18)
            for row in records:
                self.assertEqual(len(row["ranked"]), 5)
                self.assertEqual(len(row["full_pool_ranking"]), 16)
                self.assertEqual({r["candidate_id"] for r in row["full_pool_ranking"]}, set(ranks["candidate_ids"]))
            scored = scores["arms"][view]
            self.assertEqual([len(scored[k]) for k in ("positive_rows", "negative_diagnostic_rows", "context_diagnostic_rows")], [8, 8, 2])
            self.assertTrue(all(r["semantic_score"] is None for k in ("negative_diagnostic_rows", "context_diagnostic_rows") for r in scored[k]))
            self.assertTrue(all(not r["score"]["reference_target_present_in_pool"] for r in scored["positive_rows"]))
        self.assertFalse(ranks["model_inference_executed"])
        self.assertTrue(ranks["upstream_model_inference_executed"])
        self.assertEqual(ranks["masks"], dict.fromkeys(subject.MASKS, 0))

    def test_raw_native_metrics_match_historical_authored_baselines(self):
        for lane in subject.LANES:
            with self.subTest(lane=lane):
                value, panel = fixture(lane)
                scores = subject.score_rankings(subject.rank_endpoints(value), value, panel)
                old = json.loads((OLD / "richer-embedding-01" / (lane + "_retrieval.json")).read_text())
                expected = {r["id"]: r["score"]["policies"]["source_cosine"]["authored_metrics"]["graded_facet_ndcg"]
                            for r in old["posthoc_scores"]}
                actual = {r["id"]: r["score"]["authored_metrics"]["graded_facet_ndcg"] for r in scores["arms"]["raw_source"]["positive_rows"]}
                self.assertEqual(actual.keys(), expected.keys())
                for identity in actual:
                    self.assertAlmostEqual(actual[identity], expected[identity], places=14)

    def test_wrong_native_bank_and_source_ids_rejected(self):
        value, _ = fixture()
        value["native_train_bundle_binding"] = value["native_query_bundle_binding"]
        subject.seal(value)
        with self.assertRaisesRegex(ValueError, "cohort counts"):
            subject.verify_bound_inputs(value)
        value, _ = fixture()
        value["rows"][0]["id"] = "sha256:" + "f" * 64
        value["rows"][0]["panel_input_sha256"] = "f" * 64
        subject.seal(value)
        with self.assertRaisesRegex(ValueError, "wrong TRAIN bank/source IDs"):
            subject.verify_bound_inputs(value)

    def test_source_profile_and_raw_vector_tampering_rejected(self):
        for action, expected in ((lambda v: v.update(source_profile_sha256="f" * 64), "source profile"),
                                 (lambda v: v["rows"][0]["endpoints"]["raw_source"].__setitem__(0, 3.0), "raw vectors"),
                                 (lambda v: v["rows"][0].update(source_sha256="f" * 64), "source identity")):
            value, _ = fixture()
            action(value)
            subject.seal(value)
            with self.assertRaisesRegex(ValueError, expected):
                subject.verify_bound_inputs(value)

    def test_exact_saved_train_forward_required(self):
        value, _ = fixture()
        value["rows"][0]["endpoints"]["latent"][0] += 1
        subject.seal(value)
        with self.assertRaisesRegex(ValueError, "TRAIN forward"):
            subject.verify_bound_inputs(value)

    def test_wrong_width_nonfinite_and_unrequested_views_rejected(self):
        for mutate in (lambda v: v["rows"][0]["endpoints"]["latent"].append(0.),
                       lambda v: v["rows"][0]["endpoints"]["raw_source"].__setitem__(0, True),
                       lambda v: v["rows"][0]["endpoints"].update(extra_view=[1.])):
            value, _ = fixture()
            mutate(value)
            subject.seal(value)
            with self.assertRaises(ValueError):
                subject.rank_endpoints(value)
        value, _ = fixture()
        value["rows"][0]["endpoints"]["latent"][0] = float("nan")
        with self.assertRaises(ValueError):
            subject.rank_endpoints(value)

    def test_zero_or_missing_candidate_keeps_all_query_denominators(self):
        for vector in ([0.] * 4, None):
            value, panel = fixture()
            value["rows"][0]["endpoints"]["latent"] = vector
            subject.seal(value)
            ranks = subject.rank_endpoints(value)
            self.assertEqual(len(ranks["arms"]["latent"]["rows"]), 18)
            self.assertTrue(all(r["status"] == "unavailable" and r["ranked"] == [] for r in ranks["arms"]["latent"]["rows"]))
            score = subject.score_rankings(ranks, value, panel)["arms"]["latent"]["summary"]
            self.assertEqual(score["eligible_positive_queries"], 8)
            self.assertEqual(score["unavailable_positive_score_count"], 8)
            self.assertIsNone(score["mean_graded_facet_ndcg"])
            self.assertEqual(score["mean_ndcg_over8_with_unavailable_zero"], 0.0)

    def test_candidate_count_and_group_leakage_rejected(self):
        value, _ = fixture()
        value["rows"][16]["split"] = "train"
        subject.seal(value)
        with self.assertRaisesRegex(ValueError, "accounting"):
            subject.rank_endpoints(value)
        value, _ = fixture()
        query_group = value["rows"][16]["group_id"]
        for row in value["rows"]:
            if row["group_id"] == query_group:
                row["group_id"] = value["rows"][0]["group_id"]
        subject.seal(value)
        with self.assertRaisesRegex(ValueError, "group_id leakage"):
            subject.rank_endpoints(value)

    def test_variable_pca_axes_are_declared_and_closed(self):
        value, _ = fixture()
        value["pca_control"].update(effective_train_rank=2, retained_axes=2)
        for row in value["rows"]:
            row["endpoints"]["pca_latent"] = row["endpoints"]["pca_latent"][:2]
        subject.seal(value)
        self.assertEqual(subject.rank_endpoints(value)["arms"]["pca_latent"]["dimension"], 2)
        value["pca_control"]["retained_axes"] = 3
        subject.seal(value)
        with self.assertRaisesRegex(ValueError, "PCA axes/rank"):
            subject.rank_endpoints(value)
        value, _ = fixture("native384")
        value["pca_control"]["effective_train_rank"] = 16
        subject.seal(value)
        with self.assertRaisesRegex(ValueError, "PCA axes/rank"):
            subject.rank_endpoints(value)

    def test_resealed_rank_tampering_is_recomputed(self):
        value, _ = fixture()
        ranks = subject.rank_endpoints(value)
        ranks["arms"]["raw_source"]["rows"][0]["ranked"].reverse()
        subject.seal(ranks)
        with self.assertRaisesRegex(ValueError, "source-only recomputation"):
            subject.validate_rankings(ranks, value)
        ranks = subject.rank_endpoints(value)
        ranks["content_sha256"] = "f" * 64
        with self.assertRaisesRegex(ValueError, "content seal"):
            subject.validate_rankings(ranks, value)

    def test_reference_change_changes_scores_but_cannot_enter_ranker(self):
        value, panel = fixture()
        ranks = subject.rank_endpoints(value)
        before = subject.score_rankings(ranks, value, panel)
        changed = copy.deepcopy(panel)
        row = next(r for r in changed["rows"] if r["split"] == "validation" and r["row_kind"] == "positive")
        row["target"]["rules"][0]["actor"] = "clerk" if row["target"]["rules"][0]["actor"] != "clerk" else "custodian"
        row["target_sha256"] = subject.digest(row["target"])
        _, owner = subject.owners(include_panel=True)
        changed["integrity"] = owner._integrity(changed)
        after = subject.score_rankings(ranks, value, changed)
        self.assertNotEqual(before, after)
        self.assertEqual(subject.rank_endpoints(value), ranks)
        value["rows"][0]["target"] = row["target"]
        subject.seal(value)
        with self.assertRaisesRegex(ValueError, "target-free endpoint row"):
            subject.rank_endpoints(value)

    def test_file_sha_duplicate_json_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "value.json"
            subject.write_json(path, {"a": 1})
            with self.assertRaises(FileExistsError):
                subject.write_json(path, {"a": 2})
            with self.assertRaisesRegex(ValueError, "externally selected"):
                subject.selected_file(path, "f" * 64)
            with self.assertRaisesRegex(ValueError, "duplicate JSON"):
                subject.parse_json(b'{"a":1,"a":2}')

    def test_ranking_file_bindings_replayed_and_panel_opened_after_rank_validation(self):
        value, panel = fixture()
        with tempfile.TemporaryDirectory() as temp:
            endpoint_path = Path(temp) / "endpoints.json"
            endpoint_binding = subject.write_json(endpoint_path, value)
            ranks = subject.seal({**subject.rank_endpoints(value), "endpoints_file_binding": endpoint_binding,
                                  "evaluation_owner_binding": subject.binding(subject.__file__)})
            subject.validate_rankings(ranks, value)
            ranks["evaluation_owner_binding"]["sha256"] = "f" * 64
            subject.seal(ranks)
            with self.assertRaisesRegex(ValueError, "evaluation owner"):
                subject.validate_rankings(ranks, value)
        # The pure ranker never accepts a panel argument or invokes its owner.
        with mock.patch.object(subject, "owners", side_effect=AssertionError("reference owner accessed")):
            subject.rank_endpoints(value)
        broken = subject.rank_endpoints(value)
        broken["arms"]["raw_source"]["rows"][0]["ranked"].reverse()
        subject.seal(broken)
        with mock.patch.object(subject, "owners", side_effect=AssertionError("reference owner accessed")):
            with self.assertRaisesRegex(ValueError, "source-only recomputation"):
                subject.score_rankings(broken, value, panel)


if __name__ == "__main__":
    unittest.main()

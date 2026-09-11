#!/usr/bin/env python3
"""Adversarial isolation tests for AF-008. Compact recipes, not golden dumps.

These tests recover withheld source/gold through each documented channel,
confirm main generalization arms disable sample-indexed memory, and keep
forward, cycle, and final reconstruction scores distinct.  They do not run
models, compilers, retrievers, or native checkers.
"""
from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import inference_isolation as iso  # noqa: E402


SOURCE = (
    "A permit holder must file a notice within ten days after approval, "
    "unless exempt."
)


def _phase(status: str = "success", score: float | None = 1.0, **extra) -> dict:
    body = {"status": status, "score": score}
    body.update(extra)
    return body


def _parser_feature() -> dict:
    return {
        "name": "actor_action_object_roles",
        "kind": "actor_action_object_roles",
        "producer": "typed-deontic-compiler/v1",
        "depends_on_parse": True,
        "requires_complete_compilation": True,
        "cost": {"compile_seconds": 0.4, "extraction_seconds": 0.05},
    }


class ChannelRejectionTests(unittest.TestCase):
    def test_each_documented_channel_is_rejected_on_source_withheld(self) -> None:
        for channel in iso.CHANNELS:
            with self.subTest(channel=channel):
                result = iso.probe_channel("source_withheld", channel)
                self.assertTrue(result["attempted"], channel)
                self.assertFalse(result["recovered"], channel)
                self.assertEqual(result["decision"], "rejected", result)
                self.assertFalse(result["blind_prediction_credit"], channel)

    def test_source_only_and_parser_assisted_reject_non_input_channels(self) -> None:
        for view in ("source_only", "parser_assisted"):
            for channel in iso.CHANNELS:
                if channel == "source_text":
                    continue
                with self.subTest(view=view, channel=channel):
                    result = iso.probe_channel(view, channel)
                    self.assertFalse(result["recovered"], (view, channel, result))
                    self.assertEqual(result["decision"], "rejected", result)

    def test_source_text_is_allowed_input_of_source_only_and_parser_assisted(self) -> None:
        for view in ("source_only", "parser_assisted"):
            result = iso.probe_channel(view, "source_text")
            self.assertEqual(result["decision"], "allowed_input", result)
            self.assertFalse(result["recovered"])

    def test_explicit_non_blind_declaration_is_not_silent_recovery(self) -> None:
        result = iso.probe_channel(
            "source_withheld", "filesystem", declare_non_blind=True,
        )
        self.assertEqual(result["decision"], "non_blind")
        self.assertFalse(result["recovered"])
        self.assertFalse(result["blind_prediction_credit"])

    def test_nested_source_map_is_rejected(self) -> None:
        payload = iso._fixture_payload("source_withheld", source_text=SOURCE)
        payload["config"] = {"hidden": {"source_map": {"actor": [0, 4]}}}
        with self.assertRaises(iso.IsolationError):
            iso.build_inference_view("source_withheld", payload, source_text=SOURCE)

    def test_source_sentence_in_canonical_ir_is_rejected(self) -> None:
        payload = iso._fixture_payload("source_withheld", source_text=SOURCE)
        payload["canonical_ir"] = {"rules": [{"note": SOURCE}]}
        with self.assertRaisesRegex(iso.IsolationError, "source text leaked"):
            iso.build_inference_view("source_withheld", payload, source_text=SOURCE)

    def test_filesystem_locator_aliases_are_rejected(self) -> None:
        payload = iso._fixture_payload("source_withheld", source_text=SOURCE)
        payload["corpus_path"] = "/var/corpus/unit-1.txt"
        with self.assertRaises(iso.IsolationError):
            iso.build_inference_view("source_withheld", payload, source_text=SOURCE)

    def test_retrieval_query_is_rejected(self) -> None:
        payload = iso._fixture_payload("source_withheld", source_text=SOURCE)
        payload["index_lookup"] = {"k": 1, "query": "permit holder"}
        with self.assertRaises(iso.IsolationError):
            iso.build_inference_view("source_withheld", payload, source_text=SOURCE)

    def test_parser_cache_is_rejected_even_under_parser_assisted(self) -> None:
        payload = iso._fixture_payload("parser_assisted", source_text=SOURCE)
        payload["parser_cache"] = {"raw": SOURCE}
        with self.assertRaises(iso.IsolationError):
            iso.build_inference_view(
                "parser_assisted", payload, source_text=SOURCE,
                features=payload.get("features"),
            )

    def test_gold_ir_cannot_enter_source_only_predictor(self) -> None:
        payload = iso._fixture_payload("source_only", source_text=SOURCE)
        with self.assertRaises(iso.IsolationError):
            iso.build_inference_view(
                "source_only", payload, source_text=SOURCE, gold_ir=iso._fixture_ir(),
            )

    def test_reference_decoder_fallback_is_excluded_from_blind_credit(self) -> None:
        credit = iso.credit_prediction(
            view="source_only", arm="T2", fallback_used=True,
            reconstruction={
                "forward": _phase(),
                "cycle": _phase(),
                "final": _phase(),
            },
        )
        self.assertFalse(credit["blind_prediction_credit"])
        self.assertTrue(credit["excluded_from_blind_prediction_credit"])
        self.assertEqual(credit["condition_class"], "non_blind")


class MemoryPolicyTests(unittest.TestCase):
    def test_main_generalization_arms_disable_update_and_evaluation_memory(self) -> None:
        for arm in iso.MAIN_GENERALIZATION_ARMS:
            policy = iso.sample_memory_policy(arm)
            self.assertFalse(policy["update"]["use_sample_memory"], arm)
            self.assertFalse(policy["evaluation"]["use_sample_memory"], arm)
            self.assertTrue(policy["generalization_arm"], arm)
            iso.assert_arm_memory_policy(arm, update_memory=False, evaluation_memory=False)

    def test_enabling_memory_on_generalization_arm_fails(self) -> None:
        for arm in ("T2", "T0", "A", "T4"):
            with self.assertRaises(iso.IsolationError):
                iso.assert_arm_memory_policy(arm, update_memory=True, evaluation_memory=False)
            with self.assertRaises(iso.IsolationError):
                iso.assert_arm_memory_policy(arm, update_memory=False, evaluation_memory=True)

    def test_t1_is_explicit_memory_diagnostic_not_generalization(self) -> None:
        policy = iso.sample_memory_policy("T1")
        self.assertFalse(policy["generalization_arm"])
        self.assertTrue(policy["update"]["use_sample_memory"])
        self.assertTrue(policy["evaluation"]["use_sample_memory"])
        self.assertTrue(policy["evaluation"]["report_seen_and_unseen_separately"])
        self.assertFalse(policy["blind_prediction_credit"])
        self.assertEqual(policy["condition_class"], "non_blind_sample_memory")
        iso.assert_arm_memory_policy("T1", update_memory=True, evaluation_memory=True)

    def test_t1_cannot_hide_memory_off_as_generalization(self) -> None:
        with self.assertRaises(iso.IsolationError):
            iso.assert_arm_memory_policy("T1", update_memory=False, evaluation_memory=False)

    def test_generalization_arm_cannot_relabel_memory_as_non_blind(self) -> None:
        with self.assertRaisesRegex(iso.IsolationError, "must disable sample-indexed memory"):
            iso.classify_condition(
                arm="T2",
                view="source_only",
                leaked_channels=(),
                declared_non_blind=True,
                declared_non_blind_channels=["sample_memory"],
            )

    def test_cache_key_equal_to_sample_id_is_a_shortcut(self) -> None:
        probe = iso.inspect_memory_shortcuts(
            sample_id="unit-1", cache_key="unit-1", use_sample_memory=False,
        )
        self.assertTrue(probe["shortcut"])
        self.assertIn("cache_key_equals_sample_id", probe["reasons"])

    def test_decoded_embeddings_by_sample_id_are_a_shortcut(self) -> None:
        probe = iso.inspect_memory_shortcuts({
            "sample_id": "unit-1",
            "decoded_embeddings": {"unit-1": [0.0, 1.0]},
            "use_sample_memory": False,
        })
        self.assertTrue(probe["shortcut"])

    def test_train_eval_overlap_with_memory_is_a_shortcut(self) -> None:
        probe = iso.inspect_memory_shortcuts(
            train_ids=["a", "b"], eval_ids=["b", "c"], use_sample_memory=True,
        )
        self.assertTrue(probe["shortcut"])
        self.assertEqual(probe["train_eval_overlap"], ["b"])

    def test_overlap_without_memory_is_not_a_lookup_shortcut(self) -> None:
        probe = iso.inspect_memory_shortcuts(
            train_ids=["a", "b"], eval_ids=["b"], use_sample_memory=False,
        )
        self.assertFalse(probe["shortcut"])
        self.assertEqual(probe["train_eval_overlap"], ["b"])

    def test_source_withheld_rejects_sample_id_cache_key(self) -> None:
        payload = iso._fixture_payload("source_withheld", source_text=SOURCE)
        payload["sample_id"] = "unit-1"
        payload["cache_key"] = "unit-1"
        with self.assertRaisesRegex(iso.IsolationError, "sample_id_cache|memory shortcut"):
            iso.build_inference_view("source_withheld", payload, source_text=SOURCE)

    def test_environment_manifest_keeps_generalization_memory_off(self) -> None:
        flags = iso.load_feature_flags()
        self.assertIs(flags["sample_memory_main_generalization"], False)
        self.assertIs(flags["source_withheld_retrieval"], False)


class ReconstructionAndFeatureTests(unittest.TestCase):
    def test_forward_cycle_final_remain_distinct(self) -> None:
        bundle = iso.reconstruction_bundle(
            forward=_phase("success", 0.91, compares="gold_to_first_ir"),
            cycle=_phase("success", 0.40, compares="first_ir_to_second_ir"),
            final=_phase("success", 0.38, compares="gold_to_second_ir"),
            vector={"mse": 0.02, "cosine": 0.99},
        )
        self.assertEqual(set(iso.RECONSTRUCTION_SCORES), {"forward", "cycle", "final"})
        self.assertNotEqual(bundle["forward"]["score"], bundle["cycle"]["score"])
        self.assertNotEqual(bundle["forward"]["compares"], bundle["cycle"]["compares"])
        self.assertNotEqual(bundle["cycle"]["compares"], bundle["final"]["compares"])
        self.assertTrue(bundle["vector_is_not_free_text_decoder"])
        iso.validate_reconstruction_scores(bundle)

    def test_collapsed_mean_score_is_rejected(self) -> None:
        with self.assertRaisesRegex(iso.IsolationError, "collapsed"):
            iso.validate_reconstruction_scores({
                "forward": _phase(),
                "cycle": _phase(),
                "final": _phase(),
                "mean": 0.9,
            })

    def test_missing_cycle_field_is_rejected(self) -> None:
        with self.assertRaisesRegex(iso.IsolationError, "missing distinct fields"):
            iso.validate_reconstruction_scores({
                "forward": _phase(),
                "final": _phase(),
            })

    def test_shared_score_object_is_rejected(self) -> None:
        shared = _phase()
        with self.assertRaisesRegex(iso.IsolationError, "share one object"):
            iso.validate_reconstruction_scores({
                "forward": shared,
                "cycle": shared,
                "final": shared,
            })

    def test_parser_assisted_features_must_be_disclosed_with_cost(self) -> None:
        disclosed = iso.disclose_parser_features([_parser_feature()])
        self.assertEqual(disclosed[0]["producer"], "typed-deontic-compiler/v1")
        self.assertTrue(disclosed[0]["depends_on_parse"])
        self.assertGreater(disclosed[0]["cost"]["compile_seconds"], 0)
        built = iso.build_inference_view(
            "parser_assisted",
            {"request_id": "p1", "source_text": SOURCE},
            source_text=SOURCE,
            features=[_parser_feature()],
        )
        self.assertFalse(built["raw_text_prediction"])
        self.assertTrue(built["parser_assisted"])
        self.assertGreater(built["feature_cost_seconds"], 0)

    def test_complete_compilation_with_zero_cost_is_rejected(self) -> None:
        feature = _parser_feature()
        feature["cost"]["compile_seconds"] = 0
        with self.assertRaisesRegex(iso.IsolationError, "charged zero compile cost"):
            iso.disclose_parser_features([feature])

    def test_undisclosed_parser_assisted_view_is_rejected(self) -> None:
        with self.assertRaisesRegex(iso.IsolationError, "disclosed features"):
            iso.build_inference_view(
                "parser_assisted",
                {"request_id": "p2", "source_text": SOURCE},
                source_text=SOURCE,
                features=[],
            )

    def test_source_only_cannot_silently_consume_parser_features(self) -> None:
        with self.assertRaisesRegex(iso.IsolationError, "parser-assisted"):
            iso.build_inference_view(
                "source_only",
                {"request_id": "s1", "source_text": SOURCE},
                source_text=SOURCE,
                features=[_parser_feature()],
            )

    def test_parser_assisted_is_not_blind_raw_text_credit(self) -> None:
        condition = iso.classify_condition(
            arm="T2",
            view="parser_assisted",
            parser_features=[_parser_feature()],
        )
        self.assertEqual(condition["condition_class"], "non_blind")
        self.assertFalse(condition["blind_prediction_credit"])
        self.assertIn("parser_assisted_features_are_not_raw_text_prediction", condition["reasons"])

    def test_source_withheld_cannot_consume_original_parser_features(self) -> None:
        payload = iso._fixture_payload("source_withheld", source_text=SOURCE)
        with self.assertRaisesRegex(iso.IsolationError, "parser features"):
            iso.build_inference_view(
                "source_withheld", payload, source_text=SOURCE, features=[_parser_feature()],
            )

    def test_clean_source_withheld_request_contains_ir_not_source(self) -> None:
        payload = iso._fixture_payload("source_withheld", source_text=SOURCE)
        built = iso.build_inference_view("source_withheld", payload, source_text=SOURCE)
        self.assertTrue(built["source_withheld"])
        self.assertIn("canonical_ir", built)
        self.assertNotIn("source_text", built)
        self.assertFalse(built["raw_text_prediction"])
        self.assertFalse(iso.source_text_leaked(built, SOURCE))


class ReportContractTests(unittest.TestCase):
    def test_probe_matrix_never_recovers_withheld_material(self) -> None:
        results = iso.run_adversarial_probes()
        self.assertGreaterEqual(len(results), len(iso.VIEWS) * len(iso.CHANNELS))
        recovered = [item for item in results if item["recovered"]]
        self.assertEqual(recovered, [])
        withheld = [item for item in results if item["view"] == "source_withheld"]
        for item in withheld:
            self.assertIn(item["decision"], {"rejected", "non_blind"}, item)

    def test_report_is_deterministic_and_covers_acceptance_criteria(self) -> None:
        first = iso.build_leakage_control_report()
        second = iso.build_leakage_control_report()
        self.assertEqual(iso.canonical_dumps(first), iso.canonical_dumps(second))
        self.assertEqual(first["report_sha256"], second["report_sha256"])
        self.assertEqual(first["task_id"], "AF-008")
        self.assertEqual(first["documented_channels"], list(iso.CHANNELS))
        self.assertEqual(first["reconstruction_contract"]["symbolic_scores"], list(iso.RECONSTRUCTION_SCORES))
        self.assertTrue(first["reconstruction_contract"]["distinct"])
        self.assertTrue(first["parser_assisted_disclosure"]["cannot_be_described_as_raw_text_prediction"])
        self.assertEqual(first["probe_summary"]["recovered"], 0)
        for arm in iso.MAIN_GENERALIZATION_ARMS:
            policy = first["arm_memory_policy"][arm]
            self.assertFalse(policy["update"]["use_sample_memory"], arm)
            self.assertFalse(policy["evaluation"]["use_sample_memory"], arm)
        self.assertFalse(first["arm_memory_policy"]["T1"]["generalization_arm"])
        self.assertIn("reference_decoder_fallback", first["blind_prediction_credit"]["excludes"])

    def test_report_tamper_changes_digest(self) -> None:
        report = iso.build_leakage_control_report()
        tampered = copy.deepcopy(report)
        tampered["probe_summary"]["recovered"] = 1
        self.assertNotEqual(
            iso.sha256_obj({key: tampered[key] for key in tampered if key != "report_sha256"}),
            report["report_sha256"],
        )

    def test_frozen_experiment_arms_match_isolation_contract(self) -> None:
        self.assertEqual(iso.load_frozen_arm_ids(), list(iso.EXPERIMENT_ARMS))

    def test_blind_source_only_t2_receives_credit_without_fallback(self) -> None:
        credit = iso.credit_prediction(view="source_only", arm="T2", fallback_used=False)
        self.assertTrue(credit["blind_prediction_credit"])
        self.assertEqual(credit["condition_class"], "blind")


if __name__ == "__main__":
    runner = unittest.TextTestRunner(stream=sys.stdout, verbosity=2)
    result = runner.run(unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__]))
    raise SystemExit(0 if result.wasSuccessful() else 1)

#!/usr/bin/env python3
"""Executor-bound isolation tests for AF-026. Compact recipes, not golden dumps.

These tests recover withheld source/gold through each documented channel on the
actual executor, confirm main generalization arms disable native sample-indexed
memory for update and evaluation, and keep forward, cycle, and final
reconstruction scores distinct.  They use synthetic canaries only.
"""
from __future__ import annotations

import base64
import copy
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import inference_isolation as iso  # noqa: E402


SOURCE = iso.SYNTHETIC_SOURCE


def _phase(status: str = "success", score: float | None = 1.0, **extra) -> dict:
    body = {"status": status, "score": score}
    body.update(extra)
    return body


def _parser_feature() -> dict:
    return {
        "name": "actor_action_object_roles",
        "kind": "actor_action_object_roles",
        "producer": iso.COMPILER_PRODUCER,
        "depends_on_parse": True,
        "requires_complete_compilation": True,
        "cost": {"compile_seconds": 0.4, "extraction_seconds": 0.05},
    }


class ChannelRejectionTests(unittest.TestCase):
    def test_each_documented_channel_is_rejected_on_source_withheld(self) -> None:
        executor = iso.IsolationExecutor()
        for channel in iso.CHANNELS:
            with self.subTest(channel=channel):
                result = iso.probe_channel("source_withheld", channel, executor=executor)
                self.assertTrue(result["attempted"], channel)
                self.assertFalse(result["recovered"], channel)
                self.assertIn(result["decision"], {"rejected", "non_blind"}, result)
                self.assertFalse(result["blind_prediction_credit"], channel)
                self.assertFalse(result["request_shape_only"], channel)

    def test_source_only_and_parser_assisted_reject_non_input_channels(self) -> None:
        for view in ("source_only", "parser_assisted"):
            for channel in iso.CHANNELS:
                if channel == "source_text":
                    continue
                with self.subTest(view=view, channel=channel):
                    result = iso.probe_channel(view, channel)
                    self.assertFalse(result["recovered"], (view, channel, result))
                    self.assertEqual(result["decision"], "rejected", result)
                    self.assertFalse(result["blind_prediction_credit"])

    def test_source_text_is_allowed_input_of_source_only_and_parser_assisted(self) -> None:
        for view in ("source_only", "parser_assisted"):
            result = iso.probe_channel(view, "source_text")
            self.assertEqual(result["decision"], "allowed_input", result)
            self.assertFalse(result["recovered"])
            self.assertFalse(result["blind_prediction_credit"])

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

    def test_invalid_ir_rule_without_permitted_fields_is_rejected(self) -> None:
        payload = iso._fixture_payload("source_withheld", source_text=SOURCE)
        payload["canonical_ir"] = {"rules": [{"note": SOURCE}]}
        with self.assertRaises(iso.IsolationError):
            iso.build_inference_view("source_withheld", payload, source_text=SOURCE)

    def test_encoded_auxiliary_in_canonical_ir_is_dropped_not_recovered(self) -> None:
        result = iso.probe_encoded_ir_auxiliary(SOURCE)
        self.assertFalse(result["recovered"], result)
        self.assertEqual(result["decision"], "rejected")
        self.assertTrue(any("auxiliary" in path or "freeform" in path or "canonical_ir_text" in path
                            for path in result["dropped_paths"]), result)
        self.assertEqual(result["projection"], "permitted_v1_rule_atoms")

    def test_base64_payload_in_permitted_atom_is_rejected(self) -> None:
        encoded = base64.b64encode(SOURCE.encode("utf-8")).decode("ascii")
        payload = iso._fixture_payload("source_withheld", source_text=SOURCE)
        payload["canonical_ir"] = {
            "rules": [{
                "modality": "O",
                "actor": encoded,
                "action": "file",
                "object": "notice",
                "conditions": [],
                "exceptions": [],
                "temporal": [],
            }]
        }
        with self.assertRaisesRegex(
            iso.IsolationError, "not a permitted identifier atom|encodes withheld source",
        ):
            iso.project_canonical_ir(payload["canonical_ir"], withheld_source=SOURCE)

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
        executor = iso.IsolationExecutor()
        realized = executor.realize(
            "source_only",
            iso._fixture_payload("source_only", source_text=SOURCE),
            source_text=SOURCE,
            arm="T2",
        )
        credit = iso.credit_prediction(
            view="source_only",
            arm="T2",
            fallback_used=True,
            reconstruction={
                "forward": _phase(),
                "cycle": _phase(),
                "final": _phase(),
            },
            prediction=realized["prediction"],
            executor_evidence=realized["evidence"],
            executor=executor,
            invocation=realized["invocation"],
        )
        self.assertFalse(credit["blind_prediction_credit"])
        self.assertTrue(credit["excluded_from_blind_prediction_credit"])
        self.assertEqual(credit["condition_class"], "non_blind")


class ExecutorCreditTests(unittest.TestCase):
    def test_classify_without_executor_or_prediction_grants_no_credit(self) -> None:
        condition = iso.classify_condition(arm="A", view="source_withheld")
        self.assertFalse(condition["blind_prediction_credit"])
        self.assertFalse(condition["blind"])
        self.assertIn("no_retained_prediction", condition["reasons"])

    def test_credit_prediction_without_prediction_or_executor_grants_no_credit(self) -> None:
        credit = iso.credit_prediction(view="source_only", arm="T2", fallback_used=False)
        self.assertFalse(credit["blind_prediction_credit"])
        self.assertNotEqual(credit["condition_class"], "blind")

    def test_caller_supplied_clean_flag_does_not_grant_credit(self) -> None:
        credit = iso.credit_prediction(
            view="source_only", arm="T2", fallback_used=False, clean=True,
        )
        self.assertFalse(credit["blind_prediction_credit"])
        self.assertIn("caller_supplied_clean_flag_is_not_credit", credit["reasons"])

    def test_stale_executor_digest_grants_no_credit(self) -> None:
        executor = iso.IsolationExecutor()
        realized = executor.realize(
            "source_only",
            iso._fixture_payload("source_only", source_text=SOURCE),
            source_text=SOURCE,
            arm="T2",
        )
        evidence = dict(realized["evidence"])
        evidence["executor_digest"] = "0" * 64
        credit = iso.credit_prediction(
            view="source_only",
            arm="T2",
            prediction=realized["prediction"],
            executor_evidence=evidence,
            executor=executor,
            invocation=realized["invocation"],
        )
        self.assertFalse(credit["blind_prediction_credit"])
        self.assertIn("stale_or_mismatched_executor_digest", credit["reasons"])

    def test_mismatched_invocation_grants_no_credit(self) -> None:
        executor = iso.IsolationExecutor()
        realized = executor.realize(
            "source_only",
            iso._fixture_payload("source_only", source_text=SOURCE),
            source_text=SOURCE,
            arm="T2",
        )
        evidence = dict(realized["evidence"])
        evidence["invocation_id"] = "not-the-invocation"
        credit = iso.credit_prediction(
            view="source_only",
            arm="T2",
            prediction=realized["prediction"],
            executor_evidence=evidence,
            executor=executor,
            invocation=realized["invocation"],
        )
        self.assertFalse(credit["blind_prediction_credit"])
        self.assertIn("mismatched_invocation", credit["reasons"])

    def test_retained_prediction_with_validated_evidence_can_receive_credit(self) -> None:
        executor = iso.IsolationExecutor()
        realized = executor.realize(
            "source_only",
            iso._fixture_payload("source_only", source_text=SOURCE),
            source_text=SOURCE,
            arm="T2",
        )
        credit = iso.credit_prediction(
            view="source_only",
            arm="T2",
            prediction=realized["prediction"],
            executor_evidence=realized["evidence"],
            executor=executor,
            invocation=realized["invocation"],
        )
        self.assertTrue(credit["blind_prediction_credit"])
        self.assertEqual(credit["condition_class"], "blind")
        self.assertTrue(realized["prediction"]["retained"])

    def test_source_withheld_prediction_does_not_contain_source(self) -> None:
        executor = iso.IsolationExecutor()
        realized = executor.realize(
            "source_withheld",
            iso._fixture_payload("source_withheld", source_text=SOURCE),
            source_text=SOURCE,
            arm="T2",
        )
        self.assertFalse(iso.encodes_withheld_source(realized["prediction"], SOURCE))
        self.assertNotIn("source_text", realized["request"])
        credit = iso.credit_prediction(
            view="source_withheld",
            arm="T2",
            prediction=realized["prediction"],
            executor_evidence=realized["evidence"],
            executor=executor,
            invocation=realized["invocation"],
        )
        self.assertTrue(credit["blind_prediction_credit"])

    def test_executor_filesystem_read_is_blocked_while_parent_read_is_not_a_leak(self) -> None:
        with tempfile.TemporaryDirectory(prefix="af026-parent-") as tmp:
            canary = Path(tmp) / "withheld.txt"
            canary.write_text(SOURCE, encoding="utf-8")
            executor = iso.IsolationExecutor()
            attempt = executor.attempt_channel(
                "filesystem", canary_file=str(canary), source_text=SOURCE,
            )
            self.assertFalse(attempt["recovered"], attempt)
            self.assertTrue(attempt["sandbox_attempts"])
            self.assertEqual(canary.read_text(encoding="utf-8"), SOURCE)

    def test_subprocess_executor_cannot_read_canary_file(self) -> None:
        result = iso.run_subprocess_filesystem_probe(source_text=SOURCE)
        self.assertFalse(result["recovered"], result)
        self.assertEqual(result["decision"], "rejected")
        self.assertTrue(result["parent_same_process_read_possible"])
        self.assertTrue(result["parent_read_is_not_executor_leak"])
        self.assertFalse(result["network_or_pretraining_claimed"])
        self.assertEqual(result["exit_code"], 0, result)

    def test_open_channel_restriction_is_non_blind(self) -> None:
        executor = iso.IsolationExecutor()
        realized = executor.realize(
            "source_only",
            iso._fixture_payload("source_only", source_text=SOURCE),
            source_text=SOURCE,
            arm="T2",
        )
        evidence = dict(realized["evidence"])
        restrictions = dict(evidence["channel_restrictions"])
        restrictions["filesystem"] = "available"
        evidence["channel_restrictions"] = restrictions
        credit = iso.credit_prediction(
            view="source_only",
            arm="T2",
            prediction=realized["prediction"],
            executor_evidence=evidence,
            executor=executor,
            invocation=realized["invocation"],
        )
        self.assertFalse(credit["blind_prediction_credit"])
        self.assertTrue(
            any("unqualified_or_open_channel:filesystem" in item for item in credit["reasons"])
        )


class MemoryPolicyTests(unittest.TestCase):
    def test_main_generalization_arms_disable_update_and_evaluation_memory(self) -> None:
        for arm in iso.MAIN_GENERALIZATION_ARMS:
            policy = iso.sample_memory_policy(arm)
            self.assertFalse(policy["update"]["use_sample_memory"], arm)
            self.assertFalse(policy["evaluation"]["use_sample_memory"], arm)
            self.assertTrue(policy["generalization_arm"], arm)
            self.assertFalse(policy["blind_prediction_credit"], arm)
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
        self.assertTrue(flags["declaration_only"])

    def test_native_sample_memory_route_is_disabled_for_every_main_arm(self) -> None:
        result = iso.qualify_native_sample_memory()
        self.assertTrue(result["all_main_arms_update_and_eval_disabled"], result)
        self.assertTrue(result["json_flag_alone_insufficient"])
        self.assertTrue(result["non_blind_declaration_does_not_waive"])
        self.assertFalse(result["synthetic_text_is_heldout"])
        for arm in iso.MAIN_GENERALIZATION_ARMS:
            item = result["main_generalization_arms"][arm]
            self.assertTrue(item["native_update_write_blocked"], arm)
            self.assertTrue(item["native_evaluation_read_blocked"], arm)
            self.assertTrue(item["shared_id_cache_shortcut_detected"], arm)
        t1 = result["t1_positive_control"]
        self.assertTrue(t1["native_update_write_observed"])
        self.assertTrue(t1["native_evaluation_read_observed"])
        self.assertTrue(t1["disabled_read_still_ignores_memory"])
        self.assertFalse(t1["blind_prediction_credit"])


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
        self.assertEqual(disclosed[0]["producer"], iso.COMPILER_PRODUCER)
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
        self.assertEqual(built["canonical_ir"]["rules"][0]["actor"], "permit_holder")
        self.assertNotIn("auxiliary", built["canonical_ir"])


class ReportContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.report = iso.build_leakage_control_report()

    def test_probe_matrix_never_recovers_withheld_material(self) -> None:
        results = self.report["probes"]
        self.assertGreaterEqual(len(results), len(iso.VIEWS) * len(iso.CHANNELS))
        recovered = [item for item in results if item["recovered"]]
        self.assertEqual(recovered, [])
        withheld = [
            item for item in results
            if item.get("view") == "source_withheld" and item.get("channel") in iso.CHANNELS
            and item.get("probe") is None
        ]
        for item in withheld:
            self.assertIn(item["decision"], {"rejected", "non_blind"}, item)

    def test_report_is_deterministic_and_covers_acceptance_criteria(self) -> None:
        first = self.report
        second = iso.build_leakage_control_report()
        self.assertEqual(iso.canonical_dumps(first), iso.canonical_dumps(second))
        self.assertEqual(first["report_sha256"], second["report_sha256"])
        self.assertEqual(first["task_id"], "AF-026")
        self.assertEqual(first["parent_receipt_sha256"], iso.PARENT_RECEIPT_SHA256)
        self.assertTrue(first["request_shape_checks_are_not_executor_qualification"])
        self.assertEqual(first["documented_channels"], list(iso.CHANNELS))
        self.assertEqual(first["reconstruction_contract"]["symbolic_scores"], list(iso.RECONSTRUCTION_SCORES))
        self.assertTrue(first["reconstruction_contract"]["distinct"])
        self.assertTrue(first["parser_assisted_disclosure"]["cannot_be_described_as_raw_text_prediction"])
        self.assertEqual(first["parser_assisted_disclosure"]["producer"], iso.COMPILER_PRODUCER)
        self.assertEqual(first["probe_summary"]["recovered"], 0)
        for arm in iso.MAIN_GENERALIZATION_ARMS:
            policy = first["arm_memory_policy"][arm]
            self.assertFalse(policy["update"]["use_sample_memory"], arm)
            self.assertFalse(policy["evaluation"]["use_sample_memory"], arm)
            self.assertFalse(policy["blind_prediction_credit"], arm)
        self.assertFalse(first["arm_memory_policy"]["T1"]["generalization_arm"])
        self.assertTrue(first["native_sample_memory"]["all_main_arms_update_and_eval_disabled"])
        self.assertIn("reference_decoder_fallback", first["blind_prediction_credit"]["excludes"])
        self.assertIn("arm_or_view_name_alone", first["blind_prediction_credit"]["excludes"])
        self.assertFalse(first["unqualified_non_documented_channels"]["network"]["qualified"])
        self.assertTrue(first["inert_reviewer_counterexamples_are_not_paper_experiment_leaks"])

    def test_report_tamper_changes_digest(self) -> None:
        report = self.report
        tampered = copy.deepcopy(report)
        tampered["probe_summary"]["recovered"] = 1
        self.assertNotEqual(
            iso.sha256_obj({key: tampered[key] for key in tampered if key != "report_sha256"}),
            report["report_sha256"],
        )

    def test_frozen_experiment_arms_match_isolation_contract(self) -> None:
        self.assertEqual(iso.load_frozen_arm_ids(), list(iso.EXPERIMENT_ARMS))

    def test_encoded_and_subprocess_probes_are_in_the_report(self) -> None:
        probes = {item.get("probe") for item in self.report["probes"]}
        self.assertIn("encoded_canonical_ir_auxiliary", probes)
        self.assertIn("subprocess_executor_filesystem", probes)


if __name__ == "__main__":
    runner = unittest.TextTestRunner(stream=sys.stdout, verbosity=2)
    result = runner.run(unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__]))
    raise SystemExit(0 if result.wasSuccessful() else 1)

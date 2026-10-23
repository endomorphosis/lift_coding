"""Authored accounting fixtures only; no source imports or provider execution."""
import json
from pathlib import Path
import tempfile
import unittest

import aggregate_trials as aggregate


def call(identity="one", *, complete=True, status="provider_returned"):
    return {"invocation_id": identity, "provider": "codex_cli", "model": "gpt-6.1-sol",
        "phase": "coding", "status": status, "native_rollout_usage": {
            "schema": "native-codex-cumulative-usage@1", "cache_included_in_input": True,
            "usage_available": True, "task_complete_observed": complete,
            "thread_id": "thread-" + identity, "usage": {
                "input_tokens": 100, "cached_input_tokens": 80,
                "output_tokens": 10, "total_tokens": 110}}}


def arm_row(solved, tokens=110, complete=True):
    return {"state": "finished", "solved": solved, "usage_complete": complete,
        "complete_tokens": {"input_tokens": tokens - 10, "cached_input_tokens": 80,
            "output_tokens": 10, "total_tokens": tokens} if complete else dict.fromkeys(aggregate.TOKENS),
        "known_token_subtotal": {"total_tokens": tokens}}


class AccountingTests(unittest.TestCase):
    def test_failed_and_successful_provider_calls_count_once(self):
        successful, failed = call(), call("two", status="failed")
        value = aggregate.usage({"provider_invocations": [successful, failed, successful]})
        self.assertTrue(value["complete"])
        self.assertEqual(value["complete_tokens"]["total_tokens"], 220)
        self.assertEqual(value["complete_tokens"]["cached_input_tokens"], 160)
        self.assertEqual(value["provider_invocations_observed"], 2)

    def test_interrupted_usage_retained_but_not_complete(self):
        value = aggregate.usage({"provider_invocations": [call(complete=False)]})
        self.assertFalse(value["complete"])
        self.assertIsNone(value["complete_tokens"]["total_tokens"])
        self.assertEqual(value["known_token_subtotal"]["total_tokens"], 110)

    def test_unreceipted_unknown_and_empty_are_never_zero(self):
        for report in ({}, {"provider_invocations": []},
                       {"provider_invocations": [call()], "unreceipted_provider_attempt": {"phase": "coding"}}):
            value = aggregate.usage(report)
            self.assertIsNone(value["complete_tokens"]["total_tokens"])
        self.assertIsNone(aggregate.usage({})["known_token_subtotal"]["total_tokens"])

    def test_duplicate_conflict_and_reused_cumulative_session_refuse_subtotals(self):
        for duplicate in (dict(call(), status="failed"),
                          dict(call(), invocation_id="different")):
            value = aggregate.usage({"provider_invocations": [call(), duplicate]})
            self.assertFalse(value["complete"])
            self.assertIsNone(value["known_token_subtotal"]["total_tokens"])

    def test_invalid_counters_never_qualify(self):
        for key, value in (("total_tokens", 111), ("input_tokens", True), ("cached_input_tokens", 101), ("output_tokens", -1)):
            row = call()
            row["native_rollout_usage"]["usage"][key] = value
            self.assertFalse(aggregate.usage({"provider_invocations": [row]})["complete"])

    def test_grok_disjoint_cache_requires_explicit_completeness(self):
        row = {"invocation_id": "grok", "provider": "grok_cli", "phase": "coding",
            "native_rollout_usage": {"schema": "native-grok-final-usage@1",
                "usage_available": True, "task_complete_observed": True,
                "usage_complete_observed": True, "cache_included_in_input": False,
                "totals_scope": "native_final_envelope", "usage": {
                    "input_tokens": 10, "cached_input_tokens": 20, "cache_write_input_tokens": 5,
                    "output_tokens": 3, "total_tokens": 38}}}
        self.assertEqual(aggregate.usage({"provider_invocations": [row]})["complete_tokens"]["total_tokens"], 38)
        row["native_rollout_usage"].pop("usage_complete_observed")
        self.assertFalse(aggregate.usage({"provider_invocations": [row]})["complete"])

    def test_failed_attempt_spend_is_in_tokens_per_solved(self):
        value = aggregate.summarize_arm([arm_row(True), arm_row(False, tokens=210)])
        self.assertEqual(value["tokens_per_solved_task_including_failures"], 320)
        self.assertEqual(value["solved_tasks"], 1)

    def test_zero_solved_or_unknown_outcome_or_partial_usage_is_undefined(self):
        for rows in ([arm_row(False)], [arm_row(True), arm_row(None)],
                     [arm_row(True), arm_row(False, complete=False)]):
            self.assertIsNone(aggregate.summarize_arm(rows)["tokens_per_solved_task_including_failures"])

    def test_pending_collection_and_receipt_fallback_with_multiple_attempts(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            folder = root / "trials" / "test"
            folder.mkdir(parents=True)
            config = {"job_name": "job", "agents": [{"kwargs": {"semantic_context_profile": "indexed-default@1"}}]}
            encoded = json.dumps(config).encode()
            (folder / "config.json").write_bytes(encoded)
            prepared = {"config_sha256": aggregate.digest(encoded), "task_input_sha256": {},
                "archive_sha256": "a" * 64, "host_source_sha256": {}, "semantic_context_profile": "indexed-default@1"}
            (folder / "preparation.json").write_text(json.dumps(prepared))
            frozen = {key: prepared[key] for key in ("task_input_sha256", "archive_sha256", "host_source_sha256")}
            frozen["normalized_configuration"] = aggregate.normalize_config(config)
            protocol = {"preparations": {"task": frozen}}
            selected = {"name": "test", "task": "task", "semantic_context_profile": "indexed-default@1"}
            pending = aggregate.collect_trial(root, selected, protocol)
            self.assertEqual(pending["state"], "pending")
            self.assertIsNone(pending["solved"])
            self.assertIsNone(pending["complete_tokens"]["total_tokens"])
            receipt = {"native_job_result_present": True, "trials": [
                {"trial": "fail", "task": "task", "reward": {"reward": 0.}, "supervisor": {
                    "implementation_route": "model_router", "provider_invocations": [call("fail", status="failed")]}},
                {"trial": "pass", "task": "task", "reward": {"reward": 1.}, "supervisor": {
                    "implementation_route": "model_router", "provider_invocations": [call("pass")]}}]}
            (folder / "receipt.json").write_text(json.dumps(receipt))
            result = aggregate.collect_trial(root, selected, protocol)
            self.assertEqual(result["tokens_per_solved_task"], 220)
            self.assertEqual(result["attempt_count_observed"], 2)
            self.assertTrue(result["solved"])
            # A copied raw result and its retained receipt are one attempt.
            attempt = folder / "jobs/job/pass"
            (attempt / "agent").mkdir(parents=True)
            (attempt / "result.json").write_text(json.dumps({"task_name": "task", "verifier_result": {"rewards": {"reward": 1.}}}))
            (attempt / "agent/supervisor-result.json").write_text(json.dumps(receipt["trials"][1]["supervisor"]))
            repeated = aggregate.collect_trial(root, selected, protocol)
            self.assertEqual(repeated["attempt_count_observed"], 2)
            self.assertEqual(repeated["tokens_per_solved_task"], 220)

            # Resumed cumulative sessions cannot be added across attempts.
            receipt["trials"][0]["supervisor"]["provider_invocations"][0]["native_rollout_usage"]["thread_id"] = "thread-pass"
            (folder / "receipt.json").write_text(json.dumps(receipt))
            reused = aggregate.collect_trial(root, selected, protocol)
            self.assertFalse(reused["usage_complete"])
            self.assertIsNone(reused["known_token_subtotal"]["total_tokens"])

    def test_complete_model_usage_does_not_imply_reward_or_input_audit(self):
        row = aggregate.attempt_row("a", {}, {"provider_invocations": [call()]}, native_present=True, source="fixture")
        self.assertTrue(row["provider_usage"]["complete"])
        self.assertIsNone(row["official_reward"])
        self.assertIsNone(row["context_input_audit"]["all_observed_coding_inputs_verified"])

    def test_predispatch_budget_failure_is_not_a_model_task_failure(self):
        row = aggregate.attempt_row("blocked", {"verifier_result": {"rewards": {"reward": 0.}}},
            {"error_phase": "initial_context", "error": {"type": "ValueError",
                "message": "worker context exceeds configured budget"}, "provider_invocations": [],
                "task_completed": False}, native_present=True, source="fixture")
        self.assertEqual(row["official_reward"], 0.)
        self.assertEqual(row["outcome_class"], "predispatch_pipeline_failure")
        self.assertEqual(row["failure_phase"], "initial_context")
        self.assertEqual(row["supervisor_error"]["message"], "worker context exceeds configured budget")
        self.assertFalse(row["genuine_model_implementation_observed"])
        self.assertIsNone(row["provider_usage"]["complete_tokens"]["total_tokens"])

    def test_job_summary_during_verifier_does_not_finalize_attempt(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            folder = root / "trials/test"
            attempt = folder / "jobs/job/attempt"
            (attempt / "agent").mkdir(parents=True)
            (folder / "config.json").write_text(json.dumps({"job_name": "job"}))
            (folder / "jobs/job/result.json").write_text("{}")
            (attempt / "agent/supervisor-result.json").write_text(json.dumps({"provider_invocations": [call()]}))
            selected = {"name": "test", "task": "task", "semantic_context_profile": "indexed-default@1"}
            value = aggregate.collect_trial(root, selected, {"preparations": {}})
            self.assertEqual(value["state"], "started_or_partial")
            self.assertFalse(value["usage_complete"])
            self.assertIsNone(value["complete_tokens"]["total_tokens"])
            self.assertIsNone(value["frozen_controls"]["observed_tasks_match_selection"])
            self.assertEqual(value["known_token_subtotal"]["total_tokens"], 110)


if __name__ == "__main__":
    unittest.main(verbosity=2)

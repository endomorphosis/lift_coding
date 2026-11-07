from __future__ import annotations

import copy
import contextlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import watchdog_loop as w

HERE = Path(__file__).resolve().parent


class WatchdogScenarios(unittest.TestCase):
    def setUp(self):
        self.policy = json.loads((HERE / "watchdog.policy.json").read_text())
        self.now = 10_000
        self.snapshot = {
            "schema": "wwl.watchdog.snapshot@1", "run_id": "test-run", "observed_at": self.now,
            "authority_revision": "native-task-revision-1", "accepted_tree": "accepted-tree-1", "admitted_plan_revision": "plan-1",
            "hold": False, "completion_verified": False, "completion_receipt": "",
            "required_task_ids": ["WWL-000", "WWL-001"], "verified_task_ids": [],
            "stage": "implementation", "task_id": "WWL-000", "progress_token": "artifact-stage-1",
            "heartbeat_at": self.now, "owner_alive": True, "owner_identity_verified": True,
            "runnable_count": 0, "blocked_kind": "none", "dependency_running": False,
            "stage_deadline_at": self.now + 3000, "effects_unknown": False,
            "failure_key": "", "reproducer_receipt": "",
        }
        self.state = w.initial_state(self.policy, "test-run", self.now - 2000)
        self.state.update(progress_token=self.snapshot["progress_token"], last_progress_at=self.now - 100)

    def poll(self, offset=0):
        now = self.now + offset
        self.snapshot["observed_at"] = now
        self.snapshot["heartbeat_at"] = now
        return w.decide(self.snapshot, self.state, self.policy, now)

    def confirmed(self):
        self.assertEqual(self.poll()["status"], "suspect")
        self.assertEqual(self.poll(30)["status"], "suspect")
        return self.poll(60)

    def test_bounded_active_work_is_healthy(self):
        self.assertEqual(self.poll()["status"], "healthy")
        self.assertEqual(self.state["actions"], 0)

    def test_fresh_heartbeat_does_not_mask_frozen_progress(self):
        self.state["last_progress_at"] = self.now - 1300
        result = self.confirmed()
        self.assertEqual(result["action"]["reason"], "meaningful_progress_stalled")
        self.assertEqual(result["action"]["kind"], "reconcile")

    def test_log_growth_does_not_refresh_progress(self):
        self.state["last_progress_at"] = self.now - 1300
        self.snapshot["log_bytes"] = 1_000_000
        self.poll()
        self.snapshot["log_bytes"] = 2_000_000
        self.poll(30)
        self.assertEqual(self.poll(60)["status"], "action_requested")

    def test_verified_artifact_progress_refreshes_timer(self):
        self.state["last_progress_at"] = self.now - 1300
        self.poll()
        self.snapshot["progress_token"] = "accepted-artifact-2"
        self.assertEqual(self.poll(30)["status"], "healthy")
        self.assertEqual(self.state["last_progress_at"], self.now + 30)

    def test_idle_runnable_frontier_recovers_after_confirmations(self):
        self.snapshot.update(task_id="", stage="idle", runnable_count=2, stage_deadline_at=0)
        self.state["last_progress_at"] = self.now - 400
        self.assertEqual(self.confirmed()["action"]["kind"], "recover")

    def test_dependency_work_is_not_idle_failure(self):
        self.snapshot.update(task_id="", dependency_running=True, stage_deadline_at=0)
        self.state["last_progress_at"] = self.now - 1500
        self.assertEqual(self.poll()["status"], "waiting")

    def test_external_credential_blocker_has_no_repair_attempt(self):
        self.snapshot["blocked_kind"] = "credentials"
        result = self.poll()
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(self.state["actions"], 0)

    def test_external_blocker_does_not_hold_independent_ready_work(self):
        self.snapshot.update(blocked_kind="credentials", task_id="", stage="idle", runnable_count=2)
        self.state["last_progress_at"] = self.now - 400
        self.assertEqual(self.confirmed()["action"]["kind"], "recover")

    def test_hold_prevents_even_unknown_effect_dispatch(self):
        self.snapshot.update(hold=True, effects_unknown=True)
        self.assertEqual(self.poll()["status"], "held")
        self.assertEqual(self.state["actions"], 0)

    def test_unknown_effects_take_precedence_over_code_repair(self):
        self.snapshot.update(effects_unknown=True, blocked_kind="software_defect", failure_key="reproducer", reproducer_receipt="native:reproducer")
        self.assertEqual(self.confirmed()["action"]["kind"], "reconcile")
        self.assertEqual(self.state["repairs"], 0)

    def test_reproduced_defect_requests_native_isolated_repair(self):
        self.snapshot.update(blocked_kind="software_defect", failure_key="queue-cas-defect", reproducer_receipt="native:reproducer")
        result = self.confirmed()
        self.assertEqual(result["action"]["kind"], "repair")
        self.assertEqual(result["action"]["reproducer_receipt"], "native:reproducer")
        self.assertFalse(result["completion_authority"])

    def test_unreproduced_defect_cannot_request_code_repair(self):
        self.snapshot.update(blocked_kind="software_defect", failure_key="unknown-defect")
        self.assertEqual(self.confirmed()["action"]["kind"], "reconcile")

    def test_unverified_owner_identity_requires_reconciliation(self):
        self.snapshot["owner_identity_verified"] = False
        self.assertEqual(self.confirmed()["action"]["kind"], "reconcile")

    def test_deadline_expiry_not_hidden_by_heartbeat(self):
        self.snapshot["stage_deadline_at"] = self.now - 1
        self.assertEqual(self.confirmed()["action"]["reason"], "stage_deadline_expired")

    def test_successful_dispatch_ack_does_not_complete_task(self):
        self.snapshot.update(blocked_kind="software_defect", failure_key="defect", reproducer_receipt="native:reproducer")
        action = self.confirmed()["action"]
        w.acknowledge(self.state, {"schema": "wwl.watchdog.action-result@1", "action_id": action["action_id"], "status": "accepted", "receipt": "native:admitted", "deadline_at": self.now + 1000}, self.policy, self.now + 60)
        self.assertIsNone(self.state["outbox"])
        self.assertIn(action["action_id"], self.state["inflight"])
        self.assertEqual(self.poll(90)["reason"], "native_action_in_progress")
        self.assertFalse(self.snapshot["completion_verified"])

    def test_lost_ack_stays_in_outbox_and_reconciles_original_incident(self):
        self.snapshot.update(blocked_kind="software_defect", failure_key="defect", reproducer_receipt="native:reproducer")
        action = self.confirmed()["action"]
        with self.assertRaises(w.ContractError):
            w.acknowledge(self.state, {"status": "ok"}, self.policy, self.now + 60)
        self.assertEqual(self.state["outbox"]["action_id"], action["action_id"])
        result = self.poll(361)
        self.assertEqual(result["action"]["kind"], "reconcile")
        self.assertEqual(result["action"]["incident_id"], action["incident_id"])
        self.assertEqual(result["action"]["previous_unacknowledged_action"], action["action_id"])

    def test_retry_budget_persists_across_loop_restart(self):
        self.snapshot.update(blocked_kind="software_defect", failure_key="defect", reproducer_receipt="native:reproducer")
        result = self.confirmed()
        for offset in (361, 1000):
            action = result["action"]
            w.acknowledge(self.state, {"schema": "wwl.watchdog.action-result@1", "action_id": action["action_id"], "status": "accepted", "receipt": "native:repair-admitted", "deadline_at": self.now + 3000}, self.policy, self.now + offset - 1)
            self.snapshot["action_observations"] = [{"schema": "wwl.watchdog.action-observation@1", "action_id": action["action_id"], "status": "failed", "effects_verified": True, "receipt": "native:verified-terminal-failure"}]
            with tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "watchdog.json"
                w.atomic_save(path, self.state)
                self.state = w.read_json(path)
            result = self.poll(offset)
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(result["reason"], "repair_incident_budget_exhausted")
        self.assertEqual(self.state["repairs"], 2)

    def test_campaign_cap_does_not_reset_for_new_defect(self):
        self.state["repairs"] = self.policy["max_campaign_repairs"]
        self.snapshot.update(blocked_kind="software_defect", failure_key="different-defect", reproducer_receipt="native:reproducer")
        self.assertEqual(self.confirmed()["status"], "blocked")

    def test_same_poll_cannot_supply_three_confirmations(self):
        self.state["last_progress_at"] = self.now - 1300
        for _ in range(10):
            self.assertEqual(self.poll()["status"], "suspect")
        self.assertEqual(self.state["actions"], 0)

    def test_healthy_intervals_reset_dead_owner_confirmation_streak(self):
        for offset in (0, 60, 120):
            self.snapshot["owner_alive"] = False
            self.assertEqual(self.poll(offset)["status"], "suspect")
            self.snapshot["owner_alive"] = True
            self.assertEqual(self.poll(offset + 30)["status"], "healthy")
        self.assertEqual(self.state["actions"], 0)

    def test_persisted_source_expansion_cannot_be_pruned_after_restart(self):
        expanded_id = "WWL-SRC-0123456789abcdef-verify-0001"
        self.snapshot["required_task_ids"].append(expanded_id)
        self.poll()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "state.json"
            w.atomic_save(path, self.state)
            self.state = w.read_json(path)
        self.snapshot["required_task_ids"].remove(expanded_id)
        with self.assertRaises(w.ContractError):
            self.poll(30)

    def test_admitted_long_repair_is_not_duplicated_after_cooldown(self):
        self.snapshot.update(blocked_kind="software_defect", failure_key="defect", reproducer_receipt="native:reproducer")
        action = self.confirmed()["action"]
        w.acknowledge(self.state, {"schema": "wwl.watchdog.action-result@1", "action_id": action["action_id"], "status": "accepted", "receipt": "native:admitted", "deadline_at": self.now + 3000}, self.policy, self.now + 60)
        for offset in (361, 900, 1600):
            self.assertEqual(self.poll(offset)["reason"], "native_action_in_progress")
        self.assertEqual(self.state["repairs"], 1)
        self.assertEqual(self.state["actions"], 1)

    def test_native_terminal_receipt_is_required_to_settle_action(self):
        self.snapshot.update(blocked_kind="software_defect", failure_key="defect", reproducer_receipt="native:reproducer")
        action = self.confirmed()["action"]
        w.acknowledge(self.state, {"schema": "wwl.watchdog.action-result@1", "action_id": action["action_id"], "status": "accepted", "receipt": "native:admitted", "deadline_at": self.now + 3000}, self.policy, self.now + 60)
        self.snapshot["action_observations"] = [{"schema": "wwl.watchdog.action-observation@1", "action_id": action["action_id"], "status": "succeeded", "effects_verified": False, "receipt": "unverified"}]
        with self.assertRaises(w.ContractError):
            self.poll(90)
        self.assertIn(action["action_id"], self.state["inflight"])

    def test_completion_requires_full_current_native_evidence(self):
        self.snapshot.update(completion_verified=True, completion_receipt="native:root-completion", task_id="", runnable_count=0, verified_task_ids=["WWL-000", "WWL-001"])
        self.assertEqual(self.poll()["status"], "complete")
        self.snapshot["verified_task_ids"] = ["WWL-000"]
        with self.assertRaises(w.ContractError):
            self.poll(30)

    def test_count_only_completion_needs_verifier(self):
        self.snapshot.update(task_id="", stage="idle", runnable_count=0, verified_task_ids=["WWL-000", "WWL-001"])
        self.assertEqual(self.confirmed()["action"]["reason"], "completion_needs_native_verification")

    def test_outstanding_action_blocks_completion_exit(self):
        self.snapshot.update(blocked_kind="software_defect", failure_key="defect", reproducer_receipt="native:reproducer")
        self.confirmed()
        self.snapshot.update(completion_verified=True, completion_receipt="native:root", task_id="", runnable_count=0, verified_task_ids=["WWL-000", "WWL-001"])
        self.assertNotEqual(self.poll(90)["status"], "complete")

    def test_stale_snapshot_and_policy_drift_fail_closed(self):
        stale = copy.deepcopy(self.snapshot)
        stale["observed_at"] -= 200
        with self.assertRaises(w.ContractError):
            w.decide(stale, self.state, self.policy, self.now)
        self.policy["max_campaign_repairs"] += 1
        with self.assertRaises(w.ContractError):
            self.poll()

    def test_native_readiness_requires_real_binding_contract(self):
        plan = json.loads((HERE / "plan.json").read_text())
        ready = {"schema": "wwl.watchdog.ready@1", "policy_id": self.policy["policy_id"], "run_id": "test-run", "native_revision": "operational-commit", "admitted_plan_revision": "plan-revision-1", "readiness_receipt": "native:verified-canary", "repository": plan["product"]["repository"], "required_task_ids": [t["id"] for t in plan["tasks"]], "bindings": {key: True for key in w.BINDINGS}}
        self.assertEqual(w.ready_check(ready, plan, self.policy), "test-run")
        ready["bindings"]["rescue_orchestrator"] = False
        with self.assertRaises(w.ContractError):
            w.ready_check(ready, plan, self.policy)

    def test_source_expansion_needs_a_bound_native_receipt(self):
        plan = json.loads((HERE / "plan.json").read_text())
        ready = {"schema": "wwl.watchdog.ready@1", "policy_id": self.policy["policy_id"], "run_id": "test-run", "native_revision": "operational-commit", "admitted_plan_revision": "expanded-plan-2", "readiness_receipt": "native:canary", "repository": plan["product"]["repository"], "required_task_ids": [t["id"] for t in plan["tasks"]] + ["WWL-SRC-0123456789abcdef-verify-0001"], "bindings": {key: True for key in w.BINDINGS}}
        with self.assertRaises(w.ContractError):
            w.ready_check(ready, plan, self.policy)
        ready["expansion_receipt"] = "native:inventory-bound-expansion"
        self.assertEqual(w.ready_check(ready, plan, self.policy), "test-run")
        ready["required_task_ids"].remove("WWL-000")
        with self.assertRaises(w.ContractError):
            w.ready_check(ready, plan, self.policy)

    def test_owned_loop_lock_prevents_duplicate_driver(self):
        with tempfile.TemporaryDirectory() as directory:
            lock = Path(directory) / "watchdog.lock"
            with w.owner_lock(lock):
                with self.assertRaises(w.ContractError):
                    with w.owner_lock(lock):
                        self.fail("duplicate lock acquired")

    def test_fixture_cli_never_dispatches_or_writes_state(self):
        with tempfile.TemporaryDirectory() as directory:
            state = Path(directory) / "state.json"
            fixture = Path(directory) / "snapshot.json"
            fixture.write_text(json.dumps(self.snapshot))
            command = [sys.executable, "-B", str(HERE / "watchdog_loop.py"), "--snapshot", str(fixture), "--once", "--state", str(state)]
            result = subprocess.run(command, capture_output=True, text=True, check=False)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(json.loads(result.stdout)["observation_only"])
            self.assertFalse(state.exists())
            forbidden = subprocess.run([*command, "--execute"], capture_output=True, text=True, check=False)
            self.assertEqual(forbidden.returncode, 2)
            self.assertFalse(state.exists())

    def test_execute_loop_waits_for_native_action_settlement_before_completion(self):
        plan = json.loads((HERE / "plan.json").read_text())
        required = [t["id"] for t in plan["tasks"]]
        ready = {"schema": "wwl.watchdog.ready@1", "policy_id": self.policy["policy_id"], "run_id": "test-run", "native_revision": "accepted-operational-code", "admitted_plan_revision": "plan-1", "readiness_receipt": "native:canary", "repository": plan["product"]["repository"], "required_task_ids": required, "bindings": {key: True for key in w.BINDINGS}}
        clock, observed, dispatched = [self.now], [0], []

        def adapter(argv, operation, request, timeout):
            if operation == "ready":
                return copy.deepcopy(ready)
            if operation == "dispatch":
                dispatched.append(copy.deepcopy(request))
                return {"schema": "wwl.watchdog.action-result@1", "action_id": request["action_id"], "status": "accepted", "receipt": "native:repair-admitted", "deadline_at": clock[0] + 1200}
            self.assertEqual(operation, "observe")
            observed[0] += 1
            snapshot = copy.deepcopy(self.snapshot)
            snapshot.update(observed_at=clock[0], heartbeat_at=clock[0], required_task_ids=required, blocked_kind="software_defect", failure_key="stable-defect", reproducer_receipt="native:reproducer")
            if observed[0] == 4:
                self.assertEqual(request["action_ids"], [dispatched[0]["action_id"]])
                snapshot["action_observations"] = [{"schema": "wwl.watchdog.action-observation@1", "action_id": dispatched[0]["action_id"], "status": "running", "receipt": "native:repair-active", "effects_verified": False, "deadline_at": dispatched[0]["issued_at"] + 1200}]
            if observed[0] == 5:
                snapshot.update(blocked_kind="none", failure_key="", reproducer_receipt="", completion_verified=True, completion_receipt="native:verified-root", task_id="", stage="", verified_task_ids=required)
                snapshot["action_observations"] = [{"schema": "wwl.watchdog.action-observation@1", "action_id": dispatched[0]["action_id"], "status": "succeeded", "receipt": "native:verified-repair-effects", "effects_verified": True}]
            self.assertLess(observed[0], 6, "loop did not finish after verified settlement")
            return snapshot

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "watchdog.json"
            with patch.object(w, "call_adapter", side_effect=adapter), patch.object(w.time, "time", side_effect=lambda: clock[0]), patch.object(w.time, "sleep", side_effect=lambda seconds: clock.__setitem__(0, clock[0] + seconds)), contextlib.redirect_stdout(io.StringIO()):
                code = w.main(["--adapter-argv-json", '["native-contract-fixture"]', "--state", str(path), "--execute"])
            self.assertEqual(code, 0)
            self.assertEqual(len(dispatched), 1)
            state = w.read_json(path)
            self.assertEqual(state["actions"], 1)
            self.assertEqual(state["inflight"], {})
            self.assertEqual(state["settled_actions"][dispatched[0]["action_id"]]["status"], "succeeded")
            self.assertEqual(state["required_task_ids"], required)

    def test_execute_restart_rejects_pruned_source_tasks_at_readiness(self):
        plan = json.loads((HERE / "plan.json").read_text())
        required = [t["id"] for t in plan["tasks"]]
        ready = {"schema": "wwl.watchdog.ready@1", "policy_id": self.policy["policy_id"], "run_id": "test-run", "native_revision": "accepted-operational-code", "admitted_plan_revision": "plan-1", "readiness_receipt": "native:canary", "repository": plan["product"]["repository"], "required_task_ids": required, "bindings": {key: True for key in w.BINDINGS}}
        self.state["required_task_ids"] = required + ["WWL-SRC-0123456789abcdef-publish-0001"]
        self.state["admitted_plan_revision"] = "expanded-plan-2"
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "watchdog.json"
            w.atomic_save(path, self.state)
            with patch.object(w, "call_adapter", return_value=ready) as adapter, contextlib.redirect_stderr(io.StringIO()) as errors:
                code = w.main(["--adapter-argv-json", '["native-contract-fixture"]', "--state", str(path), "--execute", "--once"])
            self.assertEqual(code, 2)
            self.assertEqual(adapter.call_count, 1)
            self.assertIn("pruned required tasks", errors.getvalue())
            self.assertEqual(w.read_json(path)["required_task_ids"], self.state["required_task_ids"])


if __name__ == "__main__":
    unittest.main()

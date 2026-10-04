from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

SPEC = importlib.util.spec_from_file_location("paper_worker_observation", Path(__file__).resolve().parents[1] / "scripts/paper_worker_observation.py")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class WorkerObservationTests(unittest.TestCase):
    def projection(self, lane, attempt, *, binding=True, claim=None, heartbeat="2026-09-11T10:00:00Z"):
        path = lane / "state/paper_database_portal_attempts" / attempt / "portal-task-state.json"
        path.parent.mkdir(parents=True)
        path.write_text(json.dumps({"active_task_id": "NS-002", "heartbeat_at": heartbeat}))
        if binding:
            path.with_name("database-attempt-binding.json").write_text(json.dumps({
                "task_cid": "cid:task", "attempt_id": attempt, "claim_id": claim or "claim:" + attempt}))
        return path

    def owner_task(self, status="in_progress", attempt="new", claim=None):
        return {"task_cid": "cid:task", "task_alias": "NS-002", "status": status,
                "body_json": json.dumps({"completion_receipt": {
                    "operation": "database_claim", "attempt_id": attempt, "claim_id": claim or "claim:" + attempt}})}

    def test_old_and_current_same_alias_match_exact_claim_and_preserve_files(self):
        with tempfile.TemporaryDirectory() as temp:
            lane = Path(temp)
            old = self.projection(lane, "old")
            current = self.projection(lane, "new")
            # Same attempt ID but a different claim must also be historical.
            wrong_claim = self.projection(lane, "wrong", claim="claim:wrong")
            binding = wrong_claim.with_name("database-attempt-binding.json")
            value = json.loads(binding.read_text()); value["attempt_id"] = "new"
            binding.write_text(json.dumps(value))
            before = {p: p.read_bytes() for p in lane.rglob("*.json")}
            result = MODULE.observe_lane(lane, now=1789124400, authoritative_tasks=[self.owner_task()])
            records = {r["projection"]: r for r in result["attempts"]}
            self.assertEqual(records[str(old)]["authority_match"], "historical")
            self.assertEqual(records[str(wrong_claim)]["authority_match"], "historical")
            self.assertEqual(records[str(current)]["authority_match"], "current")
            self.assertEqual([n["projection"] for n in result["notices"]], [str(current)])
            self.assertEqual(before, {p: p.read_bytes() for p in before})

    def test_completed_owner_task_suppresses_nonterminal_projection(self):
        with tempfile.TemporaryDirectory() as temp:
            lane = Path(temp)
            self.projection(lane, "old")
            result = MODULE.observe_lane(lane, now=1789124400, authoritative_tasks=[self.owner_task("done")])
            self.assertTrue(result["attempts"][0]["active_projection"])
            self.assertEqual(result["attempts"][0]["authority_match"], "historical")
            self.assertEqual(result["notices"], [])

    def test_missing_binding_cannot_mask_current_claim_even_with_fresh_same_alias(self):
        with tempfile.TemporaryDirectory() as temp:
            lane = Path(temp)
            self.projection(lane, "old")
            self.projection(lane, "new", binding=False, heartbeat="2026-09-11T11:00:00Z")
            now = datetime(2026, 9, 11, 11, tzinfo=timezone.utc).timestamp()
            result = MODULE.observe_lane(lane, now=now, authoritative_tasks=[self.owner_task()])
            self.assertEqual({r["authority_match"] for r in result["attempts"]}, {"historical", "unconfirmed"})
            self.assertEqual([n["reason"] for n in result["notices"]], ["current_owner_claim_projection_unconfirmed"])

    def test_unknown_or_malformed_owner_claim_does_not_suppress_stale_attempt(self):
        with tempfile.TemporaryDirectory() as temp:
            lane = Path(temp)
            self.projection(lane, "new")
            for tasks in (None, [], [dict(self.owner_task(), body_json="{")]):
                with self.subTest(tasks=tasks):
                    result = MODULE.observe_lane(lane, now=1789124400, authoritative_tasks=tasks)
                    self.assertEqual(result["attempts"][0]["authority_match"], "unconfirmed")
                    self.assertIn("active_projection_heartbeat_missing_or_stale", [n["reason"] for n in result["notices"]])

    def test_completed_history_does_not_raise_stall_and_active_stale_does(self):
        with tempfile.TemporaryDirectory() as temp:
            lane = Path(temp)
            for key, task in (("finished", ""), ("active", "AF-001")):
                path = lane / "state/paper_database_portal_attempts" / key / "portal-task-state.json"
                path.parent.mkdir(parents=True)
                path.write_text(json.dumps({"active_task_id": task, "heartbeat_at": "2026-09-11T10:00:00Z"}))
            before = {p: p.read_bytes() for p in lane.rglob("*.json")}
            now = datetime(2026, 9, 11, 11, tzinfo=timezone.utc).timestamp()
            result = MODULE.observe_lane(lane, now=now)
            self.assertEqual([n["task"] for n in result["notices"]], ["AF-001"])
            self.assertFalse(result["authoritative"])
            self.assertEqual(before, {p: p.read_bytes() for p in before})

    def test_malformed_projection_and_outside_log_do_not_hide_other_worker(self):
        with tempfile.TemporaryDirectory() as temp:
            lane = Path(temp)
            root = lane / "state/paper_database_portal_attempts"
            for key, body in (("bad", "{"), ("good", json.dumps({"active_task_id": "AF-002", "heartbeat_at": "2026-09-11T11:00:00Z", "last_implementation_log_path": "/etc/passwd"}))):
                path = root / key / "portal-task-state.json"
                path.parent.mkdir(parents=True)
                path.write_text(body)
            now = datetime(2026, 9, 11, 11, tzinfo=timezone.utc).timestamp()
            result = MODULE.observe_lane(lane, now=now)
            self.assertEqual(len(result["attempts"]), 1)
            self.assertNotIn("log_path", result["attempts"][0])
            self.assertEqual(result["notices"][0]["reason"], "worker_projection_unreadable")


if __name__ == "__main__":
    unittest.main()

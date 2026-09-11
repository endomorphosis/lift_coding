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

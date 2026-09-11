"""Bounded campaign lifecycle and real temporary Quack/DuckLake integration."""
from __future__ import annotations

import fcntl
import importlib.util
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import threading
import types
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


CAM = load("campaign_under_test", "paper_supervisor_campaign.py")
MAT = load("campaign_materializer_under_test", "materialize_paper_database.py")
LAKE = load("campaign_projection_under_test", "paper_ducklake_projection.py")
WORKERS = load("campaign_workers_under_test", "paper_worker_observation.py")


def native_ready(process, database, paper):
    record = CAM.process_record(process.pid)
    return {"ready": True, "database": str(database.resolve()),
            "store_id": "vericodegen-2026-" + paper,
            "identity": {"process_birth": {"pid": record["pid"],
                         "start_time_ticks": int(record["birth"]),
                         "boot_id": record["boot_id"]}}}


class CampaignTests(unittest.TestCase):
    def test_environment_selects_complete_terra_high_quota_route_and_scrubs_foreign_scope(self):
        expected = {
            "IPFS_ACCELERATE_AGENT_IMPLEMENTATION_PROVIDER": "grok",
            "IPFS_ACCELERATE_AGENT_GROK_MODEL": "grok-4.6",
            "IPFS_ACCELERATE_AGENT_IMPLEMENTATION_FALLBACK_PROVIDER": "codex",
            "IPFS_ACCELERATE_AGENT_CODEX_MODEL": "gpt-5.6-terra",
            "IPFS_ACCELERATE_AGENT_IMPLEMENTATION_FALLBACK_TRIGGER": "primary_quota_exhausted",
            "IPFS_ACCELERATE_AGENT_CODEX_REASONING_EFFORT": "high",
        }
        foreign = {"IPFS_ACCELERATE_AGENT_IMPLEMENTATION_ROUTE_" + suffix: "foreign-test-only"
                   for suffix in ("BOARD_NAMESPACE", "AUTHORIZATION_PATH", "AUTHORIZATION_SHA256",
                                  "AUTHORIZATION_ID", "AUTHORIZATION_KIND", "SOURCE_HEAD", "SOURCE_TREE", "ID")}
        foreign.update({key: "foreign-test-only" for key in (
            "IPFS_ACCELERATE_AGENT_STATE_STORE_ID", "IPFS_ACCELERATE_AGENT_QUACK_ENDPOINT",
            "IPFS_ACCELERATE_AGENT_QUACK_TOKEN", "IPFS_ACCELERATE_AGENT_DATABASE_PROGRAM_JSON")})
        inherited = {**{key: "conflicting-inherited-value" for key in expected}, **foreign,
                     "PAPER_TEST_UNRELATED": "preserved"}
        with patch.dict(os.environ, inherited, clear=True):
            result = CAM.environment(ROOT)
            self.assertEqual(dict(os.environ), inherited)
        self.assertEqual({key: result[key] for key in expected}, expected)
        self.assertFalse(set(foreign) & set(result))
        self.assertEqual(result["PAPER_TEST_UNRELATED"], "preserved")
        self.assertEqual(result["PYTHONPATH"], os.pathsep.join(str(ROOT / p) for p in CAM.SUBMODULES))
        # Resolve through the actual native selector: six strings alone must
        # produce the supported quota-only high route, not an ambient default.
        with patch.object(sys, "path", [str(ROOT / p) for p in CAM.SUBMODULES] + sys.path), patch.dict(os.environ, result, clear=True):
            from ipfs_accelerate_py.agent_supervisor.todo_daemon.implementation_daemon import _configured_agent_implementation_route_plan
            route = _configured_agent_implementation_route_plan(ROOT)
        self.assertEqual((route.primary_provider_id, route.primary_model_id,
                          route.fallback_provider_id, route.fallback_model_id,
                          route.fallback_trigger, route.fallback_reasoning_effort),
                         ("grok_cli", "grok-4.6", "codex", "gpt-5.6-terra", "primary_quota_exhausted", "high"))
        self.assertFalse(route.permits_authentication_unavailable)
        self.assertIsNone(route.authorization)
        self.assertIsNone(route.invocation_binding)

    def test_worker_observation_forwards_fresh_owner_tasks(self):
        rows = [{"task_cid": "cid:test", "status": "done"}]
        with patch.object(WORKERS, "observe_lane", return_value={"checked": True}) as observe, patch.dict(sys.modules, {"paper_worker_observation": WORKERS}):
            self.assertEqual(CAM.worker_observation(Path("/tmp/test-lane"), authoritative_tasks=rows), {"checked": True})
        observe.assert_called_once_with(Path("/tmp/test-lane"), authoritative_tasks=rows)

    def test_birth_parsing_and_identity_validation(self):
        # The parenthesized comm field itself may contain spaces and ')'.
        text = "123 (python ) worker) S " + " ".join(["0"] * 18 + ["7654321", "0"])
        with patch.object(Path, "read_text", return_value=text):
            self.assertEqual(CAM.birth(123), "7654321")
        current = CAM.process_record(os.getpid())
        self.assertTrue(CAM.alive(current))
        self.assertFalse(CAM.alive(dict(current, boot_id="different-boot")))
        for bad in (None, {}, {"pid": "oops"}, {"pid": -1, "birth": "1"}):
            self.assertFalse(CAM.alive(bad))

    def test_live_foreign_owner_is_preserved_and_cannot_satisfy_child_readiness(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            database = root / "control.duckdb"
            ready_path = root / "paper-owner.ready.json"
            foreign = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
            child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
            try:
                ready = native_ready(foreign, database, "law_to_action")
                CAM.write(ready_path, ready)
                original = ready_path.read_bytes()
                with self.assertRaisesRegex(RuntimeError, "live owner already exists"):
                    CAM.prepare_owner_start(ready_path, "law_to_action")
                self.assertEqual(ready_path.read_bytes(), original)
                with self.assertRaisesRegex(RuntimeError, "different owner process"):
                    CAM.wait_owner_ready(child, CAM.process_record(child.pid), ready_path,
                                         paper="law_to_action", database=database, timeout=1)
                self.assertEqual(CAM.cleanup_children([("owner", child, CAM.process_record(child.pid))]), [])
                self.assertIsNotNone(child.poll())
                self.assertIsNone(foreign.poll())
                self.assertEqual(ready_path.read_bytes(), original)
            finally:
                for process in (child, foreign):
                    if process.poll() is None:
                        process.terminate()
                    process.wait(timeout=10)

    def test_dirty_preflight_starts_nothing_and_duplicate_lock_preserves_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp) / "state"
            state.mkdir()
            old_handler = signal.getsignal(signal.SIGTERM)
            def git(argv, **_kwargs):
                return "agent/vericodegen-2026-law_to_action\n" if argv[1] == "branch" else "?? scripts/uncommitted.py\n"
            with patch.object(CAM, "PAPERS", ("law_to_action",)), patch.object(CAM.subprocess, "check_output", side_effect=git), patch.object(CAM, "launch") as launch:
                with self.assertRaisesRegex(RuntimeError, "uncommitted changes"):
                    CAM.serve(state, Path(tmp))
                launch.assert_not_called()
            self.assertEqual(signal.getsignal(signal.SIGTERM), old_handler)
            report_bytes = (state / "campaign.json").read_bytes()
            with (state / "campaign.lock").open("a") as held:
                fcntl.flock(held, fcntl.LOCK_EX | fcntl.LOCK_NB)
                with self.assertRaises(BlockingIOError):
                    CAM.serve(state, Path(tmp))
            self.assertEqual((state / "campaign.json").read_bytes(), report_bytes)

    def test_sigterm_stops_only_owned_dummy_children_and_releases_lock(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state, paper = root / "state", "law_to_action"
            lane = state / paper
            lane.mkdir(parents=True)
            (lane / "control.duckdb").touch()
            (lane / "control.duckdb.bootstrap.json").write_text("{}")
            children, timers = [], []
            original_launch = CAM.launch
            old_handler = signal.getsignal(signal.SIGTERM)
            def git(argv, **_kwargs):
                if argv[1] == "branch":
                    return f"agent/vericodegen-2026-{paper}\n"
                return "" if argv[1] == "status" else "tracked\n"
            def launch(argv, cwd, env, log):
                process, record = original_launch([sys.executable, "-c", "import time; time.sleep(60)"], root, env, log)
                children.append(process)
                if len(children) == 1:
                    ready = native_ready(process, lane / "control.duckdb", paper)
                    ready.update(quack_endpoint="quack://127.0.0.1:1", endpoint_secret_handle="handle:test")
                    CAM.write(lane / "quack-owner/paper-owner.ready.json", ready)
                else:
                    timer = threading.Timer(0.2, os.kill, args=(os.getpid(), signal.SIGTERM))
                    timer.start()
                    timers.append(timer)
                return process, record
            fake_projection = types.SimpleNamespace(project_snapshot=lambda *args, **kwargs: {"ok": True})
            try:
                with patch.object(CAM, "PAPERS", (paper,)), patch.object(CAM.subprocess, "check_output", side_effect=git), patch.object(CAM, "launch", side_effect=launch), patch.object(CAM, "fetch_board", return_value={"paper_id": paper, "tasks": []}), patch.object(CAM, "token_for", return_value="temporary-test-only"), patch.object(CAM, "native_argv", return_value=[]), patch.dict(sys.modules, {"paper_ducklake_projection": fake_projection, "paper_worker_observation": WORKERS}):
                    CAM.serve(state, root)
                self.assertEqual(len(children), 2)
                self.assertTrue(all(process.poll() is not None for process in children))
                self.assertEqual(signal.getsignal(signal.SIGTERM), old_handler)
                report = CAM.read(state / "campaign.json")
                self.assertIn("stopped_at", report)
                self.assertEqual(report["cleanup_errors"], [])
                workers = CAM.read(state / "health.json")["workers"][paper]
                self.assertFalse(workers["authoritative"])
                self.assertTrue(workers["owner_tasks_supplied"])
                self.assertEqual(workers["projection_count"], 0)
                with (state / "campaign.lock").open("a") as lock:
                    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            finally:
                for timer in timers:
                    timer.join(timeout=2)
                for process in children:
                    if process.poll() is None:
                        process.terminate()
                    process.wait(timeout=10)

    def test_three_real_owners_snapshot_and_actual_ducklake_projection(self):
        # No provider runs: reviewed manifests seed isolated temporary databases.
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp)
            children = []
            try:
                for paper in CAM.PAPERS:
                    lane = state / paper
                    lane.mkdir()
                    database = lane / "control.duckdb"
                    MAT.materialize(paper, database, ROOT)
                    argv = [sys.executable, str(ROOT / "scripts/paper_state_owner.py"),
                            "--database", str(database), "--state-dir", str(lane / "quack-owner"),
                            "--store-id", "vericodegen-2026-" + paper,
                            "--secret-handle", "handle:campaign-test:" + paper]
                    process, record = CAM.launch(argv, ROOT, CAM.environment(ROOT), lane / "owner.log")
                    children.append(("owner", process, record))
                    CAM.wait_owner_ready(process, record, lane / "quack-owner/paper-owner.ready.json",
                                         paper=paper, database=database, timeout=25)
                snap = CAM.snapshot(state)
                self.assertEqual({b["paper_id"] for b in snap["boards"]}, set(CAM.PAPERS))
                self.assertEqual(len({b["store_identity"]["database_uuid"] for b in snap["boards"]}), 3)
                for board in snap["boards"]:
                    self.assertEqual(len(board["tasks"]), 25)
                    self.assertIn(board["tasks"][0]["status"], {"ready", "blocked"})
                    self.assertTrue(board["goals"])
                source = state / "snapshot.json"
                CAM.write(source, snap)
                result = LAKE.project_snapshot(snap, state / "lake", repo_root=ROOT, source_path=source)
                self.assertTrue(result["ok"])
                self.assertFalse(result["authoritative"])
                self.assertGreater(result["lake_snapshot_count"], 0)
                self.assertEqual(set(result["boards"]), set(CAM.PAPERS))
                self.assertTrue(all(b["current_task_rows"] == 25 for b in result["boards"].values()))
            finally:
                errors = CAM.cleanup_children(children)
                for _kind, process, _record in children:
                    if process.poll() is None:
                        process.kill()
                    process.wait(timeout=10)
                self.assertEqual(errors, [])


if __name__ == "__main__":
    unittest.main()

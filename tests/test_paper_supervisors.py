"""Evidence-integrity tests use temporary files; no providers or experiments run."""
from __future__ import annotations

import importlib.util
import fcntl
import os
import re
import select
import signal
import subprocess
import sys
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location(
    "paper_supervisors", Path(__file__).resolve().parents[1] / "scripts/paper_supervisors.py"
)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class PaperEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.paper = "law_to_action"
        self.base = f"papers/completion/{self.paper}"
        self.output = f"{self.base}/manuscript/main.tex"
        self.seeds = [self.seed("LA-001", "recover source")]
        self.tasks = [self.native("LA-001", "recover source")]
        self.goals = [SimpleNamespace(goal_id="LA-G000", fields={"parent": ""}),
                      SimpleNamespace(goal_id="LA-G1", fields={"parent": "LA-G000"})]
        self.cfg = {"root_goal_id": "LA-G000", "objective_path": f"{self.base}/goals.md",
                    "todo_path": f"{self.base}/todo.md", "task_prefix": "LA-",
                    "board_namespace": "paper-law"}
        self.write(self.cfg["objective_path"], "placeholder for mocked parser")
        self.write(self.cfg["todo_path"], "placeholder for mocked parser")
        for mocker in [
            patch.object(MODULE, "ROOT", self.root),
            patch.object(MODULE, "config", side_effect=lambda _: self.cfg),
            patch.object(MODULE, "manifest", side_effect=lambda _: {"tasks": self.seeds}),
            patch.object(MODULE, "native_modules", return_value=(lambda _: self.goals,
                                                                  lambda *_: self.tasks,
                                                                  None, None)),
        ]:
            mocker.start()
            self.addCleanup(mocker.stop)

    def seed(self, task_id, criterion):
        return {"id": task_id, "subgoal_id": "LA-G1", "deliverables": [self.output],
                "acceptance_criteria": [criterion], "depends_on": []}

    def native(self, task_id, acceptance, outputs=None):
        return SimpleNamespace(task_id=task_id, metadata={"goal id": "LA-G1"},
                               board_namespace="paper-law", depends_on=[],
                               outputs=outputs or [self.output], validation=["validate"],
                               acceptance=acceptance)

    def write(self, relative, text):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        return path

    def receipt(self, task_id="LA-001", text="version one", criterion="recover source",
                completed_at="2026-09-11T10:00:00Z", output=None):
        output = output or self.output
        self.write(output, text)
        snapshot = f"{self.base}/receipts/snapshots/{task_id}/main.tex"
        log = f"{self.base}/receipts/snapshots/{task_id}/validation.log"
        paths = {snapshot: self.write(snapshot, text), log: self.write(log, "validation passed\n")}
        receipt = {"schema": "paper-task-evidence/v1", "task_id": task_id, "status": "complete",
                   "completed_at": completed_at,
                   "artifacts": {name: MODULE.digest(path) for name, path in paths.items()},
                   "outputs": {output: snapshot},
                   "criteria": [{"criterion": criterion, "status": "met", "explanation": "Inspected artifact",
                                 "evidence": [snapshot]}],
                   "commands": [{"argv": ["python", "check.py"], "exit_code": 0, "log": log}],
                   "source_versions": {"repository": "commit-abc"}}
        self.save_receipt(task_id, receipt)
        return receipt

    def save_receipt(self, task_id, receipt):
        self.write(f"{self.base}/receipts/{task_id}.json", json.dumps(receipt))

    def test_valid_current_task(self):
        self.receipt()
        result = MODULE.verify_task(self.paper, "LA-001")
        self.assertTrue(result["current_outputs_checked"])

    def test_snapshot_tampering_rejected(self):
        receipt = self.receipt()
        self.write(next(iter(receipt["artifacts"])), "tampered")
        with self.assertRaisesRegex(ValueError, "changed.*evidence"):
            MODULE.verify_task(self.paper, "LA-001")

    def test_current_output_tampering_rejected(self):
        self.receipt()
        self.write(self.output, "changed without a later completion")
        with self.assertRaisesRegex(ValueError, "current output differs"):
            MODULE.verify_task(self.paper, "LA-001")

    def test_incomplete_evidence_rejected(self):
        receipt = self.receipt()
        receipt["criteria"][0]["evidence"] = []
        self.save_receipt("LA-001", receipt)
        with self.assertRaisesRegex(ValueError, "absent or unhashed"):
            MODULE.verify_task(self.paper, "LA-001")

    def test_missing_output_mapping_rejected(self):
        receipt = self.receipt()
        receipt["outputs"] = {}
        self.save_receipt("LA-001", receipt)
        with self.assertRaisesRegex(ValueError, "current-output mappings"):
            MODULE.verify_task(self.paper, "LA-001")

    def test_naive_or_non_utc_timestamp_rejected(self):
        for timestamp in ("2026-09-11T10:00:00", "2026-09-11T10:00:00+03:00"):
            with self.subTest(timestamp=timestamp):
                self.receipt(completed_at=timestamp)
                with self.assertRaisesRegex(ValueError, "explicit UTC"):
                    MODULE.verify_task(self.paper, "LA-001")

    def test_historical_edits_pass_root_but_original_current_task_fails(self):
        self.receipt()
        self.seeds.append(self.seed("LA-022", "complete paper"))
        self.tasks.append(self.native("LA-022", "complete paper"))
        self.receipt("LA-022", "version two", "complete paper", "2026-09-11T11:00:00Z")
        with self.assertRaisesRegex(ValueError, "current output differs"):
            MODULE.verify_task(self.paper, "LA-001")
        results = MODULE.verify_goal(self.paper, "LA-G000")
        self.assertEqual({r["task"] for r in results}, {"LA-001", "LA-022"})
        self.assertTrue(all(r["latest_outputs_checked_at_root"] for r in results))
        self.write(self.output, "unrecorded later edit")
        with self.assertRaisesRegex(ValueError, "current output differs"):
            MODULE.verify_goal(self.paper, "LA-G000")

    def test_historical_snapshot_tampering_still_fails_root(self):
        old = self.receipt()
        self.seeds.append(self.seed("LA-022", "complete paper"))
        self.tasks.append(self.native("LA-022", "complete paper"))
        self.receipt("LA-022", "version two", "complete paper", "2026-09-11T11:00:00Z")
        self.write(next(iter(old["artifacts"])), "rewritten history")
        with self.assertRaisesRegex(ValueError, "changed.*evidence"):
            MODULE.verify_goal(self.paper, "LA-G000")

    def test_root_requires_followup_and_followup_has_native_contract(self):
        self.receipt()
        extra_output = f"{self.base}/followup.md"
        own_receipt = f"{self.base}/receipts/LA-026.json"
        self.tasks.append(self.native("LA-026", "resolve discovered gap", [extra_output, own_receipt]))
        with self.assertRaises(FileNotFoundError):
            MODULE.verify_goal(self.paper, "LA-G000")
        self.receipt("LA-026", "gap addressed", "resolve discovered gap", "2026-09-11T11:00:00Z", extra_output)
        self.assertTrue(MODULE.verify_task(self.paper, "LA-026")["artifact_integrity_valid"])
        self.assertEqual(len(MODULE.verify_goal(self.paper, "LA-G000")), 2)

    def test_followup_criteria_cannot_be_omitted(self):
        self.receipt()
        extra_output = f"{self.base}/followup.md"
        self.tasks.append(self.native("LA-026", "resolve discovered gap", [extra_output]))
        self.receipt("LA-026", "gap addressed", "weaker criterion", "2026-09-11T11:00:00Z", extra_output)
        with self.assertRaisesRegex(ValueError, "exact task acceptance"):
            MODULE.verify_task(self.paper, "LA-026")

    def test_seed_criteria_remain_immutable_despite_board_edit(self):
        self.tasks[0].acceptance = "weaker criterion"
        self.receipt(criterion="weaker criterion")
        with self.assertRaisesRegex(ValueError, "exact task acceptance"):
            MODULE.verify_task(self.paper, "LA-001")

    def test_removed_seed_task_cannot_disappear_from_root(self):
        self.tasks = []
        with self.assertRaisesRegex(ValueError, "reviewed tasks disappeared"):
            MODULE.verify_goal(self.paper, "LA-G000")

    def test_ambiguous_latest_versions_rejected(self):
        self.receipt()
        self.seeds.append(self.seed("LA-022", "complete paper"))
        self.tasks.append(self.native("LA-022", "complete paper"))
        self.receipt("LA-022", "version two", "complete paper")
        with self.assertRaisesRegex(ValueError, "ambiguous simultaneous"):
            MODULE.verify_goal(self.paper, "LA-G000")

    def test_directory_outputs_require_all_current_files(self):
        directory = f"{self.base}/generated/"
        self.seeds[0]["deliverables"] = [directory]
        self.tasks[0].outputs = [directory]
        self.receipt(output=directory + "one.py")
        self.write(directory + "unaccounted.py", "not snapshotted")
        with self.assertRaisesRegex(ValueError, "unaccounted output files"):
            MODULE.verify_task(self.paper, "LA-001")


class PaperLauncherTests(unittest.TestCase):
    def test_dirty_or_untracked_inputs_start_no_children(self):
        for status in (" M papers/completion/law_to_action/tasks.json\n",
                       "?? papers/completion/law_to_action/paper.todo.md\n"):
            with self.subTest(status=status), \
                    patch.object(MODULE, "validate", return_value={}), \
                    patch.object(MODULE.subprocess, "check_output", return_value=status), \
                    patch.object(MODULE.subprocess, "Popen") as popen:
                with self.assertRaisesRegex(ValueError, "commit the reviewed"):
                    MODULE.run(list(MODULE.PAPERS))
                popen.assert_not_called()

    def test_native_lane_configs_are_isolated_with_one_shared_merge_queue(self):
        _, _, parse_args, make_config = MODULE.native_modules()
        with tempfile.TemporaryDirectory() as state, patch.dict(os.environ, {"VERICODEGEN_STATE_ROOT": state}):
            configs = [make_config(parse_args(MODULE.supervisor_argv(paper)), repo_root=MODULE.ROOT)
                       for paper in MODULE.PAPERS]
        for field in ("state_prefix", "task_prefix", "state_dir", "state_path", "worktree_root"):
            self.assertEqual(len({str(getattr(cfg, field)) for cfg in configs}), 3, field)
        self.assertEqual(len({str(cfg.merge_queue_dir) for cfg in configs}), 1)
        self.assertTrue(all(cfg.implement and cfg.use_ephemeral_worktree for cfg in configs))

    def test_duplicate_lane_rejects_all_children_and_releases_prior_locks(self):
        with tempfile.TemporaryDirectory() as state:
            root = Path(state)
            occupied = root / "law_to_action" / "launcher.lock"
            occupied.parent.mkdir()
            with occupied.open("a") as lock, \
                    patch.object(MODULE, "validate", return_value={}), \
                    patch.object(MODULE, "state_root", return_value=root), \
                    patch.object(MODULE.subprocess, "check_output", return_value=""), \
                    patch.object(MODULE.subprocess, "Popen") as popen:
                fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                with self.assertRaisesRegex(RuntimeError, "already owns law_to_action"):
                    MODULE.run(["autoformalization", "law_to_action"])
                popen.assert_not_called()
                with (root / "autoformalization" / "launcher.lock").open("a") as released:
                    fcntl.flock(released.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)

    def test_sigterm_stops_dummy_child_and_releases_lane_lock(self):
        # Run an isolated launcher interpreter so the unittest process never
        # changes signal disposition or risks signaling a provider process.
        launcher_path = Path(MODULE.__file__).resolve()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            subprocess.run(["git", "init", "-q", str(root)], check=True)
            wrapper = root / "dummy_launcher.py"
            wrapper.write_text(
                "import importlib.util, pathlib, sys\n"
                f"spec = importlib.util.spec_from_file_location('launcher', {str(launcher_path)!r})\n"
                "m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)\n"
                "m.native_modules()  # imports cleanup helper; starts no supervisor\n"
                f"m.ROOT = pathlib.Path({str(root)!r})\n"
                f"m.state_root = lambda: pathlib.Path({str(root / 'state')!r})\n"
                "m.validate = lambda paper: {}\n"
                "m.command = lambda paper: [sys.executable, '-c', 'import time; time.sleep(120)']\n"
                "try:\n"
                "    m.run(['law_to_action'])\n"
                "except KeyboardInterrupt:\n"
                "    print('dummy launcher cleaned up', flush=True)\n"
            )
            # The wrapper is outside the preflight's papers/scripts scope.
            proc = subprocess.Popen([sys.executable, str(wrapper)], cwd=root,
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            child_pid = None
            try:
                startup = []
                import time
                deadline = time.monotonic() + 20
                while time.monotonic() < deadline:
                    ready, _, _ = select.select([proc.stdout], [], [], max(0, deadline - time.monotonic()))
                    if not ready:
                        break
                    line = proc.stdout.readline()
                    if not line:
                        break
                    startup.append(line)
                    match = re.search(r"law_to_action: PID (\d+);", line)
                    if match:
                        child_pid = int(match.group(1))
                        break
                self.assertIsNotNone(child_pid, "dummy child did not start: " + "".join(startup))
                proc.send_signal(signal.SIGTERM)
                out, err = proc.communicate(timeout=20)
                self.assertEqual(proc.returncode, 0, err)
                self.assertIn("dummy launcher cleaned up", out)
                with self.assertRaises(ProcessLookupError):
                    os.kill(child_pid, 0)
                with (root / "state/law_to_action/launcher.lock").open("a") as lock:
                    fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            finally:
                if proc.poll() is None:
                    proc.kill()
                proc.communicate()
                if child_pid is not None:
                    try:
                        os.killpg(child_pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass


if __name__ == "__main__":
    unittest.main()

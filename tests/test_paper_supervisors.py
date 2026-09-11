"""Evidence-integrity tests use temporary files; no providers or experiments run."""
from __future__ import annotations

import importlib.util
import os
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
    def test_native_database_lane_configs_are_isolated(self):
        _, _, parse_args, make_config = MODULE.native_modules()
        with tempfile.TemporaryDirectory() as state, patch.dict(os.environ, {"VERICODEGEN_STATE_ROOT": state}):
            configs = [make_config(parse_args(MODULE.supervisor_argv(paper)), repo_root=MODULE.ROOT)
                       for paper in MODULE.PAPERS]
        for field in ("state_prefix", "task_prefix", "state_dir", "state_path", "worktree_root"):
            self.assertEqual(len({str(getattr(cfg, field)) for cfg in configs}), 3, field)
        self.assertEqual(len({str(cfg.merge_queue_dir) for cfg in configs}), 3)
        self.assertTrue(all(cfg.implement and cfg.use_ephemeral_worktree for cfg in configs))

        self.assertTrue(all(cfg.database_program.authority_mode == "quack" for cfg in configs))
        self.assertTrue(all(cfg.database_program.task_source_kind == "duckdb" for cfg in configs))


if __name__ == "__main__":
    unittest.main()

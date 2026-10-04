"""Evidence-integrity tests use temporary files; no providers or experiments run."""
from __future__ import annotations

import importlib.util
from datetime import datetime, timezone
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
        self.write("check.py", "print('validation passed')\n")
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

    def test_future_completion_rejected_with_small_explicit_clock_tolerance(self):
        now = datetime(2026, 9, 11, 12, 0, tzinfo=timezone.utc)
        with patch.object(MODULE, "_utc_now", return_value=now):
            for timestamp in ("2026-09-11T11:59:59Z", "2026-09-11T12:01:00Z"):
                self.receipt(completed_at=timestamp)
                self.assertTrue(MODULE.verify_task(self.paper, "LA-001")["artifact_integrity_valid"])
            self.receipt(completed_at="2026-09-11T12:01:01Z")
            with self.assertRaisesRegex(ValueError, "future.*60-second"):
                MODULE.verify_task(self.paper, "LA-001")

    def test_literal_python_requires_executable_syntax_and_is_never_executed(self):
        receipt = self.receipt()
        for argv in (["/usr/bin/python3.12", "-c", "LA-002 structural assertions over matrix, scope, and inventory"],
                     ["env", "-i", "PATH=/usr/bin", "python3", "-c", "return 1"], ["python3", "-c"]):
            receipt["commands"][0]["argv"] = argv
            self.save_receipt("LA-001", receipt)
            with self.assertRaisesRegex(ValueError, "invalid Python source|has no source"):
                MODULE.verify_task(self.paper, "LA-001")
        marker = self.root / "not-executed.txt"
        receipt["commands"][0]["argv"] = ["python3", "-I", "-c", f"open({str(marker)!r}, 'w').write('executed')"]
        self.save_receipt("LA-001", receipt)
        self.assertTrue(MODULE.verify_task(self.paper, "LA-001")["artifact_integrity_valid"])
        self.assertFalse(marker.exists())

    def test_python_stdin_requires_hash_bound_source_even_through_env(self):
        receipt = self.receipt()
        command = receipt["commands"][0]
        command["argv"] = ["env", "-i", "HOME=/tmp/recorded-home", "python3", "-"]
        self.save_receipt("LA-001", receipt)
        with self.assertRaisesRegex(ValueError, "requires a hashed stdin_artifact"):
            MODULE.verify_task(self.paper, "LA-001")
        command["stdin_artifact"] = f"{self.base}/receipts/snapshots/LA-001/validation.py"
        source = self.write(command["stdin_artifact"], "print('actual program retained')\n")
        self.save_receipt("LA-001", receipt)
        with self.assertRaisesRegex(ValueError, "stdin_artifact must name a hashed"):
            MODULE.verify_task(self.paper, "LA-001")
        receipt["artifacts"][command["stdin_artifact"]] = MODULE.digest(source)
        self.save_receipt("LA-001", receipt)
        self.assertTrue(MODULE.verify_task(self.paper, "LA-001")["artifact_integrity_valid"])
        self.write(command["stdin_artifact"], "this is not executable Python")
        receipt["artifacts"][command["stdin_artifact"]] = MODULE.digest(source)
        self.save_receipt("LA-001", receipt)
        with self.assertRaisesRegex(ValueError, "invalid Python source"):
            MODULE.verify_task(self.paper, "LA-001")

    def test_clear_environment_placeholders_rejected_but_literal_values_accepted(self):
        receipt = self.receipt()
        for value in ("<fresh-validation-home>", "[TBD]", "PLACEHOLDER"):
            receipt["commands"][0]["argv"] = ["env", "-i", "HOME=" + value, "python3", "-c", "print(1)"]
            self.save_receipt("LA-001", receipt)
            with self.assertRaisesRegex(ValueError, "placeholder environment"):
                MODULE.verify_task(self.paper, "LA-001")
        receipt["commands"][0]["argv"] = ["env", "-i", "FORMAT=<html>", "MODE=tbd-later", "python3", "-c", "print(1)"]
        self.save_receipt("LA-001", receipt)
        self.assertTrue(MODULE.verify_task(self.paper, "LA-001")["artifact_integrity_valid"])

    def test_named_script_uses_safe_repository_source_or_explicit_hashed_snapshot(self):
        receipt = self.receipt()
        command = receipt["commands"][0]
        command["argv"] = ["python3", "missing.py"]
        self.save_receipt("LA-001", receipt)
        with self.assertRaisesRegex(ValueError, "requires retained repository source"):
            MODULE.verify_task(self.paper, "LA-001")
        command["script_artifact"] = f"{self.base}/receipts/snapshots/LA-001/retained-script.py"
        source = self.write(command["script_artifact"], "print('retained named source')\n")
        self.save_receipt("LA-001", receipt)
        with self.assertRaisesRegex(ValueError, "script_artifact must name a hashed"):
            MODULE.verify_task(self.paper, "LA-001")
        receipt["artifacts"][command["script_artifact"]] = MODULE.digest(source)
        self.save_receipt("LA-001", receipt)
        self.assertTrue(MODULE.verify_task(self.paper, "LA-001")["artifact_integrity_valid"])
        del command["script_artifact"]
        command["argv"] = ["python3", "../unretained.py"]
        self.save_receipt("LA-001", receipt)
        with self.assertRaisesRegex(ValueError, "repository-relative path"):
            MODULE.verify_task(self.paper, "LA-001")

    def test_named_module_and_interpreter_version_commands_retain_literal_argv(self):
        receipt = self.receipt()
        for argv in (["python3", "-m", "json.tool", self.output], ["python3", "--version"]):
            receipt["commands"][0]["argv"] = argv
            self.save_receipt("LA-001", receipt)
            self.assertTrue(MODULE.verify_task(self.paper, "LA-001")["artifact_integrity_valid"])
        receipt["commands"][0]["argv"] = ["python3", "-m"]
        self.save_receipt("LA-001", receipt)
        with self.assertRaisesRegex(ValueError, "has no module"):
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
        own_snapshots = f"{self.base}/receipts/snapshots/LA-026/"
        self.tasks.append(self.native("LA-026", "resolve discovered gap", [extra_output, own_receipt, own_snapshots]))
        self.assertEqual(MODULE.paper_task_contracts(self.paper)[2]["LA-026"]["deliverables"], [extra_output])
        with self.assertRaises(FileNotFoundError):
            MODULE.verify_goal(self.paper, "LA-G000")
        self.receipt("LA-026", "gap addressed", "resolve discovered gap", "2026-09-11T11:00:00Z", extra_output)
        self.assertTrue(MODULE.verify_task(self.paper, "LA-026")["artifact_integrity_valid"])
        self.assertEqual(len(MODULE.verify_goal(self.paper, "LA-G000")), 2)

    def test_followup_evidence_does_not_replace_scientific_deliverables(self):
        own_receipt, own_snapshots = MODULE.task_evidence_paths(self.paper, "LA-026")
        self.tasks.append(self.native("LA-026", "resolve discovered gap", [own_receipt, own_snapshots]))
        with self.assertRaisesRegex(ValueError, "incomplete task contract: LA-026"):
            MODULE.paper_task_contracts(self.paper)

    def test_followup_excludes_only_its_own_evidence_paths(self):
        foreign_snapshots = f"{self.base}/receipts/snapshots/LA-027/"
        own_receipt, own_snapshots = MODULE.task_evidence_paths(self.paper, "LA-026")
        self.tasks.append(self.native("LA-026", "resolve discovered gap", [self.output, own_receipt, own_snapshots, foreign_snapshots]))
        self.assertEqual(MODULE.paper_task_contracts(self.paper)[2]["LA-026"]["deliverables"],
                         [self.output, foreign_snapshots])

    def test_evidence_path_cannot_redirect_into_another_tasks_directory(self):
        snapshots = self.root / self.base / "receipts/snapshots"
        (snapshots / "LA-027").mkdir(parents=True)
        (snapshots / "LA-026").symlink_to(snapshots / "LA-027", target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "redirect through symlinks"):
            MODULE.task_evidence_paths(self.paper, "LA-026")

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


class PaperBoardBuildTests(unittest.TestCase):
    def test_three_fresh_boards_admit_only_each_tasks_evidence_without_changing_seed_science(self):
        parse_goals, parse_tasks, _, _ = MODULE.native_modules()
        manifests = {paper: MODULE.manifest(paper) for paper in MODULE.RESEARCH_PAPERS}
        original = json.dumps(manifests, sort_keys=True)
        with tempfile.TemporaryDirectory() as temporary, patch.object(MODULE, "ROOT", Path(temporary)), \
                patch.object(MODULE, "manifest", side_effect=manifests.__getitem__):
            for paper in MODULE.RESEARCH_PAPERS:
                with self.subTest(paper=paper):
                    folder = MODULE.ROOT / MODULE.BASE / paper
                    folder.mkdir(parents=True)
                    MODULE.build(paper)
                    native = parse_tasks(folder / "paper.todo.md", MODULE.PREFIXES[paper] + "-")
                    self.assertEqual(len(native), 25)
                    for task, seed in zip(native, manifests[paper]["tasks"]):
                        receipt, snapshots = MODULE.task_evidence_paths(paper, seed["id"])
                        self.assertEqual(task.outputs, list(dict.fromkeys([*seed["deliverables"], receipt, snapshots])))
                        self.assertEqual(task.acceptance, "; ".join(seed["acceptance_criteria"]))
                    goals = parse_goals((folder / "paper.objectives.md").read_text())
                    self.assertTrue(all("receipts/snapshots" not in goal.fields["outputs"] for goal in goals))
        self.assertEqual(json.dumps(manifests, sort_keys=True), original)

    def test_evidence_identity_is_bound_to_exact_paper_and_numeric_task(self):
        for paper, task_id in (("law_to_action", "AF-002"), ("law_to_action", "LA-002/../LA-003"),
                               ("law_to_action", "LA-*"), ("law_to_action", "LA-\u0660\u0660\u0662"),
                               ("other", "LA-002"), ("law_to_action", None)):
            with self.subTest(paper=paper, task=task_id), self.assertRaisesRegex(ValueError, "evidence identity"):
                MODULE.task_evidence_paths(paper, task_id)


class PaperLauncherTests(unittest.TestCase):
    def test_native_database_lane_configs_are_isolated(self):
        _, _, parse_args, make_config = MODULE.native_modules()
        with tempfile.TemporaryDirectory() as state, patch.dict(os.environ, {"VERICODEGEN_STATE_ROOT": state}):
            configs = [make_config(parse_args(MODULE.supervisor_argv(paper)), repo_root=MODULE.ROOT)
                       for paper in MODULE.RESEARCH_PAPERS]
        for field in ("state_prefix", "task_prefix", "state_dir", "state_path", "worktree_root"):
            self.assertEqual(len({str(getattr(cfg, field)) for cfg in configs}), len(MODULE.RESEARCH_PAPERS), field)
        self.assertEqual(len({str(cfg.merge_queue_dir) for cfg in configs}), len(MODULE.RESEARCH_PAPERS))
        self.assertTrue(all(cfg.implement and cfg.use_ephemeral_worktree for cfg in configs))

        self.assertTrue(all(cfg.database_program.authority_mode == "quack" for cfg in configs))
        self.assertTrue(all(cfg.database_program.task_source_kind == "duckdb" for cfg in configs))


if __name__ == "__main__":
    unittest.main()

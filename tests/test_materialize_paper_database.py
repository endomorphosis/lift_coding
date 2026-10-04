"""Native paper-board import tests; only fresh temporary embedded stores."""
from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import subprocess
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location("paper_materializer", Path(__file__).resolve().parents[1] / "scripts/materialize_paper_database.py")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class PaperDatabaseMaterializationTests(unittest.TestCase):
    def test_actual_three_boards_preserve_native_goals_metadata_and_dependency_cids(self):
        for paper in MODULE.PAPERS:
            with self.subTest(paper=paper):
                population, provenance = MODULE.build_population(paper)
                self.assertEqual(len(population["taskboard"]), 25)
                known, seen = set(provenance["task_cids"].values()), set()
                for task in population["taskboard"]:
                    self.assertLessEqual(set(task["depends_on"]), known)
                    self.assertLessEqual(set(task["depends_on"]), seen)
                    self.assertEqual(task["goal_cid"], provenance["goal_cids"][task["goal id"]])
                    self.assertIn("predicted files", task)
                    self.assertTrue(task["native_source_block"].startswith("## " + task["task_id"]))
                    self.assertTrue(all(isinstance(item, dict) and item["path"] for item in task["outputs"]))
                    snapshots = f"papers/completion/{paper}/receipts/snapshots/{task['task_id']}/"
                    self.assertEqual([item for item in task["outputs"] if "receipts/snapshots/" in item["path"]],
                                     [{"path": snapshots, "kind": "directory"}])
                    self.assertTrue(all(item["argv"] == ["python3", "scripts/paper_supervisors.py", "verify-task",
                                                        "--paper", paper, "--task", task["task_id"]]
                                        for item in task["validation_commands"]))
                    seen.add(task["task_cid"])
                for goal in population["objectives"]:
                    parents = [v.strip() for v in goal["native_fields"].get("parent", "").split(",") if v.strip()]
                    expected = provenance["goal_cids"][parents[0]] if parents else ""
                    self.assertEqual(goal["parent_goal_cid"], expected)

    def test_fresh_database_is_queryable_with_exact_outputs_parent_edges_and_ready_set(self):
        _, parse_tasks, _, DatabaseTaskSource, _ = MODULE._native(MODULE.ROOT)
        from ipfs_accelerate_py.agent_supervisor.todo_daemon.database_portal_bridge import DatabasePortalExecutionBridge
        from ipfs_accelerate_py.agent_supervisor.todo_daemon.implementation_daemon import TodoImplementationDaemon
        from ipfs_accelerate_py.agent_supervisor.context.context_compiler import render_context_capsule
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "control.duckdb"
            report = MODULE.materialize("law_to_action", db)
            self.assertTrue(db.is_file())
            self.assertEqual(report["ready_tasks"], ["LA-001", "LA-002"])
            self.assertEqual(report["population"]["task_count"], 25)
            self.assertEqual(report["population"]["goal_count"], 9)
            self.assertEqual(report["task_snapshot"]["objective_count"], 1)
            self.assertEqual(MODULE._digest(db), report["bootstrap_database_sha256"])
            self.assertFalse(report["server_started"])
            receipt = json.loads(db.with_name(db.name + ".bootstrap.json").read_text())
            self.assertEqual(receipt, report)
            with DatabaseTaskSource(db, install_schema=False) as source:
                record = source.get_task("LA-003")
                self.assertEqual(record.dependencies, (report["source_provenance"]["task_cids"]["LA-002"],))
                objective = source.get_objective(report["source_provenance"]["objective_id"])
                self.assertIn("From Law to Action", objective["title"])
                attempt = SimpleNamespace(task_cid=record.task_cid, task_alias=record.task_alias,
                                          attempt_id="test-attempt", claim_id="test-claim")
                projection = DatabasePortalExecutionBridge._render_projection(None, attempt, record)
                self.assertIn("- Goal Id: LA-G2", projection)
                self.assertIn("- Predicted Files:", projection)
                self.assertIn("python3 scripts/paper_supervisors.py verify-task", projection)
                self.assertNotIn("bash -lc", projection)
                snapshots = "papers/completion/law_to_action/receipts/snapshots/LA-003/"
                self.assertEqual([dict(output["effect"]) for output in record.outputs if output["path"] == snapshots],
                                 [{"path": snapshots, "kind": "directory"}])
                repo = Path(tmp) / "worker"
                repo.mkdir()
                todo = repo / "projected.todo.md"
                todo.write_text(projection)
                for arguments in (("init",), ("add", "projected.todo.md"),
                                  ("-c", "user.name=Paper Test", "-c", "user.email=paper@example.invalid", "commit", "-m", "baseline")):
                    subprocess.run(["git", *arguments], cwd=repo, check=True, capture_output=True)
                projected = parse_tasks(todo, "LA-")[0]
                daemon = TodoImplementationDaemon(todo_path=todo, state_path=repo / "state/task.json",
                    strategy_path=repo / "state/strategy.json", events_path=repo / "state/events.jsonl",
                    repo_root=repo, task_header_prefix="## LA-")
                with patch.dict(os.environ, {"IPFS_ACCELERATE_AGENT_IMPLEMENTATION_PROVIDER": "grok"}):
                    compiled = daemon._compile_implementation_context(projected, attempt=1)
                capsule = json.loads(render_context_capsule(compiled.capsule))
                allowed = capsule["authority"]["edit_policy"]["allowed_paths"]
                self.assertEqual(set(allowed), {output["path"] for output in record.outputs})
                self.assertIn(snapshots, allowed)
                self.assertIn(snapshots, capsule["scope"]["expected_outputs"])
                self.assertNotIn(snapshots.replace("LA-003/", "LA-002/"), allowed)
                self.assertNotIn(snapshots.removesuffix("LA-003/"), allowed)
            self.assertFalse(list(Path(tmp).glob(".paper-bootstrap-*")))

    def test_existing_database_is_never_opened_or_replaced(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "control.duckdb"
            db.write_bytes(b"existing owner data")
            with patch.object(MODULE, "build_population") as build:
                with self.assertRaisesRegex(ValueError, "refusing to overwrite"):
                    MODULE.materialize("law_to_action", db)
                build.assert_not_called()
            self.assertEqual(db.read_bytes(), b"existing owner data")

    def test_snapshot_output_admission_rejects_foreign_broad_and_nonliteral_paths(self):
        base = "papers/completion/law_to_action/receipts"
        invalid = [".", "papers/", "papers/completion/law_to_action/", base + "/", base + "/snapshots/",
                   base + "/snapshots/LA-004/", base + "/LA-004.json", base + "/snapshots/LA-003/extra.json",
                   "papers/completion/autoformalization/receipts/snapshots/AF-003/",
                   "reports/*.json", "./report.json", "reports//result.json", "reports/../result.json",
                   "reports/result.json,other.json", "reports/bad\nname.json", "reports///", None, {}]
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for output in invalid:
                with self.subTest(output=output), self.assertRaises(ValueError):
                    MODULE._task_outputs("law_to_action", "LA-003", [output], root)
            own = [base + "/LA-003.json", base + "/snapshots/LA-003/"]
            self.assertEqual(MODULE._task_outputs("law_to_action", "LA-003", [*own, *own], root), own)
            for task_id in ("AF-003", "LA-003/../LA-004", "LA-*", "LA-\u0660\u0660\u0663", None):
                with self.subTest(task=task_id), self.assertRaisesRegex(ValueError, "evidence identity"):
                    MODULE._task_outputs("law_to_action", task_id, [], root)
            other = root / "another-task"
            other.mkdir()
            snapshots = root / base / "snapshots/LA-003"
            snapshots.parent.mkdir(parents=True)
            snapshots.symlink_to(other, target_is_directory=True)
            with self.assertRaisesRegex(ValueError, "redirect through symlinks"):
                MODULE._task_outputs("law_to_action", "LA-003", [], root)
            snapshots.unlink()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with tempfile.TemporaryDirectory() as outside:
                (root / "papers").symlink_to(outside, target_is_directory=True)
                with self.assertRaisesRegex(ValueError, "escapes repository"):
                    MODULE._task_outputs("law_to_action", "LA-003", [], root)

    def test_unknown_dependency_is_rejected_before_database_creation(self):
        native = MODULE._native(MODULE.ROOT)
        actual_parse = native[1]
        def invalid_parse(*args):
            tasks = actual_parse(*args)
            tasks[0].depends_on.append("LA-MISSING")
            return tasks
        with tempfile.TemporaryDirectory() as tmp, patch.object(MODULE, "_native", return_value=(native[0], invalid_parse, *native[2:])):
            db = Path(tmp) / "control.duckdb"
            with self.assertRaisesRegex(ValueError, "unknown dependency"):
                MODULE.materialize("law_to_action", db)
            self.assertFalse(db.exists())

    def test_validation_import_rejects_shell_wrappers_compounds_and_other_task_authority(self):
        command = "python3 scripts/paper_supervisors.py verify-task --paper law_to_action --task LA-001"
        self.assertEqual(MODULE._validation_argv(command, "law_to_action", "LA-001"), command.split())
        for invalid in ("bash -lc '" + command + "'", command + " && true", command.replace("LA-001", "LA-002")):
            with self.subTest(command=invalid), self.assertRaisesRegex(ValueError, "direct reviewed paper verifier"):
                MODULE._validation_argv(invalid, "law_to_action", "LA-001")


if __name__ == "__main__":
    unittest.main()

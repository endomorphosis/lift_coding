"""Native paper-board import tests; only fresh temporary embedded stores."""
from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
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
                    self.assertTrue(all(item["argv"][:2] == ["bash", "-lc"] for item in task["validation_commands"]))
                    seen.add(task["task_cid"])
                for goal in population["objectives"]:
                    parents = [v.strip() for v in goal["native_fields"].get("parent", "").split(",") if v.strip()]
                    expected = provenance["goal_cids"][parents[0]] if parents else ""
                    self.assertEqual(goal["parent_goal_cid"], expected)

    def test_fresh_database_is_queryable_with_exact_outputs_parent_edges_and_ready_set(self):
        _, _, _, DatabaseTaskSource, _ = MODULE._native(MODULE.ROOT)
        from ipfs_accelerate_py.agent_supervisor.todo_daemon.database_portal_bridge import DatabasePortalExecutionBridge
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
                self.assertIn("bash -lc 'python3 scripts/paper_supervisors.py verify-task", projection)
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


if __name__ == "__main__":
    unittest.main()

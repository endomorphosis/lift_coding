"""Real temporary DuckLake projection plus provenance/immutability boundaries."""
from __future__ import annotations

import copy
import importlib.util
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest

SPEC = importlib.util.spec_from_file_location(
    "paper_ducklake_projection", Path(__file__).resolve().parents[1] / "scripts/paper_ducklake_projection.py"
)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def snapshot():
    return {"schema": MODULE.SNAPSHOT_SCHEMA, "transport": "quack",
            "fetched_at": MODULE.utc_now(), "boards": [
                {"paper_id": paper, "board_namespace": f"vericodegen-2026-{paper}",
                 "store_identity": {"database_uuid": f"fixture-store-{paper}"},
                 "store_generation": {"generation": 1, "revision": 1},
                 "tasks": [{"task_id": f"{i}-task", "status": "todo", "title": "Fixture task"}],
                 "goals": [{"goal_id": f"{i}-goal", "status": "active"}],
                 "events": [{"event_id": f"{i}-event", "sequence": 1, "status": "todo"}]}
                for i, paper in enumerate(MODULE.PAPERS)]}


class SnapshotAdmissionTests(unittest.TestCase):
    def test_rejects_file_transport_missing_identity_and_duplicate_tasks(self):
        for mutation in [
            lambda s: s.update(transport="duckdb"),
            lambda s: s["boards"][0].update(store_identity={}),
            lambda s: s["boards"].pop(),
            lambda s: s["boards"][0]["tasks"].append(s["boards"][0]["tasks"][0]),
            lambda s: s.update(fetched_at="2026-09-11T12:00:00"),
        ]:
            value = snapshot()
            mutation(value)
            with self.assertRaises(MODULE.ProjectionError):
                MODULE.validate_snapshot(value)

    def test_plain_duckdb_fallback_is_rejected(self):
        with self.assertRaisesRegex(MODULE.ProjectionError, "fallback is forbidden"):
            MODULE.require_ducklake(SimpleNamespace(ducklake_loaded=False,
                                                    ducklake_attached=False, quack_loaded=True))

    def test_event_identity_does_not_change_with_mutable_store_revision(self):
        original = snapshot()
        changed = copy.deepcopy(original)
        changed["boards"][0]["store_generation"]["revision"] = 9
        first = [x for x in MODULE.projected_artifacts(original) if x[2]["record_kind"] == "event"]
        second = [x for x in MODULE.projected_artifacts(changed) if x[2]["record_kind"] == "event"]
        self.assertEqual(first, second)


class ActualDuckLakeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            import duckdb
        except ImportError as exc:
            raise unittest.SkipTest("DuckDB unavailable") from exc
        connection = duckdb.connect(":memory:")
        try:
            for extension in ("ducklake", "quack"):
                connection.execute(f"LOAD {extension}")
        except Exception as exc:
            raise unittest.SkipTest("installed DuckLake/Quack extensions unavailable") from exc
        finally:
            connection.close()

    def test_real_lake_rows_history_idempotency_and_conflicting_event(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "lake"
            source = snapshot()
            first = MODULE.project_snapshot(source, root)
            self.assertTrue(first["ok"])
            self.assertEqual(first["ducklake"]["catalog_type"], "ducklake")
            self.assertGreater(first["lake_snapshot_count"], 0)
            self.assertFalse(first["authoritative"])
            self.assertFalse(first["paper_benchmark_evidence"])
            for result in first["boards"].values():
                self.assertEqual(result["current_task_rows"], 1)
                self.assertEqual(result["artifact_rows_by_kind"]["event"], 1)
                self.assertEqual(result["artifact_rows_by_kind"]["goal"], 1)
            replay = MODULE.project_snapshot(source, root)
            self.assertEqual(replay["new_immutable_artifacts"], 0)
            changed = copy.deepcopy(source)
            changed["boards"][0]["tasks"][0]["status"] = "completed"
            changed["fetched_at"] = MODULE.utc_now()
            third = MODULE.project_snapshot(changed, root)
            paper = MODULE.PAPERS[0]
            self.assertEqual(third["boards"][paper]["current_task_rows"], 1)
            self.assertEqual(third["boards"][paper]["artifact_rows_by_kind"]["task"], 2)
            corrupted = copy.deepcopy(changed)
            corrupted["boards"][0]["events"][0]["status"] = "completed"
            with self.assertRaisesRegex(MODULE.ProjectionError, "conflicting content"):
                MODULE.project_snapshot(corrupted, root)
            final = MODULE.project_snapshot(changed, root)
            self.assertEqual(final["boards"][paper]["artifact_rows_by_kind"]["event"], 1)


if __name__ == "__main__":
    unittest.main()

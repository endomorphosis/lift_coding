"""Real Quack/CAS snapshot-scope repair without touching active task authority."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def load(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


REPAIR = load("paper_snapshot_repair_under_test", "scripts/repair_paper_snapshot_outputs.py")
FIX = load("paper_snapshot_quack_fixtures", "tests/test_migrate_paper_validation_argv.py")


def legacy_outputs(source):
    # Future fresh imports include snapshots; recreate exactly the old output
    # relation on these temporary stores only, retaining original metadata.
    for record in FIX.snapshot(source):
        effects = [item["effect"] for item in record["outputs"]
                   if "/receipts/snapshots/" not in item["path"]]
        if len(effects) != len(record["outputs"]):
            FIX.upsert_record(source, record, outputs=effects)


class SnapshotOutputRepairTests(unittest.TestCase):
    def test_all_four_boards_preserve_active_blocked_completed_and_other_relations(self):
        for paper in REPAIR.COMMON.MAT.PAPERS:
            def prepare(source):
                legacy_outputs(source)
                rows = FIX.snapshot(source)
                FIX.upsert_record(source, rows[0], status="completed")
                FIX.upsert_record(source, rows[1], status="in_progress")
            with self.subTest(paper=paper), FIX.old_quack_board(paper, prepare=prepare) as (endpoint, token), FIX.native_source(endpoint) as source:
                before = FIX.snapshot(source)
                dry = REPAIR.repair(paper, endpoint)
                self.assertTrue(dry["dry_run"])
                self.assertEqual(dry["changed"], 0)
                self.assertEqual(before, FIX.snapshot(source))
                result = REPAIR.repair(paper, endpoint, dry_run=False)
                self.assertTrue(result["success"])
                self.assertEqual(result["changed"], sum(row["status"] == "ready" for row in before))
                self.assertNotIn(token, json.dumps(result))
                after = FIX.snapshot(source)
                for old, new in zip(before, after):
                    self.assertEqual(REPAIR.preserved(old), REPAIR.preserved(new))
                    if old["status"] != "ready":
                        self.assertEqual(old, new)
                    else:
                        self.assertEqual(new["revision"], old["revision"] + 1)
                        self.assertEqual(new["outputs"][:-1], old["outputs"])
                        snapshot = f"papers/completion/{paper}/receipts/snapshots/{old['task_alias']}/"
                        self.assertEqual(new["outputs"][-1]["effect"], {"path": snapshot, "kind": "directory"})
                again = REPAIR.repair(paper, endpoint, dry_run=False)
                self.assertEqual(again["changed"], 0)
                self.assertEqual(FIX.snapshot(source), after)

    def test_unknown_contract_or_foreign_store_rejected_before_first_mutation(self):
        paper = "law_to_action"
        for case in ("foreign_prediction", "foreign_output", "changed_criterion", "changed_board"):
            def prepare(source):
                legacy_outputs(source)
                current = REPAIR.plain(source.intent.get_task("LA-025"))
                body = dict(current["body"])
                outputs = [item["effect"] for item in current["outputs"]]
                acceptance = [item["criterion"] for item in current["acceptance"]]
                if case == "foreign_prediction":
                    body["predicted files"] += ", papers/completion/autoformalization/receipts/snapshots/AF-001/"
                elif case == "foreign_output":
                    outputs.append({"path": "papers/completion/autoformalization/unrelated.json", "kind": "file"})
                elif case == "changed_criterion":
                    acceptance = ["invented completion"]
                else:
                    body["board_namespace"] = "foreign-campaign"
                FIX.upsert_record(source, current, body=body, outputs=outputs, acceptance=acceptance)
            with self.subTest(case=case), FIX.old_quack_board(paper, prepare=prepare) as (endpoint, _), FIX.native_source(endpoint) as source:
                before = FIX.snapshot(source)
                with self.assertRaises(REPAIR.SnapshotRepairError):
                    REPAIR.repair(paper, endpoint, dry_run=False)
                self.assertEqual(before, FIX.snapshot(source))
        with FIX.old_quack_board(paper, prepare=legacy_outputs) as (endpoint, _), FIX.native_source(endpoint) as source:
            before = FIX.snapshot(source)
            with self.assertRaises(REPAIR.SnapshotRepairError):
                REPAIR.repair("autoformalization", endpoint, dry_run=False)
            self.assertEqual(before, FIX.snapshot(source))

    def test_native_stale_revision_cannot_repeat_snapshot_grant(self):
        paper = "neurosymbolic_supervision"
        with FIX.old_quack_board(paper, prepare=legacy_outputs) as (endpoint, _), FIX.native_source(endpoint) as source:
            before = FIX.snapshot(source)
            record = before[0]
            # A genuine owner-side correction advances the native CAS.
            # Replaying its old revision must neither duplicate the output
            # declaration nor append another native event.
            from ipfs_accelerate_py.agent_supervisor.task_sources.duckdb_state import open_quack_transport_connection
            connection = open_quack_transport_connection(endpoint)
            try:
                row = connection.execute("SELECT server_id, store_id, database_uuid, generation, process_birth_id, listen_uri FROM state_servers WHERE stopped_at IS NULL").fetchone()
                owner = dict(zip(("server_id", "store_id", "database_uuid", "generation", "process_birth_id", "listen_uri"), [row[i] for i in range(6)]))
            finally:
                connection.close()
            result = FIX.MIG.maintenance_submit("snapshot_directory", record, owner)
            self.assertTrue(result["changed"])
            observed = REPAIR.plain(source.intent.get_task(record["task_cid"]))
            with self.assertRaises(ValueError):
                FIX.MIG.maintenance_submit("snapshot_directory", record, owner)
            self.assertEqual(REPAIR.plain(source.intent.get_task(record["task_cid"])), observed)
            self.assertEqual(observed["outputs"][:-1], record["outputs"])
            self.assertEqual(len(observed["outputs"]), len(record["outputs"]) + 1)
            self.assertEqual(observed["revision"], record["revision"] + 1)


if __name__ == "__main__":
    unittest.main()

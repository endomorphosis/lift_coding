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
    def test_three_boards_preserve_active_and_completed_tasks_and_all_other_relations(self):
        for paper in REPAIR.COMMON.MAT.PAPERS:
            with self.subTest(paper=paper), FIX.old_quack_board(paper) as (endpoint, token), FIX.native_source(endpoint) as source:
                legacy_outputs(source)
                rows = FIX.snapshot(source)
                FIX.upsert_record(source, rows[0], status="completed")
                FIX.upsert_record(source, rows[1], status="in_progress")
                before = FIX.snapshot(source)
                dry = REPAIR.repair(paper, endpoint)
                self.assertTrue(dry["dry_run"])
                self.assertEqual(dry["changed"], 0)
                self.assertEqual(before, FIX.snapshot(source))
                result = REPAIR.repair(paper, endpoint, dry_run=False)
                self.assertTrue(result["success"])
                self.assertEqual(result["changed"], 23)
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
        with FIX.old_quack_board(paper) as (endpoint, _), FIX.native_source(endpoint) as source:
            legacy_outputs(source)
            pristine = REPAIR.plain(source.intent.get_task("LA-025"))
            for case in ("foreign_prediction", "foreign_output", "changed_criterion", "changed_board"):
                current = REPAIR.plain(source.intent.get_task("LA-025"))
                body = dict(pristine["body"])
                outputs = [item["effect"] for item in pristine["outputs"]]
                acceptance = [item["criterion"] for item in pristine["acceptance"]]
                if case == "foreign_prediction":
                    body["predicted files"] += ", papers/completion/autoformalization/receipts/snapshots/AF-001/"
                elif case == "foreign_output":
                    outputs.append({"path": "papers/completion/autoformalization/unrelated.json", "kind": "file"})
                elif case == "changed_criterion":
                    acceptance = ["invented completion"]
                else:
                    body["board_namespace"] = "foreign-campaign"
                FIX.upsert_record(source, current, body=body, outputs=outputs, acceptance=acceptance)
                before = FIX.snapshot(source)
                with self.subTest(case=case), self.assertRaises(REPAIR.SnapshotRepairError):
                    REPAIR.repair(paper, endpoint, dry_run=False)
                self.assertEqual(before, FIX.snapshot(source))
            with self.assertRaises(REPAIR.SnapshotRepairError):
                REPAIR.repair("autoformalization", endpoint, dry_run=False)
            self.assertEqual(before, FIX.snapshot(source))

    def test_native_stale_revision_preserves_concurrent_claim_without_granting_scope(self):
        paper = "neurosymbolic_supervision"
        with FIX.old_quack_board(paper) as (endpoint, _), FIX.native_source(endpoint) as source:
            legacy_outputs(source)
            before = FIX.snapshot(source)
            repository_type = type(source.intent)
            original = repository_type.upsert_task
            raced = []

            def claim_then_repair(repository, **kwargs):
                if not raced:
                    raced.append(kwargs["task_cid"])
                    record = REPAIR.plain(source.intent.get_task(kwargs["task_cid"]))
                    payload = {key: record[key] for key in ("task_cid", "task_alias", "goal_cid", "ordinal",
                               "status", "priority", "plan_cid", "objective_id", "body", "identity")}
                    payload["status"] = "in_progress"
                    original(source.intent, **payload, expected_revision=record["revision"])
                return original(repository, **kwargs)

            with patch.object(repository_type, "upsert_task", claim_then_repair), self.assertRaises(REPAIR.SnapshotRepairError) as error:
                REPAIR.repair(paper, endpoint, dry_run=False)
            self.assertEqual(error.exception.receipt["changed"], 0)
            self.assertEqual(len(raced), 1)
            after = FIX.snapshot(source)
            for old, new in zip(before, after):
                self.assertEqual(old["outputs"], new["outputs"])
                if old["task_cid"] == raced[0]:
                    self.assertEqual(new["status"], "in_progress")
                    self.assertEqual(new["revision"], old["revision"] + 1)
                else:
                    self.assertEqual(old, new)


if __name__ == "__main__":
    unittest.main()

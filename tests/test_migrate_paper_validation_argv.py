"""Actual temporary Quack migration, contract preservation, and admission tests."""
from __future__ import annotations

from contextlib import contextmanager
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("paper_validation_migration_tests", ROOT / "scripts/migrate_paper_validation_argv.py")
MIG = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MIG)


@contextmanager
def old_quack_board(paper, *, restart_owner=False):
    isolated = {k: v for k, v in os.environ.items() if not k.startswith(("IPFS_ACCELERATE_AGENT_QUACK_", "IPFS_ACCELERATE_AGENT_STATE_"))}
    isolated["IPFS_ACCELERATE_AGENT_QUACK_PREFER"] = "false"
    with patch.dict(os.environ, isolated, clear=True), tempfile.TemporaryDirectory(prefix="paper-argv-migration-test-") as tmp:
        folder = Path(tmp)
        database, owner = folder / "control.duckdb", folder / "owner"
        # Reproduce the former import representation, on a fresh test DB only.
        with patch.object(MIG.MAT, "_validation_argv", side_effect=lambda command, *_: ["bash", "-lc", command]):
            MIG.MAT.materialize(paper, database, ROOT)
        argv = [sys.executable, str(ROOT / "scripts/paper_state_owner.py"), "--database", str(database),
             "--state-dir", str(owner), "--store-id", "vericodegen-2026-" + paper,
             "--secret-handle", "handle:migration-test"]
        def start():
            return subprocess.Popen(argv, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        proc = start()
        token = ""
        try:
            deadline = time.monotonic() + 25
            ready = None
            while time.monotonic() < deadline and proc.poll() is None:
                path = owner / "paper-owner.ready.json"
                if path.exists():
                    observed = json.loads(path.read_text())
                    if observed.get("ready"):
                        ready = observed
                        break
                time.sleep(0.05)
            if ready is None:
                raise AssertionError("fresh migration owner failed readiness")
            if restart_owner:
                first_identity = ready["identity"]
                proc.terminate()
                proc.communicate(timeout=15)
                if proc.returncode != 0:
                    raise AssertionError("first test owner did not stop cleanly")
                proc = start()
                ready = None
                deadline = time.monotonic() + 25
                while time.monotonic() < deadline and proc.poll() is None:
                    observed = json.loads((owner / "paper-owner.ready.json").read_text())
                    if observed.get("ready") and observed["identity"]["server_id"] != first_identity["server_id"]:
                        ready = observed
                        break
                    time.sleep(0.05)
                if ready is None or ready["identity"]["generation"] != first_identity["generation"] + 1:
                    raise AssertionError("test owner generation did not advance")
            token = (owner / "handle_migration-test.quack-token").read_text().strip()
            os.environ[MIG.TOKEN_ENV] = token
            yield ready["quack_endpoint"], token
        finally:
            if proc.poll() is None:
                proc.terminate()
            try:
                out, err = proc.communicate(timeout=15)
            except subprocess.TimeoutExpired:
                proc.kill()
                out, err = proc.communicate(timeout=5)
            if token and token in out + err:
                raise AssertionError("test owner diagnostics leaked token")
            if proc.returncode != 0:
                raise AssertionError("test owner did not exit cleanly")


def native_source(endpoint):
    _, _, _, source_type, _ = MIG.MAT._native(ROOT)
    return source_type(endpoint, install_schema=False)


def snapshot(source):
    return [MIG.plain(r) for r in source.intent.list_tasks(limit=1000)]


def upsert_record(source, record, **changes):
    keys = ("task_cid", "task_alias", "goal_cid", "ordinal", "status", "priority", "plan_cid", "objective_id", "body", "identity")
    payload = {key: record[key] for key in keys}
    payload.update(changes)
    return source.intent.upsert_task(**payload, expected_revision=record["revision"])


class PaperValidationMigrationTests(unittest.TestCase):
    def test_dispatch_forbidden_receipt_preserves_unknown_observation_and_rejects_positive_dispatch(self):
        failure = {"operation": "database_portal_attempt_failure", "reason": "validation_project_dependency_preflight_failed",
                   "deferred": True, "attempt_consumed": False, "provider_dispatched": None, "provider_call_allowed": False,
                   "failure_kind": "lifecycle_setup", "repair_required": True, "task_cid": "task:test",
                   "claim_id": "claim:test", "attempt_id": "attempt:test", "owner_session_id": "session:test",
                   "lease_id": "lease:test", "fencing_token": 1, "fence_epoch": 1,
                   "control_expected_revision": 1, "control_result_revision": 2}
        record = {"task_alias": "NS-001", "task_cid": "task:test", "revision": 2,
                  "body": {"completion_receipt": failure}}
        self.assertIs(MIG.known_blocked_failure(record, already_correct=False), failure)
        self.assertIsNone(failure["provider_dispatched"])
        for changes in ({"provider_dispatched": True}, {"provider_call_allowed": None}):
            observed = {**record, "body": {"completion_receipt": {**failure, **changes}}}
            with self.subTest(changes=changes), self.assertRaises(MIG.MigrationError):
                MIG.known_blocked_failure(observed, already_correct=False)

    def test_restarted_owner_with_historical_generation_migrates_without_erasing_history(self):
        paper = "neurosymbolic_supervision"
        with old_quack_board(paper, restart_owner=True) as (endpoint, token):
            report = MIG.migrate(paper, endpoint)
            self.assertEqual(report["changed"], 25)
            self.assertEqual(report["owner"]["generation"], 2)
            self.assertEqual(report["owner_history_row_count"], 2)
            self.assertEqual(report["owner"]["listen_uri"], endpoint)
            self.assertNotIn(token, json.dumps(report))
            if os.environ.get("PAPER_ARGV_RESTART_TEST_RECEIPT"):
                Path(os.environ["PAPER_ARGV_RESTART_TEST_RECEIPT"]).write_text(json.dumps(report, indent=2) + "\n")

    def test_all_three_actual_boards_migrate_with_one_event_per_task_and_idempotent_retry(self):
        receipts = []
        for paper in MIG.MAT.PAPERS:
            with self.subTest(paper=paper), old_quack_board(paper) as (endpoint, token):
                with native_source(endpoint) as source:
                    before = snapshot(source)
                dry = MIG.migrate(paper, endpoint, dry_run=True)
                self.assertEqual(dry["changed"], 0)
                self.assertEqual(dry["before_snapshot_sha256"], dry["after_snapshot_sha256"])
                result = MIG.migrate(paper, endpoint)
                self.assertTrue(result["success"])
                self.assertEqual(result["changed"], 25)
                self.assertEqual(result["after_event_watermark"] - result["before_event_watermark"], 25)
                self.assertNotIn(token, json.dumps(result))
                with native_source(endpoint) as source:
                    after = snapshot(source)
                    for old, new in zip(before, after):
                        self.assertEqual(MIG.preserved_contract(old), MIG.preserved_contract(new))
                        self.assertEqual(new["revision"], old["revision"] + 1)
                        self.assertEqual(new["validations"][0]["argv"][:2], ["python3", "scripts/paper_supervisors.py"])
                        self.assertEqual(new["validations"][0]["policy"], old["validations"][0]["policy"])
                repeated = MIG.migrate(paper, endpoint)
                self.assertEqual((repeated["changed"], repeated["unchanged"]), (0, 25))
                self.assertEqual(repeated["before_snapshot_sha256"], repeated["after_snapshot_sha256"])
                self.assertEqual(repeated["before_event_watermark"], repeated["after_event_watermark"])
                receipts.append(result)
        if os.environ.get("PAPER_ARGV_MIGRATION_TEST_RECEIPT"):
            Path(os.environ["PAPER_ARGV_MIGRATION_TEST_RECEIPT"]).write_text(json.dumps({"schema": "paper-validation-migration-test/v1", "live_campaign_modified": False, "receipts": receipts}, indent=2) + "\n")

    def test_admission_rejects_any_inprogress_bad_argv_or_source_before_first_update(self):
        paper = "neurosymbolic_supervision"
        with old_quack_board(paper) as (endpoint, _), native_source(endpoint) as source:
            pristine = MIG.plain(source.intent.get_task("NS-025"))
            for case in ("in_progress", "bad_argv", "bad_source", "unknown_blocked"):
                current = MIG.plain(source.intent.get_task("NS-025"))
                old_validation = pristine["validations"][0]
                validation = {"argv": old_validation["argv"], **old_validation["policy"]}
                body, status = dict(pristine["body"]), "ready"
                if case == "in_progress":
                    status = "in_progress"
                elif case == "bad_argv":
                    validation["argv"] = ["python3", "unexpected.py"]
                elif case == "bad_source":
                    validation["source_command"] = "python3 unexpected.py"
                else:
                    status = "blocked"
                    body["completion_receipt"] = {"operation": "unrelated"}
                upsert_record(source, current, validations=[validation], body=body, status=status)
                before = MIG.digest(snapshot(source))
                with self.subTest(case=case), self.assertRaises(MIG.MigrationError):
                    MIG.migrate(paper, endpoint)
                self.assertEqual(MIG.digest(snapshot(source)), before)
            current = MIG.plain(source.intent.get_task("NS-025"))
            upsert_record(source, current, status="ready", body=pristine["body"],
                          validations=[{"argv": old_validation["argv"], **old_validation["policy"]}])
            before = MIG.digest(snapshot(source))
            with self.assertRaises(MIG.MigrationError):
                MIG.migrate("law_to_action", endpoint)
            self.assertEqual(MIG.digest(snapshot(source)), before)

    def test_exact_preflight_blocked_receipt_is_preserved_without_requeue(self):
        paper = "neurosymbolic_supervision"
        with old_quack_board(paper) as (endpoint, _), native_source(endpoint) as source:
            task = MIG.plain(source.intent.get_task("NS-001"))
            failure = {"operation": "database_portal_attempt_failure", "reason": "validation_project_dependency_preflight_failed",
                       "deferred": True, "attempt_consumed": False, "provider_dispatched": False,
                       "failure_kind": "lifecycle_setup", "repair_required": True,
                       "task_cid": task["task_cid"], "claim_id": "claim:test-fixture", "attempt_id": "attempt:test-fixture",
                       "owner_session_id": "session:test-fixture", "lease_id": "lease:test-fixture",
                       "fencing_token": 1, "fence_epoch": 1,
                       "control_expected_revision": task["revision"], "control_result_revision": task["revision"] + 1}
            source.intent.cas_task_status(task_cid=task["task_cid"], expected_revision=task["revision"],
                                          new_status="blocked", receipt=failure)
            report = MIG.migrate(paper, endpoint)
            self.assertEqual(report["changed"], 25)
            self.assertEqual(report["blocked_tasks_requeued"], 0)
            observed = MIG.plain(source.intent.get_task("NS-001"))
            self.assertEqual(observed["status"], "blocked")
            self.assertEqual(observed["body"]["completion_receipt"], failure)
            item = next(t for t in report["tasks"] if t["task_id"] == "NS-001")
            self.assertEqual(item["failure_receipt"], failure)
            repeated = MIG.migrate(paper, endpoint)
            self.assertEqual((repeated["changed"], repeated["unchanged"]), (0, 25))


if __name__ == "__main__":
    unittest.main()

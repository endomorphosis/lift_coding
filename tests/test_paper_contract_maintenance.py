"""Real owner-side maintenance authority and CAS refusal controls."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import time
import tempfile
import unittest
import uuid
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def load(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


FIX = load("maintenance_native_fixtures", "tests/test_migrate_paper_validation_argv.py")
ADMIN = load("maintenance_under_test", "scripts/paper_contract_maintenance.py")


class PaperMaintenanceTests(unittest.TestCase):
    def test_source_guard_refuses_changed_bytes_and_growth_without_loading_a_database(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "reviewed.json"
            path.write_bytes(b"reviewed")
            controller = object.__new__(ADMIN.OwnerMaintenance)
            controller.source_pins = {path.name: hashlib.sha256(path.read_bytes()).hexdigest()}
            controller.source_sizes = {path.name: path.stat().st_size}
            with patch.object(ADMIN, "ROOT", root):
                controller._check_sources()
                path.write_bytes(b"modified")
                with self.assertRaises(ADMIN.MaintenanceError):
                    controller._check_sources()
                path.write_bytes(b"reviewed" + b"appended")
                with self.assertRaises(ADMIN.MaintenanceError):
                    controller._check_sources()

    def test_read_credential_alone_and_foreign_owner_directory_cannot_write(self):
        with FIX.old_quack_board("neurosymbolic_supervision") as (endpoint, _), FIX.native_source(endpoint) as source:
            ready = json.loads((Path(os.environ[ADMIN.STATE_ENV]) / "paper-owner.ready.json").read_text())
            owner = ADMIN.identity(ready["identity"])
            before = FIX.snapshot(source)
            record = before[0]
            with patch.dict(os.environ, {ADMIN.STATE_ENV: ""}), self.assertRaises(ADMIN.MaintenanceError):
                ADMIN.submit("validation_argv", record["task_cid"], record["revision"], owner)
            foreign = {**owner, "database_uuid": "different-store"}
            with self.assertRaises(ADMIN.MaintenanceError):
                ADMIN.submit("validation_argv", record["task_cid"], record["revision"], foreign)
            self.assertEqual(FIX.snapshot(source), before)

    def test_owner_refuses_forgery_arbitrary_operations_fields_and_stale_revisions(self):
        with FIX.old_quack_board("neurosymbolic_supervision") as (endpoint, _), FIX.native_source(endpoint) as source:
            folder = Path(os.environ[ADMIN.STATE_ENV]) / "paper-maintenance"
            token = (folder / "credential").read_text().strip()
            ready = json.loads((folder.parent / "paper-owner.ready.json").read_text())
            owner = ADMIN.identity(ready["identity"])
            before = FIX.snapshot(source)
            row = before[0]
            def request(changes, *, wrong_mac=False):
                nonce = uuid.uuid4().hex
                body = {"schema": ADMIN.SCHEMA, "request_id": nonce, "issued_at_ms": int(time.time()*1000),
                        "owner": owner, "operation": "validation_argv", "task_cid": row["task_cid"],
                        "expected_revision": row["revision"], **changes}
                signed = {**body, "mac": "0"*64 if wrong_mac else ADMIN.sign(body, token)}
                ADMIN.atomic(folder / (nonce + ".request.json"), signed)
                path = folder / (nonce + ".done.json")
                deadline = time.monotonic() + 10
                while not path.exists() and time.monotonic() < deadline:
                    time.sleep(.05)
                response = json.loads(path.read_text())
                signature = response.pop("mac")
                self.assertEqual(signature, ADMIN.sign(response, token))
                self.assertEqual(response["request_sha256"], hashlib.sha256(ADMIN.wire(signed)).hexdigest())
                path.unlink()
                self.assertFalse(response["ok"])
                self.assertEqual(FIX.snapshot(source), before)
                return response["error_code"]
            self.assertEqual(request({}, wrong_mac=True), "authentication_failed")
            self.assertEqual(request({"operation": "generic_upsert"}), "owner_or_operation_differs")
            self.assertEqual(request({"argv": ["bash", "-lc", "arbitrary command"]}), "closed_request_required")
            self.assertEqual(request({"owner": {**owner, "generation": owner["generation"] + 1}}), "owner_or_operation_differs")
            self.assertEqual(request({"issued_at_ms": int(time.time()*1000) - ADMIN.TTL_MS - 1000}), "expired_request")
            self.assertEqual(request({"expected_revision": True}), "exact_revision_required")
            self.assertEqual(request({"expected_revision": row["revision"] + 1}), "revision_conflict")
            # Owner admission checks the entire reviewed population, even
            # when the caller bypasses the migration script's own preflight.
            result = ADMIN.submit("validation_argv", row["task_cid"], row["revision"], owner)
            self.assertTrue(result["changed"])
            after = FIX.snapshot(source)
            with self.assertRaises(ADMIN.MaintenanceError):
                ADMIN.submit("validation_argv", row["task_cid"], row["revision"], owner)
            self.assertEqual(FIX.snapshot(source), after)
            self.assertEqual((folder / "credential").stat().st_mode & 0o777, 0o600)
            self.assertNotIn(token, json.dumps(result) + json.dumps(ready))

    def test_snapshot_owner_rejects_foreign_task_binding_before_first_update(self):
        def prepare(source):
            row = FIX.MIG.plain(source.intent.get_task("NS-025"))
            FIX.upsert_record(source, row, priority="UNREVIEWED")
        with FIX.old_quack_board("neurosymbolic_supervision", prepare=prepare) as (endpoint, _), FIX.native_source(endpoint) as source:
            ready = json.loads((Path(os.environ[ADMIN.STATE_ENV]) / "paper-owner.ready.json").read_text())
            before = FIX.snapshot(source)
            row = before[0]
            with self.assertRaises(ADMIN.MaintenanceError):
                ADMIN.submit("snapshot_directory", row["task_cid"], row["revision"], ADMIN.identity(ready["identity"]))
            self.assertEqual(FIX.snapshot(source), before)

    def test_owner_rejects_invalid_population_without_trusting_client_preflight(self):
        def prepare(source):
            row = FIX.MIG.plain(source.intent.get_task("NS-025"))
            FIX.upsert_record(source, row, status="in_progress")
        with FIX.old_quack_board("neurosymbolic_supervision", prepare=prepare) as (endpoint, _), FIX.native_source(endpoint) as source:
            ready = json.loads((Path(os.environ[ADMIN.STATE_ENV]) / "paper-owner.ready.json").read_text())
            before = FIX.snapshot(source)
            row = before[0]
            with self.assertRaises(ADMIN.MaintenanceError):
                ADMIN.submit("validation_argv", row["task_cid"], row["revision"], ADMIN.identity(ready["identity"]))
            self.assertEqual(FIX.snapshot(source), before)


if __name__ == "__main__":
    unittest.main()

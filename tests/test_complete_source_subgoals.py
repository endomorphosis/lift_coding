"""Owner fencing survives health refreshes without accepting a new authority."""
from __future__ import annotations

import copy
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "complete_source_subgoals_owner_test",
    ROOT / "papers/completion/runtime_bootstrap/complete_source_subgoals.py")
HELPER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(HELPER)


def readiness():
    return {
        "schema": "paper-quack-owner/v1", "ready": True,
        "database": "/state/autoformalization/control.duckdb",
        "state_dir": "/state/autoformalization/quack-owner",
        "quack_endpoint": "quack:127.0.0.1:5555", "endpoint_secret_handle": "handle:test-owner",
        "store_id": "vericodegen-2026-autoformalization", "store_generation": "14",
        "schema_revision": "7", "checked_at": "2026-09-11T18:00:00+00:00",
        "identity": {
            "schema": "native-owner/v1", "contract_version": 1,
            "server_id": "server:original", "database_uuid": "uuid:original",
            "store_id": "vericodegen-2026-autoformalization", "generation": 14,
            "schema_revision": 7, "schema_fingerprint": "schema:original",
            "listen_uri": "quack:127.0.0.1:5555", "secret_handle": "handle:test-owner",
            "credential_generation": 1, "extension_fingerprint": "extensions:original",
            "fence_epoch": 14, "revision": 1, "startup_epoch": 14,
            "repository_id": "repository:test", "started_at": "2026-09-11T17:59:50+00:00",
            "process_birth_id": "birth:original", "status": "ready",
            "process_birth": {"pid": 1234, "start_time_ticks": 9876, "boot_id": "boot:test", "parent_pid": 1000},
        },
        "remote_probe": {"identity_checked": True, "network_query": True, "rollback_checked": True,
                         "task_count": 25, "checked_at": "2026-09-11T18:00:00+00:00"},
    }


class SelectOnlyConnection:
    def __init__(self, ready):
        self.identity = {k: ready["identity"][k] for k in ("server_id", "database_uuid", "generation", "schema_revision")}
        self.uuid = self.identity["database_uuid"]
        self.queries = []

    def execute(self, sql, parameters):
        assert sql.startswith("SELECT "), "Test connection must never accept native writes"
        self.queries.append((sql, parameters))
        self.answer = [self.identity] if "FROM state_servers" in sql else [{"value": self.uuid}]
        return self

    def fetchall(self):
        return self.answer


class SourceSubgoalOwnerBindingTests(unittest.TestCase):
    def setUp(self):
        self.ready = readiness()
        self.connection = SelectOnlyConnection(self.ready)

    def check(self, current, *, alive=True):
        with patch.object(HELPER.C, "read", return_value=current), patch.object(HELPER.C, "alive", return_value=alive):
            return HELPER.checked_owner(self.connection, "autoformalization", self.ready)

    def test_actual_publisher_health_refresh_shape_is_accepted(self):
        current = copy.deepcopy(self.ready)
        current["checked_at"] = "2026-09-11T18:00:10+00:00"
        current["remote_health"] = {"identity_checked": True, "network_query": True,
                                    "rollback_checked": False, "task_count": 25,
                                    "checked_at": current["checked_at"]}
        self.assertNotEqual(current, self.ready)  # The old whole-document guard rejected this.
        self.assertEqual(self.check(current), self.connection.identity)
        current["remote_health"]["task_count"] = 26
        self.assertEqual(self.check(current), self.connection.identity)
        self.assertTrue(all(sql.startswith("SELECT ") for sql, _ in self.connection.queries))

    def test_top_level_authority_swaps_and_missing_fields_are_rejected(self):
        for field in ("schema", "database", "state_dir", "quack_endpoint", "endpoint_secret_handle",
                      "store_id", "store_generation", "schema_revision", "remote_probe"):
            for mode in ("changed", "missing"):
                with self.subTest(field=field, mode=mode):
                    current = copy.deepcopy(self.ready)
                    if mode == "missing":
                        del current[field]
                    else:
                        current[field] = "different-authority"
                    with self.assertRaisesRegex(RuntimeError, "Owner changed during validation"):
                        self.check(current)

    def test_all_native_identity_fields_remain_fenced(self):
        for field in self.ready["identity"]:
            with self.subTest(field=field):
                current = copy.deepcopy(self.ready)
                current["identity"][field] = "different-authority"
                with self.assertRaisesRegex(RuntimeError, "Owner changed during validation"):
                    self.check(current)

    def test_pid_reuse_birth_boot_and_parent_changes_are_rejected(self):
        for field in ("pid", "start_time_ticks", "boot_id", "parent_pid"):
            with self.subTest(field=field):
                current = copy.deepcopy(self.ready)
                original = current["identity"]["process_birth"][field]
                current["identity"]["process_birth"][field] = original + 1 if isinstance(original, int) else original + "-new"
                with self.assertRaisesRegex(RuntimeError, "Owner changed during validation"):
                    self.check(current)

    def test_stopped_owner_dead_process_and_unknown_contract_change_are_rejected(self):
        for update in ({"ready": False}, {"ready": 1}, {"stopped": True}, {"new_authority_field": "new"}):
            with self.subTest(update=update):
                with self.assertRaisesRegex(RuntimeError, "Owner changed during validation"):
                    self.check({**self.ready, **update})
        with self.assertRaisesRegex(RuntimeError, "Owner changed during validation"):
            self.check(self.ready, alive=False)

    def test_authenticated_sql_owner_and_metadata_uuid_still_must_match(self):
        for field in self.connection.identity:
            with self.subTest(field=field):
                self.connection = SelectOnlyConnection(self.ready)
                self.connection.identity[field] = "different-owner"
                with self.assertRaisesRegex(RuntimeError, "Authenticated server generation/identity differs"):
                    self.check(self.ready)
        self.connection = SelectOnlyConnection(self.ready)
        self.connection.uuid = "different-database"
        with self.assertRaisesRegex(RuntimeError, "Database UUID differs"):
            self.check(self.ready)


if __name__ == "__main__":
    unittest.main()

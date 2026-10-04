"""Real Quack task claim and native sidecar persistence, without provider calls."""
from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "paper_materializer_for_daemon_test", ROOT / "scripts/materialize_paper_database.py"
)
MAT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MAT)


class PaperDatabaseDaemonTests(unittest.TestCase):
    def test_real_quack_claim_persists_remote_cas_and_native_sidecars(self):
        MAT._native(ROOT)
        from ipfs_accelerate_py.agent_supervisor.task_sources.duckdb_state import (
            open_duckdb_connection,
            open_quack_transport_connection,
        )
        from ipfs_accelerate_py.agent_supervisor.todo_daemon.implementation_daemon import (
            DatabaseImplementationDaemon,
        )

        isolated = dict(os.environ)
        for name in tuple(isolated):
            if name.startswith("IPFS_ACCELERATE_AGENT_QUACK_") or name in {
                "IPFS_ACCELERATE_AGENT_STATE_STORE_ID",
                "IPFS_ACCELERATE_AGENT_STATE_SCHEMA_REVISION",
            }:
                isolated.pop(name)
        isolated["IPFS_ACCELERATE_AGENT_QUACK_PREFER"] = "false"
        with patch.dict(os.environ, isolated, clear=True), tempfile.TemporaryDirectory(
            prefix="vericodegen-daemon-smoke-"
        ) as tmp:
            folder = Path(tmp)
            database, state = folder / "control.duckdb", folder / "owner"
            execution = folder / "control.execution.duckdb"
            coordination = folder / "control.coordination.duckdb"
            report = MAT.materialize("neurosymbolic_supervision", database, ROOT)
            board = folder / "board.md"
            config = json.loads((ROOT / "papers/completion/neurosymbolic_supervision/supervisor.json").read_text())
            board.write_bytes((ROOT / config["todo_path"]).read_bytes())
            board_before = board.read_bytes()
            proc = subprocess.Popen(
                [sys.executable, str(ROOT / "scripts/paper_state_owner.py"),
                 "--database", str(database), "--state-dir", str(state),
                 "--store-id", "paper-daemon-smoke", "--secret-handle", "handle:paper-daemon-smoke"],
                cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
            )
            daemon, remote, ready, token = None, None, None, ""
            try:
                ready_path = state / "paper-owner.ready.json"
                deadline = time.monotonic() + 25
                while time.monotonic() < deadline and proc.poll() is None:
                    if ready_path.is_file():
                        observed = json.loads(ready_path.read_text())
                        if observed.get("ready"):
                            ready = observed
                            break
                    time.sleep(0.05)
                if ready is None:
                    if proc.poll() is None:
                        proc.terminate()
                    out, err = proc.communicate(timeout=10)
                    self.fail("fresh owner did not become ready: " + err + out)
                vault = state / "handle_paper-daemon-smoke.quack-token"
                token = vault.read_text().strip()
                os.environ["IPFS_ACCELERATE_AGENT_QUACK_TOKEN"] = token
                endpoint = ready["quack_endpoint"]
                remote = open_quack_transport_connection(endpoint, token=token)
                before = remote.execute("SELECT count(*) FROM domain_events").fetchone()[0]
                original = {row[0]: row[1] for row in remote.execute("SELECT task_cid, revision FROM tasks").fetchall()}

                def forbidden_provider(*args, **kwargs):
                    raise AssertionError("this smoke must never invoke a provider or effect")

                daemon = DatabaseImplementationDaemon(
                    database_path=database, execution_path=execution,
                    coordination_path=coordination, authority_mode="quack",
                    quack_uri=endpoint, task_source_kind="duckdb",
                    owner_session_id="paper-daemon-smoke-session", task_prefix="NS-",
                    markdown_path=board, lease_ms=60_000,
                    provider_fn=forbidden_provider, effect_fn=forbidden_provider,
                    validation_fn=forbidden_provider, require_real_execution=True,
                )
                attempt = daemon.claim_next()
                self.assertIsNotNone(attempt)
                self.assertIn(attempt.task_alias, report["ready_tasks"])
                self.assertEqual(attempt.status, "running")
                self.assertEqual(attempt.committed_phase, "claimed")
                self.assertEqual(len(daemon.list_running_attempts()), 1)
                self.assertEqual(daemon.get_attempt(attempt.attempt_id), attempt)
                self.assertEqual([p["phase"] for p in daemon.phase_history(attempt.attempt_id)], ["claimed"])
                self.assertEqual(daemon.markdown_status_write_count, 0)
                self.assertEqual(board.read_bytes(), board_before)
                changed = remote.execute(
                    "SELECT task_cid, status, revision FROM tasks WHERE status = 'in_progress'"
                ).fetchall()
                changed = [tuple(row[i] for i in range(len(row))) for row in changed]
                self.assertIn(attempt.task_cid, original, f"initial revisions: {original!r}; changed: {changed!r}")
                self.assertEqual(changed, [(attempt.task_cid, "in_progress", original[attempt.task_cid] + 1)])
                events = remote.execute(
                    "SELECT event_type, task_cid, body_json FROM domain_events WHERE global_sequence > ?",
                    [before],
                ).fetchall()
                events = [tuple(row[i] for i in range(len(row))) for row in events]
                self.assertEqual(len(events), 1)
                self.assertEqual(events[0][:2], ("intent.task_status_changed", attempt.task_cid))
                event_body = json.loads(events[0][2])
                self.assertIn(attempt.attempt_id, json.dumps(event_body))
                self.assertIn(attempt.claim_id, json.dumps(event_body))
                daemon.close()
                daemon = None
                persisted = {}
                for name, path, sql in (
                    ("execution_attempts", execution, "SELECT attempt_id, task_cid, committed_phase, status FROM database_task_attempts"),
                    ("execution_events", execution, "SELECT event_type, attempt_id FROM daemon_execution_events"),
                    ("provider_invocations", execution, "SELECT attempt_id FROM provider_invocations"),
                    ("coordination_claims", coordination, "SELECT claim_id, task_cid, attempt_id, state FROM task_claims"),
                    ("coordination_attempts", coordination, "SELECT attempt_id, task_cid, status FROM task_attempts"),
                ):
                    connection = open_duckdb_connection(path)
                    try:
                        persisted[name] = [tuple(row[i] for i in range(len(row))) for row in connection.execute(sql).fetchall()]
                    finally:
                        connection.close()
                self.assertEqual(persisted["execution_attempts"], [(attempt.attempt_id, attempt.task_cid, "claimed", "running")])
                self.assertEqual(persisted["execution_events"], [("task_claimed", attempt.attempt_id)])
                self.assertEqual(persisted["provider_invocations"], [])
                self.assertEqual(len(persisted["coordination_claims"]), 1)
                self.assertEqual(persisted["coordination_claims"][0][:3], (attempt.claim_id, attempt.task_cid, attempt.attempt_id))
                self.assertEqual(persisted["coordination_attempts"], [(attempt.attempt_id, attempt.task_cid, "running")])
                remote.close()
                remote = None
                proc.send_signal(signal.SIGTERM)
                out, err = proc.communicate(timeout=15)
                self.assertEqual(proc.returncode, 0, err)
                self.assertNotIn(token, out + err)
                self.assertFalse(vault.exists())
                self.assertTrue(json.loads(ready_path.read_text())["stopped"])
                with socket.socket() as probe:
                    probe.settimeout(1)
                    self.assertNotEqual(probe.connect_ex(("127.0.0.1", int(endpoint.rsplit(":", 1)[1]))), 0)
                proof = {
                    "schema": "paper-database-daemon-smoke/v1",
                    "paper": "neurosymbolic_supervision", "task_alias": attempt.task_alias,
                    "initial_task_count": 25, "claimed_task_count": 1,
                    "native_api": "DatabaseImplementationDaemon.claim_next",
                    "remote_authority": {"task_status": "in_progress", "revision_increment": 1,
                                         "new_domain_events": 1, "event_type": events[0][0]},
                    "sidecar_row_counts": {key: len(value) for key, value in persisted.items()},
                    "committed_phase": "claimed", "provider_invocations": 0,
                    "markdown_unchanged": True, "owned_owner_stopped": True,
                    "owned_listener_closed": True, "owned_token_removed": True,
                }
                if os.environ.get("PAPER_DAEMON_SMOKE_REPORT"):
                    Path(os.environ["PAPER_DAEMON_SMOKE_REPORT"]).write_text(json.dumps(proof, indent=2) + "\n")
            finally:
                if daemon is not None:
                    daemon.close()
                if remote is not None:
                    remote.close()
                if proc.poll() is None:
                    proc.terminate()
                    try:
                        proc.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        proc.kill()
                        proc.wait(timeout=5)
                proc.communicate()


if __name__ == "__main__":
    unittest.main()

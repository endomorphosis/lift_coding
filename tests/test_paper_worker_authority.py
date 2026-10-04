"""Native worker authority, durable replay, and hardened campaign handoff."""
from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import socket
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


MAT = load("worker_materializer", "materialize_paper_database.py")
CAM = load("worker_campaign", "paper_supervisor_campaign.py")


class WorkerAuthorityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        MAT._native(ROOT)

    def test_bound_command_replay_and_failure_are_transactional(self):
        from ipfs_accelerate_py.agent_supervisor.task_sources.database_task_source import execute_quack_owner_command
        from ipfs_accelerate_py.agent_supervisor.task_sources.intent_repository import IntentRepository, IntentRepositoryError
        from ipfs_accelerate_py.agent_supervisor.task_sources.duckdb_state import open_duckdb_connection
        with tempfile.TemporaryDirectory() as tmp:
            database = Path(tmp) / "control.duckdb"
            MAT.materialize("neurosymbolic_supervision", database, ROOT)
            connection = open_duckdb_connection(database)
            try:
                task = connection.execute("SELECT task_cid FROM tasks ORDER BY ordinal LIMIT 1").fetchone()[0]
                payload = {"task_cid": task, "evidence_kind": "validation", "digest": "sha256:" + "3" * 64}
                kwargs = {"request_id": "b" * 32, "store_id": str(database), "store_generation": "generation-1"}
                repository = IntentRepository(bound_connection=connection, install_schema=False)
                before = connection.execute("SELECT count(*) FROM domain_events").fetchone()[0]
                result = execute_quack_owner_command(repository, "record_evidence", payload, **kwargs)
                repository.close()
                connection.close()
                connection = open_duckdb_connection(database)
                repository = IntentRepository(bound_connection=connection, install_schema=False, session_id="restarted-session")
                self.assertEqual(execute_quack_owner_command(repository, "record_evidence", payload, **kwargs), result)
                self.assertEqual(connection.execute("SELECT count(*) FROM domain_events").fetchone()[0], before + 1)
                for changed in ({"store_generation": "generation-2"}, {"store_id": "foreign-store"}):
                    with self.subTest(changed=changed), self.assertRaises(IntentRepositoryError):
                        execute_quack_owner_command(repository, "record_evidence", payload, **{**kwargs, **changed})
                with self.assertRaises(IntentRepositoryError):
                    execute_quack_owner_command(repository, "record_evidence", {**payload, "digest": "sha256:" + "4" * 64}, **kwargs)
                def fail_after_write():
                    execute_quack_owner_command(repository, "record_evidence", {**payload, "digest": "sha256:" + "5" * 64})
                    raise RuntimeError("injected transaction failure")
                with self.assertRaisesRegex(RuntimeError, "injected transaction failure"):
                    repository.run_idempotent_owner_command(
                        **{**kwargs, "request_id": "c" * 32}, command="record_evidence",
                        command_payload={**payload, "digest": "sha256:" + "5" * 64}, operation=fail_after_write,
                    )
                self.assertEqual(connection.execute("SELECT count(*) FROM domain_events").fetchone()[0], before + 1)
                self.assertEqual(connection.execute("SELECT count(*) FROM idempotency_records WHERE idempotency_key LIKE 'quack-owner-command:%'").fetchone()[0], 1)
                self.assertEqual(connection.execute("SELECT 1").fetchone()[0], 1)
                repository.close()
            finally:
                connection.close()

    def test_broker_denies_unsealed_or_foreign_credentials_and_preserves_live_sockets(self):
        from ipfs_accelerate_py.agent_supervisor.runtime.worker_grant_broker import (
            TypedStateOwnerGrantBroker, sealed_worker_bootstrap, read_sealed_worker_bootstrap,
        )
        from ipfs_accelerate_py.agent_supervisor.runtime.quack_state_server import QuackStateServerControlError
        from ipfs_accelerate_py.agent_supervisor.task_sources import typed_state_owner as typed
        descriptor = sealed_worker_bootstrap()
        try:
            secret = read_sealed_worker_bootstrap(descriptor)
            with self.assertRaises(OSError):
                os.pwrite(descriptor, b"x", 0)
            with tempfile.TemporaryFile() as ordinary:
                ordinary.write(secret.encode("ascii")); ordinary.flush()
                with self.assertRaises((OSError, ValueError)):
                    read_sealed_worker_bootstrap(ordinary.fileno())
            with tempfile.TemporaryDirectory() as tmp:
                path = Path(tmp) / "grants.sock"
                stale = socket.socket(socket.AF_UNIX); stale.bind(str(path)); stale.close()
                issued = []
                broker = TypedStateOwnerGrantBroker(socket_path=path, bootstrap_secret=secret, store_id="test-store",
                    resolve_credential=lambda *args: issued.append(args) or "test_only_credential")
                broker.start()
                try:
                    base = {"schema": typed.TYPED_STATE_OWNER_GRANT_BROKER_SCHEMA,
                            "credential_kind": "database_task_command", "bootstrap_secret": secret,
                            "client_id": f"database-task-source:{os.getpid()}",
                            "process_birth_id": typed.kernel_process_birth_id(), "store_id": "test-store"}
                    for change in ({"bootstrap_secret": "0" * 64}, {"store_id": "foreign"},
                                   {"process_birth_id": "foreign-birth"}, {"credential_kind": "arbitrary_sql"},
                                   {"sql": "UPDATE tasks SET status='completed'"}):
                        with self.subTest(fields=list(change)), socket.socket(socket.AF_UNIX) as client:
                            client.settimeout(2); client.connect(str(path))
                            client.sendall(json.dumps({**base, **change}).encode() + b"\n")
                            with client.makefile("rb") as stream:
                                response = json.loads(stream.readline())
                            self.assertFalse(response["ok"]); self.assertEqual(response["token"], "")
                    self.assertEqual(issued, [])
                    other = TypedStateOwnerGrantBroker(socket_path=path, bootstrap_secret=secret, store_id="test-store", resolve_credential=lambda *args: "unused")
                    with self.assertRaisesRegex(QuackStateServerControlError, "live listener"):
                        other.start()
                    self.assertTrue(path.is_socket()); self.assertTrue(broker.alive())
                finally:
                    broker.stop()
                self.assertFalse(path.exists())
                path.write_text("retained foreign file")
                other = TypedStateOwnerGrantBroker(socket_path=path, bootstrap_secret=secret, store_id="test-store", resolve_credential=lambda *args: "unused")
                with self.assertRaisesRegex(QuackStateServerControlError, "same-UID socket"):
                    other.start()
                self.assertEqual(path.read_text(), "retained foreign file")
        finally:
            os.close(descriptor)

    def test_campaign_handoff_real_owner_and_closed_command(self):
        from ipfs_accelerate_py.agent_supervisor.task_sources.duckdb_state import open_quack_transport_connection, submit_quack_owner_command
        from ipfs_accelerate_py.agent_supervisor.task_sources import typed_state_owner as typed
        from ipfs_accelerate_py.agent_supervisor.todo_daemon.supervisor_runtime import SupervisedChildSpec, launch_supervised_child
        from ipfs_accelerate_py.agent_supervisor.runtime.multi_supervisor_runner import provider_subprocess_environment
        from ipfs_accelerate_py.agent_supervisor.validation.validation_runtime import build_validation_environment
        with tempfile.TemporaryDirectory() as tmp:
            lane = Path(tmp); database = lane / "control.duckdb"; state = lane / "quack-owner"
            MAT.materialize("neurosymbolic_supervision", database, ROOT)
            descriptor = CAM.worker_bootstrap()
            process = None; remote = None
            try:
                argv = [sys.executable, str(ROOT / "scripts/paper_state_owner.py"),
                        "--database", str(database), "--state-dir", str(state),
                        "--store-id", "vericodegen-2026-neurosymbolic_supervision",
                        "--secret-handle", "handle:worker-handoff-test", "--enable-worker-authority"]
                process, record = CAM.launch(argv, ROOT, CAM.worker_owner_environment(ROOT, database, state), lane / "owner.log", worker_bootstrap_fd=descriptor)
                ready = CAM.wait_owner_ready(process, record, state / "paper-owner.ready.json",
                    paper="neurosymbolic_supervision", database=database, timeout=45)
                token = CAM.token_for(ready, lane)
                remote = open_quack_transport_connection(ready["quack_endpoint"], token=token)
                task = remote.execute("SELECT task_cid FROM tasks ORDER BY ordinal LIMIT 1").fetchone()[0]
                before = remote.execute("SELECT count(*) FROM domain_events").fetchone()[0]
                binding = {"IPFS_ACCELERATE_AGENT_STATE_STORE_ID": ready["store_id"],
                           "IPFS_ACCELERATE_AGENT_STATE_OWNER_SOCKET": ready["worker_authority"]["socket_path"],
                           "IPFS_ACCELERATE_AGENT_STATE_GRANT_BROKER_SOCKET": ready["worker_authority"]["grant_broker_socket"],
                           "IPFS_ACCELERATE_AGENT_STATE_GRANT_BROKER_SECRET_FD": str(descriptor),
                           "IPFS_ACCELERATE_AGENT_QUACK_TOKEN": token,
                           "IPFS_ACCELERATE_AGENT_QUACK_MUTATION_DIR": str(state / "mutations")}
                clean = {k: v for k, v in os.environ.items() if not k.startswith(("IPFS_ACCELERATE_AGENT_STATE_", "IPFS_ACCELERATE_AGENT_QUACK_"))}
                payload = {"task_cid": task, "evidence_kind": "validation", "digest": "sha256:" + "6" * 64}
                with patch.dict(os.environ, {**clean, **binding}, clear=True):
                    client_id = f"database-task-source:{os.getpid()}"
                    birth = typed.kernel_process_birth_id()
                    with self.assertRaises(typed.TypedStateOwnerError):
                        typed.TypedStateOwnerConnection(socket_path=ready["worker_authority"]["socket_path"],
                            token=token, client_id=client_id, process_birth_id=birth, store_id=ready["store_id"])
                    with self.assertRaises(typed.TypedStateOwnerError):
                        typed.request_database_task_command_credential(store_id=ready["store_id"],
                            client_id="caller-selected-worker", process_birth_id=birth)
                    grant_token = typed.request_database_task_command_credential(store_id=ready["store_id"],
                        client_id=client_id, process_birth_id=birth)
                    client_kwargs = dict(socket_path=ready["worker_authority"]["socket_path"],
                        token=grant_token, client_id=client_id, process_birth_id=birth, store_id=ready["store_id"])
                    client = typed.TypedStateOwnerConnection(**client_kwargs)
                    try:
                        with self.assertRaises(typed.TypedStateOwnerError):
                            client.execute_database_task_command("upsert_task", {"status": "completed"}, command_request_id="e" * 32)
                        with self.assertRaises(typed.TypedStateOwnerError):
                            typed.TypedStateOwnerConnection(**client_kwargs)
                    finally:
                        client.close()
                    first = submit_quack_owner_command("record_evidence", payload, request_id="d" * 32)
                    replay = submit_quack_owner_command("record_evidence", payload, request_id="d" * 32)
                    for child_env in (provider_subprocess_environment(os.environ), build_validation_environment(os.environ)):
                        for name in ("IPFS_ACCELERATE_AGENT_QUACK_TOKEN", "IPFS_ACCELERATE_AGENT_STATE_GRANT_BROKER_SECRET_FD",
                                     "IPFS_ACCELERATE_AGENT_STATE_GRANT_BROKER_SOCKET"):
                            self.assertTrue(name not in child_env, name + " must be absent")
                    from ipfs_accelerate_py.agent_supervisor.task_sources.quack_owner_command import QuackOwnerCommandRemoteError
                    with self.assertRaises(QuackOwnerCommandRemoteError) as conflict:
                        submit_quack_owner_command("record_evidence", {**payload, "digest": "sha256:" + "7" * 64}, request_id="d" * 32)
                    self.assertEqual(conflict.exception.code, "conflict")
                self.assertEqual(first, replay)
                self.assertEqual(remote.execute("SELECT count(*) FROM domain_events").fetchone()[0], before + 1)
                worker = lane / "qualification_worker.py"
                receipt_path = lane / "worker-receipt.json"
                worker.write_text('''import json, sys
from pathlib import Path
from ipfs_accelerate_py.agent_supervisor.runtime.process_security import harden_state_authority_process
harden_state_authority_process()
from ipfs_accelerate_py.agent_supervisor.todo_daemon.implementation_daemon import DatabaseImplementationDaemon
def forbidden(*args, **kwargs):
    raise AssertionError("qualification must never invoke a provider")
database = Path(sys.argv[1])
daemon = DatabaseImplementationDaemon(database_path=database,
    execution_path=database.with_name("worker.execution.duckdb"),
    coordination_path=database.with_name("control.coordination.duckdb"),
    authority_mode="quack", quack_uri=sys.argv[2], task_source_kind="duckdb",
    owner_session_id="campaign-worker-qualification", task_prefix="NS-",
    provider_fn=forbidden, effect_fn=forbidden, validation_fn=forbidden,
    require_real_execution=True)
try:
    attempt = daemon.claim_next()
    assert attempt is not None and attempt.committed_phase == "claimed"
    Path(sys.argv[3]).write_text(json.dumps({"attempt_id": attempt.attempt_id,
        "task_cid": attempt.task_cid, "status": attempt.status, "phase": attempt.committed_phase}))
finally:
    daemon.close()
''')
                worker_env = {**CAM.environment(ROOT), **binding}
                child = launch_supervised_child(SupervisedChildSpec(repo_root=ROOT,
                    command=(sys.executable, str(worker), str(database), ready["quack_endpoint"], str(receipt_path)),
                    log_path=lane / "worker.log", child_pid_path=lane / "worker.pid",
                    env=worker_env, worker_credential_handoff=True))
                deadline = time.monotonic() + 45
                while True:
                    waited, status = os.waitpid(child.pid, os.WNOHANG)
                    if waited:
                        break
                    if time.monotonic() >= deadline:
                        os.kill(child.pid, 9); os.waitpid(child.pid, 0)
                        self.fail("managed worker did not exit")
                    time.sleep(0.05)
                self.assertEqual(os.waitstatus_to_exitcode(status), 0, (lane / "worker.log").read_text())
                receipt = json.loads(receipt_path.read_text())
                self.assertEqual((receipt["status"], receipt["phase"]), ("running", "claimed"))
                self.assertEqual(remote.execute("SELECT count(*) FROM domain_events").fetchone()[0], before + 2)
                self.assertEqual(remote.execute("SELECT status FROM tasks WHERE task_cid=?", [receipt["task_cid"]]).fetchone()[0], "in_progress")
                from ipfs_accelerate_py.agent_supervisor.task_sources.duckdb_state import open_duckdb_connection
                for filename, table, expected in (("worker.execution.duckdb", "database_task_attempts", 1),
                                                   ("worker.execution.duckdb", "provider_invocations", 0),
                                                   ("control.coordination.duckdb", "task_claims", 1)):
                    sidecar = open_duckdb_connection(lane / filename)
                    try:
                        self.assertEqual(sidecar.execute("SELECT count(*) FROM " + table).fetchone()[0], expected)
                    finally:
                        sidecar.close()
                self.assertNotIn(token, (state / "paper-owner.ready.json").read_text())
                self.assertNotIn(token, (lane / "owner.log").read_text())
            finally:
                if remote is not None:
                    remote.close()
                if process is not None:
                    process.terminate(); process.wait(timeout=15)
                os.close(descriptor)
            self.assertEqual(process.returncode, 0)
            self.assertFalse(Path(ready["worker_authority"]["grant_broker_socket"]).exists())
            self.assertFalse(Path(ready["worker_authority"]["socket_path"]).exists())


if __name__ == "__main__":
    unittest.main()

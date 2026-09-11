#!/usr/bin/env python3
"""Serve one prebuilt paper control database through authenticated loopback Quack.

The owner alone opens the file. The public ready/status files contain only
identities and opaque credential handles; native token files remain mode 0600.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import signal
import sys
import tempfile
import time
import uuid

ROOT = Path(__file__).resolve().parents[1]
READY_FILENAME = "paper-owner.ready.json"


def _native():
    os.environ.setdefault("IPFS_ACCEL_SKIP_CORE", "1")
    os.environ.setdefault("IPFS_AUTO_INSTALL", "false")
    os.environ.setdefault("IPFS_DATASETS_AUTO_INSTALL", "false")
    for relative in reversed(("external/ipfs_accelerate", "external/ipfs_datasets", "external/ipfs_kit")):
        sys.path.insert(0, str(ROOT / relative))
    from ipfs_accelerate_py.agent_supervisor.runtime.quack_state_server import build_server, ServerLifecycle
    from ipfs_accelerate_py.agent_supervisor.task_sources.duckdb_state import open_quack_transport_connection
    return build_server, ServerLifecycle, open_quack_transport_connection


def _now():
    return datetime.now(timezone.utc).isoformat()


def _atomic_json(path, payload):
    path = Path(path)
    fd, name = tempfile.mkstemp(prefix="." + path.name + ".", dir=path.parent)
    temporary = Path(name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        temporary.chmod(0o600)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _owner_connection(database):
    import duckdb
    # This is a trusted owner process. Providers retain their restrictive
    # client environment. Load only installed extensions; never network-install.
    connection = duckdb.connect(str(database), config={
        "autoload_known_extensions": True, "autoinstall_known_extensions": False,
    })
    try:
        connection.execute("LOAD quack")
    except BaseException:
        connection.close()
        raise
    return connection


def remote_readiness(server, *, exercise_rollback=True):
    _, _, connect = _native()
    identity = server.identity
    if identity is None or server._vault is None:
        raise RuntimeError("native owner has no live identity/vault")
    # Deliberately in-process only: never return/log the credential.
    token = server._vault.resolve(identity.secret_handle)
    connection = connect(identity.listen_uri, token=token)
    try:
        row = connection.execute(
            "SELECT store_id, database_uuid, schema_revision, generation, process_birth_id "
            "FROM state_servers WHERE server_id = ?", [identity.server_id]
        ).fetchone()
        expected = (identity.store_id, identity.database_uuid, identity.schema_revision,
                    identity.generation, identity.process_birth_id)
        if row is None or tuple(row[index] for index in range(5)) != expected:
            raise RuntimeError("remote owner identity does not match the published native identity")
        task_count = int(connection.execute("SELECT count(*) FROM tasks").fetchone()[0])
        rollback_checked = False
        if exercise_rollback:
            sample_id = "paper-readiness:" + uuid.uuid4().hex
            connection.execute("BEGIN TRANSACTION")
            try:
                connection.execute(
                    "INSERT INTO health_samples(sample_id, subject_kind, subject_id, observed_at, status, body_json) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    [sample_id, "paper-owner-readiness", identity.server_id, _now(), "before", "{}"],
                )
                connection.execute("UPDATE health_samples SET status = ? WHERE sample_id = ?", ["after", sample_id])
                observed = connection.execute("SELECT status FROM health_samples WHERE sample_id = ?", [sample_id]).fetchone()
                if observed is None or observed[0] != "after":
                    raise RuntimeError("remote transaction did not observe its own update")
            finally:
                connection.execute("ROLLBACK")
            absent = connection.execute("SELECT count(*) FROM health_samples WHERE sample_id = ?", [sample_id]).fetchone()[0]
            if absent != 0:
                raise RuntimeError("remote rollback did not remove readiness-only health sample")
            independent = connect(identity.listen_uri, token=token)
            try:
                if independent.execute("SELECT count(*) FROM health_samples WHERE sample_id = ?", [sample_id]).fetchone()[0] != 0:
                    raise RuntimeError("independent remote connection observed rolled-back readiness sample")
            finally:
                independent.close()
            rollback_checked = True
        result = {"network_query": True, "identity_checked": True, "task_count": task_count,
                  "rollback_checked": rollback_checked, "checked_at": _now()}
        server._vault.assert_absent_from(result, surface_name="paper remote readiness")
        return result
    finally:
        connection.close()


def serve(database, state_dir, store_id, secret_handle, port=0):
    database, state_dir = Path(database).expanduser().resolve(), Path(state_dir).expanduser().resolve()
    if not database.is_file():
        raise ValueError("materialize the paper database before starting its owner")
    state_dir.mkdir(parents=True, exist_ok=True)
    state_dir.chmod(0o700)
    build_server, ServerLifecycle, _ = _native()
    server = build_server(database_path=database, state_dir=state_dir,
                          host="127.0.0.1", port=int(port), store_id=store_id,
                          secret_handle=secret_handle, allow_experimental=False,
                          connection_factory=_owner_connection)
    ready_path = state_dir / READY_FILENAME
    stop_requested = False
    def stop(_signum, _frame):
        nonlocal stop_requested
        stop_requested = True
    previous = {sig: signal.signal(sig, stop) for sig in (signal.SIGINT, signal.SIGTERM)}
    public = {"schema": "paper-quack-owner/v1", "ready": False, "database": str(database),
              "state_dir": str(state_dir), "checked_at": _now()}
    started = False
    try:
        identity = server.start()
        started = True
        server.ready()
        probe = remote_readiness(server)
        public.update({"ready": True, "quack_endpoint": identity.listen_uri,
                       "endpoint_secret_handle": identity.secret_handle,
                       "store_id": identity.store_id, "store_generation": str(identity.generation),
                       "schema_revision": str(identity.schema_revision),
                       "identity": identity.to_dict(), "remote_probe": probe,
                       "checked_at": _now()})
        server._vault.assert_absent_from(public, surface_name="paper public readiness")
        _atomic_json(ready_path, public)
        print(json.dumps(public, sort_keys=True), flush=True)
        last_remote_check = time.monotonic()
        while server.lifecycle is ServerLifecycle.READY and not stop_requested:
            if server.stop_control_path().is_file():
                break
            if time.monotonic() - last_remote_check >= 5:
                server.ready()
                health = remote_readiness(server, exercise_rollback=False)
                public["remote_health"] = health
                public["checked_at"] = health["checked_at"]
                _atomic_json(ready_path, public)
                last_remote_check = time.monotonic()
            time.sleep(0.25)
        return 0
    except BaseException as exc:
        # Bound diagnostics do not include query text or credentials.
        public.update({"ready": False, "error_type": type(exc).__name__, "checked_at": _now()})
        if started:
            _atomic_json(ready_path, public)
        raise
    finally:
        try:
            if started:
                server.stop()
                public.update({"ready": False, "stopped": True, "checked_at": _now()})
                _atomic_json(ready_path, public)
        finally:
            for sig, handler in previous.items():
                signal.signal(sig, handler)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--state-dir", type=Path, required=True)
    parser.add_argument("--store-id", required=True)
    parser.add_argument("--secret-handle", required=True)
    parser.add_argument("--port", type=int, default=0)
    args = parser.parse_args()
    return serve(args.database, args.state_dir, args.store_id, args.secret_handle, args.port)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"paper state owner failed: {type(exc).__name__}", file=sys.stderr)
        raise SystemExit(1)

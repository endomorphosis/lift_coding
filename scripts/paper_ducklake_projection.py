#!/usr/bin/env python3
"""Project owner-fetched Quack snapshots into a genuine, non-authoritative DuckLake.

The campaign monitor owns Quack reads and atomically writes the input JSON. This
process never opens the live state database and never grants task/lease authority.
It uses the native board control plane for task and immutable artifact projection.

Input schema::

  {"schema": "vericodegen-quack-snapshot/v1", "transport": "quack",
   "fetched_at": "2026-09-11T17:00:00+00:00", "boards": [
     {"paper_id": "autoformalization",
      "board_namespace": "vericodegen-2026-autoformalization",
      "store_identity": {"database_uuid": "..."},
      "store_generation": {"generation": 1},
      "tasks": [...], "goals": [...], "events": [...], "artifacts": []}, ...]}

All three paper boards are required. ``artifacts`` and ``store_generation`` are
optional. Tasks and goals must have stable IDs; events must have event_cid,
event_id, id, or sequence. The monitor must actually fetch records through Quack;
a JSON transport label alone is not a cryptographic attestation of that fact.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from collections.abc import Mapping
from datetime import datetime, timezone
from pathlib import Path
import signal
import sys
import time
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PAPERS = ("autoformalization", "law_to_action", "neurosymbolic_supervision")
SNAPSHOT_SCHEMA = "vericodegen-quack-snapshot/v1"
STATUS_SCHEMA = "vericodegen-ducklake-projection/v1"
MAX_SNAPSHOT_BYTES = 64 * 1024 * 1024
MAX_TASKS_PER_BOARD = 8_192
MAX_RECORDS_PER_BOARD = 100_000


class ProjectionError(ValueError):
    pass


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                      allow_nan=False)


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def parse_time(value: Any) -> datetime:
    try:
        result = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError) as exc:
        raise ProjectionError("fetched_at must be an ISO8601 timestamp") from exc
    if result.tzinfo is None:
        raise ProjectionError("fetched_at must include a timezone")
    return result


def record_id(record: Mapping[str, Any], kind: str) -> str:
    keys = {"task": ("task_id", "id", "task_alias", "task_cid"),
            "goal": ("goal_id", "id", "goal_alias", "goal_cid"),
            "event": ("event_cid", "event_id", "id", "sequence"),
            "artifact": ("artifact_cid", "artefact_id", "artifact_id", "cid", "id")}[kind]
    for key in keys:
        value = record.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
    raise ProjectionError(f"{kind} record has no stable identifier")


def validate_snapshot(snapshot: Any) -> dict[str, Any]:
    if not isinstance(snapshot, dict) or snapshot.get("schema") != SNAPSHOT_SCHEMA:
        raise ProjectionError(f"snapshot schema must be {SNAPSHOT_SCHEMA}")
    if snapshot.get("transport") != "quack":
        raise ProjectionError("snapshot must declare the actual owner-fetch transport quack")
    fetched = parse_time(snapshot.get("fetched_at"))
    if (fetched - datetime.now(timezone.utc)).total_seconds() > 300:
        raise ProjectionError("fetched_at is more than five minutes in the future")
    boards = snapshot.get("boards")
    if not isinstance(boards, list) or len(boards) != len(PAPERS):
        raise ProjectionError("snapshot must contain exactly the three paper boards")
    seen: set[str] = set()
    for board in boards:
        if not isinstance(board, dict):
            raise ProjectionError("each board must be an object")
        paper = board.get("paper_id")
        if paper not in PAPERS or paper in seen:
            raise ProjectionError("unknown or duplicate paper_id")
        seen.add(paper)
        if board.get("board_namespace") != f"vericodegen-2026-{paper}":
            raise ProjectionError(f"wrong board_namespace for {paper}")
        identity = board.get("store_identity")
        if not isinstance(identity, dict) or not identity or not any(
            str(identity.get(key) or "").strip()
            for key in ("database_uuid", "store_id", "state_db_uuid", "database_id")
        ):
            raise ProjectionError(f"{paper}: real store_identity/database_uuid is required")
        if "store_generation" in board and not isinstance(board["store_generation"], dict):
            raise ProjectionError(f"{paper}: store_generation must be an object")
        for plural, kind in (("tasks", "task"), ("goals", "goal"),
                             ("events", "event"), ("artifacts", "artifact")):
            records = board.get(plural, [] if plural == "artifacts" else None)
            if not isinstance(records, list) or any(not isinstance(r, dict) for r in records):
                raise ProjectionError(f"{paper}: {plural} must be a list of objects")
            maximum = MAX_TASKS_PER_BOARD if plural == "tasks" else MAX_RECORDS_PER_BOARD
            if len(records) > maximum:
                raise ProjectionError(f"{paper}: {plural} exceeds bounded row limit")
            identifiers: set[str] = set()
            for record in records:
                identifier = record_id(record, kind)
                if identifier in identifiers:
                    raise ProjectionError(f"{paper}: duplicate {kind} identifier")
                identifiers.add(identifier)
    canonical(snapshot)  # Reject NaN/Infinity and non-JSON records before any writes.
    return snapshot


def load_snapshot(path: Path) -> dict[str, Any]:
    with path.open("rb") as handle:
        raw = handle.read(MAX_SNAPSHOT_BYTES + 1)
    if len(raw) > MAX_SNAPSHOT_BYTES:
        raise ProjectionError("snapshot exceeds 64 MiB limit")
    return validate_snapshot(json.loads(raw))


def native_open():
    for path in (ROOT / "external/ipfs_accelerate", ROOT / "external/ipfs_datasets"):
        if str(path) not in sys.path:
            sys.path.insert(0, str(path))
    from ipfs_accelerate_py.agent_supervisor.task_sources.board_control_plane import (
        open_board_control_plane,
    )
    return open_board_control_plane


def require_ducklake(plane: Any) -> dict[str, Any]:
    if not plane.ducklake_loaded or not plane.ducklake_attached or not plane.quack_loaded:
        raise ProjectionError("native control plane did not load Quack and attach DuckLake; plain DuckDB fallback is forbidden")
    connection = plane._conn()
    databases = connection.execute(
        "SELECT database_name, type, path FROM duckdb_databases() WHERE database_name = 'lake'"
    ).fetchall()
    if len(databases) != 1 or str(databases[0][1]).lower() != "ducklake":
        raise ProjectionError("catalog lake is not an actual DuckLake catalog")
    extensions = connection.execute(
        "SELECT extension_name, extension_version FROM duckdb_extensions() "
        "WHERE loaded AND extension_name IN ('ducklake', 'quack') ORDER BY extension_name"
    ).fetchall()
    if {str(row[0]) for row in extensions} != {"ducklake", "quack"}:
        raise ProjectionError("both actual DuckLake and Quack extensions must be loaded")
    return {"catalog": "lake", "catalog_type": str(databases[0][1]),
            "catalog_path": str(databases[0][2]),
            "extension_versions": {str(row[0]): str(row[1]) for row in extensions}}


def projected_artifacts(snapshot: Mapping[str, Any]):
    """Stable event identity detects rewrites; content IDs preserve changing state."""
    for board in snapshot["boards"]:
        namespace = board["board_namespace"]
        identity = board["store_identity"]
        # Only durable database identity scopes immutable events. Mutable generation
        # revisions and fetched_at must not turn a rewritten event into a new event.
        store_id = next(str(identity[k]) for k in
                        ("database_uuid", "store_id", "state_db_uuid", "database_id")
                        if identity.get(k))
        store_key = digest(store_id)
        for plural, kind in (("tasks", "task"), ("goals", "goal"),
                             ("events", "event"), ("artifacts", "artifact")):
            for record in board.get(plural, []):
                identity_key = digest(record_id(record, kind))
                payload = {"record_kind": kind, "source_transport": "quack",
                           "authoritative": False, "store_id": store_id,
                           "record": record}
                suffix = identity_key if kind == "event" else digest(payload)
                yield namespace, f"{kind}:{store_key}:{suffix}", payload
        payload = {"record_kind": "owner_snapshot", "source_transport": "quack",
                   "authoritative": False, "fetched_at": snapshot["fetched_at"],
                   "store_identity": identity,
                   "store_generation": board.get("store_generation", {}),
                   "source_snapshot_sha256": digest(snapshot),
                   "board_payload_sha256": digest(board),
                   "counts": {k: len(board.get(k, [])) for k in
                              ("tasks", "goals", "events", "artifacts")}}
        yield namespace, f"owner_snapshot:{digest(payload)}", payload


def existing_artifact(plane: Any, namespace: str, artifact_id: str):
    row = plane._conn().execute(
        "SELECT payload_json FROM artefact_generic WHERE board_namespace = ? "
        "AND kind = 'other' AND artefact_id = ?", [namespace, artifact_id]
    ).fetchone()
    return None if row is None else json.loads(str(row[0]))


def project_snapshot(snapshot: dict[str, Any], lake_root: Path, *,
                     repo_root: Path = ROOT, source_path: Path | None = None,
                     opener=None) -> dict[str, Any]:
    validate_snapshot(snapshot)
    artifacts = list(projected_artifacts(snapshot))
    open_plane = opener or native_open()
    with open_plane(repo_root, root=lake_root) as plane:
        engine = require_ducklake(plane)
        # Check all immutable identities before replacing any current task state.
        new_artifacts = []
        for namespace, artifact_id, payload in artifacts:
            old = existing_artifact(plane, namespace, artifact_id)
            if old is not None and canonical(old) != canonical(payload):
                raise ProjectionError("immutable event/artifact identity has conflicting content")
            if old is None:
                new_artifacts.append((namespace, artifact_id, payload))
        for board in snapshot["boards"]:
            tasks = [dict(record, task_id=record_id(record, "task"))
                     for record in board["tasks"]]
            plane.register_board(
                board["board_namespace"], source_path=source_path,
                source_kind="quack-owner-snapshot", tasks=tasks,
                extra={"authoritative": False, "source_transport": "quack",
                       "store_identity": board["store_identity"],
                       "store_generation": board.get("store_generation", {}),
                       "fetched_at": snapshot["fetched_at"],
                       "source_snapshot_sha256": digest(snapshot)},
            )
            require_ducklake(plane)  # register_board calls the native projection.
        for namespace, artifact_id, payload in new_artifacts:
            plane.put_artefact("other", board_namespace=namespace,
                               artefact_id=artifact_id, payload=payload)
        plane.aggregate_boards()
        engine = require_ducklake(plane)  # Native API can silently drop attached flag.
        connection = plane._conn()
        counts: dict[str, Any] = {}
        for board in snapshot["boards"]:
            namespace = board["board_namespace"]
            task_count = int(connection.execute(
                "SELECT COUNT(*) FROM lake.board_tasks WHERE board_namespace = ?",
                [namespace],
            ).fetchone()[0])
            board_count = int(connection.execute(
                "SELECT COUNT(*) FROM lake.board_catalog WHERE board_namespace = ?",
                [namespace],
            ).fetchone()[0])
            if task_count != len(board["tasks"]) or board_count != 1:
                raise ProjectionError("DuckLake task/board row count does not match input snapshot")
            rows = connection.execute(
                "SELECT json_extract_string(payload_json, '$.record_kind'), COUNT(*) "
                "FROM lake.artefact_generic WHERE board_namespace = ? AND kind = 'other' "
                "GROUP BY 1 ORDER BY 1", [namespace],
            ).fetchall()
            counts[board["paper_id"]] = {"board_namespace": namespace,
                "board_rows": board_count, "current_task_rows": task_count,
                "artifact_rows_by_kind": {str(r[0]): int(r[1]) for r in rows},
                "input_goal_count": len(board["goals"]),
                "input_event_count": len(board["events"])}
        # Verify payload equality in the actual lake, including previously stored events.
        for namespace, artifact_id, payload in artifacts:
            row = connection.execute(
                "SELECT payload_json FROM lake.artefact_generic WHERE board_namespace = ? "
                "AND kind = 'other' AND artefact_id = ?", [namespace, artifact_id],
            ).fetchone()
            if row is None or canonical(json.loads(str(row[0]))) != canonical(payload):
                raise ProjectionError("actual DuckLake artifact projection is missing or differs")
        snapshot_id = connection.execute("SELECT * FROM ducklake_current_snapshot('lake')").fetchone()[0]
        snapshot_count = int(connection.execute(
            "SELECT COUNT(*) FROM ducklake_snapshots('lake')"
        ).fetchone()[0])
        return {"schema": STATUS_SCHEMA, "ok": True, "authoritative": False,
                "paper_benchmark_evidence": False,
                "source_transport": "quack", "fetch_verification": "owner_snapshot_provenance",
                "source_snapshot_sha256": digest(snapshot),
                "source_fetched_at": snapshot["fetched_at"],
                "source_age_seconds": max(0, (datetime.now(timezone.utc) -
                                              parse_time(snapshot["fetched_at"])).total_seconds()),
                "projected_at": utc_now(), "ducklake": engine,
                "lake_snapshot_id": int(snapshot_id), "lake_snapshot_count": snapshot_count,
                "new_immutable_artifacts": len(new_artifacts), "boards": counts}


def write_status(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        with temporary.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True, allow_nan=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", required=True, type=Path)
    parser.add_argument("--root", required=True, type=Path, help="dedicated DuckLake projection directory")
    parser.add_argument("--repo-root", default=ROOT, type=Path)
    parser.add_argument("--status", type=Path, help="default: ROOT/projection-status.json")
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--interval", type=float, default=15.0)
    args = parser.parse_args(argv)
    if not 1 <= args.interval <= 60:
        parser.error("--interval must be between 1 and 60 seconds")
    status_path = args.status or args.root / "projection-status.json"
    stop = False
    def request_stop(_signum, _frame):
        nonlocal stop
        stop = True
    signal.signal(signal.SIGTERM, request_stop)
    signal.signal(signal.SIGINT, request_stop)
    previous_digest = None
    last_success = None
    while not stop:
        try:
            snapshot = load_snapshot(args.snapshot)
            current_digest = digest(snapshot)
            if current_digest != previous_digest or args.once:
                status = project_snapshot(snapshot, args.root, repo_root=args.repo_root,
                                          source_path=args.snapshot)
                write_status(status_path, status)
                print(canonical(status), flush=True)
                previous_digest = current_digest
                last_success = status
            elif last_success:
                status = dict(last_success, observed_at=utc_now(),
                              source_age_seconds=max(0, (datetime.now(timezone.utc) -
                                   parse_time(snapshot["fetched_at"])).total_seconds()))
                write_status(status_path, status)
            if args.once:
                return 0
        except Exception as exc:
            error = {"schema": STATUS_SCHEMA, "ok": False, "authoritative": False,
                     "paper_benchmark_evidence": False, "observed_at": utc_now(),
                     "error_type": type(exc).__name__, "error": str(exc),
                     "last_success_at": (last_success or {}).get("projected_at")}
            write_status(status_path, error)
            print(canonical(error), file=sys.stderr, flush=True)
            if args.once:
                return 1
        deadline = time.monotonic() + args.interval
        while not stop and time.monotonic() < deadline:
            time.sleep(min(0.5, max(0.0, deadline - time.monotonic())))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

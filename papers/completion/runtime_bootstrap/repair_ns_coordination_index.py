"""Repair only the independently diagnosed NS readiness index; default is rehearsal.

Run with the campaign DuckDB 1.5.5 Python. --apply requires the exact paused
database/WAL baseline. DuckDB performs WAL replay/checkpoint; this utility never
deletes a WAL or changes a task, claim, completion, fence, or event row.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import tempfile

import duckdb

ROOT = Path.home() / ".local/state/ipfs_accelerate_py/vericodegen-2026"
BASELINE = ROOT / ".maintenance_backups/ns-coordination-20260911T165817Z"
LIVE = ROOT / "neurosymbolic_supervision"
EXPECTED = {
    "control.coordination.duckdb": "a37bc0c71dfb5fb633577d3c5d35773db53c4e3ed1fcc00d3094bf411ac91cb2",
    "control.coordination.duckdb.wal": "b20cdca404e0d39db868df89669f347acc1e1ab8ddd09381fed214fe668d561e",
}
INDEX = "coordination_tasks_ready_idx"
INDEX_SQL = "CREATE INDEX coordination_tasks_ready_idx ON coordination_tasks(ready, registered_at_ms, task_cid);"


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def verify_files(directory):
    result = {}
    for name, expected in EXPECTED.items():
        path = directory / name
        assert path.resolve(strict=True) == path, "Database path has a symlink"
        info = path.lstat()
        assert stat.S_ISREG(info.st_mode) and info.st_uid == os.geteuid()
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        assert actual == expected, f"Unexpected baseline bytes: {path}"
        result[name] = actual
    return result


def require_quiescence():
    targets = {str(LIVE / name) for name in EXPECTED}
    targets.add(str(LIVE / "control.execution.duckdb"))
    handles = []
    inaccessible = []
    for process in Path("/proc").iterdir():
        if not process.name.isdigit():
            continue
        try:
            if process.stat().st_uid != os.geteuid():
                continue
            descriptors = list((process / "fd").iterdir())
        except FileNotFoundError:
            continue
        except PermissionError:
            # Same-UID sshd sessions can deny fd observation. They cannot
            # silently bypass the exclusive kernel lock acquired below.
            command = (process / "cmdline").read_bytes()
            assert b"neurosymbolic_supervision" not in command, "Unobservable NS process"
            inaccessible.append(int(process.name))
            continue
        for descriptor in descriptors:
            try:
                target = os.readlink(descriptor)
            except FileNotFoundError:
                continue
            except PermissionError:
                command = (process / "cmdline").read_bytes()
                assert b"neurosymbolic_supervision" not in command, "Unobservable NS process"
                inaccessible.append(int(process.name))
                break
            if target.removesuffix(" (deleted)") in targets:
                handles.append({"pid": int(process.name), "fd": descriptor.name, "path": target})
    assert not handles, f"NS coordination/execution database still open: {handles}"
    return {"matching_handles": handles, "inaccessible_non_ns_processes": inaccessible}


def snapshot(connection):
    result = {}
    for (table,) in connection.execute("SHOW TABLES").fetchall():
        assert table.replace("_", "").isalnum()
        rows = connection.execute(f'SELECT * FROM "{table}" ORDER BY ALL').fetchall()
        result[table] = {"rows": len(rows), "sha256": digest(rows)}
    result["schema"] = {
        "tables": connection.execute("SELECT table_name,sql FROM duckdb_tables() ORDER BY table_name").fetchall(),
        "indexes": connection.execute("SELECT index_name,sql FROM duckdb_indexes() ORDER BY index_name").fetchall(),
    }
    return result


def rebuild(connection):
    index = connection.execute(
        "SELECT table_name,is_unique,sql FROM duckdb_indexes() WHERE index_name=?", [INDEX]
    ).fetchall()
    assert index == [("coordination_tasks", False, INDEX_SQL)], "Unexpected index definition"
    before = snapshot(connection)
    connection.execute("CHECKPOINT")
    connection.execute("BEGIN TRANSACTION")
    try:
        connection.execute(f"DROP INDEX {INDEX}")
        connection.execute(INDEX_SQL)
        connection.execute("COMMIT")
    except BaseException:
        connection.execute("ROLLBACK")
        raise
    after = snapshot(connection)
    assert before == after, "Index rebuild changed logical data or schema"
    connection.execute("CHECKPOINT")
    return before, after


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    assert not args.report.exists(), "Never overwrite a repair audit"
    assert duckdb.__version__ == "1.5.5", "Use the qualified campaign DuckDB runtime"
    baseline_hashes = verify_files(BASELINE)
    if args.apply:
        handles = require_quiescence()
        original_hashes = verify_files(LIVE)
        directory = LIVE
    else:
        handles = None
        directory = Path(tempfile.mkdtemp(prefix="ns-index-utility-rehearsal-"))
        for name in EXPECTED:
            shutil.copy2(BASELINE / name, directory / name)
        original_hashes = verify_files(directory)
    report = {
        "schema": "paper-ns-exact-index-repair/v1", "apply": args.apply,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "database": str(directory / "control.coordination.duckdb"),
        "baseline": str(BASELINE), "baseline_hashes": baseline_hashes,
        "original_hashes": original_hashes, "open_handles_before": handles,
        "duckdb_version": duckdb.__version__, "sql": ["CHECKPOINT", "BEGIN TRANSACTION",
            f"DROP INDEX {INDEX}", INDEX_SQL, "COMMIT", "CHECKPOINT"],
        "paper_completion_attempted": False,
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    # Persist the exact admission before opening a live database.
    args.report.write_text(json.dumps(report, indent=2) + "\n")
    # DuckDB also takes a kernel file lock. Acquire the same POSIX writer
    # exclusion first so inaccessible foreign fd tables are not an admission
    # bypass; keep this fd open until the DuckDB connection has closed.
    with Path(report["database"]).open("r+b") as guard:
        fcntl.lockf(guard, fcntl.LOCK_EX | fcntl.LOCK_NB)
        assert hashlib.file_digest(guard, "sha256").hexdigest() == EXPECTED["control.coordination.duckdb"]
        assert hashlib.sha256((directory / "control.coordination.duckdb.wal").read_bytes()).hexdigest() == EXPECTED["control.coordination.duckdb.wal"]
        connection = duckdb.connect(report["database"])
        try:
            before, after = rebuild(connection)
        finally:
            connection.close()
    assert verify_files(BASELINE) == baseline_hashes, "Immutable backup changed"
    report.update({
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "logical_before": before, "logical_after": after,
        "logical_before_sha256": digest(before), "logical_after_sha256": digest(after),
        "all_rows_and_schema_unchanged": before == after,
        "database_sha256_after": hashlib.sha256(Path(report["database"]).read_bytes()).hexdigest(),
        "wal_exists_after_duckdb_checkpoint": (directory / "control.coordination.duckdb.wal").exists(),
        "completed": True,
    })
    args.report.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({key: value for key, value in report.items()
                      if key not in {"logical_before", "logical_after"}}, indent=2))


if __name__ == "__main__":
    main()

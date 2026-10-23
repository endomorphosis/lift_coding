"""Bounded source-only native CodebaseIR preparation and fresh owner replay.

The resulting artifacts establish structural provenance only. The caller must
provide a separate Git repository and keep all output outside its source tree.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from dataclasses import replace
import hashlib
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess
from typing import Iterator

SCHEMA = "terminal-native-structural-ir@1"
MAX_SOURCES = 5
MAX_FILE_BYTES = 8192
MAX_TOTAL_SOURCE_BYTES = MAX_SOURCES * MAX_FILE_BYTES
MAX_ARTIFACT_BYTES = 16 * 1024 * 1024
MEMORY_MB = 256
CLAIMS = {
    "authority": "structural_only", "proof_authority": False,
    "source_runtime_semantics_verified": False,
    "source_model_equivalence_proved": False,
    "full_task_satisfaction_proved": False, "convergence_proved": False,
    "source_body_execution": False, "formalized_properties": 0,
    "checked_properties": 0,
}


class StructuralIRGuardError(ValueError):
    """The caller's isolated source or expected artifact scope is invalid."""


def _json_bytes(value: dict) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False).encode("ascii")


def _expected_sources(value: dict) -> dict[str, str]:
    if type(value) is not dict or not 1 <= len(value) <= MAX_SOURCES:
        raise StructuralIRGuardError("expected_sources must name one to five source files")
    copied = {}
    for name, digest in value.items():
        if type(name) is not str:
            raise StructuralIRGuardError("source paths must be canonical relative Python paths")
        path = PurePosixPath(name)
        if (path.is_absolute() or path.as_posix() != name or ".." in path.parts
                or any(part in {"", ".", ".git"} for part in path.parts)
                or not name.endswith(".py") or any(ord(c) < 32 for c in name)):
            raise StructuralIRGuardError("source paths must be canonical relative Python paths")
        if type(digest) is not str or re.fullmatch(r"[0-9a-f]{64}", digest) is None:
            raise StructuralIRGuardError("source SHA256 must be canonical lowercase hexadecimal")
        copied[name] = digest
    return dict(sorted(copied.items()))


def _git(repository: Path, *args: str) -> bytes:
    result = subprocess.run(["git", "-C", str(repository), *args],
                            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, timeout=10, check=False)
    if result.returncode or result.stderr:
        raise StructuralIRGuardError("isolated repository Git observation failed")
    if len(result.stdout) > 64 * 1024:
        raise StructuralIRGuardError("Git observation exceeds finite scope")
    return result.stdout


def _guard_repository(repository: Path, output: Path, sources: dict) -> None:
    if not repository.is_dir() or repository.is_symlink():
        raise StructuralIRGuardError("repository must be its own real directory")
    git_root = Path(os.fsdecode(_git(repository, "rev-parse", "--show-toplevel")).strip()).resolve()
    if git_root != repository:
        raise StructuralIRGuardError("repository must be its own Git root; enclosing-root scans refused")
    if repository == output or repository in output.parents or output in repository.parents:
        raise StructuralIRGuardError("output and source repositories must have separate scope")
    _git(repository, "rev-parse", "--verify", "HEAD")
    observed = _git(repository, "ls-files", "-z", "--cached", "--others", "--exclude-standard")
    paths = [os.fsdecode(item) for item in observed.split(b"\x00") if item]
    if len(paths) != len(set(paths)) or set(paths) != set(sources):
        raise StructuralIRGuardError("Git source inventory differs from the explicit allowlist")
    # Metadata checks precede native admission, but no source body is read here.
    for name in sources:
        source = repository / name
        for parent in source.parents:
            if parent == repository:
                break
            if parent.is_symlink():
                raise StructuralIRGuardError("source parent is a symlink")
        metadata = source.lstat()
        if (not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1
                or metadata.st_size > MAX_FILE_BYTES):
            raise StructuralIRGuardError("source must be single-link regular bounded file")


def _configuration_prefix(path: Path) -> dict:
    """Read only the leading native config, without reading lease/token bodies.

    Native scheduler writers sort JSON keys, placing config first. Anything
    else is refused rather than discovering fields through another state body.
    The native constructor subsequently owns full state/schema validation.
    """
    from ipfs_datasets_py.optimizers.logic_theorem_optimizer.resource_scheduler import ResourceConfigurationError
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        before = os.fstat(descriptor)
        if (not stat.S_ISREG(before.st_mode) or before.st_nlink != 1
                or before.st_size > 16 * 1024 * 1024):
            raise ResourceConfigurationError("shared scheduler configuration input is not bounded regular state")
        consumed = 0
        def byte():
            nonlocal consumed
            consumed += 1
            if consumed > 64 * 1024:
                raise ResourceConfigurationError("shared scheduler configuration prefix exceeds bound")
            result = os.read(descriptor, 1)
            if not result:
                raise ResourceConfigurationError("shared scheduler configuration prefix incomplete")
            return result
        def nonspace():
            value = byte()
            while value in (b" ", b"\t", b"\r", b"\n"):
                value = byte()
            return value
        if nonspace() != b"{":
            raise ResourceConfigurationError("shared scheduler configuration prefix malformed")
        if nonspace() != b'"' or b"".join(byte() for _ in range(7)) != b'config"':
            raise ResourceConfigurationError("shared scheduler must have the native leading config object")
        if nonspace() != b":" or nonspace() != b"{":
            raise ResourceConfigurationError("shared scheduler configuration object malformed")
        body = bytearray(b"{")
        depth, quoted, escaped = 1, False, False
        while depth:
            value = byte()
            body.extend(value)
            if quoted:
                if escaped:
                    escaped = False
                elif value == b"\\":
                    escaped = True
                elif value == b'"':
                    quoted = False
            elif value == b'"':
                quoted = True
            elif value in (b"{", b"["):
                depth += 1
            elif value in (b"}", b"]"):
                depth -= 1
        after = os.fstat(descriptor)
        witness = lambda item: (item.st_dev, item.st_ino, item.st_size,
                                item.st_mtime_ns, item.st_ctime_ns)
        if witness(before) != witness(after):
            raise ResourceConfigurationError("shared scheduler configuration changed while read")
        def unique(pairs):
            result = {}
            for name, value in pairs:
                if name in result:
                    raise ResourceConfigurationError("duplicate shared scheduler configuration field")
                result[name] = value
            return result
        def constant(_):
            raise ResourceConfigurationError("nonfinite shared scheduler configuration")
        try:
            result = json.loads(body, object_pairs_hook=unique, parse_constant=constant)
        except (ValueError, UnicodeError, RecursionError) as error:
            raise ResourceConfigurationError("shared scheduler configuration is invalid JSON") from error
        if type(result) is not dict:
            raise ResourceConfigurationError("shared scheduler configuration must be an object")
        return result
    finally:
        os.close(descriptor)


def _conservative_existing_config(safe, stored: dict):
    """Preserve exact stored capacities only inside the newly observed envelope."""
    from ipfs_datasets_py.optimizers.logic_theorem_optimizer.resource_scheduler import ResourceConfigurationError
    baseline = safe.persisted_dict()
    def need(condition, message):
        if not condition:
            raise ResourceConfigurationError(message)
    need(type(stored) is dict and set(stored) == set(baseline),
         "unknown or incomplete shared scheduler configuration")
    need(stored["proof_safety_enabled"] is True, "shared scheduler proof safety is disabled")
    # The matching copied policy knows these fields, but this experiment never
    # enables recovery grants or an operator profile from persisted data.
    recovery_fields = {"proof_resource_profile", "proof_recovery_enabled",
        "proof_recovery_samples", "proof_recovery_interval_seconds", "proof_recovery_grants"}
    need(recovery_fields <= set(baseline), "matching native scheduler policy version required")
    need(stored["proof_resource_profile"] is None and stored["proof_recovery_enabled"] is False,
         "shared scheduler recovery or nondefault proof profile is outside the admitted policy")
    need(type(stored["proof_recovery_samples"]) is int and stored["proof_recovery_samples"] == 2
         and type(stored["proof_recovery_grants"]) is int and stored["proof_recovery_grants"] == 4
         and type(stored["proof_recovery_interval_seconds"]) is float
         and stored["proof_recovery_interval_seconds"] == 0.25,
         "shared scheduler inactive recovery parameters differ from the admitted native defaults")
    for name in ("total_cpu_slots", "total_memory_mb", "total_child_process_slots"):
        need(type(stored[name]) is int and 0 < stored[name] <= baseline[name],
             "shared scheduler capacity exceeds current conservative host envelope")
    for name in ("total_gpu_memory_mb", "total_unified_memory_mb"):
        value, ceiling = stored[name], baseline[name]
        need(value is None or (type(value) is int and ceiling is not None and 0 < value <= ceiling),
             "shared scheduler accelerator capacity is unknown or exceeds safe envelope")
    for name in ("reserved_memory_mb", "reserved_gpu_memory_mb", "proof_memory_headroom_mb"):
        need(type(stored[name]) is int and stored[name] >= baseline[name],
             "shared scheduler memory reservation or headroom is weaker than safe envelope")
    for name in ("proof_memory_stall_percent", "proof_cpu_stall_percent", "proof_io_stall_percent"):
        need(type(stored[name]) in {int, float} and math.isfinite(stored[name])
             and 0 <= stored[name] <= baseline[name],
             "shared scheduler pressure guard is weaker than safe envelope")
    for name in ("max_memory_percent", "max_swap_percent", "max_gpu_memory_percent"):
        value, ceiling = stored[name], baseline[name]
        need((value is None and ceiling is None) or (type(value) in {int, float}
             and math.isfinite(value) and 0 <= value <= 100
             and (ceiling is None or value <= ceiling)),
             "shared scheduler pressure percentage guard is weaker than safe envelope")
    need(type(stored["proof_backoff_seconds"]) in {int, float}
         and math.isfinite(stored["proof_backoff_seconds"])
         and stored["proof_backoff_seconds"] >= baseline["proof_backoff_seconds"],
         "shared scheduler proof backoff is weaker than safe envelope")
    need(type(stored["max_waiting_requests"]) is int
         and 0 < stored["max_waiting_requests"] <= baseline["max_waiting_requests"],
         "shared scheduler waiting request bound is weaker than safe envelope")
    need(stored["require_known_gpu_for_gpu_work"] is True,
         "shared scheduler permits unknown accelerator authority")
    candidate = replace(safe, **stored)
    candidate.validate()
    need(_json_bytes(candidate.persisted_dict()) == _json_bytes(stored),
         "shared scheduler configuration does not preserve exact native dimensions")
    # replace preserves the genuine sampler, lease renewal and all native
    # admission methods; persisted data supplies no sampler or authority token.
    return candidate


def _construct_existing_scheduler(config):
    from ipfs_datasets_py.optimizers.logic_theorem_optimizer.resource_scheduler import (
        GlobalResourceScheduler, ResourceConfigurationError,
    )
    class AttachOnlyScheduler(GlobalResourceScheduler):
        def _new_state(self):
            raise ResourceConfigurationError("existing shared scheduler state disappeared; creation refused")

        def _validate_state_configuration(self, state, *, allow_reconfigure=False):
            # The native constructor re-locks and re-reads the same state. Its
            # ordinary strict equality path is used even during construction;
            # an idle racing pool can never be reset to our earlier projection.
            return super()._validate_state_configuration(state, allow_reconfigure=False)
    return AttachOnlyScheduler(config)


def _safe_scheduler_config():
    from ipfs_datasets_py.optimizers.logic_theorem_optimizer.resource_scheduler import ResourceSchedulerConfig
    return ResourceSchedulerConfig.for_proof_host()


def _scheduler():
    # Use precisely the native global default path. Persisted configuration is
    # an attachment hint checked against real host resources, never admission.
    # A missing, unsafe or racing state retains native refusal; no new pool.
    safe = _safe_scheduler_config()
    stored = _configuration_prefix(Path(safe.state_path).expanduser().resolve())
    config = _conservative_existing_config(safe, stored)
    return _construct_existing_scheduler(config)


@contextmanager
def _owner(output: Path, *, existing: bool = False) -> Iterator:
    import duckdb
    from ipfs_datasets_py.duckdb_control.codebase_catalog import (
        CodebaseCatalog, CodebaseCatalogLimits,
    )
    from ipfs_datasets_py.logic.software_contracts.cache import ImmutableCAS
    from ipfs_datasets_py.logic.software_contracts.codebase_ir import RepositoryCodebaseIndex
    from ipfs_datasets_py.logic.software_contracts.duckdb_ast_store import DuckDBASTStore
    from ipfs_datasets_py.logic.software_contracts.duckdb_ingest import DuckDBASTIngestor

    if existing and (not (output / "structural.duckdb").is_file()
                     or not (output / "cas").is_dir()):
        raise StructuralIRGuardError("existing native database and CAS owner are required")
    temp = output / "duckdb-temp"
    if not existing:
        temp.mkdir()
    elif not temp.is_dir():
        raise StructuralIRGuardError("existing explicit native temporary directory required")
    connection = duckdb.connect(str(output / "structural.duckdb"), config={
        "threads": "1", "memory_limit": "128MB",
        "max_temp_directory_size": "128MB", "temp_directory": str(temp),
    })
    try:
        # Apply after connection configuration: native DuckDB otherwise refuses
        # its explicit temp_directory when this option is processed first.
        connection.execute("SET enable_external_access=false")
        cas = ImmutableCAS(output / "cas", max_object_bytes=MAX_ARTIFACT_BYTES)
        store = DuckDBASTStore(connection=connection)
        catalog = CodebaseCatalog(store, cas, limits=CodebaseCatalogLimits(
            max_heads=1, max_operations=16, max_entries=MAX_SOURCES,
            max_manifest_bytes=MAX_ARTIFACT_BYTES, max_source_bytes=MAX_TOTAL_SOURCE_BYTES,
            max_ast_bytes=MAX_ARTIFACT_BYTES, max_receipt_bytes=65536,
        ))
        ingestor = DuckDBASTIngestor(store=store, languages={"python"})
        yield RepositoryCodebaseIndex(ingestor=ingestor, artifacts=cas, catalog=catalog), connection
    finally:
        connection.close()


def _replay(index, connection, manifest, sources: dict) -> tuple[list, dict]:
    entries = {entry.path: entry for entry in manifest.snapshot.entries}
    if set(entries) != set(sources) or len(manifest.units) != len(sources):
        raise StructuralIRGuardError("native manifest does not account for exactly the admitted sources")
    rows = []
    for path, digest in sources.items():
        entry = entries[path]
        raw = index.artifacts.get_bytes(entry.source_cid)
        if len(raw) > MAX_FILE_BYTES or hashlib.sha256(raw).hexdigest() != digest:
            raise StructuralIRGuardError("native captured source differs from its expected pin")
        projection = index.lookup(manifest, path)
        record = index.load_ast_artifact(manifest, path)
        if projection is None or record is None:
            raise StructuralIRGuardError("admitted Python source has no active native AST projection")
        rows.append({"path": path, "bytes": len(raw), "sha256": digest,
                     "source_cid": entry.source_cid, "entry_cid": entry.entry_cid,
                     "ast_cid": projection.ast_cid,
                     "parse_status": projection.ast_blob.parse_status,
                     "ast": record.to_dict()})
    counts = {}
    for table in index.ingestor.store.catalog_tables():
        # Native constant catalog table names, never caller-controlled SQL.
        counts[table] = connection.execute('SELECT count(*) FROM "' + table + '"').fetchone()[0]
    return rows, counts


def _write(path: Path, value: dict) -> None:
    with path.open("xb") as stream:
        stream.write(_json_bytes(value))


def _read(path: Path) -> dict:
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(descriptor, "rb") as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_size > MAX_ARTIFACT_BYTES:
            raise StructuralIRGuardError("sidecar is not a bounded single-link regular file")
        body = stream.read(MAX_ARTIFACT_BYTES + 1)
    if len(body) > MAX_ARTIFACT_BYTES:
        raise StructuralIRGuardError("sidecar exceeds byte bound")
    value = json.loads(body)
    if type(value) is not dict or _json_bytes(value) != body:
        raise StructuralIRGuardError("sidecar must be canonical plain JSON")
    return value


def prepare_structural_ir(*, repository: Path, output: Path, repository_id: str,
                          expected_sources: dict) -> dict:
    """Publish one current native structural generation for the exact allowlist."""
    from ipfs_datasets_py.logic.software_contracts.codebase_ir import CodebaseScanLimits
    sources = _expected_sources(expected_sources)
    repository, output = Path(repository).resolve(), Path(output).resolve()
    _guard_repository(repository, output, sources)
    if type(repository_id) is not str or not repository_id or repository_id != repository_id.strip():
        raise StructuralIRGuardError("an explicit repository view identity is required")
    scheduler = _scheduler()
    output.mkdir(mode=0o700, parents=False, exist_ok=False)
    with _owner(output) as (index, connection):
        receipt = index.prepare_current(
            repository, repository_id=repository_id, operation_id="prepare-01",
            expected_head=None,
            limits=CodebaseScanLimits(max_entries=MAX_SOURCES, max_file_bytes=MAX_FILE_BYTES),
            scheduler=scheduler, memory_mb=MEMORY_MB,
            admission_timeout_seconds=30, timeout_seconds=120,
        )
        observation = index.observe_current(repository, expected_head=receipt.head,
                                             scheduler=scheduler, memory_mb=MEMORY_MB)
        rows, counts = _replay(index, connection, observation.manifest, sources)
        # Recheck source/head after detached records were assembled.
        index.observe_current(repository, expected_head=receipt.head,
                              scheduler=scheduler, memory_mb=MEMORY_MB)
        result = {
            "schema": SCHEMA, "repository": str(repository), "output": str(output),
            "expected_sources": sources, "head": receipt.head.to_dict(),
            "receipt": receipt.to_dict(), "manifest_cid": observation.manifest.cid,
            "manifest": observation.manifest.to_dict(), "sources": rows,
            "semantic_state": observation.manifest.semantic_state.to_dict(),
            "coverage": observation.manifest.coverage, "sql_rows": counts,
            "claims": dict(CLAIMS),
            "resources": {"scheduler_state": str(scheduler.state_path),
                "proof_safety_enabled": scheduler.config.proof_safety_enabled,
                "sampler": "native collect_proof_host_resources",
                "memory_reservation_mb": MEMORY_MB, "cpu_slots": 1,
                "child_process_slots": 1, "admission_timeout_seconds": 30,
                "execution_timeout_seconds": 120, "duckdb_threads": 1,
                "max_file_bytes": MAX_FILE_BYTES, "max_total_source_bytes": MAX_TOTAL_SOURCE_BYTES,
                "duckdb_memory_limit": "128MB", "duckdb_temp_limit": "128MB",
                "admission_is_rss_limit": False},
        }
        for name, value in (("manifest.json", result["manifest"]), ("head.json", result["head"]),
                            ("receipt.json", result["receipt"]), ("structural.json", result)):
            _write(output / name, value)
        return result


def verify_structural_ir(*, repository: Path, output: Path, expected: dict) -> dict:
    """Reopen native ownership and compare exact structural bytes and current head."""
    from ipfs_datasets_py.duckdb_control.codebase_catalog import CodebaseHead
    repository, output = Path(repository).resolve(), Path(output).resolve()
    if (type(expected) is not dict or expected.get("schema") != SCHEMA
            or expected.get("claims") != CLAIMS
            or expected.get("repository") != str(repository)
            or expected.get("output") != str(output)):
        raise StructuralIRGuardError("expected structural record has another scope or authority")
    sources = _expected_sources(expected["expected_sources"])
    _guard_repository(repository, output, sources)
    if _json_bytes(_read(output / "structural.json")) != _json_bytes(expected):
        raise StructuralIRGuardError("structural sidecar differs from the supplied exact expected record")
    for name, key in (("manifest.json", "manifest"), ("head.json", "head"), ("receipt.json", "receipt")):
        if _json_bytes(_read(output / name)) != _json_bytes(expected[key]):
            raise StructuralIRGuardError("native structural sidecar changed")
    scheduler = _scheduler()
    head = CodebaseHead.from_dict(expected["head"])
    with _owner(output, existing=True) as (index, connection):
        observation = index.observe_current(repository, expected_head=head,
                                             scheduler=scheduler, memory_mb=MEMORY_MB)
        rows, counts = _replay(index, connection, observation.manifest, sources)
        if (observation.manifest.cid != expected["manifest_cid"]
                or _json_bytes(observation.manifest.to_dict()) != _json_bytes(expected["manifest"])
                or _json_bytes({"sources": rows}) != _json_bytes({"sources": expected["sources"]})
                or counts != expected["sql_rows"]):
            raise StructuralIRGuardError("fresh native source/AST/SQL replay differs")
        index.observe_current(repository, expected_head=head,
                              scheduler=scheduler, memory_mb=MEMORY_MB)
        return {"schema": "terminal-native-structural-ir-replay@1", "verified": True,
                "fresh_native_owner": True, "same_head": head.to_dict(),
                "manifest_cid": observation.manifest.cid,
                "source_files": len(rows), "source_bytes": sum(row["bytes"] for row in rows),
                "coverage": observation.manifest.coverage,
                "exact_source_ast_semantic_sql_replay": True, "claims": dict(CLAIMS)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("operation", choices=("prepare", "verify"))
    parser.add_argument("--repository", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--expected", type=Path, required=True)
    parser.add_argument("--repository-id")
    args = parser.parse_args()
    expected = _read(args.expected)
    if args.operation == "prepare":
        if not args.repository_id:
            parser.error("prepare requires --repository-id")
        result = prepare_structural_ir(repository=args.repository, output=args.output,
            repository_id=args.repository_id, expected_sources=expected)
    else:
        result = verify_structural_ir(repository=args.repository, output=args.output, expected=expected)
    print(json.dumps({"verified": result.get("verified"), "schema": result["schema"],
                      "manifest_cid": result["manifest_cid"],
                      "claims": result["claims"]}, sort_keys=True))


if __name__ == "__main__":
    main()

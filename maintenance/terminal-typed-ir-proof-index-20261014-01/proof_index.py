"""Exact historical cache for the successor's qualified alignment profile.

The native evidence index admits only its integer-offset profile. This named
experimental index stores the new alignment certificates separately. Lookup
requires native current-source observation and verifies retained checker bytes;
it grants no execution, completion or Python runtime proof authority.
"""
from __future__ import annotations

from contextlib import contextmanager
import hashlib
import json
from pathlib import Path

from train_codebase_ir import read, wire, write

SCHEMA = "terminal-align-conditional-proof-index@1"
PROFILE = "python-align-int-positive-granularity-64@1"
MAX_PAYLOAD_BYTES = 4 * 1024**2
MAX_IDENTITY_BYTES = 65536
MAX_DEPENDENCIES = 32
AUTHORITY = {"proof_authority": False, "execution_authority": False,
    "completion_authority": False, "runtime_behavior_verified": False,
    "cpython_equivalence_proved": False, "whole_program_equivalence_proved": False,
    "training_convergence_proved": False, "full_task_satisfaction_proved": False}
DDL = (
    "CREATE TABLE proof_identity (singleton INTEGER PRIMARY KEY CHECK(singleton=1), payload_json VARCHAR NOT NULL)",
    "CREATE TABLE conditional_proofs (proof_id VARCHAR PRIMARY KEY, head_id VARCHAR NOT NULL, "
    "source_cid VARCHAR NOT NULL, source_sha256 VARCHAR NOT NULL, projection_id VARCHAR NOT NULL, "
    "certificate_sha256 VARCHAR NOT NULL, payload_sha256 VARCHAR NOT NULL, payload_json VARCHAR NOT NULL)",
    "CREATE TABLE proof_dependencies (proof_id VARCHAR NOT NULL, kind VARCHAR NOT NULL, value VARCHAR NOT NULL, "
    "PRIMARY KEY(proof_id,kind,value))",
)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(value):
    return hashlib.sha256(wire(value)).hexdigest()


def bindings(structural_report, projection, proof_report):
    from align_projection import _checked_projection, _lean_sources, AUTHORITY as projection_authority
    from ipfs_datasets_py.logic.software_contracts.codebase_ir import CodebaseIRManifest
    from ipfs_datasets_py.duckdb_control.codebase_catalog import CodebaseHead
    manifest = CodebaseIRManifest.from_dict(structural_report["manifest"])
    head = CodebaseHead.from_dict(structural_report["head"])
    require(head.manifest_cid == manifest.cid and head.repository_id == manifest.snapshot.repository_id
        and head.snapshot_cid == manifest.snapshot.snapshot_cid and head.ast_revision_id == manifest.ast_revision_id,
        "native head/manifest identity differs")
    projection = _checked_projection(projection)
    require(projection["schema"] == "terminal-alignment-typed-projection@1"
        and projection["profile"] == PROFILE and proof_report["profile"] == PROFILE
        and proof_report["schema"] == "terminal-alignment-lean-proof-report@1"
        and proof_report["qualified"] is True and proof_report["projection_id"] == projection["projection_id"]
        and wire(proof_report["source"]) == wire(projection["source"]), "closed alignment certificate binding differs")
    require(all(proof_report.get(key) is False for key in projection_authority),
        "closed alignment report authority differs")
    require(proof_report["mathematical_fragment_claims"] == {"kernel_checked_lowering": True,
        "kernel_checked_g64_rounding_bounds": True, "kernel_checked_g64_divisibility": True},
        "complete checked mathematical fragment claims required")
    source = projection["source"]
    entry = next((item for item in manifest.snapshot.entries if item.path == source["path"]), None)
    require(entry is not None and not entry.is_opaque, "alignment source absent from native snapshot")
    row = next((item for item in structural_report["sources"] if item["path"] == source["path"]), None)
    require(row is not None and row["source_cid"] == entry.source_cid
        and row["sha256"] == source["sha256"] and row["bytes"] == source["bytes"],
        "alignment source differs from native typed source inventory")
    checks = proof_report["checks"]
    require(type(checks) is list and len(checks) == 3
        and sum(item["expected_success"] for item in checks) == 1,
        "one actual positive compiler process and two negative controls required")
    for check, (filename, lean_source, expected_success) in zip(checks, _lean_sources(projection)):
        body = lean_source.encode("utf-8")
        require(check["file"] == filename and check["expected_success"] is expected_success
            and Path(check["artifact"]["path"]).name == filename
            and check["artifact"]["sha256"] == hashlib.sha256(body).hexdigest()
            and check["artifact"]["bytes"] == len(body), "certificate theory source differs from exact typed projection")
        command = [check["executable"], "-j", "1"]
        command += ["-o", str(Path(filename).with_suffix(".olean"))] if expected_success else []
        command.append(filename)
        require(check["command"] == command and check["requested_command"] == command
            and check["limits"] == {"timeout_seconds": 20, "cpu_seconds": 20, "max_input_bytes": 262144,
                "max_output_bytes": 1048576, "max_workspace_bytes": 16 * 1024**2},
            "closed single-thread compiler command or finite policy differs")
    require(all(item["matches_expectation"] and item["backend_executed"] and item["lean_threads"] == 1
        and item["executable_unchanged"] and item["exact_command"] and item["workspace_cleaned"]
        and not any(item[k] for k in ("timed_out", "cancelled", "unavailable", "output_truncated",
                                    "workspace_limit_exceeded", "resource_exhausted")) for item in checks),
        "every compiler/control must be a complete bounded native process")
    positive = next(item for item in checks if item["expected_success"])
    require(positive["status"] == "passed" and positive["returncode"] == 0
        and len(positive["compiled_artifacts"]) == 1
        and Path(positive["compiled_artifacts"][0]["path"]).name == "Alignment.olean"
        and 0 < positive["compiled_artifacts"][0]["bytes"] <= 1048576
        and "sorryAx" not in positive["stdout"],
        "positive kernel artifact or checked theorem dependencies unavailable")
    require(all(item["status"] == "rejected" and item["returncode"] != 0
        for item in checks if not item["expected_success"]), "negative arithmetic controls were not rejected")
    require(all(value is False for key, value in proof_report.items() if key in AUTHORITY),
        "conditional certificate cannot gain runtime authority")
    binding = {"schema": SCHEMA, "profile": PROFILE, "head": head.to_dict(),
        "head_id": sha(head.to_dict()), "manifest_cid": manifest.cid,
        "snapshot_cid": manifest.snapshot.snapshot_cid, "source_path": source["path"],
        "source_cid": entry.source_cid, "source_sha256": source["sha256"],
        "projection_id": projection["projection_id"], "projection_sha256": sha(projection),
        "certificate_sha256": sha(proof_report), "proof_scope": "closed_mathematical_integer_alignment_only",
        **AUTHORITY}
    return binding


def dependency_set(binding, artifacts):
    dependencies = [("head", binding["head_id"]), ("manifest", binding["manifest_cid"]),
        ("snapshot", binding["snapshot_cid"]), ("source", binding["source_cid"]),
        ("source_sha256", binding["source_sha256"]), ("projection", binding["projection_id"]),
        ("certificate", binding["certificate_sha256"])]
    dependencies += [("checker_artifact", item["sha256"]) for item in artifacts]
    result = sorted(set(dependencies))
    require(len(result) <= MAX_DEPENDENCIES, "reverse dependency bound exceeded")
    return result


def verify_checker_artifacts(proof_report):
    result = []
    for check in proof_report["checks"]:
        selected = [check["artifact"], *check["compiled_artifacts"]]
        selected.append({"path": check["executable"], "sha256": check["executable_sha256"]})
        for item in selected:
            body = read(Path(item["path"]), 64 * 1024**2)
            require(hashlib.sha256(body).hexdigest() == item["sha256"]
                and ("bytes" not in item or len(body) == item["bytes"]), "retained checker artifact changed")
            result.append({"path": item["path"], "sha256": item["sha256"], "bytes": len(body)})
    return result


@contextmanager
def owner(output, *, create=False):
    import duckdb
    output = Path(output)
    require(output.is_absolute() and output.resolve() == output, "canonical caller-owned proof index required")
    if create:
        output.mkdir(mode=0o700)
        (output / "temp").mkdir(mode=0o700)
    require((output / "temp").is_dir() and (create or (output / "proof-index.duckdb").is_file()),
        "complete proof index owner required")
    connection = duckdb.connect(str(output / "proof-index.duckdb"), config={"threads": "1",
        "memory_limit": "64MB", "max_temp_directory_size": "64MB", "temp_directory": str(output / "temp"),
        "autoinstall_known_extensions": "false", "autoload_known_extensions": "false"})
    try:
        connection.execute("SET enable_external_access=false")
        yield connection
    finally:
        connection.close()


def create_proof_index(*, output, structural_report, projection, proof_report):
    binding = bindings(structural_report, projection, proof_report)
    artifacts = verify_checker_artifacts(proof_report)
    payload = {"binding": binding, "projection": projection, "certificate": proof_report,
               "checker_artifacts": artifacts}
    body = wire(payload)
    require(len(body) <= MAX_PAYLOAD_BYTES, "bounded complete conditional proof payload required")
    proof_id = sha(binding)
    dependencies = dependency_set(binding, artifacts)
    identity = {"schema": SCHEMA, "output": str(output), "profile": PROFILE,
        "proof_id": proof_id, "binding": binding, "payload_sha256": hashlib.sha256(body).hexdigest(),
        "dependencies": [list(item) for item in dependencies], "authority": "historical_conditional_candidate", **AUTHORITY}
    with owner(output, create=True) as connection:
        connection.execute("BEGIN")
        try:
            for statement in DDL:
                connection.execute(statement)
            connection.execute("INSERT INTO proof_identity VALUES (1,?)", [wire(identity).decode()])
            connection.execute("INSERT INTO conditional_proofs VALUES (?,?,?,?,?,?,?,?)", [proof_id,
                binding["head_id"], binding["source_cid"], binding["source_sha256"], binding["projection_id"],
                binding["certificate_sha256"], identity["payload_sha256"], body.decode()])
            connection.executemany("INSERT INTO proof_dependencies VALUES (?,?,?)",
                [(proof_id, kind, value) for kind, value in dependencies])
            connection.execute("COMMIT")
        except BaseException:
            connection.execute("ROLLBACK")
            raise
    write(Path(output) / "index.json", identity)
    return identity


def lookup_current_proof(*, output, repository, structural_output, structural_report, projection, proof_report):
    from native_structural_ir import verify_structural_ir
    from align_projection import validate_alignment_projection
    before = verify_structural_ir(repository=repository, output=structural_output, expected=structural_report)
    validate_alignment_projection(source_bytes=read(Path(repository) / projection["source"]["path"], 8192),
        source_path=projection["source"]["path"], source_sha256=projection["source"]["sha256"], expected=projection)
    binding = bindings(structural_report, projection, proof_report)
    artifacts = verify_checker_artifacts(proof_report)
    expected_id = sha(binding)
    identity_raw = read(Path(output) / "index.json", MAX_IDENTITY_BYTES)
    identity = json.loads(identity_raw)
    require(identity["binding"] == binding and identity["proof_id"] == expected_id,
        "exact complete structural head or conditional profile differs")
    with owner(output) as connection:
        counts = connection.execute("SELECT (SELECT count(*) FROM proof_identity),"
            "(SELECT count(*) FROM conditional_proofs),(SELECT count(*) FROM proof_dependencies)").fetchone()
        require(counts[0] == counts[1] == 1 and counts[2] <= MAX_DEPENDENCIES,
            "bounded complete index row counts differ")
        sizes = connection.execute("SELECT (SELECT max(octet_length(encode(payload_json))) FROM proof_identity),"
            "(SELECT max(octet_length(encode(payload_json))) FROM conditional_proofs)").fetchone()
        require(0 < sizes[0] <= MAX_IDENTITY_BYTES and 0 < sizes[1] <= MAX_PAYLOAD_BYTES,
            "proof SQL payload exceeds finite bound before hydration")
        metadata = connection.execute("SELECT payload_json FROM proof_identity WHERE singleton=1").fetchall()
        require(metadata == [(wire(identity).decode(),)], "proof index identity SQL drift")
        rows = connection.execute("SELECT proof_id,head_id,source_cid,source_sha256,projection_id,certificate_sha256,"
            "payload_sha256,payload_json FROM conditional_proofs WHERE proof_id=?", [expected_id]).fetchall()
        require(len(rows) == 1 and connection.execute("SELECT count(*) FROM conditional_proofs").fetchone() == (1,),
            "complete one-record conditional proof scope differs")
        row = rows[0]
        require(row[:6] == (expected_id, binding["head_id"], binding["source_cid"], binding["source_sha256"],
            binding["projection_id"], binding["certificate_sha256"]), "typed proof SQL joins changed")
        body = row[7].encode()
        require(hashlib.sha256(body).hexdigest() == row[6] == identity["payload_sha256"], "proof payload SQL bytes changed")
        payload = json.loads(body)
        require(payload == {"binding": binding, "projection": projection, "certificate": proof_report,
                           "checker_artifacts": artifacts}, "complete conditional proof record changed")
        deps = connection.execute("SELECT kind,value FROM proof_dependencies WHERE proof_id=? ORDER BY kind,value", [expected_id]).fetchall()
        require(deps == dependency_set(binding, artifacts)
            and [list(item) for item in deps] == identity["dependencies"], "proof reverse dependency graph changed")
    after = verify_structural_ir(repository=repository, output=structural_output, expected=structural_report)
    require(before == after and read(Path(output) / "index.json") == identity_raw,
        "source/head or proof descriptor changed during lookup")
    return {"schema": SCHEMA, "status": "current_source_bound_conditional_candidate",
        "proof_id": expected_id, "binding": binding, "live_source_and_complete_head_rechecked": True,
        "retained_checker_artifacts_rechecked": True, "dependencies": [list(item) for item in deps],
        "native_offset_evidence_index_used": False, "mathematical_fragment_claims": proof_report["mathematical_fragment_claims"],
        "requires_fresh_native_checks_for_admission": True, "historical_record_creates_authority": False,
        **AUTHORITY}

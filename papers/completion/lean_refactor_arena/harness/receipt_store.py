#!/usr/bin/env python3
"""Optional INSERT-only DuckDB sidecar for LRA proof receipts.

Filesystem receipts remain authority for warm-up. DuckDB, when used, is
INSERT-only: no DELETE of existing edges, no upsert of huge parent rows,
and no ``upsert_task``. Proof bodies live in content-addressed files;
database rows hold CIDs, verdicts, and token/elab numbers only.

``run_warmup.py`` remains the control plane. This module is a writer, not
a scheduler and not a ``todo_daemon`` worker. Learned from LA-031 ART
crashes. Loop v1 may skip DuckDB entirely.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import sqlite3
import sys
import tempfile
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence

HERE = Path(__file__).resolve().parent
PAPER_ROOT = HERE.parent
REPO_ROOT = HERE.parents[3]
WARMUP_JSONL = PAPER_ROOT / "data" / "benchmark_data_warmup.jsonl"
SUPERVISOR_JSON = PAPER_ROOT / "supervisor.json"
DATASETS_ROOT = REPO_ROOT / "external" / "ipfs_datasets"
PROOF_STORE_SOURCE = (
    DATASETS_ROOT / "ipfs_datasets_py" / "logic" / "common" / "duckdb_proof_store.py"
)
MODELS_SOURCE = DATASETS_ROOT / "ipfs_datasets_py" / "logic" / "hammers" / "models.py"

if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
import _jevops_path  # noqa: E402,F401
import retrieve as lra_retrieve  # noqa: E402
import splice as lra_splice  # noqa: E402

FROZEN_WARMUP_SHA256 = lra_splice.FROZEN_WARMUP_SHA256
WARMUP_N = lra_splice.WARMUP_N
PR_ID = "PR-7"
LRAH_ID = "LRAH-008"
from jevops.catalogs import CONTROL_PLANE
from jevops.catalogs import PROOF_RECEIPT_SCHEMA as RECEIPT_SCHEMA
from jevops.catalogs import RECEIPT_STORE_SCHEMA as STORE_SCHEMA
from jevops.catalogs import ALLOWED_SQL_HEAD
from jevops.catalogs import DEFAULT_BACKEND_ID
from jevops.catalogs import DEFAULT_IR
from jevops.catalogs import DEFAULT_POLICY
from jevops.catalogs import DEFAULT_PROPERTY
from jevops.catalogs import DEFAULT_RESOURCE
from jevops.catalogs import DEFAULT_TRANSLATOR
from jevops.catalogs import FILESYSTEM_IS_AUTHORITY
from jevops.catalogs import FORBIDDEN_SQL
from jevops.catalogs import HEX64
from jevops.catalogs import INSERT_ONLY
from jevops.catalogs import IS_CONTROL_PLANE
from jevops.catalogs import KERNEL_COMMAND_TEMPLATE
from jevops.catalogs import LEAN_NUM_THREADS
from jevops.catalogs import MAX_ROW_BYTES
from jevops.catalogs import MEASUREMENT_MAX_HEARTBEATS
from jevops.catalogs import NO_NEW_AXIOMS
from jevops.catalogs import NOT_APPLICABLE
from jevops.catalogs import PROOF_AUTHORITY_DIMENSIONS
from jevops.catalogs import PROOF_AUTHORITY_DIMENSION_SET
from jevops.catalogs import PROOF_BODY_KEYS
from jevops.catalogs import PROTOCOL
from jevops.catalogs import RECEIPT_GENERATOR as DEFAULT_GENERATOR
from jevops.catalogs import REQUIRES_DUCKDB
from jevops.catalogs import REQUIRES_TODO_DAEMON
from jevops.catalogs import SQL_STATEMENT_HEAD
FORBIDDEN_IMPORT_NAMES = frozenset(
    {
        "fcntl",
        "LeanstralProofProvider",
        "leanstral_proof_provider",
        "todo_daemon",
        "IntentRepository",
        "paper_supervisors",
        "run_warmup",
        "IndependentKernelVerifier",
        "KernelVerifier",
    }
)
FORBIDDEN_CALL_NAMES = frozenset(
    {
        "upsert_task",
        "LOCK_EX",
        "build_environment_lock",
    }
)

from jevops.catalogs import EDGE_DDL
from jevops.catalogs import INSERT_EDGE_SQL
from jevops.catalogs import INSERT_RECEIPT_SQL
from jevops.catalogs import RECEIPT_DDL
from jevops.catalogs import SELECT_COUNT_EDGES_SQL
from jevops.catalogs import SELECT_COUNT_RECEIPTS_SQL
from jevops.catalogs import SELECT_EDGE_ONE_SQL
from jevops.catalogs import SELECT_EDGE_SQL
from jevops.catalogs import SELECT_NEGATIVE_SQL
from jevops.catalogs import SELECT_RECEIPT_SQL


class ReceiptStoreError(RuntimeError):
    """Fail-closed receipt-store error."""


class DimensionError(ReceiptStoreError):
    """A PROOF_AUTHORITY_DIMENSIONS key was dropped, empty, or unknown."""


class InsertOnlyError(ReceiptStoreError):
    """SQL outside the INSERT/SELECT/CREATE TABLE IF NOT EXISTS vocabulary."""


from jevops.lean import ExecutablePaths
from jevops.lean import ProofReceipt as _KernelProofReceipt


@dataclass
class ProofReceipt(_KernelProofReceipt):
    """LRA overlay: closed authority constants stay on the public dict."""

    generator: str = DEFAULT_GENERATOR
    policy: str = DEFAULT_POLICY
    resource: str = DEFAULT_RESOURCE
    translator: str = DEFAULT_TRANSLATOR
    backend_id: str = DEFAULT_BACKEND_ID
    git_commit: str = NOT_APPLICABLE
    lean_version: str = NOT_APPLICABLE
    hardware_class: str = DEFAULT_RESOURCE

    def to_public_dict(self) -> dict[str, Any]:
        return super().to_public_dict(
            extra={
                "schema": RECEIPT_SCHEMA,
                "protocol": PROTOCOL,
                "control_plane": CONTROL_PLANE,
                "is_control_plane": IS_CONTROL_PLANE,
                "filesystem_authority": FILESYSTEM_IS_AUTHORITY,
                "insert_only": INSERT_ONLY,
                "upsert_task": False,
                "pr": PR_ID,
                "lrah": LRAH_ID,
            }
        )


def sha256_bytes(data: bytes) -> str:
    from jevops.outer import digest_hex

    return digest_hex(data)


def sha256_file(path: Path) -> str:
    from jevops.outer import digest_file

    return digest_file(path)


def canonical_bytes(value: Any) -> bytes:
    from jevops.outer import canonical_bytes as _fn

    return _fn(value)


def content_digest(value: Any) -> str:
    from jevops.outer import digest_canonical

    return digest_canonical(value)


def not_applicable_digest() -> str:
    return content_digest(NOT_APPLICABLE)


def load_warmup_records(path: Optional[Path] = None) -> tuple[bytes, str, list[dict[str, Any]]]:
    return lra_splice.load_warmup_records(path)


def closed_dimensions_from_source(path: Path = PROOF_STORE_SOURCE) -> tuple[str, ...]:
    """Parse PROOF_AUTHORITY_DIMENSIONS from DuckDBProofStore@1 source."""

    from jevops.outer import quoted_group, read_text, require_file

    path = require_file(path, error_cls=ReceiptStoreError, miss="missing proof-store source: {path}")
    return quoted_group(
        read_text(path),
        r"PROOF_AUTHORITY_DIMENSIONS: Final\[tuple\[str, \.\.\.\]\] = \((.*?)\)",
        error_cls=ReceiptStoreError,
        miss="PROOF_AUTHORITY_DIMENSIONS missing from duckdb_proof_store.py",
        empty="PROOF_AUTHORITY_DIMENSIONS parsed empty",
    )


def environment_lock_field_names(path: Path = MODELS_SOURCE) -> list[str]:
    """AnnAssign names on EnvironmentLockRecord. No primary_executable field."""

    from jevops.repair import class_ann_names
    from jevops.outer import read_text, require_file

    path = require_file(path, error_cls=ReceiptStoreError, miss="missing hammer models source: {path}")
    names = class_ann_names(read_text(path), "EnvironmentLockRecord")
    from jevops.outer import raise_if

    raise_if(names is None, ReceiptStoreError, "EnvironmentLockRecord class missing from models.py")
    return names


def parse_executable_paths(value: Any) -> ExecutablePaths:
    from jevops.outer import reject_present_keys, require_exact_keys, str_map

    if isinstance(value, ExecutablePaths):
        paths = value.to_dict()
    elif isinstance(value, Mapping):
        reject_present_keys(
            value,
            ("primary_executable",),
            error_cls=ReceiptStoreError,
            fmt="executable_paths must not include {key}",
            empty=(),
        )
        paths = str_map(value)
    else:
        raise ReceiptStoreError("executable_paths must be a mapping of lean and lake")
    got = require_exact_keys(
        paths,
        ("lean", "lake"),
        error_cls=ReceiptStoreError,
        not_map="executable_paths must be a mapping of lean and lake",
        extra_fmt="executable_paths must be exactly lean and lake",
        miss_fmt="executable_paths must be exactly lean and lake",
        empty_fmt="executable_paths lean and lake must be nonempty",
    )
    return ExecutablePaths(lean=got["lean"], lake=got["lake"])


def assumptions_digest(
    *,
    max_heartbeats: int = MEASUREMENT_MAX_HEARTBEATS,
    lean_num_threads: int = LEAN_NUM_THREADS,
    no_new_axioms: bool = NO_NEW_AXIOMS,
) -> str:
    return content_digest(
        {
            "lean_num_threads": lean_num_threads,
            "maxHeartbeats": max_heartbeats,
            "no_new_axioms": no_new_axioms,
        }
    )


def project_dimensions(receipt: ProofReceipt) -> dict[str, str]:
    """Project every closed authority dimension. Missing keys fail closed."""

    from jevops.lean import project_authority_dimensions

    from jevops.outer import or_call

    premises = or_call(receipt.premises_digest, not_applicable_digest)
    backend_config = or_call(receipt.backend_config_digest, not_applicable_digest)
    mapping = {
        "ir": DEFAULT_IR,
        "property": DEFAULT_PROPERTY,
        "assumptions": assumptions_digest(),
        "premises": premises,
        "translator": receipt.translator,
        "solver": receipt.generator,
        "toolchain": receipt.lean_tag,
        "theorem_registry": receipt.name,
        "policy": receipt.policy,
        "resource": receipt.resource,
        "tree": receipt.git_commit,
        "backend_id": receipt.backend_id,
        "backend_binary": receipt.executable_paths.lean,
        "backend_version": receipt.lean_version,
        "backend_config": backend_config,
    }
    return project_authority_dimensions(
        receipt, PROOF_AUTHORITY_DIMENSIONS, mapping, error_cls=DimensionError
    )


def receipt_key_digest(receipt: ProofReceipt, dimensions: Mapping[str, str]) -> str:
    from jevops.outer import overlay_map

    return content_digest(
        {
            "body_digest": receipt.body_digest,
            "dimensions": overlay_map(dimensions),
            "lean_tag": receipt.lean_tag,
            "name": receipt.name,
            "schema": RECEIPT_SCHEMA,
        }
    )


def _reject_proof_bodies(payload: Mapping[str, Any]) -> None:
    from jevops.outer import reject_present_keys

    reject_present_keys(
        payload,
        PROOF_BODY_KEYS,
        error_cls=ReceiptStoreError,
        fmt="proof body field {key!r} is not stored in receipt rows",
    )


def _tiny_payload(payload: Mapping[str, Any]) -> str:
    from jevops.outer import dump_tiny

    return dump_tiny(
        payload,
        max_bytes=MAX_ROW_BYTES,
        error_cls=ReceiptStoreError,
        fmt="receipt row {n} bytes exceeds tiny-row cap {max_bytes}",
    )


def sanitize_name(name: str) -> str:
    from jevops.outer import sanitize_ident

    return sanitize_ident(name, error_cls=ReceiptStoreError, empty="theorem name sanitizes empty")


def write_cas_body(root: Path, body: str) -> str:
    from jevops.outer import write_cas

    return write_cas(root, body.encode("utf-8"), prefix="artifacts", filename="candidate.lean")


def filesystem_receipt_path(root: Path, name: str, lean_tag: str) -> Path:
    from jevops.outer import join_under

    return join_under(root, "receipts", sanitize_name(name), f"{lean_tag}.json")


def write_filesystem_receipt(root: Path, receipt: ProofReceipt) -> Path:
    from jevops.outer import write_json

    path = filesystem_receipt_path(root, receipt.name, receipt.lean_tag)
    payload = receipt.to_public_dict()
    _reject_proof_bodies(payload)
    write_json(path, payload)
    return path


def try_import_duckdb() -> Any:
    from jevops.outer import try_import

    return try_import("duckdb")


def _guard_sql(sql: str) -> str:
    from jevops.outer import guard_sql

    return guard_sql(
        sql,
        allowed_head=ALLOWED_SQL_HEAD,
        forbidden=FORBIDDEN_SQL,
        error_cls=InsertOnlyError,
        empty="empty SQL",
        forbidden_fmt="forbidden mutating SQL: {sql}",
        outside_fmt="SQL outside INSERT/SELECT/CREATE TABLE IF NOT EXISTS: {sql}",
    )


from jevops.outer import InsertOnlyConnection as _KernelInsertOnly


class InsertOnlyConnection(_KernelInsertOnly):
    """Wrap a DuckDB or sqlite3 connection. Only INSERT/SELECT/CREATE IF NOT EXISTS."""

    def __init__(self, raw: Any) -> None:
        super().__init__(raw, guard_fn=_guard_sql)


def connect_optional_db(path: Path, *, duckdb_module: Any = None) -> tuple[InsertOnlyConnection, str]:
    """Open DuckDB when the package exists; otherwise sqlite3 (still INSERT-only)."""

    from jevops.outer import connect_engine

    raw, engine = connect_engine(path, duckdb_module=duckdb_module)
    return InsertOnlyConnection(raw), engine


def install_schema(conn: InsertOnlyConnection) -> None:
    conn.execute(RECEIPT_DDL)
    conn.execute(EDGE_DDL)


def _integrity_conflict(exc: BaseException) -> bool:
    from jevops.outer import integrity_conflict

    return integrity_conflict(exc)


def insert_receipt_row(conn: InsertOnlyConnection, receipt: ProofReceipt) -> bool:
    """INSERT one tiny row. Existing key is skipped; never DELETE/UPDATE."""

    from jevops.outer import dumps_compact, insert_ignore_conflict, pack_receipt_insert_params

    params = pack_receipt_insert_params(
        receipt,
        schema=RECEIPT_SCHEMA,
        dumps_fn=dumps_compact,
        tiny_fn=_tiny_payload,
    )
    return insert_ignore_conflict(
        conn.execute,
        INSERT_RECEIPT_SQL,
        params,
        error_cls=ReceiptStoreError,
        fail_fmt="INSERT receipt failed: {exc}",
    )


def insert_edge(
    conn: InsertOnlyConnection,
    parent_digest: str,
    child_digest: str,
    edge_kind: str = "candidate",
    *,
    created_at: Optional[float] = None,
) -> bool:
    """INSERT an edge. Existing edges stay; there is no DELETE."""

    from jevops.outer import if_none, insert_ignore_conflict

    stamp = float(if_none(created_at, factory=time.time))
    return insert_ignore_conflict(
        conn.execute,
        INSERT_EDGE_SQL,
        (parent_digest, child_digest, edge_kind, stamp),
        error_cls=ReceiptStoreError,
        fail_fmt="INSERT edge failed: {exc}",
    )


def select_edges(conn: InsertOnlyConnection, parent_digest: str) -> list[tuple[str, str, str]]:
    from jevops.outer import fetch_mapped, text_or

    result = conn.execute(SELECT_EDGE_SQL, (parent_digest,))
    return fetch_mapped(result, lambda row: (text_or(row[0]), text_or(row[1]), text_or(row[2])))


def lookup_receipt(conn: InsertOnlyConnection, key_digest: str) -> Optional[dict[str, Any]]:
    from jevops.outer import row_dict

    result = conn.execute(SELECT_RECEIPT_SQL, (key_digest,))
    return row_dict(
        result.fetchone(),
        (
            "key_digest",
            "theorem_name",
            "lean_tag",
            "body_digest",
            "candidate_cid",
            "verdict",
            "token_count",
            "elab_proxy",
            "dimensions_json",
            "executable_paths_json",
            "payload_json",
            "created_at",
        ),
    )


def lookup_negative(
    conn: InsertOnlyConnection,
    theorem_name: str,
    body_digest: str,
    lean_tag: str,
) -> Optional[str]:
    """Return the stored verdict for a failed (theorem, body, toolchain)."""

    from jevops.outer import row_cell, str_or_none

    result = conn.execute(SELECT_NEGATIVE_SQL, (theorem_name, body_digest, lean_tag))
    value = row_cell(result.fetchone(), 1)
    return str_or_none(value)


def should_skip_retry(verdict: Optional[str]) -> bool:
    return verdict in {"fail", "error"}


def finalize_receipt(receipt: ProofReceipt, *, body: Optional[str] = None) -> ProofReceipt:
    from jevops.lean import finalize_proof_receipt

    return finalize_proof_receipt(
        receipt,
        body=body,
        digest_fn=sha256_bytes,
        project_fn=project_dimensions,
        key_fn=receipt_key_digest,
        now_fn=time.time,
        error_cls=ReceiptStoreError,
    )


def store_receipt(
    receipt: ProofReceipt,
    *,
    root: Path,
    body: Optional[str] = None,
    duckdb_path: Optional[Path] = None,
    parent_digest: Optional[str] = None,
    require_duckdb: bool = False,
    duckdb_module: Any = None,
) -> ProofReceipt:
    """Write the filesystem receipt, then optionally INSERT a tiny DuckDB row.

    DuckDB is skipped when the package is absent unless ``require_duckdb``.
    Filesystem remains authority either way. ``run_warmup.py`` is still the
    control plane; this function does not schedule work.
    """

    from jevops.lean import persist_receipt
    from jevops.outer import first_truthy, if_none

    return persist_receipt(
        receipt,
        root=root,
        body=body,
        duckdb_path=duckdb_path,
        parent_digest=parent_digest,
        require_duckdb=require_duckdb,
        control_plane=first_truthy(IS_CONTROL_PLANE, REQUIRES_TODO_DAEMON, default=False),
        finalize_fn=finalize_receipt,
        write_cas_fn=write_cas_body,
        write_fs_fn=write_filesystem_receipt,
        connect_fn=lambda path, module: connect_optional_db(path, duckdb_module=module),
        install_fn=install_schema,
        insert_fn=insert_receipt_row,
        insert_edge_fn=insert_edge,
        try_import_fn=lambda: if_none(duckdb_module, factory=try_import_duckdb),
        error_cls=ReceiptStoreError,
        control_msg="receipt_store must not be the control plane",
    )


def _imported_names(source: str) -> set[str]:
    from jevops.repair import imported_names

    return imported_names(source)


def _call_func_names(source: str) -> set[str]:
    from jevops.repair import call_func_names

    return call_func_names(source)


def _keyword_names(source: str) -> set[str]:
    from jevops.repair import keyword_names

    return keyword_names(source)


def _string_constants(source: str) -> list[str]:
    from jevops.repair import string_constants

    return string_constants(source)


def _function_names(source: str) -> set[str]:
    from jevops.repair import function_names

    return function_names(source)


def _forbidden_sql_in_constants(source: str) -> list[str]:
    """Flag string constants that are mutating SQL statements, not prose."""

    from jevops.outer import head_chars

    issues: list[str] = []
    for value in _string_constants(source):
        stripped = value.strip()
        if SQL_STATEMENT_HEAD.match(stripped) or (
            ALLOWED_SQL_HEAD.match(stripped) and FORBIDDEN_SQL.search(stripped)
        ):
            issues.append(head_chars(stripped, 80))
    return issues


def _primary_executable_kwargs(source: str) -> bool:
    return "primary_executable" in _keyword_names(source)


def _synthetic_receipt(
    *,
    name: str = "CallElimCorrect.substOldPostSubset",
    lean_tag: str = "v4.26.0",
    verdict: str = "fail",
    body: str = "rfl",
    premises_digest: str = "",
    git_commit: str = "451e5f047bafa010d178856db76c00029bfa4d7f",
) -> tuple[ProofReceipt, str]:
    from jevops.lean import synthetic_proof_receipt

    return synthetic_proof_receipt(
        ProofReceipt,
        ExecutablePaths,
        name=name,
        lean_tag=lean_tag,
        verdict=verdict,
        body=body,
        digest_fn=sha256_bytes,
        premises_digest=premises_digest,
        git_commit=git_commit,
    )


def _load_control_plane_pin() -> dict[str, Any]:
    from jevops.outer import read_json

    cfg = read_json(SUPERVISOR_JSON)
    return {
        "primary_control_plane": cfg.get("primary_control_plane"),
        "matches_constant": cfg.get("primary_control_plane") == CONTROL_PLANE,
        "run_warmup_exists": (REPO_ROOT / CONTROL_PLANE).is_file(),
        "receipt_store_is_control_plane": IS_CONTROL_PLANE,
        "requires_todo_daemon": REQUIRES_TODO_DAEMON,
        "requires_duckdb": REQUIRES_DUCKDB,
        "filesystem_is_authority": FILESYSTEM_IS_AUTHORITY,
        "insert_only": INSERT_ONLY,
    }


def self_check(path: Optional[Path] = None) -> dict[str, Any]:
    """Exercise filesystem authority, INSERT-only SQL, and closed dimensions."""

    from jevops.outer import read_text

    source = read_text(__file__)
    from jevops.outer import path_or, relative_or_str

    jsonl = path_or(path, WARMUP_JSONL)
    before = sha256_file(jsonl)
    raw, digest, records = load_warmup_records(jsonl)
    after = sha256_file(jsonl)
    first = records[0]
    retrieval = lra_retrieve.retrieve_record(first, records)
    closed_src = closed_dimensions_from_source()
    lock_fields = environment_lock_field_names()
    imported = _imported_names(source)
    forbidden_imports = sorted(name for name in imported if name in FORBIDDEN_IMPORT_NAMES)
    call_names = _call_func_names(source)
    forbidden_calls = sorted(name for name in call_names if name in FORBIDDEN_CALL_NAMES)
    sql_issues = _forbidden_sql_in_constants(source)
    from jevops import catalogs as catalogs_mod
    from jevops.repair import module_source, string_constants

    kernel_sql = module_source(catalogs_mod)
    kernel_sql_issues = _forbidden_sql_in_constants(kernel_sql)
    kernel_has_insert = any("INSERT INTO" in value for value in string_constants(kernel_sql))
    fn_names = _function_names(source)
    control = _load_control_plane_pin()
    duckdb_module = try_import_duckdb()
    duckdb_available = duckdb_module is not None

    from jevops.outer import catch_error, closed_on_error

    def _dropped_dimension() -> None:
        bad = ProofReceipt(
            name="x",
            lean_tag="v4.26.0",
            body_digest="0" * 64,
            verdict="fail",
            executable_paths=ExecutablePaths(lean="/lean", lake="/lake"),
        )
        mapping = project_dimensions(bad)
        mapping.pop("assumptions")
        missing = PROOF_AUTHORITY_DIMENSION_SET - set(mapping)
        if missing:
            raise DimensionError(f"authority dimension(s) dropped: {', '.join(sorted(missing))}")

    _dropped, dropped_error = catch_error(_dropped_dimension, DimensionError)
    primary_rejected = closed_on_error(
        lambda: parse_executable_paths({"lean": "/lean", "lake": "/lake", "primary_executable": "/lean"}),
        ReceiptStoreError,
    )
    huge_rejected = closed_on_error(
        lambda: _tiny_payload({"src": "x" * (MAX_ROW_BYTES + 1)}),
        ReceiptStoreError,
    )
    body_rejected = closed_on_error(
        lambda: _reject_proof_bodies({"src": "theorem T : True := by rfl"}),
        ReceiptStoreError,
    )
    delete_sql_rejected = closed_on_error(
        lambda: _guard_sql("DELETE" + " FROM lra_proof_edges WHERE parent_digest = 'x'"),
        InsertOnlyError,
    )
    update_sql_rejected = closed_on_error(
        lambda: _guard_sql("UPDATE" + " lra_proof_receipts SET verdict = 'pass'"),
        InsertOnlyError,
    )
    upsert_sql_rejected = closed_on_error(
        lambda: _guard_sql("INSERT" + " OR REPLACE INTO lra_proof_receipts (key_digest) VALUES ('x')"),
        InsertOnlyError,
    )

    from jevops.outer import temp_dir

    with temp_dir(prefix="lra-023-receipt-") as tmp:
        root = Path(tmp)
        db_path = root / "receipts.duckdb"
        receipt, body = _synthetic_receipt(premises_digest=retrieval.lemma_id_digest)
        stored = store_receipt(
            receipt,
            root=root,
            body=body,
            duckdb_path=db_path,
            parent_digest=content_digest({"problem": receipt.name}),
            require_duckdb=False,
            duckdb_module=duckdb_module,
        )
        fs_path = Path(stored.filesystem_path)
        from jevops.outer import read_json

        fs_payload = read_json(fs_path)
        cas_path = root / "artifacts" / stored.candidate_cid[:2] / stored.candidate_cid / "candidate.lean"
        conn, engine = connect_optional_db(db_path, duckdb_module=duckdb_module)
        try:
            install_schema(conn)
            parent = content_digest({"problem": stored.name})
            first_edge = insert_edge(conn, parent, stored.key_digest, "candidate")
            second_child = content_digest({"other": stored.name, "n": 2})
            second_edge = insert_edge(conn, parent, second_child, "candidate")
            dup_edge = insert_edge(conn, parent, stored.key_digest, "candidate")
            edges = select_edges(conn, parent)
            row = lookup_receipt(conn, stored.key_digest)
            negative = lookup_negative(conn, stored.name, stored.body_digest, stored.lean_tag)
            count_receipts = conn.execute(SELECT_COUNT_RECEIPTS_SQL).fetchone()[0]
            count_edges = conn.execute(SELECT_COUNT_EDGES_SQL).fetchone()[0]
            commit = getattr(conn._raw, "commit", None)
            if callable(commit):
                commit()
        finally:
            conn.close()
        fs_exists = fs_path.is_file()
        cas_exists = cas_path.is_file()
        from jevops.outer import call_if

        cas_bytes = call_if(cas_exists, lambda: cas_path.stat().st_size, default=0)
        stored_again = store_receipt(
            ProofReceipt(
                name=stored.name,
                lean_tag=stored.lean_tag,
                body_digest=stored.body_digest,
                verdict=stored.verdict,
                executable_paths=stored.executable_paths,
                premises_digest=stored.premises_digest,
                git_commit=stored.git_commit,
                lean_version=stored.lean_version,
                token_count=stored.token_count,
            ),
            root=root,
            body=body,
            duckdb_path=db_path,
            parent_digest=parent,
            duckdb_module=duckdb_module,
        )
        conn, _ = connect_optional_db(db_path, duckdb_module=duckdb_module)
        try:
            edges_after = select_edges(conn, parent)
            row_after = lookup_receipt(conn, stored.key_digest)
            count_edges_after = conn.execute(SELECT_COUNT_EDGES_SQL).fetchone()[0]
            from jevops.outer import get_str

            payload_after = get_str(row_after, "payload_json")
        finally:
            conn.close()

    from jevops.outer import loads_json, nested_get, overlay_map

    dim_keys = list(stored.dimensions)
    fs_dim_keys = list(overlay_map(fs_payload.get("dimensions")))

    row_dims = loads_json(nested_get(row, "dimensions_json"), default={})
    exec_paths = loads_json(nested_get(row, "executable_paths_json"), default={})
    row_payload = loads_json(nested_get(row, "payload_json"), default={})
    edge_children = sorted(item[1] for item in edges)
    expected_children = sorted({stored.key_digest, second_child})

    from jevops.outer import any_in, any_pred, first_truthy, pack_unscored

    report = pack_unscored(**{
        "ok": True,
        "schema": STORE_SCHEMA,
        "protocol": PROTOCOL,
        "pr": PR_ID,
        "lrah": LRAH_ID,
        "n_records": len(records),
        "frozen_warmup_sha256": FROZEN_WARMUP_SHA256,
        "warmup_jsonl_sha256": digest,
        "jsonl_bytes": len(raw),
        "jsonl_unchanged": before == after == FROZEN_WARMUP_SHA256,
        "proof_authority_dimensions": list(PROOF_AUTHORITY_DIMENSIONS),
        "proof_authority_dimensions_source": list(closed_src),
        "dimensions_match_duckdb_proof_store": tuple(closed_src) == PROOF_AUTHORITY_DIMENSIONS,
        "all_dimensions_populated": dim_keys == list(PROOF_AUTHORITY_DIMENSIONS)
        and set(dim_keys) == PROOF_AUTHORITY_DIMENSION_SET
        and set(fs_dim_keys) == PROOF_AUTHORITY_DIMENSION_SET
        and set(row_dims) == PROOF_AUTHORITY_DIMENSION_SET,
        "dropped_dimension_fail_closed": "assumptions" in dropped_error,
        "environment_lock_fields": lock_fields,
        "environment_lock_has_executable_paths": "executable_paths" in lock_fields,
        "environment_lock_has_primary_executable": "primary_executable" in lock_fields,
        "primary_executable_kwarg": _primary_executable_kwargs(source),
        "primary_executable_payload_rejected": primary_rejected,
        "lock_executable_paths": stored.executable_paths.to_dict(),
        "row_executable_paths": exec_paths,
        "filesystem_authority": FILESYSTEM_IS_AUTHORITY,
        "filesystem_receipt_exists": fs_exists,
        "cas_body_exists": cas_exists,
        "cas_body_bytes": cas_bytes,
        "filesystem_has_src": "src" in fs_payload,
        "row_has_src": "src" in row_payload,
        "row_payload_bytes": call_if(row, lambda: len(row["payload_json"].encode("utf-8")), default=-1),
        "tiny_row": call_if(row, lambda: len(row["payload_json"].encode("utf-8")), default=MAX_ROW_BYTES + 1)
        <= MAX_ROW_BYTES,
        "huge_parent_row_rejected": huge_rejected,
        "proof_body_rejected": body_rejected,
        "insert_only": INSERT_ONLY,
        "insert_receipt": bool(first_truthy(stored.inserted, stored.skipped_duplicate, default=False)),
        "duplicate_skipped": bool(first_truthy(stored_again.skipped_duplicate, not stored_again.inserted, default=False)),
        "first_edge_insert_or_present": bool(first_truthy(first_edge, stored.key_digest in edge_children, default=False)),
        "second_edge_inserted": second_edge,
        "duplicate_edge_skipped": dup_edge is False,
        "existing_edges_survived": edge_children == expected_children
        and sorted(item[1] for item in edges_after) == expected_children
        and int(count_edges_after) >= 2,
        "n_edges": int(count_edges),
        "n_receipts": int(count_receipts),
        "no_delete_of_existing_edges": delete_sql_rejected
        and sorted(item[1] for item in edges_after) == expected_children,
        "delete_sql_rejected": delete_sql_rejected,
        "update_sql_rejected": update_sql_rejected,
        "upsert_sql_rejected": upsert_sql_rejected,
        "forbidden_sql_constants": sql_issues,
        "kernel_forbidden_sql_constants": kernel_sql_issues,
        "kernel_has_insert_sql": kernel_has_insert,
        "has_delete_method": any_in(fn_names, ("delete_edge", "delete_receipt")),
        "has_upsert_task": any_pred(lambda hay: "upsert_task" in hay, (fn_names, call_names)),
        "engine": engine,
        "duckdb_available": duckdb_available,
        "duckdb_used": bool(first_truthy(stored.duckdb_used, engine in {"duckdb", "sqlite3"}, default=False)),
        "requires_duckdb": REQUIRES_DUCKDB,
        "negative_cache_verdict": negative,
        "negative_cache_skips_retry": should_skip_retry(negative),
        "premises_digest": retrieval.lemma_id_digest,
        "premises_from_retrieve": stored.dimensions.get("premises") == retrieval.lemma_id_digest,
        "control_plane": CONTROL_PLANE,
        "control_plane_pin": control,
        "run_warmup_remains_control_plane": control["matches_constant"]
        and control["receipt_store_is_control_plane"] is False
        and control["requires_todo_daemon"] is False,
        "imported_names": sorted(imported),
        "forbidden_imports": forbidden_imports,
        "forbidden_calls": forbidden_calls,
        "uses_fcntl": "fcntl" in imported,
        "compiled": False,
        "lake": False,
        "llama_server_started": False,
        "arena_score": None,
        "score": None,
        "warmup_path": relative_or_str(jsonl, REPO_ROOT),
        "row_after_duplicate_unchanged": payload_after == nested_get(row, "payload_json"),
        "sample": {
            "name": stored.name,
            "lean_tag": stored.lean_tag,
            "verdict": stored.verdict,
            "key_digest": stored.key_digest,
            "dimensions": stored.dimensions,
            "executable_paths": stored.executable_paths.to_dict(),
        },
    })
    from jevops.outer import finalize_ok

    return finalize_ok(
        report,
        report["n_records"] == WARMUP_N,
        report["jsonl_unchanged"],
        report["dimensions_match_duckdb_proof_store"],
        report["all_dimensions_populated"],
        report["dropped_dimension_fail_closed"],
        report["environment_lock_has_executable_paths"],
        not report["environment_lock_has_primary_executable"],
        not report["primary_executable_kwarg"],
        report["primary_executable_payload_rejected"],
        report["filesystem_receipt_exists"],
        report["cas_body_exists"],
        not report["filesystem_has_src"],
        not report["row_has_src"],
        report["tiny_row"],
        report["huge_parent_row_rejected"],
        report["proof_body_rejected"],
        report["insert_only"],
        report["existing_edges_survived"],
        report["no_delete_of_existing_edges"],
        report["delete_sql_rejected"],
        report["update_sql_rejected"],
        report["upsert_sql_rejected"],
        not report["forbidden_sql_constants"],
        not report["kernel_forbidden_sql_constants"],
        report["kernel_has_insert_sql"],
        not report["has_delete_method"],
        not report["has_upsert_task"],
        not forbidden_imports,
        not forbidden_calls,
        report["run_warmup_remains_control_plane"],
        report["negative_cache_skips_retry"],
        report["premises_from_retrieve"],
        report["compiled"] is False,
        report["lake"] is False,
        report["arena_score"] is None,
        report["score"] is None,
        not REQUIRES_DUCKDB,
        not IS_CONTROL_PLANE,
        _dropped,
    )


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-check", action="store_true", help="filesystem + INSERT-only audit; no compile")
    parser.add_argument("--store", action="store_true", help="write one tiny receipt (filesystem, optional DuckDB)")
    parser.add_argument("--name", default="CallElimCorrect.substOldPostSubset")
    parser.add_argument("--tag", default="v4.26.0")
    parser.add_argument("--verdict", default="fail", choices=("pass", "fail", "error", "unknown"))
    parser.add_argument("--body", default="rfl", help="proof body written to CAS only")
    parser.add_argument("--out-dir", type=Path, default=None)
    parser.add_argument("--duckdb", type=Path, default=None, help="optional DuckDB/sqlite file; omitted = filesystem only")
    parser.add_argument("--require-duckdb", action="store_true")
    parser.add_argument("--jsonl", type=Path, default=None)
    from jevops.outer import list_or_none

    args = parser.parse_args(list_or_none(argv))
    if args.store:
        from jevops.outer import if_none, path_or

        jsonl = path_or(args.jsonl, WARMUP_JSONL)
        _raw, _digest, records = load_warmup_records(jsonl)
        retrieval = lra_retrieve.retrieve_by_name(args.name, records)
        receipt, body = _synthetic_receipt(
            name=args.name,
            lean_tag=args.tag,
            verdict=args.verdict,
            body=args.body,
            premises_digest=retrieval.lemma_id_digest,
        )
        from jevops.outer import mkdtemp

        root = if_none(args.out_dir, factory=lambda: mkdtemp(prefix="lra-023-store-"))
        stored = store_receipt(
            receipt,
            root=root,
            body=body,
            duckdb_path=args.duckdb,
            parent_digest=content_digest({"problem": args.name}),
            require_duckdb=args.require_duckdb,
        )
        from jevops.outer import print_json

        print_json(stored.to_public_dict())
        return 0
    if args.self_check or argv is None or argv == []:
        from jevops.outer import print_ok

        return print_ok(self_check(args.jsonl))
    parser.error("choose --self-check or --store")
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

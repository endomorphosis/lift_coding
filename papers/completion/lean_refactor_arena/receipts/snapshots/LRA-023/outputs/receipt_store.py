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
import re
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
import retrieve as lra_retrieve  # noqa: E402
import splice as lra_splice  # noqa: E402

FROZEN_WARMUP_SHA256 = lra_splice.FROZEN_WARMUP_SHA256
WARMUP_N = lra_splice.WARMUP_N
PROTOCOL = "LRA/v1"
RECEIPT_SCHEMA = "lra-proof-receipt/v1"
STORE_SCHEMA = "lra-receipt-store/v1"
PR_ID = "PR-7"
LRAH_ID = "LRAH-008"
CONTROL_PLANE = "papers/completion/lean_refactor_arena/harness/run_warmup.py"
IS_CONTROL_PLANE = False
REQUIRES_TODO_DAEMON = False
REQUIRES_DUCKDB = False
FILESYSTEM_IS_AUTHORITY = True
INSERT_ONLY = True
KERNEL_COMMAND_TEMPLATE = "{lake} env {lean} --json {source_file}"
MEASUREMENT_MAX_HEARTBEATS = 400000
LEAN_NUM_THREADS = 1
NO_NEW_AXIOMS = True
NOT_APPLICABLE = "not-applicable"
DEFAULT_IR = "lean4-proof-body"
DEFAULT_PROPERTY = "statement-preserving-refactor"
DEFAULT_TRANSLATOR = "body-splice-v1"
DEFAULT_BACKEND_ID = "lake-env-lean"
DEFAULT_POLICY = "open_policy_v1"
DEFAULT_RESOURCE = "spark_gb10"
DEFAULT_GENERATOR = "leanstral_local"
MAX_ROW_BYTES = 8192
HEX64 = re.compile(r"^[0-9a-f]{64}$")

# Closed vocabulary copied from DuckDBProofStore@1. Self-check diffs this
# against logic/common/duckdb_proof_store.py and fails on drift.
PROOF_AUTHORITY_DIMENSIONS: tuple[str, ...] = (
    "ir",
    "property",
    "assumptions",
    "premises",
    "translator",
    "solver",
    "toolchain",
    "theorem_registry",
    "policy",
    "resource",
    "tree",
    "backend_id",
    "backend_binary",
    "backend_version",
    "backend_config",
)
PROOF_AUTHORITY_DIMENSION_SET = frozenset(PROOF_AUTHORITY_DIMENSIONS)

ALLOWED_SQL_HEAD = re.compile(
    r"^\s*(CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS|INSERT\s+INTO|SELECT)\b",
    re.IGNORECASE | re.DOTALL,
)
FORBIDDEN_SQL = re.compile(
    r"\b(DELETE\s+FROM|DROP\s+TABLE|UPDATE\s+\w+|MERGE\s+INTO|REPLACE\s+INTO|"
    r"INSERT\s+OR\s+REPLACE|INSERT\s+OR\s+IGNORE|TRUNCATE\s+TABLE|"
    r"ALTER\s+TABLE)\b",
    re.IGNORECASE,
)
SQL_STATEMENT_HEAD = re.compile(
    r"^\s*(DELETE\s+FROM|DROP\s+TABLE|UPDATE\s+|MERGE\s+INTO|REPLACE\s+INTO|"
    r"INSERT\s+OR\s+|TRUNCATE\s+TABLE|ALTER\s+TABLE)\b",
    re.IGNORECASE,
)
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
PROOF_BODY_KEYS = frozenset({"src", "proof_text", "candidate_source", "body", "lean_source"})

RECEIPT_DDL = """
CREATE TABLE IF NOT EXISTS lra_proof_receipts (
    key_digest VARCHAR PRIMARY KEY,
    theorem_name VARCHAR NOT NULL,
    lean_tag VARCHAR NOT NULL,
    body_digest VARCHAR NOT NULL,
    candidate_cid VARCHAR NOT NULL,
    verdict VARCHAR NOT NULL,
    token_count INTEGER,
    elab_proxy DOUBLE,
    dimensions_json VARCHAR NOT NULL,
    executable_paths_json VARCHAR NOT NULL,
    payload_json VARCHAR NOT NULL,
    created_at DOUBLE NOT NULL
)
""".strip()

EDGE_DDL = """
CREATE TABLE IF NOT EXISTS lra_proof_edges (
    parent_digest VARCHAR NOT NULL,
    child_digest VARCHAR NOT NULL,
    edge_kind VARCHAR NOT NULL,
    created_at DOUBLE NOT NULL,
    PRIMARY KEY (parent_digest, child_digest, edge_kind)
)
""".strip()

INSERT_RECEIPT_SQL = """
INSERT INTO lra_proof_receipts (
    key_digest, theorem_name, lean_tag, body_digest, candidate_cid,
    verdict, token_count, elab_proxy, dimensions_json,
    executable_paths_json, payload_json, created_at
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
""".strip()

INSERT_EDGE_SQL = """
INSERT INTO lra_proof_edges (
    parent_digest, child_digest, edge_kind, created_at
) VALUES (?, ?, ?, ?)
""".strip()

SELECT_RECEIPT_SQL = (
    "SELECT key_digest, theorem_name, lean_tag, body_digest, candidate_cid, "
    "verdict, token_count, elab_proxy, dimensions_json, executable_paths_json, "
    "payload_json, created_at FROM lra_proof_receipts WHERE key_digest = ?"
)
SELECT_NEGATIVE_SQL = (
    "SELECT key_digest, verdict FROM lra_proof_receipts "
    "WHERE theorem_name = ? AND body_digest = ? AND lean_tag = ?"
)
SELECT_EDGE_SQL = (
    "SELECT parent_digest, child_digest, edge_kind, created_at "
    "FROM lra_proof_edges WHERE parent_digest = ?"
)
SELECT_EDGE_ONE_SQL = (
    "SELECT parent_digest, child_digest, edge_kind FROM lra_proof_edges "
    "WHERE parent_digest = ? AND child_digest = ? AND edge_kind = ?"
)
SELECT_COUNT_RECEIPTS_SQL = "SELECT COUNT(*) FROM lra_proof_receipts"
SELECT_COUNT_EDGES_SQL = "SELECT COUNT(*) FROM lra_proof_edges"


class ReceiptStoreError(RuntimeError):
    """Fail-closed receipt-store error."""


class DimensionError(ReceiptStoreError):
    """A PROOF_AUTHORITY_DIMENSIONS key was dropped, empty, or unknown."""


class InsertOnlyError(ReceiptStoreError):
    """SQL outside the INSERT/SELECT/CREATE TABLE IF NOT EXISTS vocabulary."""


@dataclass(frozen=True)
class ExecutablePaths:
    lean: str
    lake: str

    def to_dict(self) -> dict[str, str]:
        return {"lean": self.lean, "lake": self.lake}


@dataclass
class ProofReceipt:
    name: str
    lean_tag: str
    body_digest: str
    verdict: str
    executable_paths: ExecutablePaths
    generator: str = DEFAULT_GENERATOR
    policy: str = DEFAULT_POLICY
    resource: str = DEFAULT_RESOURCE
    translator: str = DEFAULT_TRANSLATOR
    backend_id: str = DEFAULT_BACKEND_ID
    git_commit: str = NOT_APPLICABLE
    lean_version: str = NOT_APPLICABLE
    backend_config_digest: str = ""
    premises_digest: str = ""
    token_count: Optional[int] = None
    elab_proxy: Optional[float] = None
    hardware_class: str = DEFAULT_RESOURCE
    kernel_command_template: str = KERNEL_COMMAND_TEMPLATE
    candidate_cid: str = ""
    created_at: float = 0.0
    arena_score: None = None
    score: None = None
    official_score: None = None
    duckdb_used: bool = False
    inserted: bool = False
    skipped_duplicate: bool = False
    filesystem_path: str = ""
    dimensions: dict[str, str] = field(default_factory=dict)
    key_digest: str = ""

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "schema": RECEIPT_SCHEMA,
            "protocol": PROTOCOL,
            "name": self.name,
            "lean_tag": self.lean_tag,
            "body_digest": self.body_digest,
            "candidate_cid": self.candidate_cid,
            "verdict": self.verdict,
            "token_count": self.token_count,
            "elab_proxy": self.elab_proxy,
            "generator": self.generator,
            "policy": self.policy,
            "resource": self.resource,
            "hardware_class": self.hardware_class,
            "executable_paths": self.executable_paths.to_dict(),
            "kernel_command_template": self.kernel_command_template,
            "dimensions": dict(self.dimensions),
            "key_digest": self.key_digest,
            "git_commit": self.git_commit,
            "lean_version": self.lean_version,
            "premises_digest": self.premises_digest,
            "arena_score": self.arena_score,
            "score": self.score,
            "official_score": self.official_score,
            "control_plane": CONTROL_PLANE,
            "is_control_plane": IS_CONTROL_PLANE,
            "filesystem_authority": FILESYSTEM_IS_AUTHORITY,
            "insert_only": INSERT_ONLY,
            "upsert_task": False,
            "duckdb_used": self.duckdb_used,
            "inserted": self.inserted,
            "skipped_duplicate": self.skipped_duplicate,
            "filesystem_path": self.filesystem_path,
            "pr": PR_ID,
            "lrah": LRAH_ID,
        }


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def content_digest(value: Any) -> str:
    return sha256_bytes(canonical_bytes(value))


def not_applicable_digest() -> str:
    return content_digest(NOT_APPLICABLE)


def load_warmup_records(path: Optional[Path] = None) -> tuple[bytes, str, list[dict[str, Any]]]:
    return lra_splice.load_warmup_records(path)


def closed_dimensions_from_source(path: Path = PROOF_STORE_SOURCE) -> tuple[str, ...]:
    """Parse PROOF_AUTHORITY_DIMENSIONS from DuckDBProofStore@1 source."""

    if not path.is_file():
        raise ReceiptStoreError(f"missing proof-store source: {path}")
    text = path.read_text(encoding="utf-8")
    match = re.search(
        r"PROOF_AUTHORITY_DIMENSIONS: Final\[tuple\[str, \.\.\.\]\] = \((.*?)\)",
        text,
        re.S,
    )
    if match is None:
        raise ReceiptStoreError("PROOF_AUTHORITY_DIMENSIONS missing from duckdb_proof_store.py")
    names = tuple(re.findall(r'"([a-z_]+)"', match.group(1)))
    if not names:
        raise ReceiptStoreError("PROOF_AUTHORITY_DIMENSIONS parsed empty")
    return names


def environment_lock_field_names(path: Path = MODELS_SOURCE) -> list[str]:
    """AnnAssign names on EnvironmentLockRecord. No primary_executable field."""

    if not path.is_file():
        raise ReceiptStoreError(f"missing hammer models source: {path}")
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == "EnvironmentLockRecord":
            names: list[str] = []
            for item in node.body:
                if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                    names.append(item.target.id)
            return names
    raise ReceiptStoreError("EnvironmentLockRecord class missing from models.py")


def parse_executable_paths(value: Any) -> ExecutablePaths:
    if isinstance(value, ExecutablePaths):
        paths = value.to_dict()
    elif isinstance(value, Mapping):
        if "primary_executable" in value:
            raise ReceiptStoreError("executable_paths must not include primary_executable")
        paths = {str(key): str(item) for key, item in value.items()}
    else:
        raise ReceiptStoreError("executable_paths must be a mapping of lean and lake")
    if set(paths) != {"lean", "lake"}:
        raise ReceiptStoreError("executable_paths must be exactly lean and lake")
    lean = paths["lean"].strip()
    lake = paths["lake"].strip()
    if not lean or not lake:
        raise ReceiptStoreError("executable_paths lean and lake must be nonempty")
    return ExecutablePaths(lean=lean, lake=lake)


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

    premises = receipt.premises_digest or not_applicable_digest()
    backend_config = receipt.backend_config_digest or not_applicable_digest()
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
    missing = PROOF_AUTHORITY_DIMENSION_SET - set(mapping)
    if missing:
        raise DimensionError(f"authority dimension(s) dropped: {', '.join(sorted(missing))}")
    extra = set(mapping) - PROOF_AUTHORITY_DIMENSION_SET
    if extra:
        raise DimensionError(f"unknown authority dimension(s): {', '.join(sorted(extra))}")
    empty = [name for name, value in mapping.items() if not str(value).strip()]
    if empty:
        raise DimensionError(f"authority dimension(s) empty: {', '.join(empty)}")
    return mapping


def receipt_key_digest(receipt: ProofReceipt, dimensions: Mapping[str, str]) -> str:
    return content_digest(
        {
            "body_digest": receipt.body_digest,
            "dimensions": dict(dimensions),
            "lean_tag": receipt.lean_tag,
            "name": receipt.name,
            "schema": RECEIPT_SCHEMA,
        }
    )


def _reject_proof_bodies(payload: Mapping[str, Any]) -> None:
    for key in PROOF_BODY_KEYS:
        if key in payload and payload[key] not in (None, "", []):
            raise ReceiptStoreError(f"proof body field {key!r} is not stored in receipt rows")


def _tiny_payload(payload: Mapping[str, Any]) -> str:
    blob = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    encoded = blob.encode("utf-8")
    if len(encoded) > MAX_ROW_BYTES:
        raise ReceiptStoreError(
            f"receipt row {len(encoded)} bytes exceeds tiny-row cap {MAX_ROW_BYTES}"
        )
    return blob


def sanitize_name(name: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", name).strip("._")
    if not cleaned:
        raise ReceiptStoreError("theorem name sanitizes empty")
    return cleaned


def write_cas_body(root: Path, body: str) -> str:
    data = body.encode("utf-8")
    digest = sha256_bytes(data)
    folder = root / "artifacts" / digest[:2] / digest
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / "candidate.lean"
    if not path.exists():
        path.write_text(body, encoding="utf-8")
    return digest


def filesystem_receipt_path(root: Path, name: str, lean_tag: str) -> Path:
    return root / "receipts" / sanitize_name(name) / f"{lean_tag}.json"


def write_filesystem_receipt(root: Path, receipt: ProofReceipt) -> Path:
    path = filesystem_receipt_path(root, receipt.name, receipt.lean_tag)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = receipt.to_public_dict()
    _reject_proof_bodies(payload)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def try_import_duckdb() -> Any:
    try:
        import duckdb  # type: ignore[import-not-found]
    except ImportError:
        return None
    return duckdb


def _guard_sql(sql: str) -> str:
    text = sql.strip()
    if not text:
        raise InsertOnlyError("empty SQL")
    if FORBIDDEN_SQL.search(text):
        raise InsertOnlyError(f"forbidden mutating SQL: {text[:120]}")
    if not ALLOWED_SQL_HEAD.match(text):
        raise InsertOnlyError(f"SQL outside INSERT/SELECT/CREATE TABLE IF NOT EXISTS: {text[:120]}")
    return text


class InsertOnlyConnection:
    """Wrap a DuckDB or sqlite3 connection. Only INSERT/SELECT/CREATE IF NOT EXISTS."""

    def __init__(self, raw: Any) -> None:
        self._raw = raw

    def execute(self, sql: str, params: Optional[Sequence[Any]] = None) -> Any:
        guarded = _guard_sql(sql)
        if params is None:
            return self._raw.execute(guarded)
        return self._raw.execute(guarded, list(params))

    def close(self) -> None:
        close = getattr(self._raw, "close", None)
        if callable(close):
            close()


def connect_optional_db(path: Path, *, duckdb_module: Any = None) -> tuple[InsertOnlyConnection, str]:
    """Open DuckDB when the package exists; otherwise sqlite3 (still INSERT-only)."""

    path.parent.mkdir(parents=True, exist_ok=True)
    module = duckdb_module if duckdb_module is not None else try_import_duckdb()
    if module is not None:
        conn = InsertOnlyConnection(module.connect(str(path)))
        return conn, "duckdb"
    conn = InsertOnlyConnection(sqlite3.connect(str(path)))
    return conn, "sqlite3"


def install_schema(conn: InsertOnlyConnection) -> None:
    conn.execute(RECEIPT_DDL)
    conn.execute(EDGE_DDL)


def _integrity_conflict(exc: BaseException) -> bool:
    name = type(exc).__name__.lower()
    text = str(exc).lower()
    needles = ("constraint", "unique", "duplicate", "primary key", "integrity")
    return any(item in name for item in needles) or any(item in text for item in needles)


def insert_receipt_row(conn: InsertOnlyConnection, receipt: ProofReceipt) -> bool:
    """INSERT one tiny row. Existing key is skipped; never DELETE/UPDATE."""

    payload = {
        "candidate_cid": receipt.candidate_cid,
        "generator": receipt.generator,
        "hardware_class": receipt.hardware_class,
        "kernel_command_template": receipt.kernel_command_template,
        "key_digest": receipt.key_digest,
        "schema": RECEIPT_SCHEMA,
    }
    blob = _tiny_payload(payload)
    params = (
        receipt.key_digest,
        receipt.name,
        receipt.lean_tag,
        receipt.body_digest,
        receipt.candidate_cid,
        receipt.verdict,
        receipt.token_count,
        receipt.elab_proxy,
        json.dumps(receipt.dimensions, separators=(",", ":"), sort_keys=True),
        json.dumps(receipt.executable_paths.to_dict(), separators=(",", ":"), sort_keys=True),
        blob,
        receipt.created_at,
    )
    try:
        conn.execute(INSERT_RECEIPT_SQL, params)
        return True
    except Exception as exc:  # noqa: BLE001 — dialect-specific unique errors
        if _integrity_conflict(exc):
            return False
        raise ReceiptStoreError(f"INSERT receipt failed: {exc}") from exc


def insert_edge(
    conn: InsertOnlyConnection,
    parent_digest: str,
    child_digest: str,
    edge_kind: str = "candidate",
    *,
    created_at: Optional[float] = None,
) -> bool:
    """INSERT an edge. Existing edges stay; there is no DELETE."""

    stamp = time.time() if created_at is None else float(created_at)
    try:
        conn.execute(INSERT_EDGE_SQL, (parent_digest, child_digest, edge_kind, stamp))
        return True
    except Exception as exc:  # noqa: BLE001
        if _integrity_conflict(exc):
            return False
        raise ReceiptStoreError(f"INSERT edge failed: {exc}") from exc


def select_edges(conn: InsertOnlyConnection, parent_digest: str) -> list[tuple[str, str, str]]:
    result = conn.execute(SELECT_EDGE_SQL, (parent_digest,))
    rows = result.fetchall()
    return [(str(row[0]), str(row[1]), str(row[2])) for row in rows]


def lookup_receipt(conn: InsertOnlyConnection, key_digest: str) -> Optional[dict[str, Any]]:
    result = conn.execute(SELECT_RECEIPT_SQL, (key_digest,))
    row = result.fetchone()
    if row is None:
        return None
    return {
        "key_digest": row[0],
        "theorem_name": row[1],
        "lean_tag": row[2],
        "body_digest": row[3],
        "candidate_cid": row[4],
        "verdict": row[5],
        "token_count": row[6],
        "elab_proxy": row[7],
        "dimensions_json": row[8],
        "executable_paths_json": row[9],
        "payload_json": row[10],
        "created_at": row[11],
    }


def lookup_negative(
    conn: InsertOnlyConnection,
    theorem_name: str,
    body_digest: str,
    lean_tag: str,
) -> Optional[str]:
    """Return the stored verdict for a failed (theorem, body, toolchain)."""

    result = conn.execute(SELECT_NEGATIVE_SQL, (theorem_name, body_digest, lean_tag))
    row = result.fetchone()
    if row is None:
        return None
    return str(row[1])


def should_skip_retry(verdict: Optional[str]) -> bool:
    return verdict in {"fail", "error"}


def finalize_receipt(receipt: ProofReceipt, *, body: Optional[str] = None) -> ProofReceipt:
    if receipt.executable_paths is None:
        raise ReceiptStoreError("executable_paths required")
    if not HEX64.match(receipt.body_digest):
        if body is not None:
            receipt.body_digest = sha256_bytes(body.encode("utf-8"))
        else:
            raise ReceiptStoreError("body_digest must be sha256 hex")
    if not receipt.candidate_cid:
        receipt.candidate_cid = receipt.body_digest
    receipt.created_at = receipt.created_at or time.time()
    receipt.dimensions = project_dimensions(receipt)
    receipt.key_digest = receipt_key_digest(receipt, receipt.dimensions)
    return receipt


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

    if IS_CONTROL_PLANE or REQUIRES_TODO_DAEMON:
        raise ReceiptStoreError("receipt_store must not be the control plane")
    finalize_receipt(receipt, body=body)
    if body is not None:
        receipt.candidate_cid = write_cas_body(root, body)
        if receipt.body_digest != receipt.candidate_cid:
            raise ReceiptStoreError("body_digest drifted from CAS write")
    path = write_filesystem_receipt(root, receipt)
    receipt.filesystem_path = str(path)
    if duckdb_path is None:
        receipt.duckdb_used = False
        receipt.inserted = False
        return receipt
    module = duckdb_module if duckdb_module is not None else try_import_duckdb()
    if require_duckdb and module is None:
        raise ReceiptStoreError("duckdb package is required for this write but is not installed")
    conn, engine = connect_optional_db(duckdb_path, duckdb_module=module)
    try:
        install_schema(conn)
        inserted = insert_receipt_row(conn, receipt)
        if parent_digest:
            insert_edge(conn, parent_digest, receipt.key_digest)
        commit = getattr(conn._raw, "commit", None)
        if callable(commit):
            commit()
    finally:
        conn.close()
    receipt.duckdb_used = engine == "duckdb"
    receipt.inserted = inserted
    receipt.skipped_duplicate = not inserted
    path = write_filesystem_receipt(root, receipt)
    receipt.filesystem_path = str(path)
    return receipt


def _imported_names(source: str) -> set[str]:
    tree = ast.parse(source)
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                names.add(alias.name.split(".", 1)[0])
                names.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                names.add(node.module.split(".", 1)[0])
                names.add(node.module)
            for alias in node.names:
                names.add(alias.name)
    return names


def _call_func_names(source: str) -> set[str]:
    names: set[str] = set()
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Name):
            names.add(func.id)
        elif isinstance(func, ast.Attribute):
            names.add(func.attr)
    return names


def _keyword_names(source: str) -> set[str]:
    return {
        node.arg
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.keyword) and isinstance(node.arg, str)
    }


def _string_constants(source: str) -> list[str]:
    return [
        node.value
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    ]


def _function_names(source: str) -> set[str]:
    tree = ast.parse(source)
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            names.add(node.name)
    return names


def _forbidden_sql_in_constants(source: str) -> list[str]:
    """Flag string constants that are mutating SQL statements, not prose."""

    issues: list[str] = []
    for value in _string_constants(source):
        stripped = value.strip()
        if SQL_STATEMENT_HEAD.match(stripped) or (
            ALLOWED_SQL_HEAD.match(stripped) and FORBIDDEN_SQL.search(stripped)
        ):
            issues.append(stripped[:80])
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
    digest = sha256_bytes(body.encode("utf-8"))
    receipt = ProofReceipt(
        name=name,
        lean_tag=lean_tag,
        body_digest=digest,
        verdict=verdict,
        executable_paths=ExecutablePaths(
            lean=f"/elan/toolchains/leanprover--lean4---{lean_tag}/bin/lean",
            lake=f"/elan/toolchains/leanprover--lean4---{lean_tag}/bin/lake",
        ),
        premises_digest=premises_digest,
        git_commit=git_commit,
        lean_version=lean_tag,
        token_count=1,
        elab_proxy=None,
    )
    return receipt, body


def _load_control_plane_pin() -> dict[str, Any]:
    cfg = json.loads(SUPERVISOR_JSON.read_text(encoding="utf-8"))
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

    source = Path(__file__).read_text(encoding="utf-8")
    jsonl = Path(path) if path is not None else WARMUP_JSONL
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
    fn_names = _function_names(source)
    control = _load_control_plane_pin()
    duckdb_module = try_import_duckdb()
    duckdb_available = duckdb_module is not None

    dropped_error = ""
    try:
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
    except DimensionError as exc:
        dropped_error = str(exc)

    primary_rejected = False
    try:
        parse_executable_paths({"lean": "/lean", "lake": "/lake", "primary_executable": "/lean"})
    except ReceiptStoreError:
        primary_rejected = True

    huge_rejected = False
    try:
        _tiny_payload({"src": "x" * (MAX_ROW_BYTES + 1)})
    except ReceiptStoreError:
        huge_rejected = True

    body_rejected = False
    try:
        _reject_proof_bodies({"src": "theorem T : True := by rfl"})
    except ReceiptStoreError:
        body_rejected = True

    delete_sql_rejected = False
    try:
        _guard_sql("DELETE" + " FROM lra_proof_edges WHERE parent_digest = 'x'")
    except InsertOnlyError:
        delete_sql_rejected = True

    update_sql_rejected = False
    try:
        _guard_sql("UPDATE" + " lra_proof_receipts SET verdict = 'pass'")
    except InsertOnlyError:
        update_sql_rejected = True

    upsert_sql_rejected = False
    try:
        _guard_sql("INSERT" + " OR REPLACE INTO lra_proof_receipts (key_digest) VALUES ('x')")
    except InsertOnlyError:
        upsert_sql_rejected = True

    with tempfile.TemporaryDirectory(prefix="lra-023-receipt-") as tmp:
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
        fs_payload = json.loads(fs_path.read_text(encoding="utf-8"))
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
        cas_bytes = cas_path.stat().st_size if cas_exists else 0
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
            payload_after = str(row_after["payload_json"] if row_after else "")
        finally:
            conn.close()

    dim_keys = list(stored.dimensions)
    fs_dim_keys = list(fs_payload.get("dimensions") or {})
    row_dims = json.loads(row["dimensions_json"]) if row else {}
    exec_paths = json.loads(row["executable_paths_json"]) if row else {}
    row_payload = json.loads(row["payload_json"]) if row else {}
    edge_children = sorted(item[1] for item in edges)
    expected_children = sorted({stored.key_digest, second_child})

    report = {
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
        "row_payload_bytes": len(row["payload_json"].encode("utf-8")) if row else -1,
        "tiny_row": (len(row["payload_json"].encode("utf-8")) if row else MAX_ROW_BYTES + 1) <= MAX_ROW_BYTES,
        "huge_parent_row_rejected": huge_rejected,
        "proof_body_rejected": body_rejected,
        "insert_only": INSERT_ONLY,
        "insert_receipt": stored.inserted or stored.skipped_duplicate,
        "duplicate_skipped": stored_again.skipped_duplicate or not stored_again.inserted,
        "first_edge_insert_or_present": first_edge or stored.key_digest in edge_children,
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
        "has_delete_method": "delete_edge" in fn_names or "delete_receipt" in fn_names,
        "has_upsert_task": "upsert_task" in fn_names or "upsert_task" in call_names,
        "engine": engine,
        "duckdb_available": duckdb_available,
        "duckdb_used": stored.duckdb_used or engine in {"duckdb", "sqlite3"},
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
        "warmup_path": str(jsonl.relative_to(REPO_ROOT)),
        "row_after_duplicate_unchanged": payload_after == (row["payload_json"] if row else None),
        "sample": {
            "name": stored.name,
            "lean_tag": stored.lean_tag,
            "verdict": stored.verdict,
            "key_digest": stored.key_digest,
            "dimensions": stored.dimensions,
            "executable_paths": stored.executable_paths.to_dict(),
        },
    }
    report["ok"] = bool(
        report["n_records"] == WARMUP_N
        and report["jsonl_unchanged"]
        and report["dimensions_match_duckdb_proof_store"]
        and report["all_dimensions_populated"]
        and report["dropped_dimension_fail_closed"]
        and report["environment_lock_has_executable_paths"]
        and not report["environment_lock_has_primary_executable"]
        and not report["primary_executable_kwarg"]
        and report["primary_executable_payload_rejected"]
        and report["filesystem_receipt_exists"]
        and report["cas_body_exists"]
        and not report["filesystem_has_src"]
        and not report["row_has_src"]
        and report["tiny_row"]
        and report["huge_parent_row_rejected"]
        and report["proof_body_rejected"]
        and report["insert_only"]
        and report["existing_edges_survived"]
        and report["no_delete_of_existing_edges"]
        and report["delete_sql_rejected"]
        and report["update_sql_rejected"]
        and report["upsert_sql_rejected"]
        and not report["forbidden_sql_constants"]
        and not report["has_delete_method"]
        and not report["has_upsert_task"]
        and not forbidden_imports
        and not forbidden_calls
        and report["run_warmup_remains_control_plane"]
        and report["negative_cache_skips_retry"]
        and report["premises_from_retrieve"]
        and report["compiled"] is False
        and report["lake"] is False
        and report["arena_score"] is None
        and report["score"] is None
        and not REQUIRES_DUCKDB
        and not IS_CONTROL_PLANE
    )
    return report


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
    args = parser.parse_args(list(argv) if argv is not None else None)
    if args.store:
        jsonl = args.jsonl if args.jsonl is not None else WARMUP_JSONL
        _raw, _digest, records = load_warmup_records(jsonl)
        retrieval = lra_retrieve.retrieve_by_name(args.name, records)
        receipt, body = _synthetic_receipt(
            name=args.name,
            lean_tag=args.tag,
            verdict=args.verdict,
            body=args.body,
            premises_digest=retrieval.lemma_id_digest,
        )
        root = args.out_dir if args.out_dir is not None else Path(tempfile.mkdtemp(prefix="lra-023-store-"))
        stored = store_receipt(
            receipt,
            root=root,
            body=body,
            duckdb_path=args.duckdb,
            parent_digest=content_digest({"problem": args.name}),
            require_duckdb=args.require_duckdb,
        )
        json.dump(stored.to_public_dict(), sys.stdout, indent=2, sort_keys=True)
        sys.stdout.write("\n")
        return 0
    if args.self_check or argv is None or argv == []:
        report = self_check(args.jsonl)
        json.dump(report, sys.stdout, indent=2, sort_keys=True)
        sys.stdout.write("\n")
        return 0 if report["ok"] else 1
    parser.error("choose --self-check or --store")
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

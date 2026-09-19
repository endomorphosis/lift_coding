#!/usr/bin/env python3
"""Lake-native tactic try for Lean Refactor Arena loop v2 (path A).

Replace the proof body with ``sorry``, then try a fixed tactic list via
tag-pinned ``lake env lean`` and ``run_lean_process``. No
``LeanFrontend.snapshot_goal`` and no ``GoalSnapshot``. Loop v1 (30 Sep)
does not run this. Do not claim HAMMER-006 is LRA-ready. Path B (a
lake-aware frontend sibling) is a follow-up, not this module.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import re
import resource
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
DATASETS_ROOT = REPO_ROOT / "external" / "ipfs_datasets"
LEAN_FRONTEND_PATH = (
    DATASETS_ROOT / "ipfs_datasets_py" / "logic" / "hammers" / "frontends" / "lean.py"
)

if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
import _jevops_path  # noqa: E402,F401
import bake_oleans as lra_bake  # noqa: E402
import compile_worker as lra_compile  # noqa: E402
import splice as lra_splice  # noqa: E402

if str(DATASETS_ROOT) not in sys.path:
    sys.path.insert(0, str(DATASETS_ROOT))
from ipfs_datasets_py.logic.hammers.frontends.lean_toolchain import (  # noqa: E402
    KERNEL_COMMAND_TEMPLATE,
    LeanToolchainMissing,
    audit_lean_frontend_path_json,
    run_lean_process,
)

FROZEN_WARMUP_SHA256 = lra_splice.FROZEN_WARMUP_SHA256
WARMUP_N = lra_splice.WARMUP_N
STRATA_SOURCE = lra_bake.STRATA_SOURCE
PUTNAM_SOURCE = lra_bake.PUTNAM_SOURCE
STRATA_FIRST_TAG = lra_bake.STRATA_FIRST_TAG
STRATA_FIRST_COMMIT = lra_bake.STRATA_FIRST_COMMIT
STRATA_URL = lra_bake.STRATA_URL
STRATA_FIRST_FILE = lra_compile.STRATA_FIRST_FILE
MEASUREMENT_MAX_HEARTBEATS = lra_bake.MEASUREMENT_MAX_HEARTBEATS
MEASUREMENT_ARGV_TEMPLATE = lra_compile.MEASUREMENT_ARGV_TEMPLATE
LEAN_NUM_THREADS = lra_compile.LEAN_NUM_THREADS
PROCESS_SUPERVISOR_ENV = lra_compile.PROCESS_SUPERVISOR_ENV
INDEPENDENT_KERNEL_VERIFIER_DEFAULT_TIMEOUT_SECONDS = (
    lra_compile.INDEPENDENT_KERNEL_VERIFIER_DEFAULT_TIMEOUT_SECONDS
)

LOOP_VERSION = "v2"
PATH_NAME = "A"
ON_30_SEP_CRITICAL_PATH = False
V1_RUNS_THIS = False
HAMMER_006_LRA_READY = False
USES_SNAPSHOT_GOAL = False
GOAL_SNAPSHOT_REQUIRED = False
PATH_B_IMPLEMENTED = False
GENERATOR_IDENTITY = "lake_native"
RECEIPT_SCHEMA = "lra-lake-native-try/v1"
PROTOCOL = "LRA/v1"
PR_ID = "PR-5"
LRAH_ID = "LRAH-005"
HAMMER_006_CLAIM = "Do not claim HAMMER-006 is LRA-ready."
CRITICAL_PATH_NOTE = "Not on the 30 Sep critical path."
FIXED_TACTICS: tuple[str, ...] = ("rfl", "decide", "omega", "simp_all")
AESOP_TACTIC = "aesop"
SORRY_TACTIC = "sorry"
TACTIC_TIMEOUT_SECONDS = 120.0
UNSOLVED_RELPATH = "Strata/Unsolved.lean"

FORBIDDEN_IMPORT_NAMES = frozenset(
    {
        "fcntl",
        "IndependentKernelVerifier",
        "KernelVerifier",
        "LeanFrontend",
        "GoalSnapshot",
        "LeanLakeFrontend",
        "attempt_native_automation",
        "LeanReconstructor",
        "LeanstralProofProvider",
        "leanstral_proof_provider",
        "shutil",
    }
)
FORBIDDEN_CALLS = frozenset(
    {
        "which",
        "find_executable",
        "LOCK_EX",
        "snapshot_goal",
        "attempt_native_automation",
    }
)
FORBIDDEN_ATTRS = frozenset(
    {
        "snapshot_goal",
        "GoalSnapshot",
        "LeanFrontend",
        "attempt_native_automation",
        "LOCK_EX",
        "find_executable",
    }
)
FORBIDDEN_SCORE_NAMES = frozenset(
    {
        "arena_score",
        "arena_score_tokens",
        "arena_score_elab",
        "official_track2_score",
        "token_savings",
    }
)

_AESOP_IMPORT = re.compile(r"(?m)^\s*import\s+Aesop\b")


class TryError(RuntimeError):
    """Fail-closed lake-native tactic-try error."""


class TryToolchainMissing(TryError):
    """Tag-pinned elan lake/lean is not installed. Not a PATH fallback."""


@dataclass
class TacticAttempt:
    """One ``lake env lean`` invocation for a single tactic (or the sorry hole)."""

    tactic: str = ""
    argv: list[str] = field(default_factory=list)
    cwd: str = ""
    source_file: str = ""
    exit_code: int = -1
    timed_out: bool = False
    timeout_seconds: float = TACTIC_TIMEOUT_SECONDS
    stdout: str = ""
    stderr: str = ""
    stdout_digest: str = ""
    axiom_names: list[str] = field(default_factory=list)
    axiom_digest: str = ""
    sorryAx: bool = False
    wall_ms: float = 0.0
    cpu_ms: float = 0.0
    measurement_maxHeartbeats: int = MEASUREMENT_MAX_HEARTBEATS
    ok: bool = False
    error: str = ""
    used_snapshot_goal: bool = False
    used_lean_frontend: bool = False
    used_goal_snapshot: bool = False
    generator: str = GENERATOR_IDENTITY
    arena_score: None = None
    score: None = None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["arena_score"] = None
        payload["score"] = None
        payload["used_snapshot_goal"] = False
        payload["used_lean_frontend"] = False
        payload["used_goal_snapshot"] = False
        payload["generator"] = GENERATOR_IDENTITY
        return payload


@dataclass
class TacticTryReceipt:
    """Loop v2 path A receipt. HAMMER-006 / snapshot_goal are unused."""

    schema: str = RECEIPT_SCHEMA
    name: str = ""
    source: str = ""
    file_path: str = ""
    url: str = ""
    lean_tag: str = ""
    git_commit: str = ""
    sorry_template_digest: str = ""
    sorry_template_prefix_bound: bool = False
    aesop_imported: bool = False
    tactics_considered: list[str] = field(default_factory=list)
    tactics_run: list[str] = field(default_factory=list)
    sorry_attempt: Optional[dict[str, Any]] = None
    attempts: list[dict[str, Any]] = field(default_factory=list)
    winning_tactic: Optional[str] = None
    ok: bool = False
    loop: str = LOOP_VERSION
    path: str = PATH_NAME
    pr: str = PR_ID
    lrah: str = LRAH_ID
    on_30_sep_critical_path: bool = ON_30_SEP_CRITICAL_PATH
    v1_runs_this: bool = V1_RUNS_THIS
    hammer_006_lra_ready: bool = HAMMER_006_LRA_READY
    uses_snapshot_goal: bool = USES_SNAPSHOT_GOAL
    goal_snapshot_required: bool = GOAL_SNAPSHOT_REQUIRED
    path_b_implemented: bool = PATH_B_IMPLEMENTED
    generator: str = GENERATOR_IDENTITY
    kernel_command_template: str = KERNEL_COMMAND_TEMPLATE
    measurement_argv_template: str = MEASUREMENT_ARGV_TEMPLATE
    timeout_seconds: float = TACTIC_TIMEOUT_SECONDS
    error: str = ""
    arena_score: None = None
    score: None = None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["arena_score"] = None
        payload["score"] = None
        payload["on_30_sep_critical_path"] = False
        payload["v1_runs_this"] = False
        payload["hammer_006_lra_ready"] = False
        payload["uses_snapshot_goal"] = False
        payload["goal_snapshot_required"] = False
        payload["path_b_implemented"] = False
        payload["loop"] = LOOP_VERSION
        payload["path"] = PATH_NAME
        payload["generator"] = GENERATOR_IDENTITY
        return payload


def sha256_bytes(data: bytes) -> str:
    from jevops.outer import digest_hex

    return digest_hex(data)


def sha256_file(path: Path) -> str:
    from jevops.outer import digest_file

    return digest_file(path)


def sha256_text(text: str) -> str:
    from jevops.outer import digest_text

    return digest_text(text)


def aesop_imported(record: Mapping[str, Any]) -> bool:
    from jevops.outer import any_search

    return any_search((record.get("header") or "", record.get("src") or ""), _AESOP_IMPORT)


def tactics_for_record(record: Mapping[str, Any]) -> list[str]:
    tactics = list(FIXED_TACTICS)
    if aesop_imported(record):
        tactics.append(AESOP_TACTIC)
    return tactics


def sorry_lake_source(record: Mapping[str, Any]) -> str:
    split = lra_splice.split_statement_body(record)
    return lra_splice.lake_candidate_source(
        header=split.header,
        statement=split.statement,
        tactic_block=SORRY_TACTIC,
    )


def tactic_lake_source(record: Mapping[str, Any], tactic: str) -> str:
    if not isinstance(tactic, str) or not tactic.strip():
        raise TryError("tactic must be a nonempty string")
    if tactic.strip() != tactic.split()[0]:
        raise TryError(f"path A tries a single tactic name, not a script: {tactic!r}")
    split = lra_splice.split_statement_body(record)
    return lra_splice.lake_candidate_source(
        header=split.header,
        statement=split.statement,
        tactic_block=tactic.strip(),
    )


def write_tactic_source(record: Mapping[str, Any], dest: Path, tactic: str) -> Path:
    from jevops.outer import write_text

    text = (
        sorry_lake_source(record) if tactic == SORRY_TACTIC else tactic_lake_source(record, tactic)
    )
    return write_text(
        dest,
        text,
        refuse=lra_bake.FORBIDDEN_PUTNAM_BASENAME,
        error_cls=TryError,
        refuse_fmt="refusing to write {name}",
    )


def _attempt_from_result(
    *,
    tactic: str,
    argv: Sequence[str],
    cwd: str,
    source_file: str,
    timeout: float,
    result: Any,
    wall_ms: float,
    cpu_ms: float,
    error: str = "",
) -> TacticAttempt:
    from jevops.outer import process_exit_code

    stdout = getattr(result, "stdout", "") or ""
    stderr = getattr(result, "stderr", "") or ""
    result_error = getattr(result, "error", None)
    exit_code, timed_out = process_exit_code(result)
    axiom_names, sorry = lra_compile.parse_axioms(stdout, stderr)
    attempt = TacticAttempt(
        tactic=tactic,
        argv=list(argv),
        cwd=cwd,
        source_file=source_file,
        exit_code=exit_code,
        timed_out=timed_out,
        timeout_seconds=timeout,
        stdout=stdout,
        stderr=stderr,
        stdout_digest=sha256_text(stdout),
        axiom_names=axiom_names,
        axiom_digest=lra_compile.axiom_digest(axiom_names),
        sorryAx=sorry,
        wall_ms=wall_ms,
        cpu_ms=cpu_ms,
        measurement_maxHeartbeats=MEASUREMENT_MAX_HEARTBEATS,
        error=error or (str(result_error) if result_error else ""),
    )
    attempt.ok = (
        exit_code == 0
        and not timed_out
        and not attempt.error
        and not sorry
        and "sorryAx" not in axiom_names
        and tactic != SORRY_TACTIC
        and bool(stdout.strip())
        and len(argv) >= 6
        and Path(argv[0]).name == "lake"
        and argv[1] == "env"
        and Path(argv[2]).name == "lean"
        and argv[3] == f"-DmaxHeartbeats={MEASUREMENT_MAX_HEARTBEATS}"
        and argv[4] == "--json"
        and not attempt.used_snapshot_goal
        and not attempt.used_lean_frontend
    )
    return attempt


def _run_tactic(
    record: Mapping[str, Any],
    *,
    tactic: str,
    dest: Path,
    source_file: str,
    cwd: Path,
    lake_path: str,
    lean_path: str,
    timeout: float,
    env: Mapping[str, str],
) -> TacticAttempt:
    write_tactic_source(record, dest, tactic)
    argv = lra_compile.measurement_argv(
        lake_path,
        lean_path,
        source_file,
        max_heartbeats=MEASUREMENT_MAX_HEARTBEATS,
    )
    from jevops.outer import timed_call

    result, wall_ms, cpu_ms = timed_call(
        lambda: run_lean_process(
            argv,
            timeout=timeout,
            cwd=str(cwd),
            env=dict(env),
        )
    )
    return _attempt_from_result(
        tactic=tactic,
        argv=argv,
        cwd=str(cwd),
        source_file=source_file,
        timeout=timeout,
        result=result,
        wall_ms=wall_ms,
        cpu_ms=cpu_ms,
    )


def _prepare_project(
    record: Mapping[str, Any],
    pin: lra_compile.VersionPin,
    *,
    state_root: Optional[Path],
    network: str,
    skip_checkout: bool,
) -> tuple[Path, str, Path]:
    source = str(record.get("source") or "")
    relpath = lra_compile.source_relpath(record)
    if source == PUTNAM_SOURCE:
        project = lra_compile.project_dir_for_record(record, pin, state_root=state_root)
        if not (project / "lakefile.lean").is_file():
            lra_bake.materialize_putnam_project(
                pin.lean_tag, project, jsonl_version_pin=pin.git_commit
            )
        dest = project / lra_bake.PUTNAM_CANDIDATE_RELPATH
        return project, lra_bake.PUTNAM_CANDIDATE_RELPATH, dest
    cwd = lra_compile.require_clone(
        str(record.get("url") or ""), network=network, state_root=state_root
    )
    if not skip_checkout:
        lra_compile.checkout_commit(cwd, pin.git_commit)
    dest = cwd / relpath
    return cwd, relpath, dest


def try_tactics(
    record: Mapping[str, Any],
    pin: lra_compile.VersionPin,
    *,
    timeout: float = TACTIC_TIMEOUT_SECONDS,
    state_root: Optional[Path] = None,
    elan_home: Optional[Path] = None,
    network: str = "allow",
    skip_checkout: bool = False,
) -> TacticTryReceipt:
    """Path A: sorry hole, then ``rfl``/``decide``/``omega``/``simp_all``/``aesop``."""

    timeout = lra_compile.require_lake_timeout(timeout)
    name = str(record.get("name") or "")
    source = str(record.get("source") or "")
    considered = tactics_for_record(record)
    split = lra_splice.split_statement_body(record)
    template = lra_splice.statement_sorry_template(split.statement)
    lake_sorry = sorry_lake_source(record)
    receipt = TacticTryReceipt(
        name=name,
        source=source,
        file_path=lra_compile.source_relpath(record),
        url=str(record.get("url") or ""),
        lean_tag=pin.lean_tag,
        git_commit=pin.git_commit,
        sorry_template_digest=sha256_text(template),
        sorry_template_prefix_bound=template.startswith(split.statement)
        and template == split.statement + lra_splice.STATEMENT_SORRY_SUFFIX
        and template in lake_sorry,
        aesop_imported=aesop_imported(record),
        tactics_considered=list(considered),
        timeout_seconds=timeout,
    )
    if AESOP_TACTIC in considered and not receipt.aesop_imported:
        receipt.error = "aesop listed without an Aesop import"
        receipt.ok = False
        return receipt
    if AESOP_TACTIC not in considered and receipt.aesop_imported:
        receipt.error = "Aesop imported but aesop was omitted from the tactic list"
        receipt.ok = False
        return receipt
    try:
        toolchain = lra_compile.resolve_pin(pin, elan_home=elan_home, require_installed=True)
        cwd, source_file, dest = _prepare_project(
            record,
            pin,
            state_root=state_root,
            network=network,
            skip_checkout=skip_checkout,
        )
        env = os.environ.copy()
        env["LEAN_NUM_THREADS"] = str(LEAN_NUM_THREADS)
        env["ELAN_HOME"] = toolchain.elan_home
        supervisor_dir = (
            Path(state_root) / "process-supervisor"
            if state_root is not None
            else Path(tempfile.gettempdir()) / "lra-021-process-supervisor"
        )
        supervisor_dir.mkdir(parents=True, exist_ok=True)
        env[PROCESS_SUPERVISOR_ENV] = str(supervisor_dir)
        sorry_attempt = _run_tactic(
            record,
            tactic=SORRY_TACTIC,
            dest=dest,
            source_file=source_file,
            cwd=cwd,
            lake_path=toolchain.lake_path,
            lean_path=toolchain.lean_path,
            timeout=timeout,
            env=env,
        )
        receipt.sorry_attempt = sorry_attempt.to_dict()
        if sorry_attempt.ok:
            receipt.error = "sorry hole must not be a successful tactic try"
            receipt.ok = False
            return receipt
        attempts: list[TacticAttempt] = []
        winner: Optional[str] = None
        for tactic in considered:
            attempt = _run_tactic(
                record,
                tactic=tactic,
                dest=dest,
                source_file=source_file,
                cwd=cwd,
                lake_path=toolchain.lake_path,
                lean_path=toolchain.lean_path,
                timeout=timeout,
                env=env,
            )
            attempts.append(attempt)
            receipt.tactics_run.append(tactic)
            if attempt.ok:
                winner = tactic
                break
        receipt.attempts = [item.to_dict() for item in attempts]
        receipt.winning_tactic = winner
        receipt.ok = winner is not None and all(
            not item.used_snapshot_goal and Path(item.argv[0]).name == "lake"
            for item in attempts
        )
        return receipt
    except (TryError, lra_compile.CompileError, LeanToolchainMissing, lra_bake.BakeError) as exc:
        receipt.error = str(exc)
        receipt.ok = False
        if isinstance(exc, (LeanToolchainMissing, lra_compile.CompileToolchainMissing)):
            receipt.error = (
                f"{exc}; tag-pinned elan is a capability gap, not PATH lean "
                "usability and not LeanFrontend.snapshot_goal"
            )
        return receipt


def first_record_of_source(
    records: Sequence[Mapping[str, Any]], source: str
) -> Mapping[str, Any]:
    from jevops.outer import first_where

    return first_where(
        records,
        lambda record: record.get("source") == source,
        error_cls=TryError,
        miss=f"warmup JSONL has no {source} record",
    )


def pin_for_tag(record: Mapping[str, Any], lean_tag: str) -> lra_compile.VersionPin:
    from jevops.outer import first_or_last

    return first_or_last(
        lra_compile.iter_version_pins(record.get("version_info")),
        lambda pin: pin.lean_tag == lean_tag,
        error_cls=TryError,
        miss=f"{record.get('name')}: no version_info pins",
    )


def plan_try(path: Optional[Path] = None) -> dict[str, Any]:
    jsonl = Path(path) if path is not None else WARMUP_JSONL
    raw, digest, records = lra_splice.load_warmup_records(jsonl)
    per_record = []
    for record in records:
        considered = tactics_for_record(record)
        per_record.append(
            {
                "aesop_imported": aesop_imported(record),
                "name": str(record.get("name") or ""),
                "source": str(record.get("source") or ""),
                "tactics": considered,
                "aesop_in_list": AESOP_TACTIC in considered,
            }
        )
    first = first_record_of_source(records, STRATA_SOURCE)
    putnam = first_record_of_source(records, PUTNAM_SOURCE)
    return {
        "arena_score": None,
        "score": None,
        "aesop_if_imported": True,
        "critical_path_note": CRITICAL_PATH_NOTE,
        "fixed_tactics": list(FIXED_TACTICS),
        "first_putnam_name": str(putnam.get("name") or ""),
        "first_putnam_tactics": tactics_for_record(putnam),
        "first_strata_name": str(first.get("name") or ""),
        "first_strata_tactics": tactics_for_record(first),
        "frozen_warmup_sha256": digest,
        "generator": GENERATOR_IDENTITY,
        "goal_snapshot_required": GOAL_SNAPSHOT_REQUIRED,
        "hammer_006_claim": HAMMER_006_CLAIM,
        "hammer_006_lra_ready": HAMMER_006_LRA_READY,
        "jsonl_bytes": len(raw),
        "kernel_command_template": KERNEL_COMMAND_TEMPLATE,
        "loop": LOOP_VERSION,
        "lrah": LRAH_ID,
        "measurement_argv_template": MEASUREMENT_ARGV_TEMPLATE,
        "n_records": len(records),
        "on_30_sep_critical_path": ON_30_SEP_CRITICAL_PATH,
        "path": PATH_NAME,
        "path_b_implemented": PATH_B_IMPLEMENTED,
        "pr": PR_ID,
        "protocol": PROTOCOL,
        "records": per_record,
        "run_lean_process": run_lean_process.__name__,
        "sorry_template": "statement + ' := by\\nsorry'",
        "tactic_timeout_seconds": TACTIC_TIMEOUT_SECONDS,
        "uses_snapshot_goal": USES_SNAPSHOT_GOAL,
        "v1_runs_this": V1_RUNS_THIS,
    }


def probe_toolchain(tags: Optional[Sequence[str]] = None) -> dict[str, Any]:
    payload = lra_compile.probe_toolchain(tags)
    payload["arena_score"] = None
    payload["score"] = None
    payload["generator"] = GENERATOR_IDENTITY
    payload["goal_snapshot_required"] = False
    payload["hammer_006_lra_ready"] = False
    payload["lake_native_try"] = True
    payload["loop"] = LOOP_VERSION
    payload["on_30_sep_critical_path"] = False
    payload["path"] = PATH_NAME
    payload["path_b_implemented"] = False
    payload["tactic_timeout_seconds"] = TACTIC_TIMEOUT_SECONDS
    payload["uses_snapshot_goal"] = False
    payload["v1_runs_this"] = False
    payload["live_elan_usable"] = False if payload.get("capability_gap") else bool(
        payload.get("installed_tags")
    )
    if payload.get("capability_gap"):
        payload["live_elan_usable"] = False
        payload["snapshot_goal_usable_for_lake_projects"] = False
    else:
        payload["snapshot_goal_usable_for_lake_projects"] = False
    return payload


def write_receipts(receipts: Sequence[TacticTryReceipt], dest_dir: Path) -> list[str]:
    from jevops.outer import write_named_jsons

    return write_named_jsons(
        dest_dir,
        receipts,
        name_fn=lambda item: item.name,
        tag_fn=lambda item: item.lean_tag,
        payload_fn=lambda item: item.to_dict(),
    )


def _imported_names(source: str) -> set[str]:
    from jevops.repair import imported_names

    return imported_names(source)


def _call_name(node: ast.AST) -> str:
    from jevops.repair import call_short_name

    return call_short_name(node)


def _assigned_constant(tree: ast.AST, name: str) -> Any:
    from jevops.repair import assigned_constant

    return assigned_constant(tree, name)


def audit_source(source: Optional[str] = None) -> dict[str, Any]:
    from jevops.repair import assigned_constants, audit_source as _audit

    text = Path(__file__).read_text(encoding="utf-8") if source is None else source
    out = _audit(
        text,
        forbidden_imports=FORBIDDEN_IMPORT_NAMES,
        forbidden_calls=FORBIDDEN_CALLS,
        forbidden_scores=FORBIDDEN_SCORE_NAMES,
        forbidden_attrs=FORBIDDEN_ATTRS,
    )
    imported = set(out["imported_names"])
    calls = set(out["call_names"])
    score_assignments = list(out["score_keys"])
    frontend = audit_lean_frontend_path_json()
    consts = assigned_constants(
        text,
        (
            "HAMMER_006_LRA_READY",
            "ON_30_SEP_CRITICAL_PATH",
            "V1_RUNS_THIS",
            "USES_SNAPSHOT_GOAL",
            "LOOP_VERSION",
            "PATH_NAME",
        ),
    )
    hammer_ready = consts["HAMMER_006_LRA_READY"]
    on_critical = consts["ON_30_SEP_CRITICAL_PATH"]
    v1_runs = consts["V1_RUNS_THIS"]
    uses_snapshot = consts["USES_SNAPSHOT_GOAL"]
    loop_value = consts["LOOP_VERSION"]
    path_value = consts["PATH_NAME"]
    return {
        "imported_names": out["imported_names"],
        "forbidden_imports": out["forbidden_imports"],
        "forbidden_calls": out["forbidden_calls"],
        "forbidden_attrs": out["forbidden_attrs"],
        "score_assignments": score_assignments,
        "uses_run_lean_process": "run_lean_process" in calls,
        "uses_measurement_argv": "measurement_argv" in calls,
        "uses_statement_sorry_template": "statement_sorry_template" in calls,
        "uses_snapshot_goal_call": "snapshot_goal" in calls,
        "imports_lean_frontend": "LeanFrontend" in imported,
        "imports_goal_snapshot": "GoalSnapshot" in imported,
        "hammer_006_lra_ready_constant": hammer_ready,
        "on_30_sep_critical_path_constant": on_critical,
        "v1_runs_this_constant": v1_runs,
        "uses_snapshot_goal_constant": uses_snapshot,
        "loop_constant": loop_value,
        "path_constant": path_value,
        "lean_frontend": frontend,
        "ok": (
            not out["forbidden_imports"]
            and not out["forbidden_calls"]
            and not out["forbidden_attrs"]
            and not score_assignments
            and "run_lean_process" in calls
            and "measurement_argv" in calls
            and "statement_sorry_template" in calls
            and "snapshot_goal" not in calls
            and "LeanFrontend" not in imported
            and "GoalSnapshot" not in imported
            and hammer_ready is False
            and on_critical is False
            and v1_runs is False
            and uses_snapshot is False
            and loop_value == "v2"
            and path_value == "A"
            and frontend.get("unchanged_path_lean_json") is True
        ),
    }


_FAKE_LAKE = """#!/usr/bin/python3.12
import os
import sys

args = sys.argv[1:]
if not args or args[0] != "env" or len(args) < 2:
    sys.stderr.write("lra-021-fake-lake: expected 'env <lean> ...'\\n")
    sys.exit(2)
os.execv(args[1], args[1:])
"""

_FAKE_LEAN = r"""#!/usr/bin/python3.12
import json
import re
import sys
from pathlib import Path

argv = sys.argv[1:]
heartbeats = None
source = None
has_json = False
for arg in argv:
    if arg.startswith("-DmaxHeartbeats="):
        try:
            heartbeats = int(arg.split("=", 1)[1])
        except ValueError:
            heartbeats = -1
    elif arg == "--json":
        has_json = True
    elif not arg.startswith("-"):
        source = arg

if not has_json:
    sys.stderr.write("lra-021-fake-lean: expected --json\n")
    sys.exit(2)
if heartbeats is None or heartbeats <= 0:
    sys.stderr.write("measurement maxHeartbeats must be finite and positive\n")
    sys.exit(3)
if source is None:
    sys.stderr.write("missing source file\n")
    sys.exit(4)
path = Path(source)
if not path.is_file():
    sys.stderr.write(f"source not found: {source}\n")
    sys.exit(4)
text = path.read_text(encoding="utf-8")
if " := by\n" in text:
    tactic_block = text.rsplit(" := by\n", 1)[-1].strip()
elif " := by" in text:
    tactic_block = text.rsplit(" := by", 1)[-1].strip()
else:
    tactic_block = ""
tactic = tactic_block.split()[0] if tactic_block.split() else ""
aesop_imported = bool(re.search(r"(?m)^\s*import\s+Aesop\b", text))
unsolved = "theorem lra_unsolved" in text
decl = path.stem.replace(".", "_") or "lra_candidate"


def fail(message: str, sorry: bool = False) -> None:
    payload = {"severity": "error", "data": message, "pos": {"line": 1, "column": 0}}
    if sorry:
        payload["data"] = "hasSorry"
        payload["severity"] = "warning"
    print(json.dumps(payload))
    print(f"#print axioms {decl}")
    print(f"{decl} : sorryAx" if sorry else f"{decl} : []")
    sys.exit(1)


def succeed() -> None:
    print(json.dumps({"severity": "information", "data": "ok", "pos": {"line": 1, "column": 0}}))
    print(f"#print axioms {decl}")
    print(f"{decl} : []")
    sys.exit(0)


if tactic == "sorry":
    fail("sorry hole", sorry=True)
if unsolved:
    fail(f"unsolved under {tactic}")
if tactic == "rfl":
    fail("rfl failed on lake-project goal")
if tactic == "aesop":
    if aesop_imported:
        succeed()
    fail("unknown identifier 'aesop' (Aesop not imported)")
if tactic in {"decide", "omega", "simp_all"}:
    if aesop_imported:
        fail(f"{tactic} failed; Putnam synthetic closes with aesop")
    succeed()
fail(f"unknown tactic {tactic!r}")
"""


def _write_executable(path: Path, text: str) -> None:
    from jevops.outer import write_executable

    write_executable(path, text)


def plant_fake_toolchain(elan_home: Path, lean_tag: str) -> Path:
    from jevops.outer import join_under, plant_executables

    toolchain_dir = join_under(
        elan_home, "toolchains", lra_bake.elan_toolchain_dirname(lean_tag), "bin"
    )
    plant_executables(toolchain_dir, {"lake": _FAKE_LAKE, "lean": _FAKE_LEAN})
    return toolchain_dir


def unsolved_record() -> dict[str, Any]:
    statement = "theorem lra_unsolved : False"
    return {
        "name": "lra_unsolved",
        "source": STRATA_SOURCE,
        "statement": statement,
        "src": statement + " := by\nsorry",
        "header": "",
        "file_path": UNSOLVED_RELPATH,
        "url": STRATA_URL,
        "version_info": [{STRATA_FIRST_TAG: STRATA_FIRST_COMMIT}],
        "proof_length": 5,
        "num_lines": 2,
    }


def _attempt_summary(attempt: Mapping[str, Any]) -> dict[str, Any]:
    from jevops.outer import argv_layout

    argv = list(attempt.get("argv") or [])
    return {
        "argv_has_lake_env_lean": argv_layout(
            argv,
            min_len=6,
            names={0: "lake", 2: "lean"},
            eq={
                1: "env",
                3: f"-DmaxHeartbeats={MEASUREMENT_MAX_HEARTBEATS}",
                4: "--json",
            },
        ),
        "argv_tag_pinned": bool(str(attempt.get("cwd") or ""))
        and argv_layout(
            argv,
            min_len=3,
            contains={0: "leanprover--lean4---", 2: "leanprover--lean4---"},
        ),
        "exit_code": attempt.get("exit_code"),
        "ok": bool(attempt.get("ok")),
        "sorryAx": bool(attempt.get("sorryAx")),
        "tactic": attempt.get("tactic"),
        "used_snapshot_goal": bool(attempt.get("used_snapshot_goal")),
        "used_lean_frontend": bool(attempt.get("used_lean_frontend")),
        "generator": attempt.get("generator"),
        "stdout_nonempty": bool(str(attempt.get("stdout") or "").strip()),
        "printed_axioms": "#print axioms" in str(attempt.get("stdout") or ""),
        "timeout_exceeds_ikv_30s": float(attempt.get("timeout_seconds") or 0.0)
        > INDEPENDENT_KERNEL_VERIFIER_DEFAULT_TIMEOUT_SECONDS,
        "arena_score": None,
        "score": None,
    }


def _receipt_summary(receipt: TacticTryReceipt) -> dict[str, Any]:
    attempts = [_attempt_summary(item) for item in receipt.attempts]
    sorry = _attempt_summary(receipt.sorry_attempt) if receipt.sorry_attempt else None
    return {
        "aesop_imported": receipt.aesop_imported,
        "aesop_in_considered": AESOP_TACTIC in receipt.tactics_considered,
        "attempts": attempts,
        "error": receipt.error,
        "generator": receipt.generator,
        "git_commit": receipt.git_commit,
        "hammer_006_lra_ready": receipt.hammer_006_lra_ready,
        "lean_tag": receipt.lean_tag,
        "loop": receipt.loop,
        "name": receipt.name,
        "ok": receipt.ok,
        "on_30_sep_critical_path": receipt.on_30_sep_critical_path,
        "path": receipt.path,
        "path_b_implemented": receipt.path_b_implemented,
        "sorry_attempt": sorry,
        "sorry_failed": sorry is not None and not sorry["ok"] and sorry["sorryAx"],
        "sorry_first": sorry is not None and sorry["tactic"] == SORRY_TACTIC,
        "sorry_template_prefix_bound": receipt.sorry_template_prefix_bound,
        "source": receipt.source,
        "stopped_after_winner": (
            receipt.winning_tactic is not None
            and receipt.tactics_run
            and receipt.tactics_run[-1] == receipt.winning_tactic
            and receipt.tactics_considered.index(receipt.winning_tactic)
            == len(receipt.tactics_run) - 1
        ),
        "tactics_considered": list(receipt.tactics_considered),
        "tactics_run": list(receipt.tactics_run),
        "uses_snapshot_goal": receipt.uses_snapshot_goal,
        "v1_runs_this": receipt.v1_runs_this,
        "winning_tactic": receipt.winning_tactic,
        "all_attempts_lake_env_lean": all(item["argv_has_lake_env_lean"] for item in attempts)
        and (sorry is None or sorry["argv_has_lake_env_lean"]),
        "no_snapshot_goal_on_attempts": all(not item["used_snapshot_goal"] for item in attempts)
        and (sorry is None or not sorry["used_snapshot_goal"]),
        "arena_score": None,
        "score": None,
    }


def _synthetic_try(
    records: Sequence[Mapping[str, Any]],
    *,
    persist_receipts: Optional[Path] = None,
) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(
        prefix="lra-021-try-", dir=str(lra_compile._exec_scratch_parent())
    ) as tmp:
        root = Path(tmp)
        elan_home = root / "elan"
        state_root = root / "state"
        receipts_dir = root / "receipts"
        for tag in ("v4.25.0", "v4.26.0", "v4.27.0"):
            plant_fake_toolchain(elan_home, tag)
        clone = lra_compile.plant_synthetic_strata_clone(
            lra_compile.clone_dir(STRATA_URL, state_root)
        )
        first = first_record_of_source(records, STRATA_SOURCE)
        putnam = first_record_of_source(records, PUTNAM_SOURCE)
        unsolved = unsolved_record()
        write_tactic_source(first, clone / STRATA_FIRST_FILE, SORRY_TACTIC)
        write_tactic_source(unsolved, clone / UNSOLVED_RELPATH, SORRY_TACTIC)
        first_pin = pin_for_tag(first, STRATA_FIRST_TAG)
        putnam_pin = pin_for_tag(putnam, STRATA_FIRST_TAG)
        unsolved_pin = pin_for_tag(unsolved, STRATA_FIRST_TAG)
        timeout_30_rejected = False
        try:
            lra_compile.require_lake_timeout(
                INDEPENDENT_KERNEL_VERIFIER_DEFAULT_TIMEOUT_SECONDS
            )
        except lra_compile.LakeTimeoutTooSmall:
            timeout_30_rejected = True
        strata_receipt = try_tactics(
            first,
            first_pin,
            timeout=TACTIC_TIMEOUT_SECONDS,
            state_root=state_root,
            elan_home=elan_home,
            network="deny",
            skip_checkout=True,
        )
        putnam_receipt = try_tactics(
            putnam,
            putnam_pin,
            timeout=TACTIC_TIMEOUT_SECONDS,
            state_root=state_root,
            elan_home=elan_home,
            network="allow",
            skip_checkout=True,
        )
        unsolved_receipt = try_tactics(
            unsolved,
            unsolved_pin,
            timeout=TACTIC_TIMEOUT_SECONDS,
            state_root=state_root,
            elan_home=elan_home,
            network="deny",
            skip_checkout=True,
        )
        all_receipts = [strata_receipt, putnam_receipt, unsolved_receipt]
        written = write_receipts(all_receipts, receipts_dir)
        persisted: list[str] = []
        if persist_receipts is not None:
            persisted = write_receipts(all_receipts, Path(persist_receipts))
        missing_closed = False
        try:
            lra_compile.require_clone(
                "https://github.com/example/missing-lra-021",
                network="deny",
                state_root=state_root,
            )
        except lra_compile.CloneMissing:
            missing_closed = True
        return {
            "elan_home": str(elan_home),
            "missing_clone_fails_closed_under_network_deny": missing_closed,
            "n_receipts_persisted": len(persisted),
            "n_receipts_written": len(written),
            "persisted_receipts": persisted,
            "putnam": _receipt_summary(putnam_receipt),
            "receipts_written": [Path(path).name for path in written],
            "strata": _receipt_summary(strata_receipt),
            "timeout_30s_rejected": timeout_30_rejected,
            "unsolved": _receipt_summary(unsolved_receipt),
        }


def self_check(
    path: Optional[Path] = None,
    *,
    receipts_dir: Optional[Path] = None,
) -> dict[str, Any]:
    jsonl = Path(path) if path is not None else WARMUP_JSONL
    raw, digest, records = lra_splice.load_warmup_records(jsonl)
    audit = audit_source()
    synthetic = _synthetic_try(records, persist_receipts=receipts_dir)
    toolchain = probe_toolchain()
    plan = plan_try(jsonl)
    strata = synthetic["strata"]
    putnam = synthetic["putnam"]
    unsolved = synthetic["unsolved"]
    putnam_aesop_only = all(
        item["aesop_imported"] and item["aesop_in_list"] for item in plan["records"]
        if item["source"] == PUTNAM_SOURCE
    )
    non_putnam_no_aesop = all(
        (not item["aesop_imported"]) and (not item["aesop_in_list"])
        for item in plan["records"]
        if item["source"] != PUTNAM_SOURCE
    )
    report: dict[str, Any] = {
        "ok": False,
        "arena_score": None,
        "score": None,
        "aesop_only_when_imported": putnam_aesop_only and non_putnam_no_aesop,
        "audit": audit,
        "capability_gap": toolchain.get("capability_gap") or "",
        "compiled": bool(strata["ok"] and putnam["ok"]),
        "critical_path_note": CRITICAL_PATH_NOTE,
        "first_putnam_name": plan["first_putnam_name"],
        "first_strata_name": plan["first_strata_name"],
        "frozen_warmup_sha256": digest,
        "generator": GENERATOR_IDENTITY,
        "goal_snapshot_required": False,
        "hammer_006_claim": HAMMER_006_CLAIM,
        "hammer_006_lra_ready": False,
        "jsonl_bytes": len(raw),
        "jsonl_unchanged": digest == FROZEN_WARMUP_SHA256,
        "kernel_command_template": KERNEL_COMMAND_TEMPLATE,
        "lake": True,
        "lean_frontend_unchanged_path_lean_json": bool(
            audit["lean_frontend"].get("unchanged_path_lean_json")
        ),
        "live_elan_installed": bool(toolchain.get("installed_tags")),
        "llama_server_started": False,
        "loop": LOOP_VERSION,
        "lrah": LRAH_ID,
        "measurement_argv_template": MEASUREMENT_ARGV_TEMPLATE,
        "n_records": len(records),
        "on_30_sep_critical_path": False,
        "path": PATH_NAME,
        "path_a_lake_env_lean": bool(
            strata["all_attempts_lake_env_lean"] and putnam["all_attempts_lake_env_lean"]
        ),
        "path_b_implemented": False,
        "plan": {
            "fixed_tactics": plan["fixed_tactics"],
            "first_putnam_tactics": plan["first_putnam_tactics"],
            "first_strata_tactics": plan["first_strata_tactics"],
        },
        "pr": PR_ID,
        "protocol": PROTOCOL,
        "putnam_aesop_won": putnam["winning_tactic"] == AESOP_TACTIC,
        "putnam_tried_fixed_tactics_before_aesop": putnam["tactics_run"]
        == list(FIXED_TACTICS) + [AESOP_TACTIC],
        "run_lean_process": run_lean_process.__name__,
        "snapshot_goal_required": False,
        "sorry_hole_then_tactic_list": bool(
            strata["sorry_first"]
            and strata["sorry_failed"]
            and putnam["sorry_first"]
            and putnam["sorry_failed"]
        ),
        "strata_decide_won": strata["winning_tactic"] == "decide",
        "strata_rfl_failed_first": (
            strata["tactics_run"][:1] == ["rfl"] and strata["winning_tactic"] == "decide"
        ),
        "synthetic": synthetic,
        "tactic_timeout_seconds": TACTIC_TIMEOUT_SECONDS,
        "toolchain": toolchain,
        "unsolved_has_no_winner": unsolved["winning_tactic"] is None and not unsolved["ok"],
        "unsolved_ran_fixed_tactics": unsolved["tactics_run"] == list(FIXED_TACTICS),
        "uses_snapshot_goal": False,
        "v1_runs_this": False,
        "warmup_path": str(jsonl.relative_to(REPO_ROOT)),
    }
    report["ok"] = bool(
        report["n_records"] == WARMUP_N
        and report["jsonl_unchanged"]
        and report["aesop_only_when_imported"]
        and report["path_a_lake_env_lean"]
        and report["sorry_hole_then_tactic_list"]
        and report["strata_decide_won"]
        and report["strata_rfl_failed_first"]
        and report["putnam_aesop_won"]
        and report["putnam_tried_fixed_tactics_before_aesop"]
        and report["unsolved_has_no_winner"]
        and report["unsolved_ran_fixed_tactics"]
        and strata["stopped_after_winner"]
        and putnam["stopped_after_winner"]
        and strata["sorry_template_prefix_bound"]
        and putnam["sorry_template_prefix_bound"]
        and strata["no_snapshot_goal_on_attempts"]
        and putnam["no_snapshot_goal_on_attempts"]
        and synthetic["timeout_30s_rejected"]
        and synthetic["missing_clone_fails_closed_under_network_deny"]
        and audit["ok"]
        and report["lean_frontend_unchanged_path_lean_json"]
        and report["hammer_006_lra_ready"] is False
        and report["on_30_sep_critical_path"] is False
        and report["v1_runs_this"] is False
        and report["uses_snapshot_goal"] is False
        and report["path_b_implemented"] is False
        and report["goal_snapshot_required"] is False
        and report["arena_score"] is None
        and report["score"] is None
        and report["llama_server_started"] is False
        and report["loop"] == "v2"
        and report["path"] == "A"
    )
    return report


def _print_json(payload: Mapping[str, Any]) -> None:
    from jevops.outer import print_json

    print_json(payload)


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--self-check",
        action="store_true",
        help="sorry-hole then lake env lean tactic try on synthetic tag-pinned lake/lean",
    )
    parser.add_argument(
        "--plan",
        action="store_true",
        help="print loop v2 path A tactic lists; not the 30 Sep critical path",
    )
    parser.add_argument(
        "--probe-toolchain",
        action="store_true",
        help="record tag-pinned elan paths; missing lake is a capability gap, not PATH usable",
    )
    parser.add_argument(
        "--try-name",
        action="store_true",
        help="run path A on one JSONL problem (live elan; fail closed if missing)",
    )
    parser.add_argument("--name", default="", help="JSONL problem name")
    parser.add_argument("--jsonl", type=Path, default=None, help="warmup JSONL path")
    parser.add_argument("--state-root", type=Path, default=None, help="clone/putnam state root")
    parser.add_argument("--elan-home", type=Path, default=None, help="tag-pinned elan home")
    parser.add_argument("--network", default=None, help="allow or deny (default: LRA_NETWORK or allow)")
    parser.add_argument(
        "--timeout",
        type=float,
        default=TACTIC_TIMEOUT_SECONDS,
        help="per-tactic timeout seconds (must exceed IndependentKernelVerifier 30s)",
    )
    parser.add_argument(
        "--receipts-dir",
        type=Path,
        default=None,
        help="write per-problem lake-native try receipts here",
    )
    parser.add_argument(
        "--skip-checkout",
        action="store_true",
        help="do not git checkout (synthetic or already-checked worktree)",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    if args.self_check or argv is None or argv == []:
        report = self_check(args.jsonl, receipts_dir=args.receipts_dir)
        _print_json(report)
        return 0 if report["ok"] else 1

    if args.plan:
        _print_json(plan_try(args.jsonl))
        return 0

    if args.probe_toolchain:
        _print_json(probe_toolchain())
        return 0

    if args.try_name:
        if not args.name:
            parser.error("--try-name requires --name")
        try:
            timeout = lra_compile.require_lake_timeout(args.timeout)
        except lra_compile.CompileError as exc:
            _print_json(
                {
                    "ok": False,
                    "error": str(exc),
                    "error_type": type(exc).__name__,
                    "arena_score": None,
                    "hammer_006_lra_ready": False,
                    "on_30_sep_critical_path": False,
                    "uses_snapshot_goal": False,
                }
            )
            return 1
        raw, digest, records = lra_splice.load_warmup_records(
            args.jsonl if args.jsonl is not None else WARMUP_JSONL
        )
        del raw, digest
        match = next((item for item in records if item.get("name") == args.name), None)
        if match is None:
            _print_json(
                {
                    "ok": False,
                    "error": f"unknown warm-up problem: {args.name}",
                    "arena_score": None,
                    "hammer_006_lra_ready": False,
                    "uses_snapshot_goal": False,
                }
            )
            return 1
        pin = pin_for_tag(match, STRATA_FIRST_TAG)
        receipt = try_tactics(
            match,
            pin,
            timeout=timeout,
            state_root=args.state_root,
            elan_home=args.elan_home,
            network=lra_bake.network_mode(args.network),
            skip_checkout=args.skip_checkout,
        )
        written: list[str] = []
        if args.receipts_dir is not None:
            written = write_receipts([receipt], args.receipts_dir)
        payload = receipt.to_dict()
        payload["receipts_written"] = written
        payload["summary"] = _receipt_summary(receipt)
        _print_json(payload)
        return 0 if receipt.ok else 1

    parser.error("choose --self-check, --plan, --probe-toolchain, or --try-name")
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

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

def _ensure_datasets_path() -> None:
    from jevops.outer import ensure_sys_path

    ensure_sys_path(DATASETS_ROOT)


from jevops.lean import load_lean_toolchain  # noqa: E402

_tc = load_lean_toolchain(setup=(_ensure_datasets_path,))
KERNEL_COMMAND_TEMPLATE = _tc["KERNEL_COMMAND_TEMPLATE"]
LeanToolchainMissing = _tc["LeanToolchainMissing"]
audit_lean_frontend_path_json = _tc["audit_lean_frontend_path_json"]
run_lean_process = _tc["run_lean_process"]

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

from jevops.catalogs import HAMMER_006_LRA_READY
from jevops.catalogs import LOOP_VERSION
from jevops.catalogs import ON_30_SEP_CRITICAL_PATH
from jevops.catalogs import PATH_NAME
from jevops.catalogs import USES_SNAPSHOT_GOAL
from jevops.catalogs import V1_RUNS_THIS
PR_ID = "PR-5"
LRAH_ID = "LRAH-005"
from jevops.catalogs import LAKE_NATIVE_SCHEMA as RECEIPT_SCHEMA
from jevops.catalogs import PROTOCOL
from jevops.catalogs import CRITICAL_PATH_NOTE
from jevops.catalogs import GENERATOR_IDENTITY
from jevops.catalogs import GOAL_SNAPSHOT_REQUIRED
from jevops.catalogs import HAMMER_006_CLAIM
from jevops.catalogs import PATH_B_IMPLEMENTED
from jevops.catalogs import TACTIC_TIMEOUT_SECONDS
from jevops.catalogs import UNSOLVED_RELPATH
from jevops.lean import AESOP_TACTIC
from jevops.lean import PATH_A_TACTICS as FIXED_TACTICS
from jevops.lean import SORRY_TACTIC

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
from jevops.catalogs import FORBIDDEN_ATTRS_LAKE_NATIVE as FORBIDDEN_ATTRS
from jevops.catalogs import FORBIDDEN_CALLS_LAKE_NATIVE as FORBIDDEN_CALLS
from jevops.catalogs import FORBIDDEN_SCORE_NAMES

from jevops.lean import AESOP_IMPORT as _AESOP_IMPORT


class TryError(RuntimeError):
    """Fail-closed lake-native tactic-try error."""


class TryToolchainMissing(TryError):
    """Tag-pinned elan lake/lean is not installed. Not a PATH fallback."""


from jevops.lean import TacticAttempt
from jevops.lean import TacticTryReceipt


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
    from jevops.lean import AESOP_IMPORT, drive_text_pair_search

    return drive_text_pair_search(record, AESOP_IMPORT)


def tactics_for_record(record: Mapping[str, Any]) -> list[str]:
    from jevops.lean import drive_header_src_tactics

    return drive_header_src_tactics(record)


def sorry_lake_source(record: Mapping[str, Any]) -> str:
    from jevops.lean import drive_split_tactic_source

    return drive_split_tactic_source(
        record,
        SORRY_TACTIC,
        split_fn=lra_splice.split_statement_body,
        error_cls=TryError,
    )


def tactic_lake_source(record: Mapping[str, Any], tactic: str) -> str:
    from jevops.lean import drive_split_tactic_source

    return drive_split_tactic_source(
        record,
        tactic,
        split_fn=lra_splice.split_statement_body,
        error_cls=TryError,
    )


def write_tactic_source(record: Mapping[str, Any], dest: Path, tactic: str) -> Path:
    from jevops.lean import write_sorry_or_tactic
    from jevops.outer import write_text

    return write_sorry_or_tactic(
        dest,
        tactic=tactic,
        sorry=SORRY_TACTIC,
        sorry_fn=lambda: sorry_lake_source(record),
        tactic_fn=lambda: tactic_lake_source(record, tactic),
        write_fn=write_text,
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
    from jevops.lean import fill_tactic_attempt

    return fill_tactic_attempt(
        tactic=tactic,
        argv=argv,
        cwd=cwd,
        source_file=source_file,
        timeout=timeout,
        result=result,
        wall_ms=wall_ms,
        cpu_ms=cpu_ms,
        max_heartbeats=MEASUREMENT_MAX_HEARTBEATS,
        sorry=SORRY_TACTIC,
        error=error,
    )


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
    from jevops.lean import timed_tactic_with_lake_process
    from jevops.outer import timed_call

    return timed_tactic_with_lake_process(
        tactic=tactic,
        source_file=source_file,
        cwd=cwd,
        lake_path=lake_path,
        lean_path=lean_path,
        timeout=timeout,
        env=env,
        max_heartbeats=MEASUREMENT_MAX_HEARTBEATS,
        write_fn=write_tactic_source,
        write_args=(record, dest, tactic),
        run_lean_process=run_lean_process,
        fill_fn=_attempt_from_result,
        timed_fn=timed_call,
        refuse=lra_bake.FORBIDDEN_PUTNAM_BASENAME,
        error_cls=lra_compile.CompileError,
    )


def _prepare_project(
    record: Mapping[str, Any],
    pin: lra_compile.VersionPin,
    *,
    state_root: Optional[Path],
    network: str,
    skip_checkout: bool,
) -> tuple[Path, str, Path]:
    from jevops.lean import prepare_lake_paths

    return prepare_lake_paths(
        record,
        pin,
        putnam_source=PUTNAM_SOURCE,
        putnam_relpath=lra_bake.PUTNAM_CANDIDATE_RELPATH,
        source_relpath_fn=lra_compile.source_relpath,
        putnam_dir_fn=lambda rec, p, root: lra_compile.project_dir_for_record(rec, p, state_root=root),
        materialize_fn=lambda p, dest: lra_bake.materialize_putnam_project(
            p.lean_tag, dest, jsonl_version_pin=p.git_commit
        ),
        require_clone_fn=lambda url, net, root: lra_compile.require_clone(
            url, network=net, state_root=root
        ),
        checkout_fn=lra_compile.checkout_commit,
        skip_checkout=skip_checkout,
        network=network,
        state_root=state_root,
    )


def _sorry_template(statement: str) -> str:
    return lra_splice.statement_sorry_template(statement)


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

    from jevops.lean import drive_path_a_try

    return drive_path_a_try(
        record,
        pin,
        timeout=timeout,
        state_root=state_root,
        elan_home=elan_home,
        network=network,
        skip_checkout=skip_checkout,
        require_timeout_fn=lra_compile.require_lake_timeout,
        tactics_fn=tactics_for_record,
        split_fn=lra_splice.split_statement_body,
        sorry_template_fn=_sorry_template,
        lake_sorry_fn=sorry_lake_source,
        aesop_fn=aesop_imported,
        relpath_fn=lra_compile.source_relpath,
        digest_fn=sha256_text,
        sorry_suffix=lra_splice.STATEMENT_SORRY_SUFFIX,
        schema=RECEIPT_SCHEMA,
        loop=LOOP_VERSION,
        path_name=PATH_NAME,
        pr=PR_ID,
        lrah=LRAH_ID,
        generator=GENERATOR_IDENTITY,
        kernel_template=KERNEL_COMMAND_TEMPLATE,
        argv_template=MEASUREMENT_ARGV_TEMPLATE,
        threads=LEAN_NUM_THREADS,
        process_env_key=PROCESS_SUPERVISOR_ENV,
        tmp_name="lra-021-process-supervisor",
        gap_types=(LeanToolchainMissing, lra_compile.CompileToolchainMissing),
        gap_note=(
            "; tag-pinned elan is a capability gap, not PATH lean "
            "usability and not LeanFrontend.snapshot_goal"
        ),
        resolve_fn=lra_compile.resolve_pin,
        prepare_fn=_prepare_project,
        run_tactic_fn=_run_tactic,
        axiom_digest_fn=lra_compile.axiom_digest,
        error_types=(TryError, lra_compile.CompileError, LeanToolchainMissing, lra_bake.BakeError),
    )


def first_record_of_source(
    records: Sequence[Mapping[str, Any]], source: str
) -> Mapping[str, Any]:
    from jevops.outer import drive_first_field

    return drive_first_field(
        records,
        "source",
        source,
        error_cls=TryError,
        miss=f"warmup JSONL has no {source} record",
    )


def pin_for_tag(record: Mapping[str, Any], lean_tag: str) -> lra_compile.VersionPin:
    from jevops.outer import drive_matching_pin

    return drive_matching_pin(
        record,
        lean_tag,
        pins_fn=lra_compile.iter_version_pins,
        error_cls=TryError,
    )


def plan_try(path: Optional[Path] = None) -> dict[str, Any]:
    from jevops.lean import drive_plan_try

    return drive_plan_try(
        path,
        default_path=WARMUP_JSONL,
        load_fn=lra_splice.load_warmup_records,
        tactics_fn=tactics_for_record,
        aesop_fn=aesop_imported,
        aesop_tactic=AESOP_TACTIC,
        first_of_source_fn=first_record_of_source,
        strata_source=STRATA_SOURCE,
        putnam_source=PUTNAM_SOURCE,
        extra={
            "aesop_if_imported": True,
            "critical_path_note": CRITICAL_PATH_NOTE,
            "fixed_tactics": list(FIXED_TACTICS),
            "generator": GENERATOR_IDENTITY,
            "goal_snapshot_required": GOAL_SNAPSHOT_REQUIRED,
            "hammer_006_claim": HAMMER_006_CLAIM,
            "hammer_006_lra_ready": HAMMER_006_LRA_READY,
            "kernel_command_template": KERNEL_COMMAND_TEMPLATE,
            "loop": LOOP_VERSION,
            "lrah": LRAH_ID,
            "measurement_argv_template": MEASUREMENT_ARGV_TEMPLATE,
            "on_30_sep_critical_path": ON_30_SEP_CRITICAL_PATH,
            "path": PATH_NAME,
            "path_b_implemented": PATH_B_IMPLEMENTED,
            "pr": PR_ID,
            "protocol": PROTOCOL,
            "run_lean_process": run_lean_process.__name__,
            "sorry_template": "statement + ' := by\\nsorry'",
            "tactic_timeout_seconds": TACTIC_TIMEOUT_SECONDS,
            "uses_snapshot_goal": USES_SNAPSHOT_GOAL,
            "v1_runs_this": V1_RUNS_THIS,
        },
    )


def probe_toolchain(tags: Optional[Sequence[str]] = None) -> dict[str, Any]:
    from jevops.lean import drive_overlay_probe

    return drive_overlay_probe(
        tags,
        probe_fn=lra_compile.probe_toolchain,
        extra={
            "arena_score": None,
            "score": None,
            "generator": GENERATOR_IDENTITY,
            "goal_snapshot_required": False,
            "hammer_006_lra_ready": False,
            "lake_native_try": True,
            "loop": LOOP_VERSION,
            "on_30_sep_critical_path": False,
            "path": PATH_NAME,
            "path_b_implemented": False,
            "tactic_timeout_seconds": TACTIC_TIMEOUT_SECONDS,
            "uses_snapshot_goal": False,
            "v1_runs_this": False,
        },
    )


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
    from jevops.outer import source_text
    from jevops.repair import audit_source as _audit

    text = source_text(source, path=__file__)
    out = _audit(
        text,
        forbidden_imports=FORBIDDEN_IMPORT_NAMES,
        forbidden_calls=FORBIDDEN_CALLS,
        forbidden_scores=FORBIDDEN_SCORE_NAMES,
        forbidden_attrs=FORBIDDEN_ATTRS,
    )
    imported = set(out["imported_names"])
    frontend = audit_lean_frontend_path_json()
    from jevops import lean as lean_mod
    from jevops.repair import catalog_constants, module_call_names

    consts = catalog_constants(
        (
            "HAMMER_006_LRA_READY",
            "ON_30_SEP_CRITICAL_PATH",
            "V1_RUNS_THIS",
            "USES_SNAPSHOT_GOAL",
            "LOOP_VERSION",
            "PATH_NAME",
        ),
    )
    from jevops.repair import pack_call_audit

    return pack_call_audit(
        out,
        required_calls=("run_lean_process", "measurement_argv", "statement_sorry_template"),
        forbidden_call_names=("snapshot_goal",),
        extra_call_names=module_call_names(lean_mod),
        extra={
            "forbidden_attrs": out["forbidden_attrs"],
            "uses_snapshot_goal_call": "snapshot_goal" in set(out["call_names"] or ()),
            "imports_lean_frontend": "LeanFrontend" in imported,
            "imports_goal_snapshot": "GoalSnapshot" in imported,
            "hammer_006_lra_ready_constant": consts["HAMMER_006_LRA_READY"],
            "on_30_sep_critical_path_constant": consts["ON_30_SEP_CRITICAL_PATH"],
            "v1_runs_this_constant": consts["V1_RUNS_THIS"],
            "uses_snapshot_goal_constant": consts["USES_SNAPSHOT_GOAL"],
            "loop_constant": consts["LOOP_VERSION"],
            "path_constant": consts["PATH_NAME"],
            "lean_frontend": frontend,
        },
        extra_ok=(
            "LeanFrontend" not in imported,
            "GoalSnapshot" not in imported,
            consts["HAMMER_006_LRA_READY"] is False,
            consts["ON_30_SEP_CRITICAL_PATH"] is False,
            consts["V1_RUNS_THIS"] is False,
            consts["USES_SNAPSHOT_GOAL"] is False,
            consts["LOOP_VERSION"] == "v2",
            consts["PATH_NAME"] == "A",
            frontend.get("unchanged_path_lean_json") is True,
        ),
    )


from jevops.lean import FAKE_LAKE_PATH_A as _FAKE_LAKE
from jevops.lean import FAKE_LEAN_PATH_A as _FAKE_LEAN


def _write_executable(path: Path, text: str) -> None:
    from jevops.outer import write_executable

    write_executable(path, text)


def plant_fake_toolchain(elan_home: Path, lean_tag: str) -> Path:
    from jevops.lean import plant_fake_toolchain as _fn

    return _fn(
        elan_home,
        lean_tag,
        dirname_fn=lra_bake.elan_toolchain_dirname,
        files={"lake": _FAKE_LAKE, "lean": _FAKE_LEAN},
    )


def unsolved_record() -> dict[str, Any]:
    from jevops.lean import unsolved_record as _fn

    return _fn(
        source=STRATA_SOURCE,
        file_path=UNSOLVED_RELPATH,
        url=STRATA_URL,
        lean_tag=STRATA_FIRST_TAG,
        git_commit=STRATA_FIRST_COMMIT,
    )


def _attempt_summary(attempt: Mapping[str, Any]) -> dict[str, Any]:
    from jevops.lean import attempt_summary

    return attempt_summary(
        attempt,
        max_heartbeats=MEASUREMENT_MAX_HEARTBEATS,
        ikv_floor=INDEPENDENT_KERNEL_VERIFIER_DEFAULT_TIMEOUT_SECONDS,
    )


def _receipt_summary(receipt: TacticTryReceipt) -> dict[str, Any]:
    from jevops.lean import try_receipt_summary

    return try_receipt_summary(
        receipt,
        attempt_fn=_attempt_summary,
        aesop_tactic=AESOP_TACTIC,
        sorry_tactic=SORRY_TACTIC,
    )


def _synthetic_try(
    records: Sequence[Mapping[str, Any]],
    *,
    persist_receipts: Optional[Path] = None,
) -> dict[str, Any]:
    from jevops.lean import planted_session
    from jevops.outer import take_keys

    with planted_session(
        "lra-021-try-",
        tags=("v4.25.0", "v4.26.0", "v4.27.0"),
        plant_fn=plant_fake_toolchain,
        clone_fn=lambda state: lra_compile.plant_synthetic_strata_clone(
            lra_compile.clone_dir(STRATA_URL, state)
        ),
        parent=lra_compile._exec_scratch_parent(),
    ) as planted:
        elan_home, state_root, receipts_dir, clone = take_keys(
            planted, "elan_home", "state_root", "receipts_dir", "clone"
        )
        first = first_record_of_source(records, STRATA_SOURCE)
        putnam = first_record_of_source(records, PUTNAM_SOURCE)
        unsolved = unsolved_record()
        write_tactic_source(first, clone / STRATA_FIRST_FILE, SORRY_TACTIC)
        write_tactic_source(unsolved, clone / UNSOLVED_RELPATH, SORRY_TACTIC)
        first_pin = pin_for_tag(first, STRATA_FIRST_TAG)
        putnam_pin = pin_for_tag(putnam, STRATA_FIRST_TAG)
        unsolved_pin = pin_for_tag(unsolved, STRATA_FIRST_TAG)
        from jevops.outer import closed_on_error

        timeout_30_rejected = closed_on_error(
            lambda: lra_compile.require_lake_timeout(
                INDEPENDENT_KERNEL_VERIFIER_DEFAULT_TIMEOUT_SECONDS
            ),
            lra_compile.LakeTimeoutTooSmall,
        )
        from jevops.outer import starmap

        def _try(record: Mapping[str, Any], pin: Any, network: str) -> TacticTryReceipt:
            return try_tactics(
                record,
                pin,
                timeout=TACTIC_TIMEOUT_SECONDS,
                state_root=state_root,
                elan_home=elan_home,
                network=network,
                skip_checkout=True,
            )

        strata_receipt, putnam_receipt, unsolved_receipt = starmap(
            _try,
            (
                (first, first_pin, "deny"),
                (putnam, putnam_pin, "allow"),
                (unsolved, unsolved_pin, "deny"),
            ),
        )
        all_receipts = [strata_receipt, putnam_receipt, unsolved_receipt]
        from jevops.outer import persist_named_rows

        written, persisted = persist_named_rows(
            all_receipts,
            receipts_dir,
            persist_receipts,
            write_receipts,
        )
        missing_closed = closed_on_error(
            lambda: lra_compile.require_clone(
                "https://github.com/example/missing-lra-021",
                network="deny",
                state_root=state_root,
            ),
            lra_compile.CloneMissing,
        )
        from jevops.lean import pack_synthetic_try

        return pack_synthetic_try(
            elan_home=elan_home,
            missing_closed=missing_closed,
            written=written,
            persisted=persisted,
            putnam=putnam_receipt,
            strata=strata_receipt,
            unsolved=unsolved_receipt,
            timeout_30_rejected=timeout_30_rejected,
            summary_fn=_receipt_summary,
        )


def self_check(
    path: Optional[Path] = None,
    *,
    receipts_dir: Optional[Path] = None,
) -> dict[str, Any]:
    from jevops.outer import head_seq, if_none, relative_or_str

    jsonl = Path(if_none(path, WARMUP_JSONL))
    raw, digest, records = lra_splice.load_warmup_records(jsonl)
    audit = audit_source()
    synthetic = _synthetic_try(records, persist_receipts=receipts_dir)
    toolchain = probe_toolchain()
    plan = plan_try(jsonl)
    strata = synthetic["strata"]
    putnam = synthetic["putnam"]
    unsolved = synthetic["unsolved"]
    from jevops.outer import all_where

    putnam_aesop_only = all_where(
        plan["records"],
        lambda item: item["source"] == PUTNAM_SOURCE,
        lambda item: item["aesop_imported"] and item["aesop_in_list"],
    )
    non_putnam_no_aesop = all_where(
        plan["records"],
        lambda item: item["source"] != PUTNAM_SOURCE,
        lambda item: (not item["aesop_imported"]) and (not item["aesop_in_list"]),
    )
    from jevops.outer import get_str, pack_unscored

    report: dict[str, Any] = pack_unscored(**{
        "ok": False,
        "aesop_only_when_imported": putnam_aesop_only and non_putnam_no_aesop,
        "audit": audit,
        "capability_gap": get_str(toolchain, "capability_gap"),
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
            head_seq(strata["tactics_run"], 1) == ["rfl"] and strata["winning_tactic"] == "decide"
        ),
        "synthetic": synthetic,
        "tactic_timeout_seconds": TACTIC_TIMEOUT_SECONDS,
        "toolchain": toolchain,
        "unsolved_has_no_winner": unsolved["winning_tactic"] is None and not unsolved["ok"],
        "unsolved_ran_fixed_tactics": unsolved["tactics_run"] == list(FIXED_TACTICS),
        "uses_snapshot_goal": False,
        "v1_runs_this": False,
        "warmup_path": relative_or_str(jsonl, REPO_ROOT),
    })
    from jevops.outer import finalize_ok

    return finalize_ok(
        report,
        report["n_records"] == WARMUP_N,
        report["jsonl_unchanged"],
        report["aesop_only_when_imported"],
        report["path_a_lake_env_lean"],
        report["sorry_hole_then_tactic_list"],
        report["strata_decide_won"],
        report["strata_rfl_failed_first"],
        report["putnam_aesop_won"],
        report["putnam_tried_fixed_tactics_before_aesop"],
        report["unsolved_has_no_winner"],
        report["unsolved_ran_fixed_tactics"],
        strata["stopped_after_winner"],
        putnam["stopped_after_winner"],
        strata["sorry_template_prefix_bound"],
        putnam["sorry_template_prefix_bound"],
        strata["no_snapshot_goal_on_attempts"],
        putnam["no_snapshot_goal_on_attempts"],
        synthetic["timeout_30s_rejected"],
        synthetic["missing_clone_fails_closed_under_network_deny"],
        audit["ok"],
        report["lean_frontend_unchanged_path_lean_json"],
        report["hammer_006_lra_ready"] is False,
        report["on_30_sep_critical_path"] is False,
        report["v1_runs_this"] is False,
        report["uses_snapshot_goal"] is False,
        report["path_b_implemented"] is False,
        report["goal_snapshot_required"] is False,
        report["arena_score"] is None,
        report["score"] is None,
        report["llama_server_started"] is False,
        report["loop"] == "v2",
        report["path"] == "A",
    )


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
    from jevops.outer import list_or_none

    args = parser.parse_args(list_or_none(argv))

    if args.self_check or argv is None or argv == []:
        from jevops.outer import print_ok

        return print_ok(self_check(args.jsonl, receipts_dir=args.receipts_dir))

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
            from jevops.outer import failed_check

            _print_json(
                failed_check(
                    exc,
                    hammer_006_lra_ready=False,
                    on_30_sep_critical_path=False,
                    uses_snapshot_goal=False,
                )
            )
            return 1
        from jevops.outer import path_or

        raw, digest, records = lra_splice.load_warmup_records(path_or(args.jsonl, WARMUP_JSONL))
        del raw, digest
        from jevops.outer import closed_fail, lookup_named

        match = lookup_named(records, args.name)
        if match is None:
            _print_json(
                closed_fail(
                    f"unknown warm-up problem: {args.name}",
                    hammer_006_lra_ready=False,
                    uses_snapshot_goal=False,
                )
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
        from jevops.outer import exit_ok

        return exit_ok(receipt.ok)

    parser.error("choose --self-check, --plan, --probe-toolchain, or --try-name")
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

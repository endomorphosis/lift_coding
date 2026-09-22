#!/usr/bin/env python3
"""Multi-tag lake compile worker for Lean Refactor Arena.

Cached clone, checkout commit, tag-pinned ``lake env lean --json``. The
measurement command forces a finite ``maxHeartbeats`` even when a Putnam
header sets ``set_option maxHeartbeats 0``. Per-tag timeout is 10 min on
warm-up (20 min official), not the IndependentKernelVerifier 30 s default.
That verifier is not the lake oracle.

Start with one Strata module (CallElimCorrect.lean at v4.26.0). Expand
remaining tags after that file is green. Receipts record argv, exit,
stdout digest, axiom digest, wall-ms, cpu-ms, and header vs measurement
heartbeats. This worker does not claim Arena scores.
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
from typing import Any, Iterable, Mapping, Optional, Sequence

HERE = Path(__file__).resolve().parent
PAPER_ROOT = HERE.parent
REPO_ROOT = HERE.parents[3]
WARMUP_JSONL = PAPER_ROOT / "data" / "benchmark_data_warmup.jsonl"
DATASETS_ROOT = REPO_ROOT / "external" / "ipfs_datasets"

if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
import _jevops_path  # noqa: E402,F401
import bake_oleans as lra_bake  # noqa: E402
import splice as lra_splice  # noqa: E402

def _ensure_datasets_path() -> None:
    from jevops.outer import ensure_sys_path

    ensure_sys_path(DATASETS_ROOT)


from jevops.lean import load_lean_toolchain  # noqa: E402

_tc = load_lean_toolchain(setup=(_ensure_datasets_path,))
KERNEL_COMMAND_TEMPLATE = _tc["KERNEL_COMMAND_TEMPLATE"]
LeanToolchainMissing = _tc["LeanToolchainMissing"]
LeanToolchainResolver = _tc["LeanToolchainResolver"]
run_lean_process = _tc["run_lean_process"]

FROZEN_WARMUP_SHA256 = lra_splice.FROZEN_WARMUP_SHA256
WARMUP_N = lra_splice.WARMUP_N
STRATA_SOURCE = lra_bake.STRATA_SOURCE
PUTNAM_SOURCE = lra_bake.PUTNAM_SOURCE
STRATA_FIRST_TAG = lra_bake.STRATA_FIRST_TAG
STRATA_FIRST_COMMIT = lra_bake.STRATA_FIRST_COMMIT
STRATA_URL = lra_bake.STRATA_URL
from jevops.catalogs import INDEPENDENT_KERNEL_VERIFIER_DEFAULT_TIMEOUT_SECONDS  # noqa: E402
from jevops.catalogs import LEAN_NUM_THREADS  # noqa: E402
from jevops.catalogs import MEASUREMENT_ARGV_TEMPLATE  # noqa: E402
from jevops.catalogs import MEASUREMENT_MAX_HEARTBEATS  # noqa: E402
from jevops.catalogs import OFFICIAL_TAG_TIMEOUT_SECONDS  # noqa: E402
from jevops.catalogs import STRATA_EXPAND_FILE  # noqa: E402
from jevops.catalogs import STRATA_FIRST_FILE  # noqa: E402
from jevops.catalogs import WARMUP_TAG_TIMEOUT_SECONDS  # noqa: E402
from jevops.catalogs import COMPILE_SCHEMA as RECEIPT_SCHEMA
from jevops.catalogs import FORBIDDEN_CALLS_CORE as FORBIDDEN_CALLS
from jevops.catalogs import FORBIDDEN_ORACLE_NAMES
from jevops.catalogs import FORBIDDEN_SCORE_NAMES
from jevops.catalogs import GIT_BIN
from jevops.catalogs import PROCESS_SUPERVISOR_ENV

FORBIDDEN_IMPORT_NAMES = frozenset(
    {
        "fcntl",
        "IndependentKernelVerifier",
        "KernelVerifier",
        "LeanstralProofProvider",
        "leanstral_proof_provider",
        "shutil",
    }
)
from jevops.lean import AXIOM_LINE as _AXIOM_LINE  # noqa: E402
from jevops.lean import HEADER_HEARTBEATS as _HEADER_HEARTBEATS  # noqa: E402


class CompileError(RuntimeError):
    """Fail-closed lake compile-worker error."""


class CompileToolchainMissing(CompileError):
    """Tag-pinned elan lake/lean is not installed. Not a PATH fallback."""


class CloneMissing(CompileError):
    """Cached clone is absent while network is denied."""


class LakeTimeoutTooSmall(CompileError):
    """Lake timeout must exceed the IndependentKernelVerifier 30 s default."""


from jevops.lean import CompilePlan as _KernelCompilePlan
from jevops.lean import CompileReceipt
from jevops.lean import VersionPin


@dataclass
class CompilePlan(_KernelCompilePlan):
    first_source: str = STRATA_SOURCE

    @property
    def first_record(self) -> dict[str, Any]:
        return super().first_record(error_cls=CompileError, miss="warmup JSONL has no Strata record")

    def to_dict(self) -> dict[str, Any]:
        from jevops.lean import pack_compile_plan

        first = self.first_record
        return pack_compile_plan(
            first,
            iter_version_pins(first.get("version_info")),
            frozen_warmup_sha256=self.frozen_warmup_sha256,
            jsonl_bytes=self.jsonl_bytes,
            n_records=self.n_records,
            first_source=STRATA_SOURCE,
            first_tag=STRATA_FIRST_TAG,
            first_commit=STRATA_FIRST_COMMIT,
            first_file=STRATA_FIRST_FILE,
            first_url=STRATA_URL,
            kernel_command_template=KERNEL_COMMAND_TEMPLATE,
            measurement_argv_template=MEASUREMENT_ARGV_TEMPLATE,
            measurement_max_heartbeats=MEASUREMENT_MAX_HEARTBEATS,
            ikv_timeout=INDEPENDENT_KERNEL_VERIFIER_DEFAULT_TIMEOUT_SECONDS,
            official_timeout=OFFICIAL_TAG_TIMEOUT_SECONDS,
            warmup_timeout=WARMUP_TAG_TIMEOUT_SECONDS,
        )


def sha256_bytes(data: bytes) -> str:
    from jevops.outer import digest_hex

    return digest_hex(data)


def sha256_file(path: Path) -> str:
    from jevops.outer import digest_file

    return digest_file(path)


def sha256_text(text: str) -> str:
    from jevops.outer import digest_text

    return digest_text(text)


def require_lake_timeout(timeout: float) -> float:
    """Reject the IndependentKernelVerifier 30 s default as a lake timeout."""

    from jevops.lean import require_lake_timeout as _fn

    return _fn(
        timeout,
        floor=INDEPENDENT_KERNEL_VERIFIER_DEFAULT_TIMEOUT_SECONDS,
        error_cls=CompileError,
        too_small_cls=LakeTimeoutTooSmall,
    )


def header_max_heartbeats(header: str) -> Optional[int]:
    from jevops.lean import header_max_heartbeats as _fn

    return _fn(header)


def iter_version_pins(version_info: Any) -> list[VersionPin]:
    pins = [
        VersionPin(lean_tag=item.lean_tag, git_commit=item.git_commit)
        for item in lra_bake.iter_version_pins(version_info)
    ]
    return sorted(pins, key=lambda pin: _tag_sort_key(pin.lean_tag), reverse=True)


def _tag_sort_key(tag: str) -> tuple[tuple[int, int, int], str]:
    from jevops.outer import version_sort_key

    return version_sort_key(lra_bake.normalize_lean_tag(tag))


def measurement_argv(
    lake_path: str,
    lean_path: str,
    source_file: str,
    *,
    max_heartbeats: int = MEASUREMENT_MAX_HEARTBEATS,
) -> list[str]:
    from jevops.lean import measurement_argv as _fn

    return _fn(
        lake_path,
        lean_path,
        source_file,
        max_heartbeats=max_heartbeats,
        refuse=lra_bake.FORBIDDEN_PUTNAM_BASENAME,
        error_cls=CompileError,
    )


def axiom_digest(axiom_names: Sequence[str]) -> str:
    from jevops.lean import axiom_digest as _fn

    return _fn(axiom_names)


def parse_axioms(stdout: str, stderr: str = "") -> tuple[list[str], bool]:
    """Extract axiom names and sorryAx from lake/lean stdout."""

    from jevops.lean import parse_axioms as _fn

    return _fn(stdout, stderr)


def clone_dir(url: str, state_root: Optional[Path] = None) -> Path:
    from jevops.outer import path_or, url_clone_dir

    root = path_or(state_root, factory=lra_bake.default_state_root)
    return url_clone_dir(root, url)


def require_clone(
    url: str,
    *,
    network: str,
    state_root: Optional[Path] = None,
) -> Path:
    from jevops.outer import replace_if, require_marked_dir

    return require_marked_dir(
        clone_dir(url, state_root),
        (".git", "lakefile.lean"),
        error_cls=replace_if(network == "deny", CloneMissing, None),
        miss=(
            f"cached clone missing for {url} under network=deny; never falling "
            "back to PATH lean or a guessed GitHub URL"
        ),
    )


def checkout_commit(clone: Path, commit: str) -> dict[str, Any]:
    from jevops.outer import git_checkout

    return git_checkout(
        clone,
        commit,
        git_bin=GIT_BIN,
        error_cls=CompileError,
        miss_cls=CompileToolchainMissing,
    )


def project_dir_for_record(
    record: Mapping[str, Any],
    pin: VersionPin,
    *,
    state_root: Optional[Path] = None,
) -> Path:
    from jevops.lean import project_dir_for_record as _fn

    def _putnam_dir(_rec: Mapping[str, Any], p: VersionPin, root: Optional[Path]) -> Path:
        from jevops.lean import putnam_bake_job
        from jevops.outer import get_str

        return lra_bake.putnam_project_dir(
            putnam_bake_job(
                lean_tag=p.lean_tag,
                git_commit=p.git_commit,
                name=get_str(_rec, "name"),
                putnam_source=PUTNAM_SOURCE,
                putnam_relpath=lra_bake.PUTNAM_CANDIDATE_RELPATH,
                putnam_module=lra_bake.PUTNAM_MODULE,
            ),
            root,
        )

    return _fn(
        record,
        pin,
        putnam_source=PUTNAM_SOURCE,
        putnam_dir_fn=_putnam_dir,
        clone_dir_fn=lambda url: clone_dir(url, state_root),
        error_cls=CompileError,
        state_root=state_root,
    )


def source_relpath(record: Mapping[str, Any]) -> str:
    from jevops.lean import source_relpath as _fn

    return _fn(
        record,
        putnam_source=PUTNAM_SOURCE,
        putnam_relpath=lra_bake.PUTNAM_CANDIDATE_RELPATH,
        refuse=lra_bake.FORBIDDEN_PUTNAM_BASENAME,
        error_cls=CompileError,
    )


def write_record_source(record: Mapping[str, Any], dest: Path) -> Path:
    from jevops.lean import write_lake_source

    split = lra_splice.split_statement_body(record)
    return write_lake_source(
        dest,
        header=split.header,
        statement=split.statement,
        tactic_block=lra_splice.tactic_block_from_body(split.body_suffix),
        refuse=lra_bake.FORBIDDEN_PUTNAM_BASENAME,
        error_cls=CompileError,
    )


def resolve_pin(
    pin: VersionPin,
    *,
    elan_home: Optional[Path] = None,
    require_installed: bool = True,
):
    from jevops.lean import resolve_tag_pin

    return resolve_tag_pin(
        pin,
        resolver_cls=LeanToolchainResolver,
        elan_home=elan_home,
        require_installed=require_installed,
        miss_types=(LeanToolchainMissing,),
        error_cls=CompileToolchainMissing,
    )


def compile_tag(
    record: Mapping[str, Any],
    pin: VersionPin,
    *,
    timeout: float = WARMUP_TAG_TIMEOUT_SECONDS,
    state_root: Optional[Path] = None,
    elan_home: Optional[Path] = None,
    network: str = "allow",
    require_oleans: bool = False,
    hardware_class: str = "unscored-dev",
    skip_checkout: bool = False,
) -> CompileReceipt:
    """Run tag-pinned ``lake env lean`` with finite measurement maxHeartbeats."""

    timeout = require_lake_timeout(timeout)
    from jevops.outer import get_str, text_or

    header_cap = header_max_heartbeats(get_str(record, "header"))
    relpath = source_relpath(record)
    from jevops.lean import init_compile_receipt

    receipt = init_compile_receipt(
        record,
        pin,
        timeout=timeout,
        relpath=relpath,
        schema=RECEIPT_SCHEMA,
        max_heartbeats=MEASUREMENT_MAX_HEARTBEATS,
        header_cap=header_cap,
        lean_num_threads=LEAN_NUM_THREADS,
        kernel_command_template=KERNEL_COMMAND_TEMPLATE,
        hardware_class=hardware_class,
    )
    from jevops.lean import (
        close_failed_receipt,
        prepare_lake_paths,
        run_tag_compile,
        stamp_measured_receipt,
        stamp_with_lake_process,
        write_candidate_if_needed,
    )

    def _stamp(receipt: CompileReceipt, *, toolchain: Any, cwd: Path, source_file: str) -> CompileReceipt:
        return stamp_with_lake_process(
            receipt,
            lake_path=toolchain.lake_path,
            lean_path=toolchain.lean_path,
            source_file=source_file,
            max_heartbeats=MEASUREMENT_MAX_HEARTBEATS,
            cwd=cwd,
            toolchain=toolchain,
            timeout=timeout,
            stamp_fn=stamp_measured_receipt,
            run_lean_process=run_lean_process,
            state_root=state_root,
            tmp_name="lra-014-process-supervisor",
            process_env_key=PROCESS_SUPERVISOR_ENV,
            threads=LEAN_NUM_THREADS,
            ikv_floor=INDEPENDENT_KERNEL_VERIFIER_DEFAULT_TIMEOUT_SECONDS,
            refuse=lra_bake.FORBIDDEN_PUTNAM_BASENAME,
            error_cls=CompileError,
        )

    from jevops.outer import optional_fn as _optional_fn

    return run_tag_compile(
        receipt,
        resolve_fn=lambda: resolve_pin(pin, elan_home=elan_home, require_installed=True),
        prepare_fn=lambda: prepare_lake_paths(
            record,
            pin,
            putnam_source=PUTNAM_SOURCE,
            putnam_relpath=lra_bake.PUTNAM_CANDIDATE_RELPATH,
            source_relpath_fn=source_relpath,
            putnam_dir_fn=lambda rec, p, root: project_dir_for_record(rec, p, state_root=root),
            materialize_fn=lambda p, project: lra_bake.materialize_putnam_project(
                p.lean_tag, project, jsonl_version_pin=p.git_commit
            ),
            require_clone_fn=lambda url, net, root: require_clone(
                url, network=net, state_root=root
            ),
            checkout_fn=checkout_commit,
            skip_checkout=skip_checkout,
            network=network,
            state_root=state_root,
        ),
        write_fn=lambda dest: write_candidate_if_needed(
            record,
            dest,
            putnam_source=PUTNAM_SOURCE,
            write_fn=write_record_source,
        ),
        bake_fn=_optional_fn(
            require_oleans,
            lambda: lra_bake.require_cache(
                _bake_job_for_record(record, pin), network=network, state_root=state_root
            ),
        ),
        stamp_fn=_stamp,
        close_fn=lambda rec, exc: close_failed_receipt(
            rec, exc, digest_fn=sha256_text, axiom_digest_fn=axiom_digest
        ),
        error_types=(CompileError, LeanToolchainMissing, lra_bake.BakeError),
    )


def _bake_job_for_record(record: Mapping[str, Any], pin: VersionPin) -> lra_bake.BakeJob:
    from jevops.lean import bake_job_for_record as _fn

    return _fn(
        record,
        pin,
        putnam_source=PUTNAM_SOURCE,
        strata_source=STRATA_SOURCE,
        strata_first_tag=STRATA_FIRST_TAG,
        putnam_relpath=lra_bake.PUTNAM_CANDIDATE_RELPATH,
        putnam_module=lra_bake.PUTNAM_MODULE,
        url_key_fn=lra_bake._url_cache_key,
    )


def compile_record(
    record: Mapping[str, Any],
    *,
    timeout: float = WARMUP_TAG_TIMEOUT_SECONDS,
    state_root: Optional[Path] = None,
    elan_home: Optional[Path] = None,
    network: str = "allow",
    require_oleans: bool = False,
    hardware_class: str = "unscored-dev",
    skip_checkout: bool = False,
    abort_on_first_failure: bool = True,
) -> list[CompileReceipt]:
    from jevops.outer import collect_until, optional_fn, replace_if

    pins = iter_version_pins(record.get("version_info"))
    return collect_until(
        pins,
        lambda pin: compile_tag(
            record,
            pin,
            timeout=timeout,
            state_root=state_root,
            elan_home=elan_home,
            network=network,
            require_oleans=require_oleans,
            hardware_class=hardware_class,
            skip_checkout=skip_checkout,
        ),
        abort_fn=optional_fn(abort_on_first_failure, lambda receipt: not receipt.ok),
        remaining_fn=lambda rest: [item.lean_tag for item in rest],
        remaining_attr=replace_if(abort_on_first_failure, "aborted_remaining_tags", ""),
    )


def write_receipts(receipts: Sequence[CompileReceipt], dest_dir: Path) -> list[str]:
    from jevops.outer import write_named_jsons

    return write_named_jsons(
        dest_dir,
        receipts,
        name_fn=lambda item: item.name,
        tag_fn=lambda item: item.lean_tag,
        payload_fn=lambda item: item.to_dict(),
    )


def plan_compile(path: Optional[Path] = None) -> CompilePlan:
    from jevops.outer import if_none

    jsonl = Path(if_none(path, WARMUP_JSONL))
    raw, digest, records = lra_splice.load_warmup_records(jsonl)
    from jevops.lean import plan_from_records

    return plan_from_records(
        records,
        digest,
        len(raw),
        first_source=STRATA_SOURCE,
        cls=CompilePlan,
    )


def first_strata_record(records: Sequence[Mapping[str, Any]]) -> Mapping[str, Any]:
    from jevops.outer import field_eq, first_where

    return first_where(
        records,
        field_eq("source", STRATA_SOURCE),
        error_cls=CompileError,
        miss="no Strata record in warmup JSONL",
    )


def expand_records(
    records: Sequence[Mapping[str, Any]],
    *,
    after_name: str,
) -> list[Mapping[str, Any]]:
    """Records whose tags are compiled after ``after_name`` is green."""

    from jevops.outer import after_named, field_eq

    return after_named(
        records,
        after_name,
        pred=field_eq("source", STRATA_SOURCE),
    )


def probe_toolchain(tags: Iterable[str] | None = None) -> dict[str, Any]:
    from jevops.outer import if_none

    tags = if_none(tags, (STRATA_FIRST_TAG, "v4.27.0", "v4.29.1"))
    from jevops.lean import probe_pins
    from jevops.outer import env_str, or_list, text_or

    resolver = LeanToolchainResolver()
    return probe_pins(
        or_list(tags, ()),
        resolve_fn=lambda tag: resolver.resolve_tag(tag, require_installed=False).to_dict(),
        extra={
            "default_elan_home": text_or(lra_bake.default_elan_home()),
            "elan_home_env": env_str("ELAN_HOME"),
            "independent_kernel_verifier_is_lake_oracle": False,
            "kernel_command_template": KERNEL_COMMAND_TEMPLATE,
            "lake": False,
            "measurement_argv_template": MEASUREMENT_ARGV_TEMPLATE,
            "path": env_str("PATH"),
            "run_lean_process": run_lean_process.__name__,
            "validation_home": text_or(Path.home()),
            "warmup_timeout_seconds": WARMUP_TAG_TIMEOUT_SECONDS,
        },
    )


def _imported_names(source: str) -> set[str]:
    from jevops.repair import imported_names

    return imported_names(source)


def _call_name(node: ast.AST) -> str:
    from jevops.repair import call_short_name

    return call_short_name(node)


def _oracle_name_uses(tree: ast.AST) -> set[str]:
    from jevops.repair import ast_name_hits

    return ast_name_hits(tree, FORBIDDEN_ORACLE_NAMES)


def _timeout_kwarg_values(tree: ast.AST) -> list[float]:
    from jevops.repair import call_kwarg_numbers

    return call_kwarg_numbers(tree, ("timeout", "timeout_seconds"))


def audit_source(source: Optional[str] = None) -> dict[str, Any]:
    from jevops.outer import source_text
    from jevops.repair import ast_name_hits, audit_source as _audit, call_kwarg_numbers, has_constant

    text = source_text(source, path=__file__)
    out = _audit(
        text,
        forbidden_imports=FORBIDDEN_IMPORT_NAMES,
        forbidden_calls=FORBIDDEN_CALLS,
        forbidden_scores=FORBIDDEN_SCORE_NAMES,
    )
    tree = ast.parse(text)
    oracle_uses = ast_name_hits(tree, FORBIDDEN_ORACLE_NAMES)
    timeout_literals = call_kwarg_numbers(tree, ("timeout", "timeout_seconds"))
    has_ikv_timeout_constant = has_constant(text, INDEPENDENT_KERNEL_VERIFIER_DEFAULT_TIMEOUT_SECONDS)
    lake_timeout_literals_ok = all(
        value > INDEPENDENT_KERNEL_VERIFIER_DEFAULT_TIMEOUT_SECONDS
        for value in timeout_literals
        if value == INDEPENDENT_KERNEL_VERIFIER_DEFAULT_TIMEOUT_SECONDS or value >= 1.0
    ) and INDEPENDENT_KERNEL_VERIFIER_DEFAULT_TIMEOUT_SECONDS not in timeout_literals
    from jevops import lean as lean_mod
    from jevops.repair import module_call_names, pack_call_audit

    packed = pack_call_audit(
        out,
        required_calls=("run_lean_process", "measurement_argv"),
        extra_call_names=module_call_names(lean_mod),
        extra={
            "forbidden_oracle_uses": sorted(oracle_uses),
            "timeout_kwarg_literals": timeout_literals,
            "has_ikv_timeout_constant": has_ikv_timeout_constant,
            "lake_timeout_literals_ok": lake_timeout_literals_ok,
            "independent_kernel_verifier_is_lake_oracle": False,
        },
        extra_ok=(not oracle_uses, lake_timeout_literals_ok),
    )
    return packed


from jevops.lean import FAKE_LAKE_EXEC as _FAKE_LAKE
from jevops.lean import FAKE_LEAN_COMPILE as _FAKE_LEAN


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


def plant_synthetic_strata_clone(clone: Path) -> Path:
    from jevops.lean import plant_synthetic_clone, render_lean_toolchain, render_package_lakefile

    return plant_synthetic_clone(
        clone,
        {
            "lakefile.lean": render_package_lakefile(
                package="strata",
                lib="Strata",
                max_heartbeats=MEASUREMENT_MAX_HEARTBEATS,
            ),
            "lean-toolchain": render_lean_toolchain(STRATA_FIRST_TAG),
        },
    )


def _receipt_summary(receipt: CompileReceipt) -> dict[str, Any]:
    from jevops.lean import compile_receipt_summary

    return compile_receipt_summary(
        receipt,
        max_heartbeats=MEASUREMENT_MAX_HEARTBEATS,
        ikv_floor=INDEPENDENT_KERNEL_VERIFIER_DEFAULT_TIMEOUT_SECONDS,
    )


def _exec_scratch_parent() -> Path:
    """Return a directory that can exec shebang scripts. ``/tmp`` is often noexec."""

    from jevops.outer import exec_capable_dir, state_home_candidates

    return exec_capable_dir(
        state_home_candidates(),
        probe_name=".lra-014-exec-probe",
        error_cls=CompileError,
        miss=(
            "no executable filesystem for tag-pinned synthetic lake/lean "
            "(refusing /tmp noexec and PATH lake)"
        ),
    )


def _synthetic_compile(
    plan: CompilePlan,
    *,
    persist_receipts: Optional[Path] = None,
) -> dict[str, Any]:
    from jevops.lean import planted_session
    from jevops.outer import get_str, take_keys

    with planted_session(
        "lra-014-compile-",
        tags=("v4.25.0", "v4.26.0", "v4.27.0", "v4.29.1"),
        plant_fn=plant_fake_toolchain,
        clone_fn=lambda state: plant_synthetic_strata_clone(clone_dir(STRATA_URL, state)),
        parent=_exec_scratch_parent(),
    ) as planted:
        elan_home, state_root, receipts_dir, clone = take_keys(
            planted, "elan_home", "state_root", "receipts_dir", "clone"
        )
        first = plan.first_record
        write_record_source(first, clone / STRATA_FIRST_FILE)
        expand = expand_records(plan.records, after_name=get_str(first, "name"))
        from jevops.outer import apply_last

        apply_last(expand, lambda record: write_record_source(record, clone / STRATA_EXPAND_FILE))
        first_job = _bake_job_for_record(first, iter_version_pins(first.get("version_info"))[0])
        lra_bake.plant_synthetic_cache(first_job, state_root)
        from jevops.outer import closed_on_error

        timeout_30_rejected = closed_on_error(
            lambda: require_lake_timeout(INDEPENDENT_KERNEL_VERIFIER_DEFAULT_TIMEOUT_SECONDS),
            LakeTimeoutTooSmall,
        )
        first_receipts = compile_record(
            first,
            timeout=WARMUP_TAG_TIMEOUT_SECONDS,
            state_root=state_root,
            elan_home=elan_home,
            network="deny",
            require_oleans=False,
            hardware_class="synthetic",
            skip_checkout=True,
        )
        from jevops.outer import all_rows, field_eq, first_where

        first_green = bool(first_receipts) and all_rows(first_receipts, lambda item: item.ok)
        expand_hit = first_where(
            expand, lambda record: get_str(record, "file_path") == STRATA_EXPAND_FILE
        )
        from jevops.outer import call_if

        expand_receipts: list[CompileReceipt] = call_if(
            first_green and expand_hit is not None,
            lambda: compile_record(
                expand_hit,
                timeout=WARMUP_TAG_TIMEOUT_SECONDS,
                state_root=state_root,
                elan_home=elan_home,
                network="deny",
                hardware_class="synthetic",
                skip_checkout=True,
            ),
            default=[],
        )
        putnam = first_where(
            plan.records,
            field_eq("source", PUTNAM_SOURCE),
            error_cls=CompileError,
            miss="no Putnam record in warmup JSONL",
        )
        putnam_pins = iter_version_pins(putnam.get("version_info"))
        putnam_pin = first_where(
            putnam_pins,
            lambda pin: pin.lean_tag == STRATA_FIRST_TAG,
            error_cls=CompileError,
            miss="no Putnam pin for first tag",
        )
        putnam_receipt = compile_tag(
            putnam,
            putnam_pin,
            timeout=WARMUP_TAG_TIMEOUT_SECONDS,
            state_root=state_root,
            elan_home=elan_home,
            network="allow",
            hardware_class="synthetic",
            skip_checkout=True,
        )
        all_receipts = [*first_receipts, *expand_receipts, putnam_receipt]
        from jevops.outer import persist_named_rows

        written, persisted = persist_named_rows(
            all_receipts,
            receipts_dir,
            persist_receipts,
            write_receipts,
        )
        missing_clone_closed = closed_on_error(
            lambda: require_clone(
                "https://github.com/example/missing-lra-014",
                network="deny",
                state_root=state_root,
            ),
            CloneMissing,
        )
        from jevops.lean import pack_synthetic_compile

        return pack_synthetic_compile(
            elan_home=elan_home,
            expand_receipts=expand_receipts,
            first_receipts=first_receipts,
            putnam_receipt=putnam_receipt,
            written=written,
            persisted=persisted,
            receipts_dir=receipts_dir,
            first_file=STRATA_FIRST_FILE,
            first_name=get_str(first, "name"),
            first_green=first_green,
            missing_clone_closed=missing_clone_closed,
            timeout_30_rejected=timeout_30_rejected,
            timeout_is_warmup=all_rows(
                [*first_receipts, *expand_receipts, putnam_receipt],
                lambda item: item.timeout_seconds == WARMUP_TAG_TIMEOUT_SECONDS,
            ),
            summary_fn=_receipt_summary,
            tag_sort_fn=_tag_sort_key,
            max_heartbeats=MEASUREMENT_MAX_HEARTBEATS,
        )


def self_check(
    path: Optional[Path] = None,
    *,
    receipts_dir: Optional[Path] = None,
) -> dict[str, Any]:
    from jevops.outer import get_str, if_none, relative_or_str

    jsonl = Path(if_none(path, WARMUP_JSONL))
    plan = plan_compile(jsonl)
    audit = audit_source()
    synthetic = _synthetic_compile(plan, persist_receipts=receipts_dir)
    toolchain = probe_toolchain()
    first = plan.first_record
    first_pins = iter_version_pins(first.get("version_info"))
    from jevops.outer import collect_where, field_eq

    putnam_headers = collect_where(
        plan.records,
        field_eq("source", PUTNAM_SOURCE),
        lambda record: header_max_heartbeats(get_str(record, "header")),
    )
    from jevops.outer import pack_unscored

    report: dict[str, Any] = pack_unscored(**{
        "ok": False,
        "compiled": bool(synthetic["first_strata_compiled"]),
        "lake": True,
        "lake_oracle": True,
        "llama_server_started": False,
        "independent_kernel_verifier_used": False,
        "independent_kernel_verifier_is_lake_oracle": False,
        "independent_kernel_verifier_default_timeout_seconds": (
            INDEPENDENT_KERNEL_VERIFIER_DEFAULT_TIMEOUT_SECONDS
        ),
        "warmup_timeout_seconds": WARMUP_TAG_TIMEOUT_SECONDS,
        "official_timeout_seconds": OFFICIAL_TAG_TIMEOUT_SECONDS,
        "measurement_maxHeartbeats": MEASUREMENT_MAX_HEARTBEATS,
        "kernel_command_template": KERNEL_COMMAND_TEMPLATE,
        "measurement_argv_template": MEASUREMENT_ARGV_TEMPLATE,
        "run_lean_process": run_lean_process.__name__,
        "frozen_warmup_sha256": plan.frozen_warmup_sha256,
        "jsonl_bytes": plan.jsonl_bytes,
        "jsonl_unchanged": plan.frozen_warmup_sha256 == FROZEN_WARMUP_SHA256,
        "n_records": plan.n_records,
        "first_name": get_str(first, "name"),
        "first_file": get_str(first, "file_path"),
        "first_is_strata_v4_26": (
            first.get("source") == STRATA_SOURCE
            and first_pins
            and first_pins[0].lean_tag == STRATA_FIRST_TAG
            and first_pins[0].git_commit == STRATA_FIRST_COMMIT
            and get_str(first, "file_path") == STRATA_FIRST_FILE
        ),
        "first_strata_compiled_via_lake_env_lean": bool(
            synthetic["first_strata_compiled"] and synthetic["first_via_lake_env_lean"]
        ),
        "per_tag_timeout_written": bool(synthetic["timeout_is_warmup_600s"]),
        "axiom_digest_receipts_written": bool(synthetic["n_receipts_written"]),
        "putnam_headers_maxHeartbeats": putnam_headers,
        "putnam_headers_are_zero": putnam_headers == [0, 0, 0],
        "timeout_30s_rejected": bool(synthetic["timeout_30s_rejected"]),
        "audit": audit,
        "synthetic": synthetic,
        "toolchain": toolchain,
        "plan": plan.to_dict(),
        "warmup_path": relative_or_str(jsonl, REPO_ROOT),
        "protocol": "LRA/v1",
        "live_elan_installed": bool(toolchain["installed_tags"]),
        "capability_gap": toolchain["capability_gap"],
    })
    first_receipts = synthetic["first_receipts"]
    from jevops.outer import all_rows, finalize_ok

    return finalize_ok(
        report,
        report["n_records"] == WARMUP_N,
        report["jsonl_unchanged"],
        report["first_is_strata_v4_26"],
        report["first_strata_compiled_via_lake_env_lean"],
        report["per_tag_timeout_written"],
        report["axiom_digest_receipts_written"],
        report["putnam_headers_are_zero"],
        synthetic["putnam_overrides_zero_header"],
        synthetic["timeout_30s_rejected"],
        synthetic["missing_clone_fails_closed_under_network_deny"],
        synthetic["expand_ok"],
        synthetic["expand_tags_newest_first"],
        all_rows(first_receipts, lambda item: item["axiom_digest_hex64"]),
        all_rows(first_receipts, lambda item: item["stdout_nonempty"] and item["printed_axioms"]),
        all_rows(first_receipts, lambda item: not item["error"]),
        all_rows(first_receipts, lambda item: item["timeout_exceeds_ikv_30s"]),
        all_rows(first_receipts, lambda item: not item["independent_kernel_verifier_used"]),
        audit["ok"],
        report["independent_kernel_verifier_used"] is False,
        report["independent_kernel_verifier_is_lake_oracle"] is False,
        report["arena_score"] is None,
        report["score"] is None,
        report["llama_server_started"] is False,
    )


def _print_json(payload: Mapping[str, Any]) -> None:
    from jevops.outer import print_json

    print_json(payload)


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--self-check",
        action="store_true",
        help="compile one Strata file via synthetic tag-pinned lake env lean; write receipts",
    )
    parser.add_argument(
        "--plan",
        action="store_true",
        help="print the compile plan; first target is Strata v4.26 CallElimCorrect.lean",
    )
    parser.add_argument(
        "--probe-toolchain",
        action="store_true",
        help="record tag-pinned elan paths; do not treat missing lake as PATH usable",
    )
    parser.add_argument(
        "--compile-first",
        action="store_true",
        help="compile the first Strata module (live elan, fail closed if missing)",
    )
    parser.add_argument(
        "--expand-tags",
        action="store_true",
        help="after the first Strata file is green, compile remaining Strata tags",
    )
    parser.add_argument("--name", default="", help="JSONL problem name (default: first Strata)")
    parser.add_argument("--jsonl", type=Path, default=None, help="warmup JSONL path")
    parser.add_argument("--state-root", type=Path, default=None, help="clone/olean/putnam state root")
    parser.add_argument("--elan-home", type=Path, default=None, help="tag-pinned elan home")
    parser.add_argument("--network", default=None, help="allow or deny (default: LRA_NETWORK or allow)")
    parser.add_argument(
        "--timeout",
        type=float,
        default=WARMUP_TAG_TIMEOUT_SECONDS,
        help="per-tag timeout seconds (must exceed IndependentKernelVerifier 30s)",
    )
    parser.add_argument(
        "--receipts-dir",
        type=Path,
        default=None,
        help="write per-tag timeout and axiom-digest receipts here",
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
        _print_json(plan_compile(args.jsonl).to_dict())
        return 0

    if args.probe_toolchain:
        _print_json(probe_toolchain())
        return 0

    if args.compile_first or args.expand_tags or args.name:
        try:
            timeout = require_lake_timeout(args.timeout)
        except CompileError as exc:
            from jevops.outer import failed_check

            _print_json(failed_check(exc, independent_kernel_verifier_is_lake_oracle=False))
            return 1
        plan = plan_compile(args.jsonl)
        network = lra_bake.network_mode(args.network)
        records: list[Mapping[str, Any]] = []
        from jevops.outer import get_str

        if args.name:
            from jevops.outer import closed_fail, lookup_named

            match = lookup_named(plan.records, args.name)
            if match is None:
                _print_json(closed_fail(f"unknown warm-up problem: {args.name}"))
                return 1
            records = [match]
        else:
            first = plan.first_record
            records = [first]
            if args.expand_tags:
                records.extend(expand_records(plan.records, after_name=get_str(first, "name")))
        all_receipts: list[CompileReceipt] = []
        first_green = False
        for index, record in enumerate(records):
            if index > 0 and args.expand_tags and not first_green:
                break
            batch = compile_record(
                record,
                timeout=timeout,
                state_root=args.state_root,
                elan_home=args.elan_home,
                network=network,
                skip_checkout=args.skip_checkout,
            )
            all_receipts.extend(batch)
            if index == 0:
                first_green = bool(batch) and all(item.ok for item in batch)
        written: list[str] = []
        if args.receipts_dir is not None:
            written = write_receipts(all_receipts, args.receipts_dir)
        payload = {
            "ok": bool(all_receipts) and all(item.ok for item in all_receipts),
            "arena_score": None,
            "score": None,
            "compiled": bool(all_receipts) and all(item.ok for item in all_receipts),
            "expand_tags": bool(args.expand_tags),
            "first_green": first_green,
            "independent_kernel_verifier_is_lake_oracle": False,
            "n_receipts": len(all_receipts),
            "receipts": [_receipt_summary(item) for item in all_receipts],
            "receipts_written": written,
        }
        _print_json(payload)
        from jevops.outer import exit_ok

        return exit_ok(payload["ok"])

    parser.error("choose --self-check, --plan, --probe-toolchain, or --compile-first")
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

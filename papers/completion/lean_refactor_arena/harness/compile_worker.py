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

if str(DATASETS_ROOT) not in sys.path:
    sys.path.insert(0, str(DATASETS_ROOT))
from ipfs_datasets_py.logic.hammers.frontends.lean_toolchain import (  # noqa: E402
    KERNEL_COMMAND_TEMPLATE,
    LeanToolchainMissing,
    LeanToolchainResolver,
    run_lean_process,
)

FROZEN_WARMUP_SHA256 = lra_splice.FROZEN_WARMUP_SHA256
WARMUP_N = lra_splice.WARMUP_N
STRATA_SOURCE = lra_bake.STRATA_SOURCE
PUTNAM_SOURCE = lra_bake.PUTNAM_SOURCE
STRATA_FIRST_TAG = lra_bake.STRATA_FIRST_TAG
STRATA_FIRST_COMMIT = lra_bake.STRATA_FIRST_COMMIT
STRATA_URL = lra_bake.STRATA_URL
STRATA_FIRST_FILE = "Strata/Transform/CallElimCorrect.lean"
STRATA_EXPAND_FILE = "Strata/Languages/Core/StatementSemanticsProps.lean"
MEASUREMENT_MAX_HEARTBEATS = lra_bake.MEASUREMENT_MAX_HEARTBEATS
MEASUREMENT_ARGV_TEMPLATE = (
    "{lake} env {lean} -DmaxHeartbeats="
    f"{MEASUREMENT_MAX_HEARTBEATS} --json {{source_file}}"
)
LEAN_NUM_THREADS = 1
WARMUP_TAG_TIMEOUT_SECONDS = 600.0
OFFICIAL_TAG_TIMEOUT_SECONDS = 1200.0
INDEPENDENT_KERNEL_VERIFIER_DEFAULT_TIMEOUT_SECONDS = 30.0
GIT_BIN = lra_bake.GIT_BIN
RECEIPT_SCHEMA = "lra-compile-receipt/v1"
PROCESS_SUPERVISOR_ENV = "IPFS_DATASETS_PROCESS_SUPERVISOR_DIR"

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
FORBIDDEN_ORACLE_NAMES = frozenset(
    {
        "IndependentKernelVerifier",
        "KernelVerifier",
        "verify_admitted_lean_proof",
        "verify_lean_proof_text",
    }
)
FORBIDDEN_CALLS = frozenset({"which", "find_executable", "LOCK_EX"})
FORBIDDEN_SCORE_NAMES = frozenset(
    {
        "arena_score",
        "arena_score_tokens",
        "arena_score_elab",
        "official_track2_score",
        "token_savings",
    }
)
_HEADER_HEARTBEATS = re.compile(r"set_option\s+maxHeartbeats\s+(\d+)")
_AXIOM_LINE = re.compile(
    r"^[^\s:]+\s*:\s*(?:\[(?P<bracket>[^\]]*)\]|(?P<bare>.+))\s*$"
)


class CompileError(RuntimeError):
    """Fail-closed lake compile-worker error."""


class CompileToolchainMissing(CompileError):
    """Tag-pinned elan lake/lean is not installed. Not a PATH fallback."""


class CloneMissing(CompileError):
    """Cached clone is absent while network is denied."""


class LakeTimeoutTooSmall(CompileError):
    """Lake timeout must exceed the IndependentKernelVerifier 30 s default."""


@dataclass(frozen=True)
class VersionPin:
    lean_tag: str
    git_commit: str

    def to_dict(self) -> dict[str, str]:
        return {"lean_tag": self.lean_tag, "git_commit": self.git_commit}


@dataclass
class CompileReceipt:
    """One per-tag lake compile receipt. IndependentKernelVerifier is unused."""

    schema: str = RECEIPT_SCHEMA
    name: str = ""
    source: str = ""
    file_path: str = ""
    url: str = ""
    lean_tag: str = ""
    git_commit: str = ""
    argv: list[str] = field(default_factory=list)
    cwd: str = ""
    exit_code: int = -1
    timed_out: bool = False
    timeout_seconds: float = WARMUP_TAG_TIMEOUT_SECONDS
    stdout: str = ""
    stderr: str = ""
    stdout_digest: str = ""
    axiom_names: list[str] = field(default_factory=list)
    axiom_digest: str = ""
    sorryAx: bool = False
    wall_ms: float = 0.0
    cpu_ms: float = 0.0
    n_samples: int = 1
    measurement_maxHeartbeats: int = MEASUREMENT_MAX_HEARTBEATS
    header_maxHeartbeats: Optional[int] = None
    lean_num_threads: int = LEAN_NUM_THREADS
    independent_kernel_verifier_used: bool = False
    independent_kernel_verifier_timeout_seconds: None = None
    lake_oracle: bool = True
    kernel_command_template: str = KERNEL_COMMAND_TEMPLATE
    ok: bool = False
    aborted_remaining_tags: list[str] = field(default_factory=list)
    hardware_class: str = "unscored-dev"
    error: str = ""
    arena_score: None = None
    score: None = None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["arena_score"] = None
        payload["score"] = None
        payload["independent_kernel_verifier_used"] = False
        payload["independent_kernel_verifier_timeout_seconds"] = None
        payload["lake_oracle"] = True
        return payload


@dataclass
class CompilePlan:
    records: list[dict[str, Any]]
    frozen_warmup_sha256: str
    jsonl_bytes: int
    n_records: int
    arena_score: None = None

    @property
    def first_record(self) -> dict[str, Any]:
        for record in self.records:
            if record.get("source") == STRATA_SOURCE:
                return record
        raise CompileError("warmup JSONL has no Strata record")

    def to_dict(self) -> dict[str, Any]:
        first = self.first_record
        first_pins = iter_version_pins(first.get("version_info"))
        return {
            "arena_score": None,
            "expand_after_first_green": True,
            "first_commit": first_pins[0].git_commit if first_pins else "",
            "first_file": str(first.get("file_path") or ""),
            "first_is_strata": first.get("source") == STRATA_SOURCE,
            "first_is_strata_v4_26": (
                first.get("source") == STRATA_SOURCE
                and first_pins
                and first_pins[0].lean_tag == STRATA_FIRST_TAG
                and first_pins[0].git_commit == STRATA_FIRST_COMMIT
                and str(first.get("file_path") or "") == STRATA_FIRST_FILE
                and str(first.get("url") or "") == STRATA_URL
            ),
            "first_name": str(first.get("name") or ""),
            "first_tag": first_pins[0].lean_tag if first_pins else "",
            "first_url": str(first.get("url") or ""),
            "frozen_warmup_sha256": self.frozen_warmup_sha256,
            "independent_kernel_verifier_default_timeout_seconds": (
                INDEPENDENT_KERNEL_VERIFIER_DEFAULT_TIMEOUT_SECONDS
            ),
            "independent_kernel_verifier_is_lake_oracle": False,
            "jsonl_bytes": self.jsonl_bytes,
            "kernel_command_template": KERNEL_COMMAND_TEMPLATE,
            "measurement_argv_template": MEASUREMENT_ARGV_TEMPLATE,
            "measurement_maxHeartbeats": MEASUREMENT_MAX_HEARTBEATS,
            "n_records": self.n_records,
            "newest_tag_first": True,
            "official_timeout_seconds": OFFICIAL_TAG_TIMEOUT_SECONDS,
            "score": None,
            "warmup_timeout_seconds": WARMUP_TAG_TIMEOUT_SECONDS,
        }


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

    from jevops.outer import require_positive_above

    return require_positive_above(
        timeout,
        INDEPENDENT_KERNEL_VERIFIER_DEFAULT_TIMEOUT_SECONDS,
        error_cls=CompileError,
        too_small_cls=LakeTimeoutTooSmall,
        not_positive="lake compile timeout must be a positive number",
        too_small=(
            "lake compile timeout {value}s must exceed IndependentKernelVerifier "
            "default {floor}s; the 30s kernel verifier is not the lake oracle"
        ),
    )


def header_max_heartbeats(header: str) -> Optional[int]:
    from jevops.outer import first_group_int

    return first_group_int(header, _HEADER_HEARTBEATS)


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
    from jevops.outer import refuse_basename, require_basename

    lake_path = require_basename(
        lake_path, "lake", error_cls=CompileError, fmt="expected tag-pinned lake, got {path!r}"
    )
    lean_path = require_basename(
        lean_path, "lean", error_cls=CompileError, fmt="expected tag-pinned lean, got {path!r}"
    )
    if max_heartbeats <= 0:
        raise CompileError("measurement maxHeartbeats must be finite and positive")
    if not source_file:
        raise CompileError("source_file is required")
    refuse_basename(
        source_file,
        lra_bake.FORBIDDEN_PUTNAM_BASENAME,
        error_cls=CompileError,
        fmt="refusing to compile {name} as the Putnam module",
    )
    return [
        lake_path,
        "env",
        lean_path,
        f"-DmaxHeartbeats={max_heartbeats}",
        "--json",
        source_file,
    ]


def axiom_digest(axiom_names: Sequence[str]) -> str:
    from jevops.outer import digest_compact

    return digest_compact(list(axiom_names))


def parse_axioms(stdout: str, stderr: str = "") -> tuple[list[str], bool]:
    """Extract axiom names and sorryAx from lake/lean stdout."""

    from jevops.search import parse_marked_list

    text = f"{stdout}\n{stderr}"
    names, _flagged = parse_marked_list(
        text,
        start_prefix="#print axioms",
        line_re=_AXIOM_LINE,
        flag_needles=("sorryAx",),
        extra_if_flagged=("sorryAx",),
    )
    sorry = "sorryAx" in text or "hasSorry" in text
    if sorry and "sorryAx" not in names:
        names.append("sorryAx")
    return names, sorry


def clone_dir(url: str, state_root: Optional[Path] = None) -> Path:
    from jevops.outer import join_under, url_cache_key

    root = Path(state_root) if state_root is not None else lra_bake.default_state_root()
    return join_under(root, "clones", url_cache_key(url))


def require_clone(
    url: str,
    *,
    network: str,
    state_root: Optional[Path] = None,
) -> Path:
    from jevops.outer import dir_has_markers

    path = clone_dir(url, state_root)
    if dir_has_markers(path, (".git", "lakefile.lean")):
        return path
    if network == "deny":
        raise CloneMissing(
            f"cached clone missing for {url} under network=deny; never falling "
            "back to PATH lean or a guessed GitHub URL"
        )
    return path


def checkout_commit(clone: Path, commit: str) -> dict[str, Any]:
    from jevops.outer import run_process

    if not commit:
        return {"ok": True, "skipped": True, "commit": commit, "cwd": str(clone)}
    git_dir = clone / ".git"
    if not git_dir.exists():
        return {"ok": True, "skipped": True, "commit": commit, "cwd": str(clone)}
    if not GIT_BIN.is_file():
        raise CompileToolchainMissing(f"git is not at {GIT_BIN}; cannot checkout {commit}")
    ran = run_process(
        [str(GIT_BIN), "-C", str(clone), "checkout", "--detach", commit],
        cwd=clone,
        error_cls=CompileError,
        fail_fmt="git checkout " + commit + " failed: {stderr}",
    )
    return {
        "ok": True,
        "skipped": False,
        "commit": commit,
        "cwd": str(clone),
        "exit_code": ran["exit_code"],
    }


def project_dir_for_record(
    record: Mapping[str, Any],
    pin: VersionPin,
    *,
    state_root: Optional[Path] = None,
) -> Path:
    source = str(record.get("source") or "")
    if source == PUTNAM_SOURCE:
        return lra_bake.putnam_project_dir(
            lra_bake.BakeJob(
                kind="putnam",
                source=PUTNAM_SOURCE,
                lean_tag=pin.lean_tag,
                git_commit=pin.git_commit,
                url="",
                cache_key=f"putnam/{pin.lean_tag}",
                phase=2,
                record_names=(str(record.get("name") or ""),),
                file_paths=(lra_bake.PUTNAM_CANDIDATE_RELPATH,),
                module=lra_bake.PUTNAM_MODULE,
                lakefile_required=True,
            ),
            state_root,
        )
    url = str(record.get("url") or "")
    if not url:
        raise CompileError(f"{record.get('name')}: repo record is missing url")
    return clone_dir(url, state_root)


def source_relpath(record: Mapping[str, Any]) -> str:
    source = str(record.get("source") or "")
    if source == PUTNAM_SOURCE:
        return lra_bake.PUTNAM_CANDIDATE_RELPATH
    from jevops.outer import refuse_basename

    path = str(record.get("file_path") or "")
    if not path:
        raise CompileError(f"{record.get('name')}: missing file_path")
    refuse_basename(path, lra_bake.FORBIDDEN_PUTNAM_BASENAME, error_cls=CompileError, fmt="refusing {name}")
    return path


def write_record_source(record: Mapping[str, Any], dest: Path) -> Path:
    from jevops.outer import write_text

    split = lra_splice.split_statement_body(record)
    text = lra_splice.lake_candidate_source(
        header=split.header,
        statement=split.statement,
        tactic_block=lra_splice.tactic_block_from_body(split.body_suffix),
    )
    return write_text(
        dest,
        text,
        refuse=lra_bake.FORBIDDEN_PUTNAM_BASENAME,
        error_cls=CompileError,
        refuse_fmt="refusing to write {name}",
    )


def resolve_pin(
    pin: VersionPin,
    *,
    elan_home: Optional[Path] = None,
    require_installed: bool = True,
):
    resolver = LeanToolchainResolver(elan_home)
    try:
        return resolver.resolve_tag(
            pin.lean_tag, git_commit=pin.git_commit, require_installed=require_installed
        )
    except LeanToolchainMissing as exc:
        raise CompileToolchainMissing(str(exc)) from exc


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
    name = str(record.get("name") or "")
    source = str(record.get("source") or "")
    header_cap = header_max_heartbeats(str(record.get("header") or ""))
    relpath = source_relpath(record)
    receipt = CompileReceipt(
        name=name,
        source=source,
        file_path=relpath,
        url=str(record.get("url") or ""),
        lean_tag=pin.lean_tag,
        git_commit=pin.git_commit,
        timeout_seconds=timeout,
        measurement_maxHeartbeats=MEASUREMENT_MAX_HEARTBEATS,
        header_maxHeartbeats=header_cap,
        hardware_class=hardware_class,
    )
    try:
        toolchain = resolve_pin(pin, elan_home=elan_home, require_installed=True)
        if source == PUTNAM_SOURCE:
            project = project_dir_for_record(record, pin, state_root=state_root)
            if not (project / "lakefile.lean").is_file():
                lra_bake.materialize_putnam_project(
                    pin.lean_tag, project, jsonl_version_pin=pin.git_commit
                )
            dest = project / lra_bake.PUTNAM_CANDIDATE_RELPATH
            write_record_source(record, dest)
            cwd = project
            source_file = lra_bake.PUTNAM_CANDIDATE_RELPATH
        else:
            cwd = require_clone(
                str(record.get("url") or ""), network=network, state_root=state_root
            )
            if not skip_checkout:
                checkout_commit(cwd, pin.git_commit)
            dest = cwd / relpath
            if not dest.is_file():
                write_record_source(record, dest)
            source_file = relpath
        if require_oleans:
            job = _bake_job_for_record(record, pin)
            lra_bake.require_cache(job, network=network, state_root=state_root)
        argv = measurement_argv(
            toolchain.lake_path,
            toolchain.lean_path,
            source_file,
            max_heartbeats=MEASUREMENT_MAX_HEARTBEATS,
        )
        receipt.argv = list(argv)
        receipt.cwd = str(cwd)
        env = os.environ.copy()
        env["LEAN_NUM_THREADS"] = str(LEAN_NUM_THREADS)
        env["ELAN_HOME"] = toolchain.elan_home
        supervisor_dir = (
            Path(state_root) / "process-supervisor"
            if state_root is not None
            else Path(tempfile.gettempdir()) / "lra-014-process-supervisor"
        )
        supervisor_dir.mkdir(parents=True, exist_ok=True)
        env[PROCESS_SUPERVISOR_ENV] = str(supervisor_dir)
        from jevops.outer import process_exit_code, timed_call

        result, wall_ms, cpu_ms = timed_call(
            lambda: run_lean_process(
                argv,
                timeout=timeout,
                cwd=str(cwd),
                env=env,
            )
        )
        stdout = result.stdout or ""
        stderr = result.stderr or ""
        axiom_names, sorry = parse_axioms(stdout, stderr)
        exit_code, timed_out = process_exit_code(result)
        receipt.exit_code = exit_code
        receipt.timed_out = timed_out
        receipt.stdout = stdout
        receipt.stderr = stderr
        receipt.stdout_digest = sha256_text(stdout)
        receipt.axiom_names = axiom_names
        receipt.axiom_digest = axiom_digest(axiom_names)
        receipt.sorryAx = sorry
        receipt.wall_ms = wall_ms
        receipt.cpu_ms = cpu_ms
        if result.error:
            receipt.error = str(result.error)
        receipt.ok = (
            exit_code == 0
            and not receipt.timed_out
            and not receipt.error
            and not sorry
            and "sorryAx" not in axiom_names
            and bool(stdout.strip())
            and receipt.measurement_maxHeartbeats == MEASUREMENT_MAX_HEARTBEATS
            and receipt.measurement_maxHeartbeats > 0
            and not receipt.independent_kernel_verifier_used
            and receipt.timeout_seconds > INDEPENDENT_KERNEL_VERIFIER_DEFAULT_TIMEOUT_SECONDS
            and argv[1:4] == ["env", toolchain.lean_path, f"-DmaxHeartbeats={MEASUREMENT_MAX_HEARTBEATS}"]
        )
        return receipt
    except (CompileError, LeanToolchainMissing, lra_bake.BakeError) as exc:
        receipt.error = str(exc)
        receipt.ok = False
        receipt.exit_code = -1
        receipt.axiom_digest = axiom_digest(receipt.axiom_names)
        receipt.stdout_digest = sha256_text(receipt.stdout)
        return receipt


def _bake_job_for_record(record: Mapping[str, Any], pin: VersionPin) -> lra_bake.BakeJob:
    source = str(record.get("source") or "")
    if source == PUTNAM_SOURCE:
        return lra_bake.BakeJob(
            kind="putnam",
            source=PUTNAM_SOURCE,
            lean_tag=pin.lean_tag,
            git_commit=pin.git_commit,
            url="",
            cache_key=f"putnam/{pin.lean_tag}",
            phase=2,
            record_names=(str(record.get("name") or ""),),
            file_paths=(lra_bake.PUTNAM_CANDIDATE_RELPATH,),
            module=lra_bake.PUTNAM_MODULE,
            lakefile_required=True,
        )
    url = str(record.get("url") or "")
    relpath = str(record.get("file_path") or "")
    return lra_bake.BakeJob(
        kind="repo",
        source=source,
        lean_tag=pin.lean_tag,
        git_commit=pin.git_commit,
        url=url,
        cache_key=f"repo/{lra_bake._url_cache_key(url)}/{pin.git_commit}/{pin.lean_tag}",
        phase=0 if source == STRATA_SOURCE and pin.lean_tag == STRATA_FIRST_TAG else 1,
        record_names=(str(record.get("name") or ""),),
        file_paths=(relpath,),
        module=relpath,
        lakefile_required=True,
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
    from jevops.outer import collect_until

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
        abort_fn=(lambda receipt: not receipt.ok) if abort_on_first_failure else None,
        remaining_fn=lambda rest: [item.lean_tag for item in rest],
        remaining_attr="aborted_remaining_tags" if abort_on_first_failure else "",
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
    jsonl = Path(path) if path is not None else WARMUP_JSONL
    raw, digest, records = lra_splice.load_warmup_records(jsonl)
    return CompilePlan(
        records=records,
        frozen_warmup_sha256=digest,
        jsonl_bytes=len(raw),
        n_records=len(records),
        arena_score=None,
    )


def first_strata_record(records: Sequence[Mapping[str, Any]]) -> Mapping[str, Any]:
    from jevops.outer import first_where

    return first_where(
        records,
        lambda record: record.get("source") == STRATA_SOURCE,
        error_cls=CompileError,
        miss="no Strata record in warmup JSONL",
    )


def expand_records(
    records: Sequence[Mapping[str, Any]],
    *,
    after_name: str,
) -> list[Mapping[str, Any]]:
    """Records whose tags are compiled after ``after_name`` is green."""

    from jevops.outer import after_named

    return after_named(
        records,
        after_name,
        pred=lambda record: record.get("source") == STRATA_SOURCE,
    )


def probe_toolchain(tags: Iterable[str] | None = None) -> dict[str, Any]:
    if tags is None:
        tags = (STRATA_FIRST_TAG, "v4.27.0", "v4.29.1")
    from jevops.outer import map_partition, unique_keep

    wanted = unique_keep(list(tags))
    resolver = LeanToolchainResolver()

    pins = [
        resolver.resolve_tag(tag, require_installed=False).to_dict() for tag in wanted
    ]
    installed, missing = map_partition(
        pins, lambda pin: pin["installed"], lambda pin: pin["lean_tag"]
    )
    return {
        "arena_score": None,
        "default_elan_home": str(lra_bake.default_elan_home()),
        "elan_home_env": os.environ.get("ELAN_HOME"),
        "independent_kernel_verifier_is_lake_oracle": False,
        "installed_tags": installed,
        "kernel_command_template": KERNEL_COMMAND_TEMPLATE,
        "lake": False,
        "measurement_argv_template": MEASUREMENT_ARGV_TEMPLATE,
        "missing_tags": missing,
        "path": os.environ.get("PATH"),
        "pins": pins,
        "run_lean_process": run_lean_process.__name__,
        "score": None,
        "validation_home": str(Path.home()),
        "warmup_timeout_seconds": WARMUP_TAG_TIMEOUT_SECONDS,
        "capability_gap": (
            "No tag-pinned elan lean/lake binaries are installed under the "
            "resolver elan home. Paths remain tag-pinned; this is not PATH "
            "lake usability and is not IndependentKernelVerifier."
            if missing and not installed
            else ""
        ),
    }


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
    from jevops.repair import ast_name_hits, audit_source as _audit, call_kwarg_numbers, has_constant

    text = Path(__file__).read_text(encoding="utf-8") if source is None else source
    out = _audit(
        text,
        forbidden_imports=FORBIDDEN_IMPORT_NAMES,
        forbidden_calls=FORBIDDEN_CALLS,
        forbidden_scores=FORBIDDEN_SCORE_NAMES,
    )
    tree = ast.parse(text)
    oracle_uses = ast_name_hits(tree, FORBIDDEN_ORACLE_NAMES)
    timeout_literals = call_kwarg_numbers(tree, ("timeout", "timeout_seconds"))
    calls = set(out["call_names"])
    score_assignments = list(out["score_keys"])
    uses_run_lean_process = "run_lean_process" in calls
    uses_measurement_argv = "measurement_argv" in calls
    has_ikv_timeout_constant = has_constant(text, INDEPENDENT_KERNEL_VERIFIER_DEFAULT_TIMEOUT_SECONDS)
    lake_timeout_literals_ok = all(
        value > INDEPENDENT_KERNEL_VERIFIER_DEFAULT_TIMEOUT_SECONDS
        for value in timeout_literals
        if value == INDEPENDENT_KERNEL_VERIFIER_DEFAULT_TIMEOUT_SECONDS or value >= 1.0
    ) and INDEPENDENT_KERNEL_VERIFIER_DEFAULT_TIMEOUT_SECONDS not in timeout_literals
    return {
        "imported_names": out["imported_names"],
        "forbidden_imports": out["forbidden_imports"],
        "forbidden_calls": out["forbidden_calls"],
        "forbidden_oracle_uses": sorted(oracle_uses),
        "score_assignments": score_assignments,
        "timeout_kwarg_literals": timeout_literals,
        "uses_run_lean_process": uses_run_lean_process,
        "uses_measurement_argv": uses_measurement_argv,
        "has_ikv_timeout_constant": has_ikv_timeout_constant,
        "lake_timeout_literals_ok": lake_timeout_literals_ok,
        "independent_kernel_verifier_is_lake_oracle": False,
        "ok": (
            not out["forbidden_imports"]
            and not out["forbidden_calls"]
            and not oracle_uses
            and not score_assignments
            and uses_run_lean_process
            and uses_measurement_argv
            and lake_timeout_literals_ok
        ),
    }


_FAKE_LAKE = """#!/usr/bin/python3.12
import os
import sys

args = sys.argv[1:]
if not args or args[0] != "env" or len(args) < 2:
    sys.stderr.write("lra-fake-lake: expected 'env <lean> ...'\\n")
    sys.exit(2)
os.execv(args[1], args[1:])
"""

_FAKE_LEAN = """#!/usr/bin/python3.12
import json
import sys
from pathlib import Path

argv = sys.argv[1:]
heartbeats = None
source = None
for arg in argv:
    if arg.startswith("-DmaxHeartbeats="):
        try:
            heartbeats = int(arg.split("=", 1)[1])
        except ValueError:
            heartbeats = -1
    elif arg == "--json":
        continue
    elif not arg.startswith("-"):
        source = arg

if heartbeats is None or heartbeats <= 0:
    sys.stderr.write("measurement maxHeartbeats must be finite and positive\\n")
    sys.exit(3)
if source is None:
    sys.stderr.write("missing source file\\n")
    sys.exit(4)
path = Path(source)
if not path.is_file():
    sys.stderr.write(f"source not found: {source}\\n")
    sys.exit(4)
text = path.read_text(encoding="utf-8")
sorry = "sorry" in text.split() or "sorryAx" in text or "admit" in text.split()
decl = path.stem.replace(".", "_") or "lra_candidate"
if sorry:
    print(json.dumps({"severity": "warning", "data": "hasSorry", "pos": {"line": 1, "column": 0}}))
    print(f"#print axioms {decl}")
    print(f"{decl} : sorryAx")
    sys.exit(1)
print(json.dumps({"severity": "information", "data": "ok", "pos": {"line": 1, "column": 0}}))
print(f"#print axioms {decl}")
print(f"{decl} : []")
sys.exit(0)
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


def plant_synthetic_strata_clone(clone: Path) -> Path:
    from jevops.outer import plant_git_skeleton

    return plant_git_skeleton(
        clone,
        files={
            "lakefile.lean": (
                "import Lake\n"
                "open Lake DSL\n"
                "\n"
                "package «strata» where\n"
                f'  moreLeanArgs := #["-DmaxHeartbeats={MEASUREMENT_MAX_HEARTBEATS}"]\n'
                "\n"
                "lean_lib «Strata»\n"
            ),
            "lean-toolchain": f"leanprover/lean4:{STRATA_FIRST_TAG}\n",
        },
    )


def _receipt_summary(receipt: CompileReceipt) -> dict[str, Any]:
    from jevops.outer import argv_layout

    return {
        "aborted_remaining_tags": list(receipt.aborted_remaining_tags),
        "argv_has_lake_env_lean": argv_layout(
            receipt.argv,
            min_len=6,
            names={0: "lake", 2: "lean"},
            eq={
                1: "env",
                3: f"-DmaxHeartbeats={MEASUREMENT_MAX_HEARTBEATS}",
                4: "--json",
            },
        ),
        "argv_tag_pinned": argv_layout(
            receipt.argv,
            min_len=3,
            contains={0: receipt.lean_tag, 2: receipt.lean_tag},
        ),
        "axiom_digest": receipt.axiom_digest,
        "axiom_digest_hex64": len(receipt.axiom_digest) == 64,
        "axiom_names": list(receipt.axiom_names),
        "cpu_ms_nonnegative": receipt.cpu_ms >= 0.0,
        "exit_code": receipt.exit_code,
        "file_path": receipt.file_path,
        "git_commit": receipt.git_commit,
        "header_maxHeartbeats": receipt.header_maxHeartbeats,
        "independent_kernel_verifier_timeout_seconds": (
            receipt.independent_kernel_verifier_timeout_seconds
        ),
        "independent_kernel_verifier_used": receipt.independent_kernel_verifier_used,
        "lake_oracle": receipt.lake_oracle,
        "lean_tag": receipt.lean_tag,
        "measurement_maxHeartbeats": receipt.measurement_maxHeartbeats,
        "measurement_maxHeartbeats_finite": receipt.measurement_maxHeartbeats > 0
        and receipt.measurement_maxHeartbeats == MEASUREMENT_MAX_HEARTBEATS,
        "name": receipt.name,
        "ok": receipt.ok,
        "sorryAx": receipt.sorryAx,
        "source": receipt.source,
        "stdout_digest": receipt.stdout_digest,
        "stdout_nonempty": bool(receipt.stdout.strip()),
        "printed_axioms": "#print axioms" in receipt.stdout,
        "timeout_exceeds_ikv_30s": (
            receipt.timeout_seconds > INDEPENDENT_KERNEL_VERIFIER_DEFAULT_TIMEOUT_SECONDS
        ),
        "timeout_seconds": receipt.timeout_seconds,
        "timed_out": receipt.timed_out,
        "wall_ms_positive": receipt.wall_ms > 0.0,
        "error": receipt.error,
        "arena_score": None,
        "score": None,
    }


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
    with tempfile.TemporaryDirectory(
        prefix="lra-014-compile-", dir=str(_exec_scratch_parent())
    ) as tmp:
        root = Path(tmp)
        elan_home = root / "elan"
        state_root = root / "state"
        receipts_dir = root / "receipts"
        for tag in ("v4.25.0", "v4.26.0", "v4.27.0", "v4.29.1"):
            plant_fake_toolchain(elan_home, tag)
        clone = plant_synthetic_strata_clone(clone_dir(STRATA_URL, state_root))
        first = plan.first_record
        write_record_source(first, clone / STRATA_FIRST_FILE)
        expand = expand_records(plan.records, after_name=str(first.get("name") or ""))
        if expand:
            write_record_source(expand[-1], clone / STRATA_EXPAND_FILE)
        first_job = _bake_job_for_record(first, iter_version_pins(first.get("version_info"))[0])
        lra_bake.plant_synthetic_cache(first_job, state_root)
        timeout_30_rejected = False
        try:
            require_lake_timeout(INDEPENDENT_KERNEL_VERIFIER_DEFAULT_TIMEOUT_SECONDS)
        except LakeTimeoutTooSmall:
            timeout_30_rejected = True
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
        first_green = bool(first_receipts) and all(item.ok for item in first_receipts)
        expand_receipts: list[CompileReceipt] = []
        if first_green:
            for record in expand:
                if str(record.get("file_path") or "") != STRATA_EXPAND_FILE:
                    continue
                expand_receipts.extend(
                    compile_record(
                        record,
                        timeout=WARMUP_TAG_TIMEOUT_SECONDS,
                        state_root=state_root,
                        elan_home=elan_home,
                        network="deny",
                        hardware_class="synthetic",
                        skip_checkout=True,
                    )
                )
                break
        putnam = next(
            record for record in plan.records if record.get("source") == PUTNAM_SOURCE
        )
        putnam_pins = iter_version_pins(putnam.get("version_info"))
        putnam_pin = next(pin for pin in putnam_pins if pin.lean_tag == STRATA_FIRST_TAG)
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
        written = write_receipts(all_receipts, receipts_dir)
        persisted: list[str] = []
        if persist_receipts is not None:
            persisted = write_receipts(all_receipts, Path(persist_receipts))
        missing_clone_closed = False
        try:
            require_clone(
                "https://github.com/example/missing-lra-014",
                network="deny",
                state_root=state_root,
            )
        except CloneMissing:
            missing_clone_closed = True
        expand_tags = [item.lean_tag for item in expand_receipts]
        return {
            "elan_home": str(elan_home),
            "expand_n_receipts": len(expand_receipts),
            "expand_ok": bool(expand_receipts) and all(item.ok for item in expand_receipts),
            "expand_receipts": [_receipt_summary(item) for item in expand_receipts],
            "expand_tags_newest_first": expand_tags == sorted(
                expand_tags, key=_tag_sort_key, reverse=True
            ),
            "first_file": STRATA_FIRST_FILE,
            "first_green": first_green,
            "first_n_receipts": len(first_receipts),
            "first_name": str(first.get("name") or ""),
            "first_receipts": [_receipt_summary(item) for item in first_receipts],
            "first_strata_compiled": first_green,
            "first_via_lake_env_lean": bool(first_receipts)
            and all(_receipt_summary(item)["argv_has_lake_env_lean"] for item in first_receipts),
            "missing_clone_fails_closed_under_network_deny": missing_clone_closed,
            "n_receipts_persisted": len(persisted),
            "n_receipts_written": len(written),
            "persisted_receipts": persisted,
            "putnam_header_maxHeartbeats": putnam_receipt.header_maxHeartbeats,
            "putnam_measurement_maxHeartbeats": putnam_receipt.measurement_maxHeartbeats,
            "putnam_ok": putnam_receipt.ok,
            "putnam_overrides_zero_header": (
                putnam_receipt.header_maxHeartbeats == 0
                and putnam_receipt.measurement_maxHeartbeats == MEASUREMENT_MAX_HEARTBEATS
                and putnam_receipt.ok
            ),
            "putnam_receipt": _receipt_summary(putnam_receipt),
            "receipts_dir": str(receipts_dir),
            "receipts_written": [Path(path).name for path in written],
            "timeout_30s_rejected": timeout_30_rejected,
            "timeout_is_warmup_600s": all(
                item.timeout_seconds == WARMUP_TAG_TIMEOUT_SECONDS
                for item in [*first_receipts, *expand_receipts, putnam_receipt]
            ),
            "independent_kernel_verifier_used": False,
        }


def self_check(
    path: Optional[Path] = None,
    *,
    receipts_dir: Optional[Path] = None,
) -> dict[str, Any]:
    jsonl = Path(path) if path is not None else WARMUP_JSONL
    plan = plan_compile(jsonl)
    audit = audit_source()
    synthetic = _synthetic_compile(plan, persist_receipts=receipts_dir)
    toolchain = probe_toolchain()
    first = plan.first_record
    first_pins = iter_version_pins(first.get("version_info"))
    putnam_headers = []
    for record in plan.records:
        if record.get("source") != PUTNAM_SOURCE:
            continue
        putnam_headers.append(header_max_heartbeats(str(record.get("header") or "")))
    report: dict[str, Any] = {
        "ok": False,
        "arena_score": None,
        "score": None,
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
        "first_name": str(first.get("name") or ""),
        "first_file": str(first.get("file_path") or ""),
        "first_is_strata_v4_26": (
            first.get("source") == STRATA_SOURCE
            and first_pins
            and first_pins[0].lean_tag == STRATA_FIRST_TAG
            and first_pins[0].git_commit == STRATA_FIRST_COMMIT
            and str(first.get("file_path") or "") == STRATA_FIRST_FILE
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
        "warmup_path": str(jsonl.relative_to(REPO_ROOT)),
        "protocol": "LRA/v1",
        "live_elan_installed": bool(toolchain["installed_tags"]),
        "capability_gap": toolchain["capability_gap"],
    }
    first_receipts = synthetic["first_receipts"]
    report["ok"] = bool(
        report["n_records"] == WARMUP_N
        and report["jsonl_unchanged"]
        and report["first_is_strata_v4_26"]
        and report["first_strata_compiled_via_lake_env_lean"]
        and report["per_tag_timeout_written"]
        and report["axiom_digest_receipts_written"]
        and report["putnam_headers_are_zero"]
        and synthetic["putnam_overrides_zero_header"]
        and synthetic["timeout_30s_rejected"]
        and synthetic["missing_clone_fails_closed_under_network_deny"]
        and synthetic["expand_ok"]
        and synthetic["expand_tags_newest_first"]
        and all(item["axiom_digest_hex64"] for item in first_receipts)
        and all(item["stdout_nonempty"] and item["printed_axioms"] for item in first_receipts)
        and all(not item["error"] for item in first_receipts)
        and all(item["timeout_exceeds_ikv_30s"] for item in first_receipts)
        and all(not item["independent_kernel_verifier_used"] for item in first_receipts)
        and audit["ok"]
        and report["independent_kernel_verifier_used"] is False
        and report["independent_kernel_verifier_is_lake_oracle"] is False
        and report["arena_score"] is None
        and report["score"] is None
        and report["llama_server_started"] is False
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
    args = parser.parse_args(list(argv) if argv is not None else None)

    if args.self_check or argv is None or argv == []:
        report = self_check(args.jsonl, receipts_dir=args.receipts_dir)
        _print_json(report)
        return 0 if report["ok"] else 1

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
            _print_json(
                {
                    "ok": False,
                    "error": str(exc),
                    "error_type": type(exc).__name__,
                    "arena_score": None,
                    "independent_kernel_verifier_is_lake_oracle": False,
                }
            )
            return 1
        plan = plan_compile(args.jsonl)
        network = lra_bake.network_mode(args.network)
        records: list[Mapping[str, Any]] = []
        if args.name:
            match = next((item for item in plan.records if item.get("name") == args.name), None)
            if match is None:
                _print_json(
                    {
                        "ok": False,
                        "error": f"unknown warm-up problem: {args.name}",
                        "arena_score": None,
                    }
                )
                return 1
            records = [match]
        else:
            first = plan.first_record
            records = [first]
            if args.expand_tags:
                records.extend(expand_records(plan.records, after_name=str(first.get("name") or "")))
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
        return 0 if payload["ok"] else 1

    parser.error("choose --self-check, --plan, --probe-toolchain, or --compile-first")
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

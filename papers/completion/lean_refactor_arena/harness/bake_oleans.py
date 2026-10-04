#!/usr/bin/env python3
"""Bake lake .olean caches and per-tag Putnam Mathlib+Aesop lake projects.

First ``lake build`` is hours. Record **Strata v4.26.0** first, then the other
``(clone, commit, tag)`` units, then one Putnam Mathlib+Aesop lake project per
JSONL Putnam tag. Missing oleans under ``network=deny`` fail closed. Putnam is
never ``Tmp.lean`` and never a guessed PutnamBench GitHub URL.

This module plans, materializes lakefiles, and checks the olean cache. A live
``lake build`` runs only when a tag-pinned elan ``lake`` is installed and
network is allowed. Self-check does not compile, does not start llama-server,
and does not claim Arena scores.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import stat
import sys
import tempfile
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping, Optional, Sequence
from urllib.parse import urlparse

HERE = Path(__file__).resolve().parent
PAPER_ROOT = HERE.parent
REPO_ROOT = HERE.parents[3]
WARMUP_JSONL = PAPER_ROOT / "data" / "benchmark_data_warmup.jsonl"
PUTNAM_README = HERE / "putnam_lake" / "README.md"

if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
import _jevops_path  # noqa: E402,F401
import splice as lra_splice  # noqa: E402

FROZEN_WARMUP_SHA256 = lra_splice.FROZEN_WARMUP_SHA256
WARMUP_N = lra_splice.WARMUP_N
from jevops.catalogs import AESOP_GIT  # noqa: E402
from jevops.catalogs import BAKE_ARGV_TEMPLATE  # noqa: E402
from jevops.catalogs import DEFAULT_LAKE_TIMEOUT_SECONDS  # noqa: E402
from jevops.catalogs import ELAN_TOOLCHAIN_DIRNAME_PREFIX  # noqa: E402
from jevops.catalogs import FORBIDDEN_PUTNAM_BASENAME  # noqa: E402
from jevops.catalogs import FORBIDDEN_PUTNAM_URL_NEEDLES  # noqa: E402
from jevops.catalogs import KERNEL_COMMAND_TEMPLATE  # noqa: E402
from jevops.catalogs import MATHLIB_GIT  # noqa: E402
from jevops.catalogs import MEASUREMENT_MAX_HEARTBEATS  # noqa: E402
from jevops.catalogs import NETWORK_DENY_VALUES  # noqa: E402
from jevops.catalogs import PUTNAM_CANDIDATE_RELPATH  # noqa: E402
from jevops.catalogs import PUTNAM_LIB  # noqa: E402
from jevops.catalogs import PUTNAM_MODULE  # noqa: E402
from jevops.catalogs import PUTNAM_PACKAGE  # noqa: E402
from jevops.catalogs import PUTNAM_ROOT_RELPATH  # noqa: E402
from jevops.catalogs import PUTNAM_SOURCE  # noqa: E402
from jevops.catalogs import PUTNAM_TAGS  # noqa: E402
from jevops.catalogs import SOURCE_ORDER  # noqa: E402
from jevops.catalogs import STRATA_FIRST_COMMIT  # noqa: E402
from jevops.catalogs import STRATA_FIRST_TAG  # noqa: E402
from jevops.catalogs import STRATA_SOURCE  # noqa: E402
from jevops.catalogs import STRATA_URL  # noqa: E402
from jevops.catalogs import FORBIDDEN_CALLS_CORE as FORBIDDEN_CALLS  # noqa: E402
from jevops.catalogs import FORBIDDEN_SCORE_NAMES  # noqa: E402
from jevops.catalogs import GIT_BIN  # noqa: E402
from jevops.catalogs import STATE_RELATIVE  # noqa: E402

FORBIDDEN_IMPORT_NAMES = frozenset(
    {
        "fcntl",
        "LeanstralProofProvider",
        "leanstral_proof_provider",
        "shutil",
    }
)



class BakeError(RuntimeError):
    """Fail-closed olean-bake or Putnam lake-project error."""


class OleanCacheMissing(BakeError):
    """Required .olean cache is absent while network is denied."""


class BakeToolchainMissing(BakeError):
    """Tag-pinned elan lake/lean is not installed. Not a PATH fallback."""


from jevops.lean import BakeJob
from jevops.lean import BakePlan as _KernelBakePlan
from jevops.lean import PutnamPin
from jevops.lean import VersionPin


@dataclass
class BakePlan(_KernelBakePlan):
    frozen_warmup_sha256: str = FROZEN_WARMUP_SHA256

    @property
    def first_job(self) -> BakeJob:
        return super().first_job(error_cls=BakeError)

    def to_dict(self) -> dict[str, Any]:
        from jevops.lean import drive_with_first, pack_bake_plan

        return drive_with_first(
            self,
            lambda first: pack_bake_plan(
                self.jobs,
                first,
                frozen_warmup_sha256=self.frozen_warmup_sha256,
                jsonl_bytes=self.jsonl_bytes,
                n_records=self.n_records,
                bake_argv_template=BAKE_ARGV_TEMPLATE,
                kernel_command_template=KERNEL_COMMAND_TEMPLATE,
                measurement_max_heartbeats=MEASUREMENT_MAX_HEARTBEATS,
                first_source=STRATA_SOURCE,
                first_tag=STRATA_FIRST_TAG,
                first_commit=STRATA_FIRST_COMMIT,
                putnam_module=PUTNAM_MODULE,
                putnam_tags=PUTNAM_TAGS,
                strata_first_tag=STRATA_FIRST_TAG,
            ),
        )


def sha256_bytes(data: bytes) -> str:
    from jevops.outer import digest_hex

    return digest_hex(data)


def sha256_file(path: Path) -> str:
    from jevops.outer import digest_file

    return digest_file(path)


def default_elan_home() -> Path:
    from jevops.outer import drive_default_home

    return drive_default_home("ELAN_HOME", ".elan")


def default_state_root() -> Path:
    from jevops.outer import state_root_from_env

    return state_root_from_env(override_key="LRA_STATE_ROOT", relative=STATE_RELATIVE)


def network_mode(value: Optional[str] = None) -> str:
    from jevops.outer import allow_or_deny

    return allow_or_deny(
        value,
        deny=NETWORK_DENY_VALUES,
        default="allow",
        env_keys=("LRA_NETWORK", "IPFS_ACCELERATE_LRA_NETWORK"),
    )


def normalize_lean_tag(value: str) -> str:
    from jevops.outer import normalize_tag

    return normalize_tag(
        value,
        prefix=ELAN_TOOLCHAIN_DIRNAME_PREFIX,
        error_cls=BakeError,
        empty="lean tag must be a nonempty string",
    )


def elan_toolchain_dirname(lean_tag: str) -> str:
    from jevops.lean import elan_toolchain_dirname as _fn

    return _fn(
        lean_tag,
        prefix=ELAN_TOOLCHAIN_DIRNAME_PREFIX,
        normalize_fn=normalize_lean_tag,
    )


def tag_pinned_paths(lean_tag: str, *, elan_home: Optional[Path] = None) -> dict[str, Any]:
    """Return elan ``lean``/``lake`` paths. Never searches PATH."""

    from jevops.outer import drive_tag_bins

    return drive_tag_bins(
        lean_tag,
        elan_home=elan_home,
        home_fn=default_elan_home,
        normalize_fn=normalize_lean_tag,
        dirname_fn=elan_toolchain_dirname,
    )


def _is_executable(path: Path) -> bool:
    from jevops.outer import is_executable

    return is_executable(path)


def iter_version_pins(version_info: Any) -> list[VersionPin]:
    from jevops.outer import iter_tag_commit_pins

    return iter_tag_commit_pins(
        version_info,
        pin_fn=lambda tag, commit: VersionPin(lean_tag=tag, git_commit=commit),
        normalize_fn=normalize_lean_tag,
        error_cls=BakeError,
        not_list="version_info must be a list of {lean_tag: git_commit} maps",
        empty_tag="version_info[{index}] has an empty lean tag",
        bad_commit="version_info[{index}] git commit must be a string, not {type}",
        not_map="version_info[{index}] is not a {{lean_tag: git_commit}} map",
        empty="version_info is empty",
    )


def _url_cache_key(url: str) -> str:
    from jevops.outer import url_cache_key

    return url_cache_key(url)


def putnam_pin(lean_tag: str, *, jsonl_version_pin: str = "") -> PutnamPin:
    from jevops.lean import putnam_pin_for_tag

    return putnam_pin_for_tag(
        lean_tag,
        PUTNAM_TAGS,
        mathlib_git=MATHLIB_GIT,
        aesop_git=AESOP_GIT,
        jsonl_version_pin=jsonl_version_pin,
        normalize_fn=normalize_lean_tag,
        error_cls=BakeError,
    )


def render_lean_toolchain(lean_tag: str) -> str:
    from jevops.lean import drive_normalized_toolchain

    return drive_normalized_toolchain(lean_tag, normalize_fn=normalize_lean_tag)


def render_lakefile(lean_tag: str) -> str:
    """Per-tag Mathlib+Aesop lakefile. Candidate module is Putnam.Candidate, not Tmp.lean."""

    from jevops.lean import drive_pin_lakefile

    return drive_pin_lakefile(
        lean_tag,
        pin_fn=putnam_pin,
        max_heartbeats=MEASUREMENT_MAX_HEARTBEATS,
    )


def render_putnam_root() -> str:
    from jevops.lean import putnam_root_import

    return putnam_root_import(PUTNAM_MODULE)


def render_putnam_candidate_stub() -> str:
    from jevops.lean import putnam_candidate_stub

    return putnam_candidate_stub()


def putnam_project_files(lean_tag: str, *, jsonl_version_pin: str = "") -> dict[str, str]:
    from jevops.lean import drive_putnam_files

    return drive_putnam_files(
        lean_tag,
        jsonl_version_pin=jsonl_version_pin,
        pin_fn=putnam_pin,
        lakefile_fn=render_lakefile,
        toolchain_fn=render_lean_toolchain,
        root_fn=render_putnam_root,
        candidate_fn=render_putnam_candidate_stub,
        root_relpath=PUTNAM_ROOT_RELPATH,
        candidate_relpath=PUTNAM_CANDIDATE_RELPATH,
    )


def materialize_putnam_project(
    lean_tag: str,
    dest: Path,
    *,
    jsonl_version_pin: str = "",
) -> dict[str, str]:
    from jevops.lean import drive_materialize_project, materialize_lake_files

    return drive_materialize_project(
        lean_tag,
        dest,
        pin=jsonl_version_pin,
        files_fn=putnam_project_files,
        write_fn=materialize_lake_files,
        refuse=FORBIDDEN_PUTNAM_BASENAME,
        error_cls=BakeError,
    )


def collect_bake_jobs(records: Sequence[Mapping[str, Any]]) -> list[BakeJob]:
    from jevops.lean import drive_collect_jobs

    return drive_collect_jobs(
        records,
        warmup_n=WARMUP_N,
        source_order=SOURCE_ORDER,
        putnam_source=PUTNAM_SOURCE,
        strata_source=STRATA_SOURCE,
        strata_first_tag=STRATA_FIRST_TAG,
        putnam_tags=PUTNAM_TAGS,
        putnam_candidate_relpath=PUTNAM_CANDIDATE_RELPATH,
        putnam_module=PUTNAM_MODULE,
        pin_fn=iter_version_pins,
        putnam_pin_fn=lambda tag, commit: putnam_pin(tag, jsonl_version_pin=commit),
        url_key_fn=_url_cache_key,
        error_cls=BakeError,
    )


def plan_bake(path: Optional[Path] = None) -> BakePlan:
    from jevops.lean import drive_loaded_plan, plan_bake_from_jobs

    return drive_loaded_plan(
        path,
        default_path=WARMUP_JSONL,
        load_fn=lra_splice.load_warmup_records,
        build_fn=lambda raw, digest, records: plan_bake_from_jobs(
            collect_bake_jobs(records),
            digest,
            len(raw),
            len(records),
            cls=BakePlan,
        ),
    )


def job_cache_dir(job: BakeJob, state_root: Optional[Path] = None) -> Path:
    from jevops.outer import drive_joined

    return drive_joined(state_root, "oleans", job.cache_key, factory=default_state_root)


def putnam_project_dir(job: BakeJob, state_root: Optional[Path] = None) -> Path:
    from jevops.outer import drive_kind_joined

    return drive_kind_joined(
        job,
        state_root,
        "putnam_lake",
        job.lean_tag,
        kind="putnam",
        factory=default_state_root,
        error_cls=BakeError,
        miss="putnam_project_dir is only defined for Putnam jobs",
    )


def cache_marker_path(cache_dir: Path) -> Path:
    from jevops.lean import cache_marker_path as _fn

    return _fn(cache_dir)


def olean_paths(cache_dir: Path) -> list[Path]:
    from jevops.outer import walk_suffix_files

    return walk_suffix_files(cache_dir, ".olean")


def cache_present(job: BakeJob, state_root: Optional[Path] = None) -> bool:
    from jevops.outer import drive_dir_of

    return drive_dir_of(
        job,
        state_root,
        dir_fn=job_cache_dir,
        marker="BAKED",
        suffix=".olean",
    )


def plant_synthetic_cache(job: BakeJob, state_root: Path, *, n_oleans: int = 1) -> Path:
    """Write a dummy olean cache. Not a live lake bake."""

    from jevops.lean import drive_synthetic_oleans, pack_olean_receipt

    return drive_synthetic_oleans(
        job,
        state_root,
        n=n_oleans,
        cache_fn=job_cache_dir,
        receipt_fn=pack_olean_receipt,
        blob=b"LRA-013-synthetic-olean\n",
        prefix="LraBake",
    )


def require_cache(
    job: BakeJob,
    *,
    network: str,
    state_root: Optional[Path] = None,
) -> dict[str, Any]:
    from jevops.lean import drive_require_cache

    return drive_require_cache(
        job,
        network=network,
        state_root=state_root,
        present_fn=cache_present,
        cache_dir_fn=job_cache_dir,
        olean_count_fn=lambda cache_dir: len(olean_paths(cache_dir)),
        error_cls=OleanCacheMissing,
    )


def require_plan_caches(
    plan: BakePlan,
    *,
    network: str,
    state_root: Optional[Path] = None,
) -> list[dict[str, Any]]:
    from jevops.lean import require_plan_caches as _fn

    return _fn(
        plan.jobs,
        require_fn=require_cache,
        network=network,
        state_root=state_root,
    )


def lake_argv(lean_tag: str, *args: str, elan_home: Optional[Path] = None) -> list[str]:
    from jevops.outer import drive_lake_argv

    return drive_lake_argv(lean_tag, args, pin_fn=tag_pinned_paths, elan_home=elan_home)


def _run_tag_pinned_lake(
    lean_tag: str,
    args: Sequence[str],
    *,
    cwd: Path,
    timeout: float,
    env: Optional[Mapping[str, str]] = None,
    elan_home: Optional[Path] = None,
) -> dict[str, Any]:
    """Run tag-pinned lake. Never PATH ``lake``. Not used by --self-check."""

    from jevops.lean import drive_run_pinned_lake

    return drive_run_pinned_lake(
        lean_tag,
        args,
        cwd=cwd,
        timeout=timeout,
        env=env,
        elan_home=elan_home,
        paths_fn=tag_pinned_paths,
        error_cls=BakeError,
        miss_cls=BakeToolchainMissing,
    )


def bake_job(
    job: BakeJob,
    *,
    network: str,
    state_root: Optional[Path] = None,
    timeout: float = DEFAULT_LAKE_TIMEOUT_SECONDS,
    execute: bool = False,
) -> dict[str, Any]:
    """Return a cache hit, fail closed under network=deny, or bake if asked."""

    from jevops.lean import drive_bake_job
    from jevops.outer import git_checkout, git_clone_if_missing, path_or, url_clone_dir

    return drive_bake_job(
        job,
        network=network,
        execute=execute,
        root=path_or(state_root, factory=default_state_root),
        timeout=timeout,
        require_cache_fn=require_cache,
        tag_paths_fn=tag_pinned_paths,
        materialize_fn=lambda item, project: materialize_putnam_project(
            item.lean_tag, project, jsonl_version_pin=item.git_commit
        ),
        putnam_dir_fn=putnam_project_dir,
        run_lake_fn=_run_tag_pinned_lake,
        copy_oleans_fn=_copy_oleans,
        cache_dir_fn=job_cache_dir,
        olean_fn=olean_paths,
        error_cls=BakeError,
        miss_cls=BakeToolchainMissing,
        git_bin=GIT_BIN,
        git_clone_fn=git_clone_if_missing,
        git_checkout_fn=git_checkout,
        url_clone_dir_fn=url_clone_dir,
        lake_argv_fn=lake_argv,
    )


def _copy_oleans(src: Path, dest: Path) -> None:
    from jevops.outer import copy_dir_required

    copy_dir_required(src, dest, error_cls=BakeError, miss="expected .lake directory at {src}")


def _copytree(src: Path, dest: Path) -> None:
    from jevops.outer import copy_tree

    copy_tree(src, dest)


def write_candidate(lean_tag: str, source_text: str, dest: Optional[Path] = None) -> Path:
    """Copy a Putnam candidate into Putnam/Candidate.lean. Never Tmp.lean."""

    from jevops.lean import drive_write_candidate, putnam_bake_job, write_putnam_candidate

    return drive_write_candidate(
        lean_tag,
        source_text,
        dest,
        normalize_fn=normalize_lean_tag,
        job_fn=putnam_bake_job,
        dir_fn=putnam_project_dir,
        write_fn=write_putnam_candidate,
        relpath=PUTNAM_CANDIDATE_RELPATH,
        source=PUTNAM_SOURCE,
        module=PUTNAM_MODULE,
        refuse=FORBIDDEN_PUTNAM_BASENAME,
        error_cls=BakeError,
    )


def _imported_names(source: str) -> set[str]:
    from jevops.repair import imported_names

    return imported_names(source)


def _call_name(node: ast.AST) -> str:
    from jevops.repair import call_short_name

    return call_short_name(node)


def audit_source(source: Optional[str] = None) -> dict[str, Any]:
    from jevops.outer import source_text
    from jevops.repair import audit_source as _audit, matching_constants

    text = source_text(source, path=__file__)
    out = _audit(
        text,
        forbidden_imports=FORBIDDEN_IMPORT_NAMES,
        forbidden_calls=FORBIDDEN_CALLS,
        forbidden_scores=FORBIDDEN_SCORE_NAMES,
    )
    imported = set(out["imported_names"])
    calls = set(out["call_names"])
    from jevops import catalogs as catalogs_mod
    from jevops.repair import module_source, string_constants

    constants = list(out["string_constants"]) + string_constants(module_source(catalogs_mod))
    catalog_text = module_source(catalogs_mod)
    forbidden_urls = sorted(
        matching_constants(
            text,
            lambda value: "://" in value
            and any(needle.lower() in value.lower() for needle in FORBIDDEN_PUTNAM_URL_NEEDLES),
        )
        + matching_constants(
            catalog_text,
            lambda value: "://" in value
            and any(needle.lower() in value.lower() for needle in FORBIDDEN_PUTNAM_URL_NEEDLES),
        )
    )
    has_tmp_constant = FORBIDDEN_PUTNAM_BASENAME in constants
    has_putnam_module = PUTNAM_MODULE in constants
    has_mathlib_git = MATHLIB_GIT in constants
    has_aesop_git = AESOP_GIT in constants
    from jevops.repair import pack_call_audit

    packed = pack_call_audit(
        out,
        extra={
            "forbidden_putnambench_urls": forbidden_urls,
            "has_tmp_lean_constant": has_tmp_constant,
            "has_putnam_module": has_putnam_module,
            "has_mathlib_git": has_mathlib_git,
            "has_aesop_git": has_aesop_git,
            "uses_fcntl": "fcntl" in imported,
            "uses_shutil_which": "shutil" in imported and "which" in calls,
        },
        extra_ok=(
            not forbidden_urls,
            has_tmp_constant,
            has_putnam_module,
            has_mathlib_git,
            has_aesop_git,
        ),
    )
    return packed


def _synthetic_fail_closed(plan: BakePlan) -> dict[str, Any]:
    from jevops.outer import temp_dir

    with temp_dir(prefix="lra-013-oleans-") as tmp:
        root = Path(tmp)
        first = plan.first_job
        planted = plant_synthetic_cache(first, root)
        hit = require_cache(first, network="deny", state_root=root)
        from jevops.outer import first_where

        putnam_job = first_where(plan.jobs, lambda job: job.kind == "putnam")
        from jevops.outer import catch_error, keyed_map, read_json, read_text

        missing_raised, missing_message = catch_error(
            lambda: require_cache(putnam_job, network="deny", state_root=root),
            OleanCacheMissing,
        )
        allow_missing = require_cache(putnam_job, network="allow", state_root=root)
        write_denied, _write_msg = catch_error(
            lambda: write_candidate(
                STRATA_FIRST_TAG, "theorem x : True := by trivial", dest=root / FORBIDDEN_PUTNAM_BASENAME
            ),
            BakeError,
        )
        from jevops.lean import pack_materialized_putnam

        def _materialize(job: Any) -> dict[str, Any]:
            dest = root / "putnam_lake" / job.lean_tag
            files = materialize_putnam_project(job.lean_tag, dest, jsonl_version_pin=job.git_commit)
            return pack_materialized_putnam(
                dest,
                files,
                lakefile=read_text(dest / "lakefile.lean"),
                toolchain=read_text(dest / "lean-toolchain").strip(),
                pins=read_json(dest / "pins.json"),
                mathlib_git=MATHLIB_GIT,
                aesop_git=AESOP_GIT,
                refuse=FORBIDDEN_PUTNAM_BASENAME,
            )

        materialized = keyed_map(
            plan.jobs,
            key_fn=lambda job: job.lean_tag,
            val_fn=_materialize,
            pred=lambda job: job.kind == "putnam",
        )
        from jevops.lean import pack_synthetic_bake

        return pack_synthetic_bake(
            planted=planted,
            planted_n=len(olean_paths(planted)),
            hit=hit,
            missing_raised=missing_raised,
            missing_message=missing_message,
            allow_missing=allow_missing,
            write_denied=write_denied,
            materialized=materialized,
            putnam_tags=PUTNAM_TAGS,
            putnam_module=PUTNAM_MODULE,
        )


def probe_toolchain(tags: Iterable[str] | None = None) -> dict[str, Any]:
    from jevops.lean import drive_home_probe

    return drive_home_probe(
        tags,
        default_tags=(STRATA_FIRST_TAG, *PUTNAM_TAGS),
        resolve_fn=tag_pinned_paths,
        elan_home_fn=default_elan_home,
        extra={},
        gap_msg=(
            "No tag-pinned elan lean/lake binaries are installed under the "
            "resolver elan home. Paths remain tag-pinned; this is not PATH "
            "lake usability and is not a completed olean bake."
        ),
    )


def self_check(path: Optional[Path] = None) -> dict[str, Any]:
    from jevops.outer import get_str, path_or, relative_or_str, text_or

    jsonl = path_or(path, WARMUP_JSONL)
    plan = plan_bake(jsonl)
    first = plan.first_job
    audit = audit_source()
    synthetic = _synthetic_fail_closed(plan)
    toolchain = probe_toolchain()
    from jevops.outer import all_rows, all_where, env_str, field_eq, head_seq, where

    putnam_jobs = where(plan.jobs, lambda job: job.kind == "putnam")
    repo_jobs = where(plan.jobs, lambda job: job.kind == "repo")
    phases = [job.phase for job in plan.jobs]

    first_phase_ok = head_seq(phases, 1) == [0] and all_rows(phases, lambda phase: phase >= 0)
    is_strata_first = lambda job: job.source == STRATA_SOURCE and job.lean_tag == STRATA_FIRST_TAG
    strata_v426_before_rest = all_where(
        plan.jobs, is_strata_first, lambda job: job.phase == 0
    ) and all_where(plan.jobs, lambda job: not is_strata_first(job), lambda job: job.phase > 0)
    raw, digest, records = lra_splice.load_warmup_records(jsonl)
    putnam_records = where(records, field_eq("source", PUTNAM_SOURCE))
    putnam_headers_ok = all_where(
        records,
        field_eq("source", PUTNAM_SOURCE),
        lambda record: "import Mathlib" in get_str(record, "header")
        and "import Aesop" in get_str(record, "header")
        and not get_str(record, "url").strip()
        and not get_str(record, "file_path").strip(),
    )
    from jevops.outer import pack_unscored

    report: dict[str, Any] = pack_unscored(**{
        "ok": False,
        "compiled": False,
        "lake": False,
        "lake_build_executed": False,
        "oleans_baked": False,
        "llama_server_started": False,
        "frozen_warmup_sha256": digest,
        "jsonl_bytes": len(raw),
        "jsonl_unchanged": digest == FROZEN_WARMUP_SHA256,
        "n_records": len(records),
        "n_jobs": len(plan.jobs),
        "n_repo_jobs": len(repo_jobs),
        "n_putnam_jobs": len(putnam_jobs),
        "n_putnam_records": len(putnam_records),
        "first_job": first.to_dict(),
        "first_is_strata_v4_26": (
            first.kind == "repo"
            and first.source == STRATA_SOURCE
            and first.lean_tag == STRATA_FIRST_TAG
            and first.git_commit == STRATA_FIRST_COMMIT
            and first.url == STRATA_URL
            and first.phase == 0
        ),
        "first_cache_key": first.cache_key,
        "strata_v4_26_recorded_first": True,
        "strata_v426_before_rest": strata_v426_before_rest,
        "first_phase_ok": first_phase_ok,
        "putnam_tags": [job.lean_tag for job in putnam_jobs],
        "putnam_tags_match": tuple(job.lean_tag for job in putnam_jobs) == PUTNAM_TAGS,
        "putnam_module": PUTNAM_MODULE,
        "putnam_not_tmp_lean": all(job.module == PUTNAM_MODULE for job in putnam_jobs)
        and all(FORBIDDEN_PUTNAM_BASENAME not in job.file_paths for job in putnam_jobs),
        "putnam_headers_import_mathlib_aesop": putnam_headers_ok,
        "putnam_url_file_path_empty": all(not job.url for job in putnam_jobs),
        "putnambench_url_not_guessed": all(job.putnambench_url is None for job in putnam_jobs),
        "missing_cache_fails_closed_under_network_deny": bool(
            synthetic["missing_putnam_under_network_deny_raises"]
            and synthetic["missing_message_mentions_network_deny"]
            and synthetic["deny_cache_hit_on_planted_strata_v4_26"]
        ),
        "measurement_maxHeartbeats": MEASUREMENT_MAX_HEARTBEATS,
        "kernel_command_template": KERNEL_COMMAND_TEMPLATE,
        "bake_argv_template": BAKE_ARGV_TEMPLATE,
        "default_state_root": text_or(default_state_root()),
        "network_env": env_str("LRA_NETWORK"),
        "protocol": "LRA/v1",
        "audit": audit,
        "synthetic": {
            key: value
            for key, value in synthetic.items()
            if key != "materialized_putnam"
        },
        "putnam_projects": synthetic["materialized_putnam"],
        "toolchain": toolchain,
        "jobs": [job.to_dict() for job in plan.jobs],
        "warmup_path": relative_or_str(jsonl, REPO_ROOT),
        "putnam_readme_exists": PUTNAM_README.is_file(),
    })
    from jevops.outer import finalize_ok

    return finalize_ok(
        report,
        report["n_records"] == WARMUP_N,
        report["jsonl_unchanged"],
        report["n_jobs"] == 15,
        report["n_repo_jobs"] == 12,
        report["n_putnam_jobs"] == 3,
        report["first_is_strata_v4_26"],
        report["strata_v426_before_rest"],
        report["putnam_tags_match"],
        report["putnam_not_tmp_lean"],
        report["putnam_headers_import_mathlib_aesop"],
        report["putnam_url_file_path_empty"],
        report["putnambench_url_not_guessed"],
        report["missing_cache_fails_closed_under_network_deny"],
        synthetic["all_putnam_tags_materialized"],
        not synthetic["any_putnam_tmp_lean"],
        synthetic["all_putnam_have_mathlib_aesop_lakefile"],
        synthetic["all_putnam_module_candidate"],
        synthetic["all_putnambench_url_null"],
        synthetic["write_candidate_rejects_tmp_lean"],
        audit["ok"],
        report["compiled"] is False,
        report["lake"] is False,
        report["lake_build_executed"] is False,
        report["oleans_baked"] is False,
        report["arena_score"] is None,
        report["score"] is None,
        report["putnam_readme_exists"],
    )


def _print_json(payload: Mapping[str, Any]) -> None:
    from jevops.outer import print_json

    print_json(payload)


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-check", action="store_true", help="plan, fail-closed cache, Putnam lakefiles; no lake build")
    parser.add_argument("--plan", action="store_true", help="print the bake plan; Strata v4.26 first")
    parser.add_argument("--probe-toolchain", action="store_true", help="record tag-pinned elan paths; do not run lake")
    parser.add_argument("--dump-putnam-project", action="store_true", help="print one per-tag Putnam lake project")
    parser.add_argument("--require-cache", action="store_true", help="fail closed if oleans are missing")
    parser.add_argument("--materialize-putnam", type=Path, default=None, help="write per-tag Putnam lake projects under this directory")
    parser.add_argument("--tag", default=STRATA_FIRST_TAG, help="Putnam/Lean tag for dump/materialize (default v4.26.0)")
    parser.add_argument("--network", default=None, help="allow or deny (default: LRA_NETWORK or allow)")
    parser.add_argument("--jsonl", type=Path, default=None, help="warmup JSONL path")
    parser.add_argument("--state-root", type=Path, default=None, help="olean/putnam_lake state root")
    from jevops.outer import list_or_none

    args = parser.parse_args(list_or_none(argv))

    if args.self_check or argv is None or argv == []:
        from jevops.outer import print_ok

        return print_ok(self_check(args.jsonl))

    if args.plan:
        plan = plan_bake(args.jsonl)
        _print_json(plan.to_dict())
        return 0

    if args.probe_toolchain:
        _print_json(probe_toolchain())
        return 0

    if args.dump_putnam_project:
        plan = plan_bake(args.jsonl)
        tag = normalize_lean_tag(args.tag)
        from jevops.outer import attr_or, first_where

        job = first_where(plan.jobs, lambda item: item.kind == "putnam" and item.lean_tag == tag)
        pin_commit = attr_or(job, "git_commit", "")
        files = putnam_project_files(tag, jsonl_version_pin=pin_commit)
        _print_json(
            {
                "arena_score": None,
                "files": files,
                "lean_tag": tag,
                "module": PUTNAM_MODULE,
                "not_tmp_lean": True,
                "putnambench_url": None,
                "jsonl_version_pin": pin_commit,
            }
        )
        return 0

    if args.materialize_putnam is not None:
        plan = plan_bake(args.jsonl)
        dest_root = Path(args.materialize_putnam)
        written: dict[str, Any] = {}
        for job in plan.jobs:
            if job.kind != "putnam":
                continue
            dest = dest_root / job.lean_tag
            files = materialize_putnam_project(job.lean_tag, dest, jsonl_version_pin=job.git_commit)
            written[job.lean_tag] = files
        from jevops.outer import text_or

        _print_json(
            {
                "arena_score": None,
                "dest": text_or(dest_root),
                "module": PUTNAM_MODULE,
                "not_tmp_lean": True,
                "putnambench_url": None,
                "written": written,
            }
        )
        return 0

    if args.require_cache:
        plan = plan_bake(args.jsonl)
        network = network_mode(args.network)
        state_root = args.state_root
        results = []
        try:
            results = require_plan_caches(plan, network=network, state_root=state_root)
        except OleanCacheMissing as exc:
            from jevops.outer import failed_check

            _print_json(failed_check(exc, network=network, first_job=plan.first_job.to_dict()))
            return 1
        _print_json(
            {
                "ok": True,
                "network": network,
                "n_jobs": len(results),
                "results": results,
                "arena_score": None,
                "first_job": plan.first_job.to_dict(),
            }
        )
        return 0

    parser.error(
        "choose --self-check, --plan, --probe-toolchain, --dump-putnam-project, "
        "--materialize-putnam, or --require-cache"
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

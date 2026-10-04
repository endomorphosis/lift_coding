#!/usr/bin/env python3
"""Lean Refactor Arena warm-up loop v1.

Primary execution path on this machine. HTTP client of live docker0 Leanstral
at 172.17.0.1:8080. Loop v1 is:

    splice -> retrieve -> optional generate -> lexical admit -> lake compile
    -> keep-best

When ``/health`` is ok, this loop MUST call Leanstral. Skipping generate is
only the fail-closed path when docker0 is down (keep the reference proof).
Hammers and TypeSafe are off. Transfer is a hard filter. Among valid
candidates the composite is tokens+elab. Failures are retained. This is not
a scored Arena run. ``hardware_class=spark_gb10``.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import re
import sys
import tempfile
from dataclasses import asdict
from pathlib import Path
from typing import Any, Callable, Mapping, Optional, Sequence

HERE = Path(__file__).resolve().parent
PAPER_ROOT = HERE.parent
REPO_ROOT = HERE.parents[3]
WARMUP_JSONL = PAPER_ROOT / "data" / "benchmark_data_warmup.jsonl"

if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
import _jevops_path  # noqa: E402,F401
import compile_worker as lra_cw  # noqa: E402
import docker0_client as lra_d0  # noqa: E402
import generate_text as lra_gt  # noqa: E402
import retrieve as lra_retrieve  # noqa: E402
import splice as lra_splice  # noqa: E402

FROZEN_WARMUP_SHA256 = lra_splice.FROZEN_WARMUP_SHA256
WARMUP_N = lra_splice.WARMUP_N
from jevops.catalogs import AUTOSTART_ENV
from jevops.catalogs import BY_NEWLINE
from jevops.catalogs import ELAB_WEIGHT
from jevops.catalogs import FORBIDDEN_ORACLE_NAMES
from jevops.catalogs import FORBIDDEN_SCORE_NAMES
from jevops.catalogs import FORBIDDEN_SERVER_BINARIES
from jevops.catalogs import GATES_OFF as GATES
from jevops.catalogs import GENERATOR_LEANSTRAL as GENERATOR
from jevops.catalogs import HAMMERS_OFF as HAMMERS
from jevops.catalogs import HARDWARE_CLASS_SPARK as HARDWARE_CLASS
from jevops.catalogs import LOOP_SCHEMA
from jevops.catalogs import LOOP_VERSION_V1 as LOOP_VERSION
from jevops.catalogs import MAX_LOOP_CANDIDATES as MAX_CANDIDATES
from jevops.catalogs import PROBLEM_SCHEMA
from jevops.catalogs import PROTOCOL
from jevops.catalogs import TOKENIZER_ID
from jevops.catalogs import TOKEN_WEIGHT
from jevops.catalogs import TYPESAFE_OFF as TYPESAFE
from jevops.catalogs import V1_PHASES
from jevops.lean import TOKEN as _TOKEN
MEASUREMENT_MAX_HEARTBEATS = lra_cw.MEASUREMENT_MAX_HEARTBEATS
WARMUP_TAG_TIMEOUT_SECONDS = lra_cw.WARMUP_TAG_TIMEOUT_SECONDS
from jevops.catalogs import LIVE_SELF_CHECK_MAX_NEW_TOKENS
from jevops.catalogs import LIVE_SELF_CHECK_TIMEOUT_SECONDS
from jevops.catalogs import SELF_CHECK_TAG_TIMEOUT_SECONDS
FORBIDDEN_IMPORT_NAMES = frozenset(
    {
        "fcntl",
        "LeanstralProofProvider",
        "leanstral_proof_provider",
        "IndependentKernelVerifier",
        "KernelVerifier",
        "TypeSafeClient",
        "typesafe_inference",
        "typesafe_sdk",
        "lake_native_try",
        "LeanFrontend",
        "portfolio",
        "shutil",
    }
)


class LoopError(RuntimeError):
    """Fail-closed warm-up loop error. Never an Arena success."""


from jevops.lean import CandidateRecord
from jevops.lean import ProblemResult


def sha256_bytes(data: bytes) -> str:
    from jevops.outer import digest_hex

    return digest_hex(data)


def sha256_file(path: Path) -> str:
    from jevops.outer import digest_file

    return digest_file(path)


def sha256_text(text: str) -> str:
    from jevops.outer import digest_text

    return digest_text(text)


def token_count(text: str) -> int:
    """Frozen local tokenizer. Not the unpublished Arena tokenizer."""

    from jevops.search import count_matches

    return count_matches(text, _TOKEN)


def composite_score(token_ratio: float, elab_ratio: float) -> float:
    from jevops.search import weighted_sum

    return weighted_sum((TOKEN_WEIGHT, token_ratio), (ELAB_WEIGHT, elab_ratio))


def ratio(candidate: float, reference: float) -> float:
    from jevops.search import div_ratio

    return div_ratio(candidate, reference)


def strip_body_comments(text: str) -> str:
    """Strip ``--`` line comments and nested ``/- -/`` blocks from a body suffix.

    Operates only on an already-split body. Does not inspect the statement
    and does not search for the first assign token.
    """

    from jevops.mask import strip_comments

    return strip_comments(text)


def extract_generated_tactics(text: str) -> str:
    """Take a tactic block from an untrusted model payload. Not a statement splice."""

    from jevops.lean import extract_generated_tactics as _fn

    return _fn(text)


def statement_plus_tactics(statement: str, tactics: str) -> str:
    from jevops.outer import join_decl

    return join_decl(statement, tactics, by_marker=BY_NEWLINE)


def candidate_source(record: Mapping[str, Any], tactics: str) -> str:
    from jevops.lean import drive_split_candidate

    return drive_split_candidate(record, tactics, split_fn=lra_splice.split_statement_body)


def record_with_tactics(record: Mapping[str, Any], tactics: str) -> dict[str, Any]:
    from jevops.outer import drive_record_src

    return drive_record_src(record, tactics, join_fn=statement_plus_tactics)


def pin_loop_env() -> None:
    from jevops.outer import drive_pin_loop

    drive_pin_loop(
        client_pin_fn=lra_d0.pin_client_env,
        autostart_env=AUTOSTART_ENV,
        typesafe=TYPESAFE,
        generator=GENERATOR,
        hardware=HARDWARE_CLASS,
        loop=LOOP_VERSION,
    )


def effective_typesafe_mode() -> str:
    """Loop v1 hard-off. Env cannot enable Jev on this path."""

    return TYPESAFE


def render_loop_prompt(record: Mapping[str, Any], retrieval: lra_retrieve.Retrieval) -> str:
    from jevops.lean import drive_retrieval_prompt

    return drive_retrieval_prompt(
        record,
        retrieval,
        prompt_fn=lra_gt.render_prompt,
        lemma_cap=lra_retrieve.SRC_LEMMA_CAP,
    )


def maybe_generate(
    prompt: str,
    *,
    health: lra_gt.HealthProbe,
    source: str = "",
    max_new_tokens: Optional[int] = None,
    timeout: Optional[float] = None,
    generate: Optional[Callable[..., str]] = None,
    get_trace: Optional[Callable[[], Mapping[str, Any]]] = None,
) -> lra_gt.LraGeneration:
    """Call Leanstral iff docker0 ``/health`` is ok. Skip only when down."""

    from jevops.lean import drive_maybe_generate, failed_generation
    from jevops.outer import exc_text

    def _fail(exc: BaseException) -> lra_gt.LraGeneration:
        return failed_generation(
            health,
            exc_text(exc),
            requested_provider=lra_gt.REQUESTED_PROVIDER,
            requested_model=lra_gt.REQUESTED_MODEL,
            generation_cls=lra_gt.LraGeneration,
            identity_cls=lra_gt.ProviderIdentity,
            skipped=False,
        )

    return drive_maybe_generate(
        pin_fn=pin_loop_env,
        autostart_env=AUTOSTART_ENV,
        error_cls=LoopError,
        health=health,
        generate_fn=lambda: lra_gt.generate_lra(
            prompt,
            max_new_tokens=max_new_tokens,
            timeout=timeout,
            source=source,
            require_health=False,
            generate=generate,
            get_trace=get_trace,
        ),
        skip_result=lra_d0.skipped_generation(
            health,
            reason="docker0 down; skip generate; keep reference",
        ),
        fail_fn=_fail,
    )


def admit_tactics(record: Mapping[str, Any], tactics: str) -> lra_splice.AdmissionView:
    return lra_splice.admission_view(record, tactics)


def _elab_ms(receipts: Sequence[lra_cw.CompileReceipt]) -> float:
    from jevops.outer import mean_nonneg

    return mean_nonneg(receipts, getter=lambda item: item.wall_ms)


def _all_tags_ok(
    record: Mapping[str, Any],
    receipts: Sequence[lra_cw.CompileReceipt],
) -> bool:
    from jevops.outer import drive_tags_ok

    return drive_tags_ok(
        record.get("version_info"),
        receipts,
        id_fn=lambda item: item.lean_tag,
        ok_fn=lambda item: bool(item.ok) and not item.sorryAx and item.exit_code == 0,
    )


def compile_tactics(
    record: Mapping[str, Any],
    tactics: str,
    *,
    timeout: float,
    state_root: Optional[Path],
    elan_home: Optional[Path],
    network: str,
    skip_checkout: bool,
) -> list[lra_cw.CompileReceipt]:
    """Lake-compile a tactic block. IndependentKernelVerifier is not the oracle."""

    from jevops.lean import drive_compile_tactics
    from jevops.outer import write_text

    return drive_compile_tactics(
        record,
        tactics,
        timeout=timeout,
        state_root=state_root,
        elan_home=elan_home,
        network=network,
        skip_checkout=skip_checkout,
        require_timeout_fn=lra_cw.require_lake_timeout,
        with_tactics_fn=record_with_tactics,
        pins_fn=lra_cw.iter_version_pins,
        source_text_fn=candidate_source,
        project_dir_fn=lambda rec, pin: lra_cw.project_dir_for_record(rec, pin, state_root=state_root),
        relpath_fn=lra_cw.source_relpath,
        write_fn=write_text,
        compile_record_fn=lra_cw.compile_record,
        putnam_source=lra_cw.PUTNAM_SOURCE,
        hardware_class=HARDWARE_CLASS,
    )


def evaluate_candidate(
    record: Mapping[str, Any],
    *,
    kind: str,
    tactics: str,
    generator: str,
    reference_tokens: int,
    reference_elab_ms: float,
    timeout: float,
    state_root: Optional[Path],
    elan_home: Optional[Path],
    network: str,
    skip_checkout: bool,
    called_leanstral: bool = False,
    skipped_generate: bool = False,
    generate_error: str = "",
) -> CandidateRecord:
    from jevops.lean import attach_compile, drive_evaluate_candidate, make_candidate, score_candidate

    return drive_evaluate_candidate(
        record,
        kind=kind,
        tactics=tactics,
        generator=generator,
        source_fn=candidate_source,
        token_fn=token_count,
        admit_fn=lambda body: admit_tactics(record, body),
        make_fn=make_candidate,
        compile_fn=lambda body: compile_tactics(
            record,
            body,
            timeout=timeout,
            state_root=state_root,
            elan_home=elan_home,
            network=network,
            skip_checkout=skip_checkout,
        ),
        attach_fn=lambda cand, receipts: attach_compile(
            cand, receipts, hardware_class=HARDWARE_CLASS, elab_fn=_elab_ms
        ),
        score_fn=lambda cand, reconstructed_ok: score_candidate(
            cand,
            reference_tokens=reference_tokens,
            reference_elab_ms=reference_elab_ms,
            token_ratio_fn=ratio,
            composite_fn=composite_score,
            all_tags_ok_fn=_all_tags_ok,
            record=record,
            reconstructed_ok=reconstructed_ok,
        ),
        reconstruct_fn=lambda: lra_splice.split_statement_body(record).reconstructed_src == record["src"],
        hardware_class=HARDWARE_CLASS,
        called_leanstral=called_leanstral,
        skipped_generate=skipped_generate,
        generate_error=generate_error,
    )


def keep_best(candidates: Sequence[CandidateRecord]) -> Optional[CandidateRecord]:
    """Hard-filter transfer, then tokens+elab among valid. Else the reference."""

    from jevops.outer import first_where
    from jevops.search import pick_min

    return pick_min(
        candidates,
        valid_fn=lambda item: item.valid,
        key_fn=lambda item: (item.composite, item.token_count, item.kind),
        fallback_fn=lambda rows: first_where(rows, lambda item: item.kind == "reference"),
    )


def _failure_row(candidate: CandidateRecord) -> dict[str, Any]:
    from jevops.lean import drive_failing_tags, failure_row
    from jevops.pick import project_items

    return drive_failing_tags(
        candidate,
        project_fn=project_items,
        row_fn=failure_row,
        fields={
            "lean_tag": "lean_tag",
            "ok": "ok",
            "exit_code": "exit_code",
            "sorryAx": "sorryAx",
            "error": "error",
            "hardware_class": lambda _item: HARDWARE_CLASS,
            "arena_score": lambda _item: None,
        },
        hardware_class=HARDWARE_CLASS,
    )


def run_problem(
    record: Mapping[str, Any],
    records: Sequence[Mapping[str, Any]],
    *,
    health: Optional[lra_gt.HealthProbe] = None,
    generate: Optional[Callable[..., str]] = None,
    get_trace: Optional[Callable[[], Mapping[str, Any]]] = None,
    max_new_tokens: Optional[int] = None,
    generate_timeout: Optional[float] = None,
    compile_timeout: float = WARMUP_TAG_TIMEOUT_SECONDS,
    state_root: Optional[Path] = None,
    elan_home: Optional[Path] = None,
    network: str = "deny",
    skip_checkout: bool = True,
) -> ProblemResult:
    """One warm-up problem through loop v1. Hammers and TypeSafe stay off."""

    from jevops.lean import drive_warmup_problem

    return drive_warmup_problem(
        record,
        records,
        health=health,
        generate=generate,
        get_trace=get_trace,
        max_new_tokens=max_new_tokens,
        generate_timeout=generate_timeout,
        compile_timeout=compile_timeout,
        state_root=state_root,
        elan_home=elan_home,
        network=network,
        skip_checkout=skip_checkout,
        pin_env_fn=pin_loop_env,
        split_fn=lra_splice.split_statement_body,
        probe_factory=lra_d0.probe_docker0_health,
        tactic_from_body_fn=lra_splice.tactic_block_from_body,
        strip_fn=strip_body_comments,
        evaluate_fn=evaluate_candidate,
        retrieve_fn=lra_retrieve.retrieve_record,
        phases=list(V1_PHASES),
        composite_fn=composite_score,
        prompt_fn=render_loop_prompt,
        maybe_generate_fn=maybe_generate,
        extract_fn=extract_generated_tactics,
        keep_fn=keep_best,
        failure_fn=_failure_row,
        token_fn=token_count,
        error_cls=LoopError,
        max_candidates=MAX_CANDIDATES,
        hardware_class=HARDWARE_CLASS,
        hammers=HAMMERS,
        typesafe=effective_typesafe_mode(),
        generator=GENERATOR,
        loop_version=LOOP_VERSION,
    )


def write_problem_receipt(result: ProblemResult, dest_dir: Path) -> dict[str, str]:
    from jevops.lean import drive_problem_receipt

    return drive_problem_receipt(
        result,
        dest_dir,
        hardware_class=HARDWARE_CLASS,
        schema=PROBLEM_SCHEMA,
        hammers=HAMMERS,
        loop_version=LOOP_VERSION,
        typesafe=TYPESAFE,
        warmup_sha256=FROZEN_WARMUP_SHA256,
        index={
            "admission": "admission.json",
            "candidate": "candidate.lean",
            "problem": "problem.json",
            "result": "result.json",
        },
    )


def plant_repo_clone(url: str, state_root: Path) -> Path:
    from jevops.lean import drive_plant_named, render_lean_toolchain, render_package_lakefile

    return drive_plant_named(
        None,
        package="lra",
        lib="Lra",
        heartbeats=lra_cw.MEASUREMENT_MAX_HEARTBEATS,
        tag="v4.26.0",
        lakefile_fn=render_package_lakefile,
        toolchain_fn=render_lean_toolchain,
        clone_fn=lra_cw.clone_dir,
        url=url,
        state_root=state_root,
    )


def plant_loop_env(
    records: Sequence[Mapping[str, Any]],
    *,
    parent: Optional[Path] = None,
) -> dict[str, Any]:
    from jevops.lean import drive_plant_loop

    return drive_plant_loop(
        records,
        parent=parent,
        parent_factory=lra_cw._exec_scratch_parent,
        prefix="lra-017-loop-",
        pin_iter_fn=lambda info: lra_cw.iter_version_pins(info),
        plant_toolchain_fn=lra_cw.plant_fake_toolchain,
        plant_clone_fn=plant_repo_clone,
    )


def run_warmup(
    *,
    jsonl: Optional[Path] = None,
    names: Optional[Sequence[str]] = None,
    limit: Optional[int] = None,
    health: Optional[lra_gt.HealthProbe] = None,
    generate: Optional[Callable[..., str]] = None,
    get_trace: Optional[Callable[[], Mapping[str, Any]]] = None,
    max_new_tokens: Optional[int] = None,
    generate_timeout: Optional[float] = None,
    compile_timeout: float = WARMUP_TAG_TIMEOUT_SECONDS,
    state_root: Optional[Path] = None,
    elan_home: Optional[Path] = None,
    network: str = "deny",
    skip_checkout: bool = True,
    receipts_dir: Optional[Path] = None,
    plant_synthetic: bool = False,
) -> dict[str, Any]:
    from jevops.lean import drive_warmup_batch

    return drive_warmup_batch(
        jsonl=jsonl,
        names=names,
        limit=limit,
        health=health,
        generate=generate,
        get_trace=get_trace,
        max_new_tokens=max_new_tokens,
        generate_timeout=generate_timeout,
        compile_timeout=compile_timeout,
        state_root=state_root,
        elan_home=elan_home,
        network=network,
        skip_checkout=skip_checkout,
        receipts_dir=receipts_dir,
        plant_synthetic=plant_synthetic,
        pin_env_fn=pin_loop_env,
        load_fn=lra_splice.load_warmup_records,
        plant_fn=plant_loop_env,
        probe_factory=lra_d0.probe_docker0_health,
        run_fn=run_problem,
        write_fn=write_problem_receipt,
        error_cls=LoopError,
        generator=GENERATOR,
        hammers=HAMMERS,
        hardware_class=HARDWARE_CLASS,
        loop_version=LOOP_VERSION,
        protocol=PROTOCOL,
        typesafe=TYPESAFE,
        gates=GATES,
        phases=V1_PHASES,
    )


def plan_loop(jsonl: Optional[Path] = None) -> dict[str, Any]:
    from jevops.lean import drive_plan_loop, plan_loop_problems

    return drive_plan_loop(
        jsonl,
        load_fn=lra_splice.load_warmup_records,
        pin_fn=pin_loop_env,
        probe_fn=lra_d0.probe_docker0_health,
        problems_fn=lambda records: plan_loop_problems(
            records,
            split_fn=lra_splice.split_statement_body,
            pins_fn=lambda rec: lra_cw.iter_version_pins(rec.get("version_info")),
        ),
        autostart_env=AUTOSTART_ENV,
        health_url=lra_gt.DOCKER0_HEALTH_URL,
        generator=GENERATOR,
        hammers=HAMMERS,
        hardware_class=HARDWARE_CLASS,
        loop_version=LOOP_VERSION,
        protocol=PROTOCOL,
        typesafe=TYPESAFE,
        gates=GATES,
        phases=V1_PHASES,
        tokenizer_id=TOKENIZER_ID,
        token_weights={"elab": ELAB_WEIGHT, "tokens": TOKEN_WEIGHT},
    )


def _imported_names(source: str) -> set[str]:
    from jevops.repair import imported_names

    return imported_names(source)


def _lock_ex_attributes(source: str) -> list[str]:
    from jevops.repair import attr_hits

    return attr_hits(source, ("LOCK_EX", "F_WRLCK", "F_SETLK", "F_SETLKW"))


def _call_func_name(func: ast.AST) -> str:
    from jevops.repair import call_func_name

    return call_func_name(func)


def _oracle_name_uses(tree: ast.AST) -> set[str]:
    from jevops.repair import ast_name_hits

    return ast_name_hits(tree, FORBIDDEN_ORACLE_NAMES)


def _subprocess_invokes_forbidden_binary(source: str) -> bool:
    from jevops.repair import subprocess_invokes

    return subprocess_invokes(source, FORBIDDEN_SERVER_BINARIES)


def audit_source(source: Optional[str] = None) -> dict[str, Any]:
    from jevops.outer import source_text
    from jevops.repair import ast_name_hits, audit_source as _audit, catalog_constants

    text = source_text(source, path=__file__)
    out = _audit(
        text,
        forbidden_imports=FORBIDDEN_IMPORT_NAMES,
        forbidden_scores=FORBIDDEN_SCORE_NAMES,
    )
    tree = ast.parse(text)
    lock_ex_attrs = _lock_ex_attributes(text)
    oracle_uses = ast_name_hits(tree, FORBIDDEN_ORACLE_NAMES)
    consts = catalog_constants(
        ("HARDWARE_CLASS_SPARK", "HAMMERS_OFF", "TYPESAFE_OFF", "GATES_OFF")
    )
    hardware_literal = consts["HARDWARE_CLASS_SPARK"] == HARDWARE_CLASS
    typesafe_off = consts["TYPESAFE_OFF"] == "off"
    hammers_off = consts["HAMMERS_OFF"] == "off"
    from jevops.repair import pack_call_audit

    return pack_call_audit(
        out,
        extra={
            "forbidden_oracle_uses": sorted(oracle_uses),
            "forbidden_server_binaries": _subprocess_invokes_forbidden_binary(text),
            "hammers_off": hammers_off,
            "hardware_class_literal": hardware_literal,
            "lock_ex_attributes": lock_ex_attrs,
            "typesafe_off": typesafe_off,
            "uses_lock_ex": bool(lock_ex_attrs),
        },
        extra_ok=(
            not oracle_uses,
            not lock_ex_attrs,
            not _subprocess_invokes_forbidden_binary(text),
            hardware_literal,
            typesafe_off,
            hammers_off,
        ),
    )


def _fake_health(ok: bool) -> lra_gt.HealthProbe:
    from jevops.outer import either

    return lra_gt.HealthProbe(
        ok=ok,
        url=lra_gt.DOCKER0_HEALTH_URL,
        alias_ok=False,
        alias_url=lra_gt.DOCKER0_HEALTH_ALIAS_URL,
        status_code=either(ok, lambda: 200, lambda: None),
        error=either(ok, lambda: "", lambda: "simulated docker0 down"),
        autostart="0",
    )


def self_check(
    path: Optional[Path] = None,
    *,
    receipts_dir: Optional[Path] = None,
    live: bool = True,
) -> dict[str, Any]:
    pin_loop_env()
    from jevops.outer import env_str, head_chars, read_text

    source = read_text(__file__)
    audit = audit_source(source)
    raw, digest, records = lra_splice.load_warmup_records(path)
    live_health = lra_d0.probe_docker0_health()
    captured: list[dict[str, Any]] = []

    def fake_generate(prompt: str, **kwargs: Any) -> str:
        from jevops.outer import first_line_value

        captured.append({"prompt_head": head_chars(prompt, 80), "kwargs": dict(kwargs)})
        source_line = first_line_value(prompt, prefix="Source:").lower()
        if source_line == "putnambench":
            return "sorry"
        return "simp"

    def fake_trace() -> dict[str, str]:
        return {
            "effective_provider_name": "leanstral_local",
            "effective_model_name": "Leanstral",
        }

    healthy = run_warmup(
        jsonl=path,
        health=_fake_health(True),
        generate=fake_generate,
        get_trace=fake_trace,
        compile_timeout=SELF_CHECK_TAG_TIMEOUT_SECONDS,
        plant_synthetic=True,
        receipts_dir=receipts_dir,
    )
    captured_healthy_n = len(captured)
    down_calls_before = len(captured)
    down = run_warmup(
        jsonl=path,
        health=_fake_health(False),
        generate=fake_generate,
        get_trace=fake_trace,
        compile_timeout=SELF_CHECK_TAG_TIMEOUT_SECONDS,
        plant_synthetic=True,
    )
    down_generate_calls = len(captured) - down_calls_before

    healthy_results = healthy["results"]
    down_results = down["results"]
    from jevops.outer import all_rows, any_row, field_eq_all, first_truthy, kwargs_match_all

    keep_best_picks_generated = any_row(
        healthy_results, lambda item: item.get("kept_kind") == "generated"
    )
    putnam_generated_failed = any_row(
        healthy_results,
        lambda item: item.get("source") == "putnambench"
        and any(
            cand.get("kind") == "generated" and not cand.get("valid")
            for cand in item.get("candidates", [])
        ),
    )
    failures_retained_healthy = all_rows(healthy_results, lambda item: item.get("failures_retained"))
    hardware_all = field_eq_all(healthy_results, "hardware_class", HARDWARE_CLASS) and field_eq_all(
        down_results, "hardware_class", HARDWARE_CLASS
    )
    hammers_off = field_eq_all(healthy_results, "hammers", "off")
    typesafe_off = field_eq_all(healthy_results, "typesafe", "off")
    phases_ok = all_rows(healthy_results, lambda item: item.get("phases") == list(V1_PHASES))
    called_when_healthy = all_rows(healthy_results, lambda item: item.get("called_leanstral"))
    skipped_when_down = all_rows(down_results, lambda item: item.get("skipped_generate"))
    kept_non_generated_when_down = all_rows(
        down_results, lambda item: item.get("kept_kind") in {"reference", "reference_stripped"}
    )
    no_generated_when_down = all_rows(
        down_results,
        lambda item: all(cand.get("kind") != "generated" for cand in item.get("candidates", [])),
    )
    down_kept_kinds = sorted({item.get("kept_kind") for item in down_results})
    kwargs_ok = kwargs_match_all(captured[:captured_healthy_n], lra_gt.FAIL_CLOSED_KWARGS)
    arena_null = healthy["arena_score"] is None and down["arena_score"] is None
    n_problems_ok = healthy["n_problems"] == WARMUP_N and down["n_problems"] == WARMUP_N

    live_run: dict[str, Any] = {
        "attempted": False,
        "called_leanstral": False,
        "health_ok": bool(live_health.ok),
        "skipped": not live_health.ok,
    }
    if live and live_health.ok:
        first = next(item for item in records if item.get("source") == "strata")
        planted = plant_loop_env([first])
        live_compiled = run_problem(
            first,
            records,
            health=live_health,
            generate=None,
            get_trace=None,
            max_new_tokens=LIVE_SELF_CHECK_MAX_NEW_TOKENS,
            generate_timeout=LIVE_SELF_CHECK_TIMEOUT_SECONDS,
            compile_timeout=SELF_CHECK_TAG_TIMEOUT_SECONDS,
            state_root=planted["state_root"],
            elan_home=planted["elan_home"],
            network="deny",
            skip_checkout=True,
        )
        generated = next(
            (item for item in live_compiled.candidates if item.kind == "generated"),
            None,
        )
        from jevops.outer import attr_or

        live_run = {
            "attempted": True,
            "called_leanstral": bool(live_compiled.called_leanstral),
            "generated_error": attr_or(generated, "error", ""),
            "generated_kinds": [item.kind for item in live_compiled.candidates],
            "generated_tactic_head": head_chars(attr_or(generated, "tactics", ""), 160),
            "hardware_class": live_compiled.hardware_class,
            "health_ok": True,
            "kept_kind": attr_or(live_compiled.kept, "kind"),
            "name": live_compiled.name,
            "n_failures": len(live_compiled.failures),
            "skip_reason": live_compiled.skip_reason,
            "skipped": live_compiled.skipped_generate,
            "arena_score": None,
        }

    must_call = called_when_healthy and first_truthy(
        not live_health.ok, bool(live_run.get("called_leanstral"))
    )
    skip_only_if_down = skipped_when_down and down_generate_calls == 0 and first_truthy(
        not live_health.ok, not live_run.get("skipped")
    )

    report = {
        "ok": False,
        "arena_score": None,
        "audit": audit,
        "autostart": env_str(AUTOSTART_ENV),
        "called_leanstral_when_health_ok": must_call,
        "down": {
            "generate_calls": down_generate_calls,
            "kept_kinds": down_kept_kinds,
            "kept_non_generated": kept_non_generated_when_down,
            "n_problems": down["n_problems"],
            "no_generated_candidate": no_generated_when_down,
            "skipped_generate": skipped_when_down,
        },
        "fail_closed_kwargs_on_generate": kwargs_ok,
        "failures_retained": failures_retained_healthy and bool(
            first_truthy(healthy["n_failures"], putnam_generated_failed, default=False)
        ),
        "frozen_warmup_sha256": digest,
        "gates": GATES,
        "generator": GENERATOR,
        "hammers": HAMMERS,
        "hammers_off": hammers_off,
        "hardware_class": HARDWARE_CLASS,
        "hardware_class_all": hardware_all,
        "healthy": {
            "called_leanstral": called_when_healthy,
            "generate_calls": captured_healthy_n,
            "keep_best_picks_generated": keep_best_picks_generated,
            "n_failures": healthy["n_failures"],
            "n_problems": healthy["n_problems"],
            "putnam_generated_failed": putnam_generated_failed,
        },
        "jsonl_bytes": len(raw),
        "jsonl_unchanged": digest == FROZEN_WARMUP_SHA256,
        "keep_best": keep_best_picks_generated,
        "llama_server_started": False,
        "live": live_run,
        "live_health": asdict(live_health),
        "lock_ex_taken_by_client": False,
        "loop_is_splice_generate_admit_lake_keepbest": phases_ok,
        "loop_version": LOOP_VERSION,
        "must_call_leanstral_if_health_ok": True,
        "n_problems_ok": n_problems_ok,
        "official_score": None,
        "phases": list(V1_PHASES),
        "protocol": PROTOCOL,
        "putnam_generated_failed_retained": putnam_generated_failed,
        "score": None,
        "skip_generate_only_if_docker0_down": skip_only_if_down,
        "typesafe": TYPESAFE,
        "typesafe_off": typesafe_off,
        "warmup_jsonl_sha256": digest,
    }
    from jevops.outer import finalize_ok

    return finalize_ok(
        report,
        audit["ok"],
        report["jsonl_unchanged"],
        n_problems_ok,
        must_call,
        skip_only_if_down,
        kwargs_ok,
        phases_ok,
        hammers_off,
        typesafe_off,
        hardware_all,
        failures_retained_healthy,
        putnam_generated_failed,
        arena_null,
        report["autostart"] == "0",
        report["llama_server_started"] is False,
        report["lock_ex_taken_by_client"] is False,
        report["arena_score"] is None,
        captured_healthy_n == WARMUP_N,
        down_generate_calls == 0,
        kept_non_generated_when_down,
        no_generated_when_down,
    )


def _print_json(payload: Mapping[str, Any]) -> None:
    from jevops.outer import print_json

    print_json(payload)


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-check", action="store_true", help="loop v1 protocol + 15-problem synthetic run")
    parser.add_argument("--plan", action="store_true", help="print the v1 loop plan; no compile")
    parser.add_argument("--probe-health", action="store_true", help="GET docker0 /health only")
    parser.add_argument("--run", action="store_true", help="run loop v1 on warm-up records")
    parser.add_argument("--name", action="append", default=[], help="restrict to JSONL problem name (repeatable)")
    parser.add_argument("--limit", type=int, default=None, help="run at most N problems in JSONL order")
    parser.add_argument("--jsonl", type=Path, default=None)
    parser.add_argument("--receipts-dir", type=Path, default=None)
    parser.add_argument("--state-root", type=Path, default=None)
    parser.add_argument("--elan-home", type=Path, default=None)
    parser.add_argument("--network", default="deny")
    parser.add_argument("--synthetic-compile", action="store_true", help="plant tag-pinned fake lake/lean")
    parser.add_argument("--max-new-tokens", type=int, default=None)
    parser.add_argument("--generate-timeout", type=float, default=None)
    parser.add_argument(
        "--compile-timeout",
        type=float,
        default=WARMUP_TAG_TIMEOUT_SECONDS,
    )
    parser.add_argument("--no-live", action="store_true", help="self-check without a live Leanstral completion")
    from jevops.outer import list_or_none

    args = parser.parse_args(list_or_none(argv))

    if args.probe_health:
        pin_loop_env()
        probe = lra_d0.probe_docker0_health()
        payload = asdict(probe)
        payload["arena_score"] = None
        payload["hardware_class"] = HARDWARE_CLASS
        payload["llama_server_started"] = False
        payload["lock_ex_taken_by_client"] = False
        payload["must_call_leanstral"] = bool(probe.ok)
        _print_json(payload)
        from jevops.outer import exit_ok

        return exit_ok(probe.ok, bad=2)

    if args.plan:
        _print_json(plan_loop(args.jsonl))
        return 0

    if args.self_check or argv is None or argv == []:
        report = self_check(
            args.jsonl,
            receipts_dir=args.receipts_dir,
            live=not args.no_live,
        )
        from jevops.outer import print_ok

        return print_ok(report)

    if args.run or args.name or args.limit is not None:
        try:
            from jevops.outer import or_none

            payload = run_warmup(
                jsonl=args.jsonl,
                names=or_none(args.name),
                limit=args.limit,
                max_new_tokens=args.max_new_tokens,
                generate_timeout=args.generate_timeout,
                compile_timeout=args.compile_timeout,
                state_root=args.state_root,
                elan_home=args.elan_home,
                network=args.network,
                skip_checkout=bool(args.synthetic_compile),
                receipts_dir=args.receipts_dir,
                plant_synthetic=bool(args.synthetic_compile),
            )
        except LoopError as exc:
            from jevops.outer import closed_fail, text_or

            _print_json(closed_fail(text_or(exc), hardware_class=HARDWARE_CLASS))
            return 1
        payload["ok"] = bool(payload.get("n_problems"))
        _print_json(payload)
        return 0

    parser.error("choose --self-check, --plan, --probe-health, or --run")
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

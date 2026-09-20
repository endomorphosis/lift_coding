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
PROTOCOL = "LRA/v1"
LOOP_VERSION = "v1"
GENERATOR = "leanstral"
GATES = "off"
HAMMERS = "off"
TYPESAFE = "off"
HARDWARE_CLASS = "spark_gb10"
TOKENIZER_ID = "lra-local-ws-punct/v1"
TOKEN_WEIGHT = 0.55
ELAB_WEIGHT = 0.45
MAX_CANDIDATES = 8
PROBLEM_SCHEMA = "lra-problem-receipt/v1"
LOOP_SCHEMA = "lra-warmup-loop/v1"
BY_NEWLINE = " := by\n"
AUTOSTART_ENV = "IPFS_ACCELERATE_LLAMA_CPP_AUTOSTART"
MEASUREMENT_MAX_HEARTBEATS = lra_cw.MEASUREMENT_MAX_HEARTBEATS
WARMUP_TAG_TIMEOUT_SECONDS = lra_cw.WARMUP_TAG_TIMEOUT_SECONDS
SELF_CHECK_TAG_TIMEOUT_SECONDS = 60.0
LIVE_SELF_CHECK_MAX_NEW_TOKENS = 32
LIVE_SELF_CHECK_TIMEOUT_SECONDS = 90.0

V1_PHASES = (
    "splice",
    "retrieve",
    "generate_or_skip",
    "lexical_admit",
    "lake_compile",
    "keep_best",
)
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
FORBIDDEN_ORACLE_NAMES = frozenset(
    {
        "IndependentKernelVerifier",
        "KernelVerifier",
        "verify_admitted_lean_proof",
        "verify_lean_proof_text",
        "TypeSafeClient",
        "system_one",
        "snapshot_goal",
        "attempt_native_automation",
    }
)
FORBIDDEN_SERVER_BINARIES = frozenset(
    {
        "llama-server",
        "llama_server",
        "ipfs-accelerate-llama-cpp-serve",
    }
)
FORBIDDEN_SCORE_NAMES = frozenset(
    {
        "arena_score",
        "arena_score_tokens",
        "arena_score_elab",
        "official_track2_score",
        "token_savings",
        "official_score",
    }
)
_TOKEN = re.compile(r"[A-Za-z0-9_']+|[^A-Za-z0-9_\s]")
_END_MARKERS = ("<|im_end|>", "</s>", "<|endoftext|>", "<|eot_id|>")


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
    from jevops.lean import lake_candidate_source

    split = lra_splice.split_statement_body(record)
    return lake_candidate_source(
        header=split.header,
        statement=split.statement,
        tactic_block=tactics,
    )


def record_with_tactics(record: Mapping[str, Any], tactics: str) -> dict[str, Any]:
    from jevops.outer import with_field

    return with_field(record, "src", statement_plus_tactics(str(record["statement"]), tactics))


def pin_loop_env() -> None:
    from jevops.outer import pin_env, pin_sys_path

    lra_d0.pin_client_env()
    pin_env(
        {
            AUTOSTART_ENV: "0",
            "LRA_TYPESAFE": TYPESAFE,
            "LRA_GENERATOR": GENERATOR,
            "LRA_HARDWARE": HARDWARE_CLASS,
            "LRA_LOOP": LOOP_VERSION,
        }
    )
    pin_sys_path(
        "",
        defaults={
            "IPFS_ACCEL_SKIP_CORE": "1",
            "IPFS_AUTO_INSTALL": "false",
        },
    )


def effective_typesafe_mode() -> str:
    """Loop v1 hard-off. Env cannot enable Jev on this path."""

    return TYPESAFE


def render_loop_prompt(record: Mapping[str, Any], retrieval: lra_retrieve.Retrieval) -> str:
    base = lra_gt.render_prompt(record)
    lemmas = ", ".join(item.name for item in retrieval.src_lemmas)
    extra = (
        "\n\nRetrieved src lemmas (cap "
        f"{lra_retrieve.SRC_LEMMA_CAP}): {lemmas or '(none)'}\n"
        f"Other warm-up JSONL neighbors: {len(retrieval.neighbors)} "
        "(public; not a Mathlib CorpusManifest).\n"
        "Return only the tactic block after := by."
    )
    return base + extra


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

    from jevops.outer import exc_text, require_env_eq

    pin_loop_env()
    require_env_eq(
        AUTOSTART_ENV,
        "0",
        error_cls=LoopError,
        fmt="{key} must be {expected}; refusing to generate",
    )
    from jevops.lean import generate_if_healthy

    def _fail(exc: BaseException) -> lra_gt.LraGeneration:
        return lra_gt.LraGeneration(
            text="",
            identity=lra_gt.ProviderIdentity(
                requested_provider=lra_gt.REQUESTED_PROVIDER,
                requested_model=lra_gt.REQUESTED_MODEL,
                resolved_provider="",
                resolved_model="",
                fallback_used=False,
                arena_score=None,
            ),
            health=health,
            skipped=False,
            error=exc_text(exc),
        )

    return generate_if_healthy(
        health_ok=bool(health.ok),
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
    from jevops.outer import flatten_version_tags
    from jevops.outer import listed_all_ok

    return listed_all_ok(
        flatten_version_tags(record.get("version_info")),
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

    timeout = lra_cw.require_lake_timeout(timeout)
    candidate_record = record_with_tactics(record, tactics)
    pins = lra_cw.iter_version_pins(record.get("version_info"))
    from jevops.lean import write_then_compile
    from jevops.outer import write_text

    return write_then_compile(
        record,
        tactics,
        putnam_source=lra_cw.PUTNAM_SOURCE,
        pins=pins,
        candidate_record=candidate_record,
        source_text=candidate_source(record, tactics),
        project_dir_fn=lambda rec, pin: lra_cw.project_dir_for_record(rec, pin, state_root=state_root),
        relpath_fn=lra_cw.source_relpath,
        write_fn=write_text,
        compile_fn=lambda rec: lra_cw.compile_record(
            rec,
            timeout=timeout,
            state_root=state_root,
            elan_home=elan_home,
            network=network,
            require_oleans=False,
            hardware_class=HARDWARE_CLASS,
            skip_checkout=skip_checkout,
            abort_on_first_failure=True,
        ),
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
    source_text = candidate_source(record, tactics)
    view = admit_tactics(record, tactics)
    candidate = CandidateRecord(
        kind=kind,
        tactics=tactics,
        source_text=source_text,
        admission_accepted=bool(view.accepted),
        admission_code=str(view.failure_code),
        admission_reason=str(view.reason),
        generator=generator,
        called_leanstral=called_leanstral,
        skipped_generate=skipped_generate,
        error=generate_error,
        token_count=token_count(tactics),
        hardware_class=HARDWARE_CLASS,
        arena_score=None,
    )
    compile_anyway = kind.startswith("reference") or bool(view.accepted)
    if compile_anyway:
        receipts = compile_tactics(
            record,
            tactics,
            timeout=timeout,
            state_root=state_root,
            elan_home=elan_home,
            network=network,
            skip_checkout=skip_checkout,
        )
        for item in receipts:
            item.hardware_class = HARDWARE_CLASS
        candidate.compile_receipts = receipts
        candidate.elab_ms = _elab_ms(receipts)
        from jevops.outer import first_where

        hit = first_where(receipts, lambda item: bool(item.error))
        if hit is not None and not candidate.error:
            candidate.error = hit.error
    from jevops.lean import score_candidate

    reconstructed_ok = False
    if kind.startswith("reference"):
        reconstructed_ok = (
            lra_splice.split_statement_body(record).reconstructed_src == record["src"]
        )
    return score_candidate(
        candidate,
        reference_tokens=reference_tokens,
        reference_elab_ms=reference_elab_ms,
        token_ratio_fn=ratio,
        composite_fn=composite_score,
        all_tags_ok_fn=_all_tags_ok,
        record=record,
        reconstructed_ok=reconstructed_ok,
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
    from jevops.pick import project_items

    failing_tags = project_items(
        [item for item in candidate.compile_receipts if not item.ok],
        {
            "lean_tag": "lean_tag",
            "ok": "ok",
            "exit_code": "exit_code",
            "sorryAx": "sorryAx",
            "error": "error",
            "hardware_class": lambda _item: HARDWARE_CLASS,
            "arena_score": lambda _item: None,
        },
    )
    return {
        "admission_accepted": candidate.admission_accepted,
        "admission_code": candidate.admission_code,
        "arena_score": None,
        "error": candidate.error,
        "failing_tags": failing_tags,
        "generator": candidate.generator,
        "hardware_class": HARDWARE_CLASS,
        "kind": candidate.kind,
        "valid": candidate.valid,
    }


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

    pin_loop_env()
    split = lra_splice.split_statement_body(record)
    if record["src"] != split.reconstructed_src:
        raise LoopError(f"{split.name}: prefix bind reconstruction drifted")
    retrieval = lra_retrieve.retrieve_record(record, records)
    phases = list(V1_PHASES)
    probe = health if health is not None else lra_d0.probe_docker0_health()
    ref_tactics = lra_splice.tactic_block_from_body(split.body_suffix)
    stripped = strip_body_comments(ref_tactics).strip() or ref_tactics
    reference_tokens = token_count(ref_tactics)
    candidates: list[CandidateRecord] = []

    reference = evaluate_candidate(
        record,
        kind="reference",
        tactics=ref_tactics,
        generator="deterministic",
        reference_tokens=reference_tokens,
        reference_elab_ms=0.0,
        timeout=compile_timeout,
        state_root=state_root,
        elan_home=elan_home,
        network=network,
        skip_checkout=skip_checkout,
    )
    if reference.elab_ms > 0:
        reference.elab_ratio = 1.0
        reference.composite = composite_score(1.0, 1.0)
    candidates.append(reference)
    reference_elab = reference.elab_ms

    if stripped != ref_tactics and len(candidates) < MAX_CANDIDATES:
        candidates.append(
            evaluate_candidate(
                record,
                kind="reference_stripped",
                tactics=stripped,
                generator="deterministic",
                reference_tokens=reference_tokens,
                reference_elab_ms=reference_elab,
                timeout=compile_timeout,
                state_root=state_root,
                elan_home=elan_home,
                network=network,
                skip_checkout=skip_checkout,
            )
        )

    prompt = render_loop_prompt(record, retrieval)
    generation = maybe_generate(
        prompt,
        health=probe,
        source=str(record.get("source") or ""),
        max_new_tokens=max_new_tokens,
        timeout=generate_timeout,
        generate=generate,
        get_trace=get_trace,
    )
    called = bool(probe.ok)
    skipped = bool(generation.skipped) or not probe.ok
    skip_reason = ""
    if skipped:
        skip_reason = generation.error or "docker0 down; skip generate; keep reference"
    elif generation.error:
        skip_reason = generation.error

    if called and not skipped and len(candidates) < MAX_CANDIDATES:
        tactics = extract_generated_tactics(generation.text)
        if not tactics:
            from jevops.lean import failed_candidate

            generated = failed_candidate(
                kind="generated",
                code="empty_generation",
                reason="Leanstral returned no tactic block",
                generator=generation.identity.resolved_provider or GENERATOR,
                error=generation.error or "empty tactic block",
                hardware_class=HARDWARE_CLASS,
            )
            candidates.append(generated)
        else:
            candidates.append(
                evaluate_candidate(
                    record,
                    kind="generated",
                    tactics=tactics,
                    generator=generation.identity.resolved_provider or GENERATOR,
                    reference_tokens=reference_tokens,
                    reference_elab_ms=reference_elab,
                    timeout=compile_timeout,
                    state_root=state_root,
                    elan_home=elan_home,
                    network=network,
                    skip_checkout=skip_checkout,
                    called_leanstral=True,
                    generate_error=generation.error,
                )
            )
    elif called and generation.error and not skipped:
        from jevops.lean import failed_candidate

        candidates.append(
            failed_candidate(
                kind="generated",
                code="generate_error",
                reason=generation.error,
                generator=GENERATOR,
                error=generation.error,
                hardware_class=HARDWARE_CLASS,
            )
        )

    kept = keep_best(candidates)
    failures = [_failure_row(item) for item in candidates if not item.valid]
    return ProblemResult(
        name=split.name,
        source=split.source,
        header=split.header,
        statement=split.statement,
        phases=phases,
        health_ok=bool(probe.ok),
        called_leanstral=called,
        skipped_generate=skipped,
        skip_reason=skip_reason,
        retrieval_digest=retrieval.lemma_id_digest,
        n_neighbors=len(retrieval.neighbors),
        n_src_lemmas=len(retrieval.src_lemmas),
        candidates=candidates,
        kept=kept,
        failures=failures,
        hardware_class=HARDWARE_CLASS,
        hammers=HAMMERS,
        typesafe=effective_typesafe_mode(),
        generator=GENERATOR,
        loop_version=LOOP_VERSION,
        arena_score=None,
        official_score=None,
    )


def write_problem_receipt(result: ProblemResult, dest_dir: Path) -> dict[str, str]:
    from jevops.outer import path_safe, write_tree

    kept = result.kept
    candidate_text = kept.source_text if kept is not None else ""
    compile_records = []
    files: dict[str, Any] = {"candidate.lean": candidate_text}
    if kept is not None:
        for item in kept.compile_receipts:
            payload = item.to_dict()
            payload["arena_score"] = None
            payload["score"] = None
            payload["hardware_class"] = HARDWARE_CLASS
            compile_records.append(payload)
            files[f"{item.lean_tag}.json"] = payload
    files["problem.json"] = {
        "schema": PROBLEM_SCHEMA,
        "accepted": bool(kept is not None and kept.valid),
        "arena_score": None,
        "candidate": candidate_text,
        "failures_retained": True,
        "generator": result.generator,
        "hammers": HAMMERS,
        "hardware_class": HARDWARE_CLASS,
        "header": result.header,
        "kept_kind": None if kept is None else kept.kind,
        "loop_version": LOOP_VERSION,
        "name": result.name,
        "official_score": None,
        "score": None,
        "source": result.source,
        "statement": result.statement,
        "typesafe": TYPESAFE,
        "warmup_sha256": FROZEN_WARMUP_SHA256,
        "compile_records": compile_records,
    }
    files["result.json"] = result.to_dict()
    files["admission.json"] = {
        "arena_score": None,
        "candidates": [
            {
                "accepted": item.admission_accepted,
                "code": item.admission_code,
                "kind": item.kind,
                "reason": item.admission_reason,
            }
            for item in result.candidates
        ],
        "hardware_class": HARDWARE_CLASS,
        "name": result.name,
    }
    paths = write_tree(Path(dest_dir) / path_safe(result.name), files)
    return {
        "admission": paths["admission.json"],
        "candidate": paths["candidate.lean"],
        "problem": paths["problem.json"],
        "result": paths["result.json"],
    }


def plant_repo_clone(url: str, state_root: Path) -> Path:
    from jevops.outer import plant_git_skeleton

    clone = lra_cw.clone_dir(url, state_root)
    return plant_git_skeleton(
        clone,
        files={
            "lakefile.lean": "import Lake\nopen Lake DSL\npackage «lra»\nlean_lib «Lra»\n",
            "lean-toolchain": "leanprover/lean4:v4.26.0\n",
        },
    )


def plant_loop_env(
    records: Sequence[Mapping[str, Any]],
    *,
    parent: Optional[Path] = None,
) -> dict[str, Any]:
    from jevops.outer import mkdtemp_under, unique_keep

    root_parent = Path(parent) if parent is not None else lra_cw._exec_scratch_parent()
    root = mkdtemp_under(root_parent, prefix="lra-017-loop-")
    elan_home = root / "elan"
    state_root = root / "state"
    tags = unique_keep(
        [
            pin.lean_tag
            for record in records
            for pin in lra_cw.iter_version_pins(record.get("version_info"))
        ]
    )
    urls = unique_keep(
        [str(record.get("url") or "") for record in records if str(record.get("url") or "")]
    )
    for tag in tags:
        lra_cw.plant_fake_toolchain(elan_home, tag)
    for url in urls:
        plant_repo_clone(url, state_root)
    return {
        "elan_home": elan_home,
        "root": root,
        "state_root": state_root,
        "tags": tags,
        "urls": urls,
    }


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
    pin_loop_env()
    raw, digest, records = lra_splice.load_warmup_records(jsonl)
    selected = list(records)
    if names:
        wanted = set(names)
        selected = [item for item in records if item.get("name") in wanted]
        missing = wanted - {item.get("name") for item in selected}
        if missing:
            raise LoopError(f"unknown warm-up names: {sorted(missing)}")
    if limit is not None:
        selected = selected[: max(0, int(limit))]
    planted = None
    if plant_synthetic:
        planted = plant_loop_env(selected)
        elan_home = planted["elan_home"]
        state_root = planted["state_root"]
        skip_checkout = True
        network = "deny"
    live_health = health if health is not None else lra_d0.probe_docker0_health()
    results: list[ProblemResult] = []
    written: list[str] = []
    for record in selected:
        result = run_problem(
            record,
            records,
            health=live_health,
            generate=generate,
            get_trace=get_trace,
            max_new_tokens=max_new_tokens,
            generate_timeout=generate_timeout,
            compile_timeout=compile_timeout,
            state_root=state_root,
            elan_home=elan_home,
            network=network,
            skip_checkout=skip_checkout,
        )
        results.append(result)
        if receipts_dir is not None:
            paths = write_problem_receipt(result, Path(receipts_dir))
            written.extend(paths.values())
    return {
        "arena_score": None,
        "called_leanstral_when_healthy": all(
            item.called_leanstral for item in results
        )
        if live_health.ok
        else True,
        "failures_retained": all(item.to_dict()["failures_retained"] for item in results),
        "frozen_warmup_sha256": digest,
        "gates": GATES,
        "generator": GENERATOR,
        "hammers": HAMMERS,
        "hardware_class": HARDWARE_CLASS,
        "health_ok": bool(live_health.ok),
        "jsonl_bytes": len(raw),
        "llama_server_started": False,
        "lock_ex_taken_by_client": False,
        "loop_version": LOOP_VERSION,
        "n_failures": sum(len(item.failures) for item in results),
        "n_problems": len(results),
        "n_records": len(records),
        "official_score": None,
        "phases": list(V1_PHASES),
        "planted_synthetic": bool(planted),
        "protocol": PROTOCOL,
        "receipts_written": written,
        "results": [item.to_dict() for item in results],
        "score": None,
        "skip_generate_only_if_docker0_down": True,
        "skipped_generate": (not live_health.ok),
        "typesafe": TYPESAFE,
        "warmup_jsonl_sha256": digest,
    }


def plan_loop(jsonl: Optional[Path] = None) -> dict[str, Any]:
    from jevops.outer import env_str

    raw, digest, records = lra_splice.load_warmup_records(jsonl)
    pin_loop_env()
    health = lra_d0.probe_docker0_health()
    problems = []
    for record in records:
        split = lra_splice.split_statement_body(record)
        pins = lra_cw.iter_version_pins(record.get("version_info"))
        problems.append(
            {
                "name": split.name,
                "n_tags": len(pins),
                "source": split.source,
                "tags": [pin.lean_tag for pin in pins],
            }
        )
    return {
        "action_if_health_ok": "generate",
        "action_if_health_down": "skip_generate_keep_reference",
        "arena_score": None,
        "autostart": env_str(AUTOSTART_ENV),
        "docker0_health_url": lra_gt.DOCKER0_HEALTH_URL,
        "frozen_warmup_sha256": digest,
        "gates": GATES,
        "generator": GENERATOR,
        "hammers": HAMMERS,
        "hardware_class": HARDWARE_CLASS,
        "health": asdict(health),
        "jsonl_bytes": len(raw),
        "llama_server_started": False,
        "lock_ex_taken_by_client": False,
        "loop_version": LOOP_VERSION,
        "must_call_leanstral_if_health_ok": True,
        "n_problems": len(problems),
        "official_score": None,
        "phases": list(V1_PHASES),
        "problems": problems,
        "protocol": PROTOCOL,
        "skip_generate_only_if_docker0_down": True,
        "token_weights": {"elab": ELAB_WEIGHT, "tokens": TOKEN_WEIGHT},
        "tokenizer_id": TOKENIZER_ID,
        "typesafe": TYPESAFE,
    }


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
    from jevops.repair import ast_name_hits, audit_source as _audit, has_constant

    text = source_text(source, path=__file__)
    out = _audit(
        text,
        forbidden_imports=FORBIDDEN_IMPORT_NAMES,
        forbidden_scores=FORBIDDEN_SCORE_NAMES,
    )
    tree = ast.parse(text)
    lock_ex_attrs = _lock_ex_attributes(text)
    oracle_uses = ast_name_hits(tree, FORBIDDEN_ORACLE_NAMES)
    score_assignments = list(out["score_keys"])
    hardware_literal = has_constant(text, HARDWARE_CLASS)
    typesafe_off = has_constant(text, "off")
    hammers_off = "HAMMERS = \"off\"" in text or "HAMMERS='off'" in text
    return {
        "forbidden_imports": out["forbidden_imports"],
        "forbidden_oracle_uses": sorted(oracle_uses),
        "forbidden_server_binaries": _subprocess_invokes_forbidden_binary(text),
        "hammers_off": hammers_off,
        "hardware_class_literal": hardware_literal,
        "imported_names": out["imported_names"],
        "lock_ex_attributes": lock_ex_attrs,
        "score_assignments": score_assignments,
        "typesafe_off": typesafe_off,
        "uses_lock_ex": bool(lock_ex_attrs),
        "ok": (
            not out["forbidden_imports"]
            and not oracle_uses
            and not lock_ex_attrs
            and not score_assignments
            and not _subprocess_invokes_forbidden_binary(text)
            and hardware_literal
            and typesafe_off
            and hammers_off
        ),
    }


def _fake_health(ok: bool) -> lra_gt.HealthProbe:
    return lra_gt.HealthProbe(
        ok=ok,
        url=lra_gt.DOCKER0_HEALTH_URL,
        alias_ok=False,
        alias_url=lra_gt.DOCKER0_HEALTH_ALIAS_URL,
        status_code=200 if ok else None,
        error="" if ok else "simulated docker0 down",
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
        captured.append({"prompt_head": head_chars(prompt, 80), "kwargs": dict(kwargs)})
        source_line = ""
        for line in prompt.splitlines():
            if line.startswith("Source:"):
                source_line = line.split(":", 1)[1].strip().lower()
                break
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
    keep_best_picks_generated = any(
        item.get("kept_kind") == "generated" for item in healthy_results
    )
    putnam_generated_failed = any(
        item.get("source") == "putnambench"
        and any(
            cand.get("kind") == "generated" and not cand.get("valid")
            for cand in item.get("candidates", [])
        )
        for item in healthy_results
    )
    failures_retained_healthy = all(item.get("failures_retained") for item in healthy_results)
    hardware_all = all(
        item.get("hardware_class") == HARDWARE_CLASS for item in healthy_results
    ) and all(item.get("hardware_class") == HARDWARE_CLASS for item in down_results)
    hammers_off = all(item.get("hammers") == "off" for item in healthy_results)
    typesafe_off = all(item.get("typesafe") == "off" for item in healthy_results)
    phases_ok = all(item.get("phases") == list(V1_PHASES) for item in healthy_results)
    called_when_healthy = all(item.get("called_leanstral") for item in healthy_results)
    skipped_when_down = all(item.get("skipped_generate") for item in down_results)
    kept_non_generated_when_down = all(
        item.get("kept_kind") in {"reference", "reference_stripped"}
        for item in down_results
    )
    no_generated_when_down = all(
        all(cand.get("kind") != "generated" for cand in item.get("candidates", []))
        for item in down_results
    )
    down_kept_kinds = sorted({item.get("kept_kind") for item in down_results})
    kwargs_ok = bool(captured) and all(
        all(call["kwargs"].get(key) == value for key, value in lra_gt.FAIL_CLOSED_KWARGS.items())
        for call in captured[:captured_healthy_n]
    )
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
        live_run = {
            "attempted": True,
            "called_leanstral": bool(live_compiled.called_leanstral),
            "generated_error": "" if generated is None else generated.error,
            "generated_kinds": [item.kind for item in live_compiled.candidates],
            "generated_tactic_head": "" if generated is None else head_chars(generated.tactics, 160),
            "hardware_class": live_compiled.hardware_class,
            "health_ok": True,
            "kept_kind": None if live_compiled.kept is None else live_compiled.kept.kind,
            "name": live_compiled.name,
            "n_failures": len(live_compiled.failures),
            "skip_reason": live_compiled.skip_reason,
            "skipped": live_compiled.skipped_generate,
            "arena_score": None,
        }

    must_call = called_when_healthy and (
        (not live_health.ok) or bool(live_run.get("called_leanstral"))
    )
    skip_only_if_down = skipped_when_down and down_generate_calls == 0 and (
        not live_health.ok or not live_run.get("skipped")
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
            healthy["n_failures"] or putnam_generated_failed
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
    report["ok"] = bool(
        audit["ok"]
        and report["jsonl_unchanged"]
        and n_problems_ok
        and must_call
        and skip_only_if_down
        and kwargs_ok
        and phases_ok
        and hammers_off
        and typesafe_off
        and hardware_all
        and failures_retained_healthy
        and putnam_generated_failed
        and arena_null
        and report["autostart"] == "0"
        and report["llama_server_started"] is False
        and report["lock_ex_taken_by_client"] is False
        and report["arena_score"] is None
        and captured_healthy_n == WARMUP_N
        and down_generate_calls == 0
        and kept_non_generated_when_down
        and no_generated_when_down
    )
    return report


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
    args = parser.parse_args(list(argv) if argv is not None else None)

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
        return 0 if probe.ok else 2

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
            payload = run_warmup(
                jsonl=args.jsonl,
                names=args.name or None,
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
            from jevops.outer import closed_fail

            _print_json(closed_fail(str(exc), hardware_class=HARDWARE_CLASS))
            return 1
        payload["ok"] = bool(payload.get("n_problems"))
        _print_json(payload)
        return 0

    parser.error("choose --self-check, --plan, --probe-health, or --run")
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

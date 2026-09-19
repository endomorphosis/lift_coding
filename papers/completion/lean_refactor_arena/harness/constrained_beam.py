#!/usr/bin/env python3
"""Greedy / beam tactic-line search on *local* docker0 Leanstral, TypeSafe-pruned.

Hosted Labs Leanstral is not used. Generator is docker0
``172.17.0.1:8080`` via ``generate_text`` (NVFP4 Spark, hardware_class
``spark_gb10``). Not official Track 2. Not an Arena ranking.

A "token" here is one Lean tactic *line*, not a BPE token: llama.cpp chat
does not expose next-token logprobs through this client. After each line,
TypeSafe Choice ranks a closed candidate set (Leanstral proposal + reference
vocab + STOP) so the beam cannot explode into all of Lean.

Never LOCK_EX. Never autostart llama-server. Jev does not write Lean.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping, Optional, Sequence

HERE = Path(__file__).resolve().parent
PAPER_ROOT = HERE.parent
OUT_DEFAULT = PAPER_ROOT / "evidence" / "canaries"
DEFAULT_STATE = Path.home() / ".local/state/ipfs_accelerate_py/vericodegen-2026-lra/track1-lake"
STOP_TOKEN = "STOP"
CLOSERS = ("simp_all", "try simp_all", "omega", "try omega", "constructor", "rfl")
_TACTIC_HEAD = (
    "case ",
    "have ",
    "exact ",
    "apply ",
    "refine ",
    "simp",
    "rw ",
    "omega",
    "constructor",
    "intro",
    "induction ",
    "exists ",
    "· ",
    ". ",
)
HARDWARE_CLASS = "spark_gb10"
PROTOCOL = "LRA/v1"
PR_ID = "PR-9f"
MAX_STEPS_DEFAULT = 12
BEAM_DEFAULT = 1
MAX_NEW_TOKENS_LINE = 48
LINE_TIMEOUT = 120.0
MAX_CANDIDATES = 12
MAX_JEV_CALLS = 48
MAX_SAMPLES = 4

if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
import _jevops_path  # noqa: E402,F401
import docker0_client as lra_d0  # noqa: E402
import draft_fanout as lra_fan  # noqa: E402
import generate_text as lra_gt  # noqa: E402
import mca_mask_replace as lra_mask  # noqa: E402
import pca_mca_fanout as lra_pca  # noqa: E402
import run_warmup as lra_loop  # noqa: E402
import splice as lra_splice  # noqa: E402
import track1_keepbest as lra_kb  # noqa: E402
import track1_ledger as lra_t1  # noqa: E402

FROZEN_WARMUP_SHA256 = lra_splice.FROZEN_WARMUP_SHA256


@dataclass
class BeamItem:
    prefix: str
    steps: list[str] = field(default_factory=list)
    stopped: bool = False
    score: float = 1.0


_HAVE_NAME = re.compile(r"have\s+([A-Za-z0-9_']+)")


def have_binder_name(stripped: str) -> str:
    from jevops.outer import first_group

    core = stripped.lstrip("·. ").strip()
    return first_group(core, _HAVE_NAME, method="match") or ""


def identifier_used(name: str, text: str) -> bool:
    from jevops.repair import ident_used

    if not name:
        return False
    return ident_used(
        name,
        text,
        pattern=re.compile(r"(?<![A-Za-z0-9_'])" + re.escape(name) + r"(?![A-Za-z0-9_'])"),
    )


def pca_prefix(tactics: str) -> str:
    """Keep PCA glue; keep MCA ``have`` only when a later line still names it."""

    from jevops.mask import split_before

    from jevops.search import filter_used_later

    pre, rest = split_before(tactics, lambda line: line.strip().startswith("case "))
    kept = filter_used_later(
        pre,
        maybe_drop=lambda stripped: stripped.startswith("have "),
        name_fn=have_binder_name,
        used_fn=identifier_used,
        extra_later=rest,
        always_drop=lambda stripped: stripped.startswith("rename_i ") or stripped.startswith("obtain "),
    )
    return "\n".join(kept).rstrip()


def reference_vocab(tactics: str) -> list[str]:
    from jevops.mask import unique_vocab

    return unique_vocab(tactics, extras=("simp_all", "omega", "constructor", STOP_TOKEN))


def last_open_case(prefix: str) -> Optional[str]:
    from jevops.search import last_header_tag

    return last_header_tag(prefix, "case ", split_on="=>")


def case_header_map(reference: str) -> dict[str, str]:
    from jevops.mask import header_map

    return header_map(
        reference,
        lra_fan.case_spans(reference),
        tag_fn=lambda span: span.label.split()[0],
    )


def case_arm_lines(reference: str, tag: str) -> list[str]:
    from jevops.mask import span_body_lines

    return span_body_lines(
        reference,
        lra_fan.case_spans(reference),
        tag,
        tag_fn=lambda span: span.label.split()[0],
    )


def _status_pack(pack: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "missing": list(pack.get("missing_cases") or []),
        "empty": list(pack.get("empty_arms") or []),
        "unfinished": list(pack.get("unfinished_arms") or []),
        "earliest": pack.get("earliest_unfinished"),
        "open": pack.get("open_case"),
        "next_original": pack.get("next_original"),
    }


def structure_pack(reference: str, prefix: str) -> dict[str, Any]:
    """PCA skeleton + MCA holes of the *original* proof, plus what the prefix still lacks."""

    from jevops.search import structure_status

    holes = lra_mask.find_holes(reference)
    skeleton = lra_mask.mask_skeleton(reference, holes)
    tags = pca_case_tags(reference)
    status = structure_status(
        prefix,
        tags,
        present_fn=lambda pref, tag: f"case {tag}" in pref,
        remaining_fn=lambda pref, tag: remaining_arm_lines(pref, reference, tag),
        empty_fn=lambda pref, _tags: empty_case_arms(pref, reference),
        open_fn=last_open_case,
    )
    counts = lra_pca.count_tactics(reference)
    mca = [
        {
            "id": hole.hole_id,
            "family": hole.family,
            "head": hole.original.strip().splitlines()[0][:120],
        }
        for hole in holes
    ]
    return {
        "pca_prefix": pca_prefix(reference),
        "pca_skeleton_head": skeleton[:900],
        "pca_case_tags": tags,
        "missing_cases": status["missing"],
        "empty_arms": status["empty"],
        "unfinished_arms": status["unfinished"],
        "next_original": status["next_original"],
        "earliest_unfinished": status["earliest"],
        "open_case": status["open"],
        "mca_holes": mca,
        "n_have": int(counts.get("n_have") or 0),
        "n_induction": int(counts.get("n_induction") or 0),
        "n_cases": int(counts.get("n_cases") or 0),
        "n_tokens_ref": int(counts.get("n_tokens") or 0),
    }


def guided_vocab(prefix: str, reference: str, pack: Mapping[str, Any]) -> list[str]:
    """Priority next lines: missing PCA case headers before MCA haves."""

    from jevops.search import guided_next

    headers = case_header_map(reference)
    return guided_next(
        prefix,
        _status_pack(pack),
        header_of=lambda tag: headers.get(str(tag), ""),
        remaining_fn=lambda tag: remaining_arm_lines(prefix, reference, str(tag)),
        arm_lines_fn=lambda tag: case_arm_lines(reference, str(tag)),
        closers=CLOSERS,
    )


def filter_to_earliest(
    lines: Sequence[str],
    pack: Mapping[str, Any],
    reference: str,
) -> list[str]:
    """Drop candidates that skip past the earliest unfinished PCA case."""

    from jevops.search import filter_to_earliest as _fn

    return _fn(
        lines,
        _status_pack(pack),
        header_of=lambda tag: case_header_map(reference).get(str(tag), ""),
        stop=STOP_TOKEN,
        closer_pred=looks_like_closer,
        header_match=lambda stripped, earliest: stripped.startswith("case ") and earliest in stripped.split(),
        tag_token_fn=lambda tag: f"case {tag}",
    )


def looks_like_closer(stripped: str) -> bool:
    from jevops.mask import starts_any

    return starts_any(
        stripped,
        ("simp", "exact ", "omega", "constructor", "rfl", "try simp", "try omega"),
        exact=CLOSERS,
    )


def looks_like_tactic(stripped: str) -> bool:
    from jevops.mask import starts_any

    key = stripped.strip()
    if key == STOP_TOKEN:
        return True
    return starts_any(key, _TACTIC_HEAD, exact=CLOSERS)


def parse_next_line(text: str) -> str:
    from jevops.search import first_line

    body = lra_loop.extract_generated_tactics(text)
    return first_line(
        body,
        stop_pred=lambda s: s.upper() == STOP_TOKEN
        or s in {".", "qed"}
        or s.startswith("sorry")
        or s.startswith("admit"),
        skip_pred=lambda s: "<|im_start|>" in s
        or "<|im_end|>" in s
        or s.startswith("<|")
        or s.startswith("You are")
        or s.startswith("Lean 4")
        or len(s) > 160,
        keep_pred=looks_like_tactic,
        default=STOP_TOKEN,
    )


def step_prompt(
    record: Mapping[str, Any],
    prefix: str,
    vocab: Sequence[str],
    pack: Optional[Mapping[str, Any]] = None,
) -> str:
    vocab_block = "\n".join(f"- {item}" for item in list(vocab)[:24])
    pack = pack or {}
    missing = pack.get("missing_cases") or []
    holes = pack.get("mca_holes") or []
    hole_block = "\n".join(
        f"- {item.get('id')} family={item.get('family')}: {item.get('head')}" for item in holes[:12]
    ) or "(none)"
    skeleton = str(pack.get("pca_skeleton_head") or "")[:700]
    return (
        "Lean 4 tactic completion. Emit ONLY the next tactic line after := by, "
        "or the word STOP if the proof is finished.\n"
        "No theorem/lemma/import/open/sorry/admit. Prefer a shorter lake-valid proof.\n"
        "PCA (principal): keep induction and every case header. Fill missing case headers "
        "before any MCA have/rename_i from the original.\n"
        "MCA (residual): simp-at / have / rw holes may be dropped or filled only inside the "
        "currently open case. Do not splice pre-induction haves after a case arm.\n\n"
        f"Problem: {record.get('name')}\n"
        f"Statement:\n{str(record.get('statement') or '')[:700]}\n\n"
        f"PCA skeleton of the original (holes marked):\n{skeleton}\n\n"
        f"MCA holes of the original:\n{hole_block}\n\n"
        f"Missing PCA case tags: {missing or 'none'}\n"
        f"Empty PCA case arms: {pack.get('empty_arms') or 'none'}\n"
        f"Fill this PCA case first: {pack.get('earliest_unfinished') or 'none'}\n"
        f"Open case: {pack.get('open_case') or 'none'}\n\n"
        f"Prefix so far:\n{prefix or '(empty)'}\n\n"
        f"Priority next lines:\n{vocab_block}\n\n"
        "Next tactic line:"
    )


def pca_case_tags(tactics: str) -> list[str]:
    from jevops.mask import top_level_labels

    spans = lra_fan.case_spans(tactics)
    return top_level_labels(spans, tag_fn=lambda span: span.label.split()[0])


def case_body_lines(prefix: str, tag: str) -> list[str]:
    from jevops.mask import capture_after_header
    from jevops.search import last_header_tag

    want = str(tag or "").split()[0]
    return capture_after_header(
        prefix,
        want,
        is_header=lambda stripped: stripped.startswith("case "),
        id_of=lambda stripped: last_header_tag(stripped, "case ", split_on="=>") or "",
    )


def empty_case_arms(prefix: str, reference: str) -> list[str]:
    from jevops.search import empty_headers

    return empty_headers(
        prefix,
        pca_case_tags(reference),
        present_fn=lambda pref, tag: f"case {tag}" in pref,
        body_fn=lambda pref, tag: case_body_lines(pref, tag),
    )


def is_mca_line(stripped: str) -> bool:
    core = stripped.lstrip("·. ").strip()
    return core.startswith(("have ", "rename_i ", "obtain "))


def arm_keep_lines(reference: str, tag: str) -> list[str]:
    """Original arm tactics; keep MCA ``have`` only when a later line still names it."""

    from jevops.search import after_item
    from jevops.search import filter_used_later

    lines = case_arm_lines(reference, tag)
    later_arms: list[str] = []
    for other in after_item(pca_case_tags(reference), tag):
        later_arms.extend(case_arm_lines(reference, other))
    return filter_used_later(
        lines,
        maybe_drop=lambda stripped: is_mca_line(stripped),
        name_fn=have_binder_name,
        used_fn=identifier_used,
        extra_later=later_arms,
    )


def remaining_arm_lines(prefix: str, reference: str, tag: str) -> list[str]:
    """Original keep-lines not yet copied, counting indent-sensitive occurrences."""

    from jevops.search import missing_occurrences

    return missing_occurrences(prefix.splitlines(), arm_keep_lines(reference, tag))


def stop_allowed(prefix: str, reference: str) -> bool:
    """Do not STOP while a PCA case header is missing or its original arm is unfinished."""

    from jevops.search import structure_complete

    return structure_complete(
        prefix,
        pca_case_tags(reference),
        present_fn=lambda pref, tag: f"case {tag}" in pref,
        empty_fn=lambda pref, _tags: empty_case_arms(pref, reference),
        remaining_fn=lambda pref, tag: remaining_arm_lines(pref, reference, tag),
    )


def unused_vocab(prefix: str, vocab: Sequence[str]) -> list[str]:
    from jevops.search import unused_items

    return unused_items(prefix, vocab, stop=STOP_TOKEN)


def typesafe_prune(
    record: Mapping[str, Any],
    prefix: str,
    candidates: Sequence[str],
    *,
    ledger: lra_t1.ProblemLedger,
    keep: int,
    context: Optional[Mapping[str, Any]] = None,
) -> dict[str, Any]:
    from jevops.search import unique_cap

    unique = unique_cap(candidates, cap=MAX_CANDIDATES, empty=STOP_TOKEN)
    lra_pca.load_keyfile()
    lra_pca.pin_typesafe_path()
    ts_path = Path("/home/barberb/lift_coding/external/ipfs_accelerate/ipfs_accelerate_py/typesafe_inference.py")
    if not ts_path.is_file():
        return {
            "skipped": True,
            "reason": "typesafe_inference_missing",
            "kept": unique[:keep],
            "jev_generated_lean": False,
            "arena_score": None,
        }
    from jevops.outer import load_module_from_path

    module = load_module_from_path(ts_path, "lra_typesafe_inference")
    if module is None:
        return {
            "skipped": True,
            "reason": "typesafe_inference_spec",
            "kept": unique[:keep],
            "jev_generated_lean": False,
            "arena_score": None,
        }
    Choice = module.Choice
    TypeSafeClient = module.TypeSafeClient
    typesafe_configured = module.typesafe_configured

    if not typesafe_configured():
        return {
            "skipped": True,
            "reason": "no_key",
            "kept": unique[:keep],
            "jev_generated_lean": False,
            "arena_score": None,
        }
    pack = dict(context or {})
    criteria = {f"c{index}": line for index, line in enumerate(unique)}
    state = {
        "problem": {"name": record.get("name")},
        "prefix_tail": prefix[-600:],
        "pca_skeleton_head": str(pack.get("pca_skeleton_head") or "")[:500],
        "pca_case_tags": pack.get("pca_case_tags"),
        "missing_cases": pack.get("missing_cases"),
        "empty_arms": pack.get("empty_arms"),
        "unfinished_arms": pack.get("unfinished_arms"),
        "next_original": pack.get("next_original"),
        "earliest_unfinished": pack.get("earliest_unfinished"),
        "open_case": pack.get("open_case"),
        "mca_holes": pack.get("mca_holes"),
        "n_have_original": pack.get("n_have"),
        "goal": "Pick the next Lean tactic line most likely to yield a shorter lake-valid proof.",
        "candidates": criteria,
    }
    questions = {
        "next_line": Choice(
            instructions=(
                "Which candidate is the best NEXT tactic line? Do not write Lean. "
                "Fill earliest_unfinished in original order: if its header is missing, pick that "
                "header; if the arm still has next_original, pick exactly that line. Never skip "
                "ahead to a later case. Never pick have/rename or English. STOP only when every "
                "PCA arm has used its original non-MCA tactics."
            ),
            criteria=criteria,
        )
    }
    try:
        result = TypeSafeClient(timeout=45.0).system_one(state, questions)
    except Exception as exc:  # noqa: BLE001 — prune must fail closed to greedy
        return {
            "skipped": True,
            "reason": str(exc)[:300],
            "kept": unique[:keep],
            "jev_generated_lean": False,
            "arena_score": None,
        }
    from jevops.outer import usage_tokens

    usage = dict(getattr(result, "usage", None) or {})
    inn, out = usage_tokens(
        usage, fallback_in=lra_t1.estimate_tokens(json.dumps(state))
    )
    line = ledger.record("jev", input_tokens=inn, output_tokens=out, model=lra_t1.JEV_MODEL_ID)
    best = (getattr(result, "choices", None) or {}).get("next_line")
    pick_id = str(getattr(best, "choice", None) or "c0")
    probs = dict(getattr(best, "probabilities", None) or {})
    from jevops.search import pin_then_rank

    ranked_ids = pin_then_rank(criteria.keys(), probs, first=pick_id if pick_id in criteria else None)
    kept = [criteria[key] for key in ranked_ids if key in criteria][:keep]
    if not kept:
        kept = unique[:keep]
    return {
        "skipped": bool(line.skipped),
        "reason": line.reason if line.skipped else "routed",
        "best": criteria.get(pick_id),
        "kept": kept,
        "confidence": getattr(best, "confidence", None),
        "usage": usage,
        "jev_generated_lean": False,
        "arena_score": None,
    }


def propose_lines(
    record: Mapping[str, Any],
    item: BeamItem,
    vocab: Sequence[str],
    *,
    beam: int,
    temperature: float,
    generate: Optional[Callable[..., str]],
    pack: Optional[Mapping[str, Any]] = None,
    reference: str = "",
) -> list[str]:
    pack = dict(pack or {})
    priority = guided_vocab(item.prefix, reference, pack) if reference else unused_vocab(item.prefix, vocab)
    prompt = step_prompt(record, item.prefix, priority or unused_vocab(item.prefix, vocab), pack)
    proposals: list[str] = []
    n_samples = 1 if beam <= 1 else min(max(int(beam), 1), MAX_SAMPLES)
    for sample_i in range(n_samples):
        del sample_i
        if generate is not None:
            raw = generate(prompt, temperature=temperature)
            proposals.append(parse_next_line(raw))
            continue
        result = lra_d0.generate_as_client(
            prompt,
            max_new_tokens=MAX_NEW_TOKENS_LINE,
            timeout=LINE_TIMEOUT,
            source=str(record.get("source") or ""),
            allow_owner_exec=False,
            temperature=temperature,
            stop=["\n\n"],
        )
        if result.skipped or not result.text:
            proposals.append(STOP_TOKEN)
            continue
        if result.identity.fallback_used:
            raise lra_gt.LraGenerateError(
                "refusing fallback "
                f"{result.identity.resolved_provider}/{result.identity.resolved_model}"
            )
        if result.identity.resolved_provider not in lra_gt.ALLOWED_RESOLVED_PROVIDERS and result.identity.resolved_provider:
            # generate_lra may leave resolved empty on some llama.cpp traces; still local.
            if result.identity.resolved_provider in lra_gt.FORBIDDEN_FALLBACK_PROVIDERS:
                raise lra_gt.LraGenerateError("refusing non-docker0 provider")
        proposals.append(parse_next_line(result.text))
    for extra in priority[: max(0, MAX_CANDIDATES - len(proposals) - 1)]:
        proposals.append(extra)
    proposals = filter_to_earliest(proposals, pack, reference) or list(priority[:MAX_CANDIDATES])
    if STOP_TOKEN not in proposals:
        proposals.append(STOP_TOKEN)
    return proposals


def extend_prefix(prefix: str, nxt: str, *, original: Optional[str] = None) -> str:
    """Append ``nxt``, preferring the original line's leading indent when it matches."""

    from jevops.search import extend_prefix as _fn

    return _fn(prefix, nxt, stop=STOP_TOKEN, original=original, case_token="case ")


def run_search(
    record: Mapping[str, Any],
    *,
    mode: str,
    max_steps: int,
    beam: int,
    temperature: float = 0.0,
    generate: Optional[Callable[..., str]] = None,
    prune: Optional[Callable[..., dict[str, Any]]] = None,
) -> dict[str, Any]:
    tactics = lra_fan.tactic_block(record)
    prefix0 = pca_prefix(tactics)
    vocab = reference_vocab(tactics)
    ledger = lra_t1.ProblemLedger(
        name=f"{record.get('name')}#constrained-beam-local",
        max_jev_calls=MAX_JEV_CALLS,
        max_mistral_calls=0,
        max_grok_calls=0,
    )
    beam_n = 1 if mode == "greedy" else max(1, int(beam))
    temp = float(temperature)
    items = [BeamItem(prefix=prefix0)]
    trace: list[dict[str, Any]] = []
    local_calls = 0
    n_samples = 1 if beam_n <= 1 else min(beam_n, MAX_SAMPLES)
    prune_fn = prune or typesafe_prune
    for step in range(int(max_steps)):
        if all(item.stopped for item in items):
            break
        nxt_items: list[BeamItem] = []
        for item in items:
            if item.stopped:
                nxt_items.append(item)
                continue
            pack = structure_pack(tactics, item.prefix)
            if stop_allowed(item.prefix, tactics):
                nxt_items.append(
                    BeamItem(prefix=item.prefix, steps=item.steps, stopped=True, score=item.score)
                )
                trace.append(
                    {
                        "step": step,
                        "stop_exhausted": True,
                        "earliest_unfinished": pack.get("earliest_unfinished"),
                    }
                )
                continue
            proposals = propose_lines(
                record,
                item,
                vocab,
                beam=beam_n,
                temperature=temp,
                generate=generate,
                pack=pack,
                reference=tactics,
            )
            local_calls += n_samples
            if prune is None:
                pruned = typesafe_prune(
                    record,
                    item.prefix,
                    proposals,
                    ledger=ledger,
                    keep=beam_n,
                    context=pack,
                )
            else:
                pruned = prune_fn(record, item.prefix, proposals, ledger=ledger, keep=beam_n)
            kept_lines = list(pruned.get("kept") or [STOP_TOKEN])
            filtered = filter_to_earliest(
                [line for line in kept_lines if line != STOP_TOKEN],
                pack,
                tactics,
            )
            kept_lines = filtered or filter_to_earliest(proposals, pack, tactics)[:beam_n] or [STOP_TOKEN]
            pruned = dict(pruned)
            pruned["kept"] = kept_lines
            pruned["stop_blocked"] = True
            trace.append(
                {
                    "step": step,
                    "prefix_lines": item.prefix.count("\n") + 1,
                    "temperature": temp,
                    "missing_cases": pack.get("missing_cases"),
                    "empty_arms": pack.get("empty_arms"),
                    "earliest_unfinished": pack.get("earliest_unfinished"),
                    "next_original": pack.get("next_original"),
                    "open_case": pack.get("open_case"),
                    "proposals": proposals[:MAX_CANDIDATES],
                    "typesafe": {k: pruned.get(k) for k in ("skipped", "reason", "best", "kept", "confidence")},
                }
            )
            for nxt in kept_lines:
                child = BeamItem(
                    prefix=extend_prefix(item.prefix, nxt, original=str(pack.get("next_original") or "") or None),
                    steps=item.steps + [nxt],
                    stopped=nxt == STOP_TOKEN,
                    score=item.score,
                )
                nxt_items.append(child)
        # Cap beam after TypeSafe prune (search space stays bounded).
        items = nxt_items[:beam_n]
    finals = []
    seen: set[str] = set()
    for item in items:
        body = item.prefix.strip("\n")
        if body in seen:
            continue
        seen.add(body)
        finals.append({"tactics": body, "steps": item.steps, "stopped": item.stopped})
    return {
        "pca_prefix": prefix0,
        "pca_mca": structure_pack(tactics, prefix0),
        "vocab_n": len(vocab),
        "mode": mode,
        "beam": beam_n,
        "temperature": temp,
        "max_steps": int(max_steps),
        "local_calls": local_calls,
        "finals": finals,
        "trace": trace,
        "ledger": ledger.as_dict(),
        "hardware_class": HARDWARE_CLASS,
        "called_hosted_mistral": False,
        "called_docker0": generate is None,
        "official_track2": False,
        "arena_score": None,
    }


_BARE_SIMP_ALL = re.compile(r"^[ \t]*\.?[ \t]*simp_all\s*$")


def drop_first_bare_simp_all(tactics: str) -> Optional[str]:
    from jevops.mask import drop_matching_line

    return drop_matching_line(tactics, lambda line: bool(_BARE_SIMP_ALL.match(line)), last=False)


def drop_last_bare_simp_all(tactics: str) -> Optional[str]:
    """Drop the last standalone ``simp_all`` / ``. simp_all`` line (not ``<;> simp_all``)."""

    from jevops.mask import drop_matching_line

    return drop_matching_line(tactics, lambda line: bool(_BARE_SIMP_ALL.match(line)), last=True)


def repair_no_progress_simp_all(tactics: str, errors: Sequence[Mapping[str, Any]]) -> Optional[str]:
    blob = "\n".join(str(item.get("data") or "") for item in errors)
    if "simp_all made no progress" not in blob:
        return None
    return drop_last_bare_simp_all(tactics)


def join_consecutive_exacts(tactics: str) -> str:
    from jevops.mask import join_consecutive_lines

    return join_consecutive_lines(
        tactics,
        lambda line: line.strip().startswith("exact "),
        joiner=lambda indent, a, b: f"{indent}{a.strip()} <;> {b.strip()}",
    )


def collapse_defined_simp(tactics: str) -> str:
    return re.sub(
        r"(?m)^(?P<indent>[ \t]*)simp \[isDefined\] at \* <;> simp_all\s*$",
        r"\g<indent>simp_all",
        tactics,
    )


def shorten_keeping_prefix_haves(tactics: str) -> list[tuple[str, str]]:
    """Compiler shortenings that must keep every original prefix ``have`` (simp_all fuel)."""

    haves = prefix_have_lines(tactics)
    seen: set[str] = {tactics.strip("\n")}
    out: list[tuple[str, str]] = []

    def keep(name: str, body: Optional[str]) -> None:
        from jevops.pick import keep_if_contains

        keep_if_contains(seen, out, name, body, required=haves)

    keep("simp_set", lra_fan.drop_redundant_simp_at(tactics))
    keep("drop_first_bare_simp", drop_first_bare_simp_all(tactics))
    keep("drop_last_bare_simp", drop_last_bare_simp_all(tactics))
    keep("join_exacts", join_consecutive_exacts(tactics))
    keep("collapse_defined_simp", collapse_defined_simp(tactics))
    keep("join_exacts_drop_last_simp", drop_last_bare_simp_all(join_consecutive_exacts(tactics)))
    import inits_updates_shorten as lra_ius

    replayed = lra_ius.replay(tactics).strip("\n")
    if replayed and replayed not in seen:
        seen.add(replayed)
        out.append(("inits_replay", replayed))
    for item in lra_ius.propose(tactics):
        nxt = str(item.get("tactics") or "").strip("\n")
        if nxt and nxt not in seen:
            seen.add(nxt)
            out.append((str(item.get("kind") or "inits_step"), nxt))
    for draft in lra_fan.span_preserving_drafts(tactics):
        keep(f"span_{draft.family}_{draft.draft_id}", draft.tactics)
    return out


def prefix_have_lines(reference: str) -> list[str]:
    from jevops.mask import lines_until

    return lines_until(
        reference,
        lambda line: line.strip().startswith("have "),
        lambda line: line.strip().startswith("case "),
    )


def insert_haves_before_induction(draft: str, haves: Sequence[str]) -> str:
    from jevops.mask import insert_before

    return insert_before(
        draft,
        haves,
        lambda line: line.strip().startswith("induction "),
        if_missing="prepend",
    )


def lake_keepbest(
    record: Mapping[str, Any],
    tactics_list: Sequence[str],
    *,
    state_root: Path,
    timeout: float,
) -> list[dict[str, Any]]:
    clone = lra_kb.lra_cw.clone_dir(str(record["url"]), state_root)
    dest = clone / lra_kb.lra_cw.source_relpath(record)
    restore = dest.read_bytes() if dest.is_file() else b""
    rows = []
    reference = lra_fan.tactic_block(record)
    seen: set[str] = set()
    for kind, body in [("reference", reference), *[(f"beam_{index}", text) for index, text in enumerate(tactics_list)]]:
        key = body.strip("\n")
        if key in seen and kind != "reference":
            continue
        variants: list[tuple[str, str]] = [(kind, body)]
        if kind != "reference":
            haves = prefix_have_lines(reference)
            present = {line.strip() for line in body.splitlines()}
            for have in haves:
                if have.strip() in present:
                    continue
                name = have_binder_name(have.strip()) or "have"
                variants.append((f"{kind}_have_{name}", insert_haves_before_induction(body, [have])))
            restored = insert_haves_before_induction(body, haves)
            if restored != body:
                variants.append((f"{kind}_haves", restored))
            current = body
            for pass_i in range(1, 4):
                nxt = drop_last_bare_simp_all(current)
                if not nxt or nxt == current:
                    break
                variants.append((f"{kind}_nosimp{pass_i}", nxt))
                current = nxt
        for label, current in variants:
            key2 = current.strip("\n")
            if key2 in seen and label != "reference":
                continue
            seen.add(key2)
            compiled = lra_kb.compile_tactics(
                record,
                current,
                state_root=state_root,
                timeout=timeout,
                restore=restore,
            )
            rows.append(
                {
                    "kind": label,
                    "n_chars": len(current),
                    "tactics_head": current[:240],
                    **{
                        k: compiled.get(k)
                        for k in ("ok", "theorem_ok", "module_exit_0", "exit_code", "token_count", "errors", "wall_ms")
                    },
                }
            )
    return rows


def self_check() -> dict[str, Any]:
    tactics = (
        "  intros Hup Hinit\n"
        "  have Hlen1 := InitStatesLength Hinit\n"
        "  induction Hup generalizing σ''\n"
        "  case update_none =>\n"
        "    simp_all\n"
        "    apply And.intro\n"
        "  case update_some =>\n"
        "    rw [List.unzip_zip]\n"
    )
    prefix = pca_prefix(tactics)
    vocab = reference_vocab(tactics)
    nxt = parse_next_line("```\n  simp_all\n  omega\n```")
    dropped = drop_last_bare_simp_all("    exact foo\n        . simp_all\n")
    indented = extend_prefix("  case update_none =>", "    exact InitStatesNotDefined Hinit")
    dup_ref = (
        "  induction H\n"
        "  case a =>\n"
        "    simp_all\n"
        "    exact foo\n"
        "    simp_all\n"
    )
    dup_pref = pca_prefix(dup_ref) + "\n  case a =>\n    simp_all"
    dup_rem = remaining_arm_lines(dup_pref, dup_ref, "a")
    pack = structure_pack(tactics, prefix)
    guided = guided_vocab(prefix, tactics, pack)
    after_none = structure_pack(tactics, prefix + "\n  case update_none =>\n    simp_all")
    guided_after = guided_vocab(prefix + "\n  case update_none =>\n    simp_all", tactics, after_none)
    return {
        "ok": "have Hlen1" not in prefix
        and "induction Hup" in prefix
        and "case update_none" not in prefix
        and STOP_TOKEN in vocab
        and nxt.strip() == "simp_all"
        and dropped == "    exact foo"
        and "have Hk" in insert_haves_before_induction("  exists x\n  induction H\n", ["  have Hk := foo"])
        and "<;> exact" in join_consecutive_exacts("    exact A\n    exact B\n")
        and indented.endswith("    exact InitStatesNotDefined Hinit")
        and any("exact foo" in item for item in dup_rem)
        and sum(item.strip() == "simp_all" for item in dup_rem) == 1
        and any(
            "exact foo" in item
            for item in guided_vocab(
                dup_pref,
                dup_ref,
                structure_pack(dup_ref, dup_pref),
            )
        )
        and any("case update_none" in item for item in guided)
        and not any("update_some" in item for item in guided)
        and not any(item.strip().startswith("have ") for item in guided)
        and not any(item.strip().startswith("have ") for item in guided_after)
        and any(
            "And.intro" in item
            for item in guided_vocab(
                prefix + "\n  case update_none =>\n    simp_all",
                tactics,
                structure_pack(tactics, prefix + "\n  case update_none =>\n    simp_all"),
            )
        )
        and not any(
            "update_some" in item
            for item in guided_vocab(
                prefix + "\n  case update_none =>\n    simp_all",
                tactics,
                structure_pack(tactics, prefix + "\n  case update_none =>\n    simp_all"),
            )
        )
        and not any(item.strip().startswith("have ") for item in guided_vocab(
            prefix + "\n  case update_none =>\n    simp_all\n  case update_some =>\n    simp_all",
            tactics,
            structure_pack(
                tactics,
                prefix + "\n  case update_none =>\n    simp_all\n  case update_some =>\n    simp_all",
            ),
        ))
        and "172.17.0.1" in lra_gt.DOCKER0_HEALTH_URL,
        "pca_prefix": prefix,
        "vocab_n": len(vocab),
        "hardware_class": HARDWARE_CLASS,
        "called_hosted_mistral": False,
        "arena_score": None,
    }


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-check", action="store_true")
    parser.add_argument("--live", action="store_true")
    parser.add_argument(
        "--repair-latest",
        action="store_true",
        help="lake keep-best + simp_all no-progress repair on constrained-beam-latest.json (no new Leanstral calls)",
    )
    parser.add_argument(
        "--shorten-reference",
        action="store_true",
        help="lake compiler shortenings of the original that keep prefix haves (no Leanstral)",
    )
    parser.add_argument("--mode", choices=("greedy", "beam"), default="greedy")
    parser.add_argument("--beam", type=int, default=BEAM_DEFAULT)
    parser.add_argument("--temperature", type=float, default=0.0, help="llama.cpp sampling temperature; 0 is greedy argmax")
    parser.add_argument("--max-steps", type=int, default=MAX_STEPS_DEFAULT)
    parser.add_argument("--names", default="Core.InitsUpdatesComm")
    parser.add_argument("--state-root", type=Path, default=DEFAULT_STATE)
    parser.add_argument("--timeout", type=float, default=180.0)
    parser.add_argument("--out", type=Path, default=OUT_DEFAULT)
    args = parser.parse_args(list(argv) if argv is not None else None)
    if args.self_check or (not args.live and not args.repair_latest and not args.shorten_reference):
        report = self_check()
        json.dump(report, sys.stdout, indent=2, sort_keys=True)
        sys.stdout.write("\n")
        return 0 if report["ok"] else 1
    os.environ.setdefault("IPFS_ACCELERATE_LLAMA_CPP_AUTOSTART", "0")
    repair_tactics: dict[str, str] = {}
    if args.repair_latest:
        latest = args.out / "constrained-beam-latest.json"
        prior = json.loads(latest.read_text(encoding="utf-8"))
        for item in prior.get("problems") or []:
            finals = ((item.get("search") or {}).get("finals") or [])
            if finals and item.get("name"):
                repair_tactics[str(item["name"])] = str(finals[0].get("tactics") or "")
    health = lra_gt.probe_docker0_health()
    if not args.repair_latest and not args.shorten_reference and not health.ok:
        payload = {
            "ok": True,
            "skipped": True,
            "reason": f"docker0_unhealthy: {health.error or health.status_code}",
            "hardware_class": HARDWARE_CLASS,
            "called_hosted_mistral": False,
            "called_docker0": False,
            "official_track2": False,
            "arena_score": None,
        }
        json.dump(payload, sys.stdout, indent=2, sort_keys=True)
        sys.stdout.write("\n")
        return 0
    _raw, digest, records = lra_splice.load_warmup_records()
    names = [item.strip() for item in str(args.names).split(",") if item.strip()]
    started = time.perf_counter()
    problems = []
    for name in names:
        record = next(item for item in records if item.get("name") == name)
        if args.repair_latest:
            body = repair_tactics.get(name) or ""
            search = {
                "mode": "repair_latest",
                "called_docker0": False,
                "finals": [{"tactics": body, "steps": [], "stopped": True}],
                "hardware_class": HARDWARE_CLASS,
                "called_hosted_mistral": False,
                "official_track2": False,
                "arena_score": None,
            }
            lake_src = [body] if body.strip() else []
        elif args.shorten_reference:
            orig = lra_fan.tactic_block(record)
            drafts = shorten_keeping_prefix_haves(orig)
            search = {
                "mode": "shorten_reference",
                "called_docker0": False,
                "n_drafts": len(drafts),
                "draft_names": [item[0] for item in drafts],
                "finals": [{"tactics": body, "steps": [name], "stopped": True} for name, body in drafts],
                "hardware_class": HARDWARE_CLASS,
                "called_hosted_mistral": False,
                "official_track2": False,
                "arena_score": None,
            }
            lake_src = [body for _name, body in drafts]
        else:
            search = run_search(
                record,
                mode=args.mode,
                max_steps=args.max_steps,
                beam=args.beam,
                temperature=args.temperature,
            )
            lake_src = [item["tactics"] for item in search.get("finals") or []]
        lake_rows = lake_keepbest(
            record,
            lake_src,
            state_root=args.state_root,
            timeout=args.timeout,
        )
        valid = [row for row in lake_rows if row.get("theorem_ok")]
        kept = None
        if valid:
            kept = sorted(
                valid,
                key=lambda row: (
                    int(row.get("token_count") or 10**9),
                    0 if row.get("kind") == "reference" else 1,
                ),
            )[0]
        ref_tokens = lra_loop.token_count(lra_fan.tactic_block(record))
        problems.append(
            lra_pca.redact(
                {
                    "name": name,
                    "warmup_jsonl_sha256": digest,
                    "search": search,
                    "candidates": lake_rows,
                    "kept": None
                    if kept is None
                    else {"kind": kept["kind"], "theorem_ok": kept.get("theorem_ok"), "token_count": kept.get("token_count")},
                    "reference_token_count": ref_tokens,
                    "beats_reference": bool(
                        kept is not None
                        and kept.get("kind") != "reference"
                        and kept.get("token_count") is not None
                        and int(kept["token_count"]) < ref_tokens
                    ),
                    "hardware_class": HARDWARE_CLASS,
                    "called_hosted_mistral": False,
                    "called_docker0": not args.repair_latest and not args.shorten_reference,
                    "official_track2": False,
                    "arena_score": None,
                }
            )
        )
    payload = {
        "schema": "lra-constrained-beam-local/v1",
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "protocol": PROTOCOL,
        "pr": PR_ID,
        "hardware_class": HARDWARE_CLASS,
        "called_hosted_mistral": False,
        "called_docker0": not args.repair_latest and not args.shorten_reference,
        "official_track2": False,
        "arena_score": None,
        "wall_ms": (time.perf_counter() - started) * 1000.0,
        "problems": problems,
    }
    text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if "apikey_" in text:
        raise SystemExit("refusing to write a receipt that contains an API key")
    args.out.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = args.out / f"constrained-beam-{stamp}.json"
    latest = args.out / "constrained-beam-latest.json"
    path.write_text(text, encoding="utf-8")
    latest.write_text(text, encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "latest": str(latest),
                "kept": [{"name": item.get("name"), "kept": item.get("kept")} for item in problems],
                "hardware_class": HARDWARE_CLASS,
                "arena_score": None,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

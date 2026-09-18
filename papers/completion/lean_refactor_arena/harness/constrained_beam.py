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
import importlib.util
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
    core = stripped.lstrip("·. ").strip()
    match = _HAVE_NAME.match(core)
    return match.group(1) if match else ""


def identifier_used(name: str, text: str) -> bool:
    if not name:
        return False
    return re.search(r"(?<![A-Za-z0-9_'])" + re.escape(name) + r"(?![A-Za-z0-9_'])", text) is not None


def pca_prefix(tactics: str) -> str:
    """Keep PCA glue; keep MCA ``have`` only when a later line still names it."""

    lines = tactics.splitlines()
    pre: list[str] = []
    rest: list[str] = []
    hit_case = False
    for line in lines:
        if not hit_case and line.strip().startswith("case "):
            hit_case = True
        (rest if hit_case else pre).append(line)
    out: list[str] = []
    for index, line in enumerate(pre):
        stripped = line.strip()
        if stripped.startswith("rename_i ") or stripped.startswith("obtain "):
            continue
        if stripped.startswith("have "):
            name = have_binder_name(stripped)
            later = "\n".join(pre[index + 1 :] + rest)
            if identifier_used(name, later):
                out.append(line)
            continue
        out.append(line)
    return "\n".join(out).rstrip()


def reference_vocab(tactics: str) -> list[str]:
    seen: set[str] = set()
    vocab: list[str] = []
    for line in tactics.splitlines():
        stripped = line.strip()
        if not stripped or stripped in seen:
            continue
        seen.add(stripped)
        vocab.append(line.rstrip())
    for extra in ("simp_all", "omega", "constructor", STOP_TOKEN):
        if extra not in seen:
            vocab.append(extra)
            seen.add(extra)
    return vocab


def last_open_case(prefix: str) -> Optional[str]:
    tag = None
    for line in prefix.splitlines():
        stripped = line.strip()
        if stripped.startswith("case "):
            rest = stripped[len("case ") :]
            if "=>" in rest:
                rest = rest.split("=>", 1)[0]
            tag = rest.split()[0] if rest.split() else None
    return tag


def case_header_map(reference: str) -> dict[str, str]:
    headers: dict[str, str] = {}
    spans = lra_fan.case_spans(reference)
    if not spans:
        return headers
    top = min(span.indent for span in spans)
    for span in spans:
        if span.indent != top:
            continue
        tag = span.label.split()[0]
        header = reference[span.start : span.header_end].splitlines()[0].rstrip()
        headers[tag] = header
    return headers


def case_arm_lines(reference: str, tag: str) -> list[str]:
    want = str(tag or "").split()[0]
    for span in lra_fan.case_spans(reference):
        if span.label.split()[0] != want:
            continue
        body = reference[span.header_end : span.end]
        return [line.rstrip() for line in body.splitlines() if line.strip()]
    return []


def structure_pack(reference: str, prefix: str) -> dict[str, Any]:
    """PCA skeleton + MCA holes of the *original* proof, plus what the prefix still lacks."""

    holes = lra_mask.find_holes(reference)
    skeleton = lra_mask.mask_skeleton(reference, holes)
    tags = pca_case_tags(reference)
    missing = [tag for tag in tags if f"case {tag}" not in prefix]
    empty_arms = empty_case_arms(prefix, reference)
    remaining = {tag: remaining_arm_lines(prefix, reference, tag) for tag in tags}
    unfinished_arms = [tag for tag in tags if f"case {tag}" in prefix and remaining.get(tag)]
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
        "missing_cases": missing,
        "empty_arms": empty_arms,
        "unfinished_arms": unfinished_arms,
        "next_original": None
        if not unfinished_arms
        else (remaining.get(unfinished_arms[0]) or [None])[0],
        "earliest_unfinished": next(
            (tag for tag in tags if tag in missing or tag in unfinished_arms or tag in empty_arms),
            None,
        ),
        "open_case": last_open_case(prefix),
        "mca_holes": mca,
        "n_have": int(counts.get("n_have") or 0),
        "n_induction": int(counts.get("n_induction") or 0),
        "n_cases": int(counts.get("n_cases") or 0),
        "n_tokens_ref": int(counts.get("n_tokens") or 0),
    }


def guided_vocab(prefix: str, reference: str, pack: Mapping[str, Any]) -> list[str]:
    """Priority next lines: missing PCA case headers before MCA haves."""

    present = {line.strip() for line in prefix.splitlines() if line.strip()}
    missing = list(pack.get("missing_cases") or [])
    empty_arms = list(pack.get("empty_arms") or [])
    headers = case_header_map(reference)
    open_tag = pack.get("open_case")
    out: list[str] = []

    def push(line: str) -> None:
        stripped = line.strip()
        if not stripped or stripped in present:
            return
        if line not in out:
            out.append(line)

    earliest = pack.get("earliest_unfinished")
    if earliest and earliest in missing:
        if earliest in headers:
            push(headers[str(earliest)])
        return out
    next_original = pack.get("next_original")
    unfinished = list(pack.get("unfinished_arms") or [])
    if earliest and (earliest in empty_arms or earliest in unfinished):
        # Always emit next_original even if the same stripped text already
        # appeared in an earlier arm (e.g. a second ``simp_all`` / ``exact``).
        if next_original:
            out.append(str(next_original))
        else:
            rem = remaining_arm_lines(prefix, reference, str(earliest))
            if rem:
                out.append(rem[0])
        return out
    if missing:
        if open_tag:
            for line in case_arm_lines(reference, str(open_tag)):
                push(line)
        for tag in missing:
            if tag in headers:
                push(headers[tag])
        return out
    if empty_arms:
        tag = empty_arms[0]
        for line in case_arm_lines(reference, tag):
            push(line)
        return out
    # PCA complete: closers only. No MCA have/rename, no English.
    for extra in CLOSERS:
        push(extra)
    return out


def filter_to_earliest(
    lines: Sequence[str],
    pack: Mapping[str, Any],
    reference: str,
) -> list[str]:
    """Drop candidates that skip past the earliest unfinished PCA case."""

    earliest = pack.get("earliest_unfinished")
    if not earliest:
        kept: list[str] = []
        seen: set[str] = set()
        for line in lines:
            stripped = str(line).strip()
            if not stripped or stripped == STOP_TOKEN or stripped in seen:
                continue
            if looks_like_closer(stripped):
                kept.append(str(line))
                seen.add(stripped)
        return kept
    missing = set(pack.get("missing_cases") or [])
    empty = set(pack.get("empty_arms") or [])
    unfinished = set(pack.get("unfinished_arms") or [])
    allowed: set[str] = set()
    nxt_raw = str(pack.get("next_original") or "")
    nxt = nxt_raw.strip()
    if earliest in missing:
        header = case_header_map(reference).get(str(earliest), "")
        if header:
            allowed.add(header.strip())
        allowed.add(f"case {earliest}")
    elif earliest in empty or earliest in unfinished:
        if nxt:
            allowed.add(nxt)
            allowed.add(nxt_raw.rstrip())
    kept: list[str] = []
    seen: set[str] = set()
    for line in lines:
        stripped = str(line).strip()
        if not stripped or stripped == STOP_TOKEN or stripped in seen:
            continue
        ok = False
        if earliest in missing:
            ok = stripped.startswith("case ") and earliest in stripped.split()
        elif allowed:
            ok = stripped in allowed or any(stripped == item or item in stripped for item in allowed)
        if ok:
            kept.append(str(line))
            seen.add(stripped)
    return kept


def looks_like_closer(stripped: str) -> bool:
    key = stripped.strip()
    if key in CLOSERS:
        return True
    return key.startswith(("simp", "exact ", "omega", "constructor", "rfl", "try simp", "try omega"))


def looks_like_tactic(stripped: str) -> bool:
    key = stripped.strip()
    if key == STOP_TOKEN:
        return True
    return key.startswith(_TACTIC_HEAD) or key in CLOSERS


def parse_next_line(text: str) -> str:
    body = lra_loop.extract_generated_tactics(text)
    for line in body.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.upper() == STOP_TOKEN or stripped in {".", "qed"}:
            return STOP_TOKEN
        if stripped.startswith("sorry") or stripped.startswith("admit"):
            return STOP_TOKEN
        if "<|im_start|>" in stripped or "<|im_end|>" in stripped or stripped.startswith("<|"):
            continue
        if stripped.startswith("You are") or stripped.startswith("Lean 4") or len(stripped) > 160:
            continue
        if not looks_like_tactic(stripped):
            continue
        return line.rstrip()
    return STOP_TOKEN


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
    spans = lra_fan.case_spans(tactics)
    if not spans:
        return []
    top = min(span.indent for span in spans)
    tags: list[str] = []
    for span in spans:
        if span.indent != top:
            continue
        tag = span.label.split()[0]
        if tag not in tags:
            tags.append(tag)
    return tags


def case_body_lines(prefix: str, tag: str) -> list[str]:
    want = str(tag or "").split()[0]
    capturing = False
    body: list[str] = []
    for line in prefix.splitlines():
        stripped = line.strip()
        if stripped.startswith("case "):
            rest = stripped[len("case ") :]
            if "=>" in rest:
                rest = rest.split("=>", 1)[0]
            this = rest.split()[0] if rest.split() else ""
            capturing = this == want
            continue
        if capturing and stripped:
            body.append(stripped)
    return body


def empty_case_arms(prefix: str, reference: str) -> list[str]:
    return [
        tag
        for tag in pca_case_tags(reference)
        if f"case {tag}" in prefix and not case_body_lines(prefix, tag)
    ]


def is_mca_line(stripped: str) -> bool:
    core = stripped.lstrip("·. ").strip()
    return core.startswith(("have ", "rename_i ", "obtain "))


def arm_keep_lines(reference: str, tag: str) -> list[str]:
    """Original arm tactics; keep MCA ``have`` only when a later line still names it."""

    lines = case_arm_lines(reference, tag)
    tags = pca_case_tags(reference)
    later_arms: list[str] = []
    seen = False
    for other in tags:
        if other == tag:
            seen = True
            continue
        if seen:
            later_arms.extend(case_arm_lines(reference, other))
    out: list[str] = []
    for index, line in enumerate(lines):
        if is_mca_line(line.strip()):
            name = have_binder_name(line.strip())
            later = "\n".join(lines[index + 1 :] + later_arms)
            if identifier_used(name, later):
                out.append(line)
            continue
        out.append(line)
    return out


def remaining_arm_lines(prefix: str, reference: str, tag: str) -> list[str]:
    """Original keep-lines not yet copied, counting indent-sensitive occurrences."""

    have: dict[str, int] = {}
    for line in prefix.splitlines():
        key = line.rstrip()
        if not key.strip():
            continue
        have[key] = have.get(key, 0) + 1
    seen: dict[str, int] = {}
    out: list[str] = []
    for line in arm_keep_lines(reference, tag):
        key = line.rstrip()
        seen[key] = seen.get(key, 0) + 1
        if have.get(key, 0) < seen[key]:
            out.append(line)
    return out


def stop_allowed(prefix: str, reference: str) -> bool:
    """Do not STOP while a PCA case header is missing or its original arm is unfinished."""

    tags = pca_case_tags(reference)
    if not tags:
        return True
    if any(f"case {tag}" not in prefix for tag in tags):
        return False
    if empty_case_arms(prefix, reference):
        return False
    return not any(remaining_arm_lines(prefix, reference, tag) for tag in tags)


def unused_vocab(prefix: str, vocab: Sequence[str]) -> list[str]:
    present = {line.strip() for line in prefix.splitlines() if line.strip()}
    out: list[str] = []
    for item in vocab:
        if item.strip() in present and item != STOP_TOKEN:
            continue
        out.append(item)
    return out


def typesafe_prune(
    record: Mapping[str, Any],
    prefix: str,
    candidates: Sequence[str],
    *,
    ledger: lra_t1.ProblemLedger,
    keep: int,
    context: Optional[Mapping[str, Any]] = None,
) -> dict[str, Any]:
    unique: list[str] = []
    seen: set[str] = set()
    for item in candidates:
        key = item.strip() or STOP_TOKEN
        if key in seen:
            continue
        seen.add(key)
        unique.append(item if item.strip() else STOP_TOKEN)
        if len(unique) >= MAX_CANDIDATES:
            break
    if not unique:
        unique = [STOP_TOKEN]
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
    spec = importlib.util.spec_from_file_location("lra_typesafe_inference", ts_path)
    if spec is None or spec.loader is None:
        return {
            "skipped": True,
            "reason": "typesafe_inference_spec",
            "kept": unique[:keep],
            "jev_generated_lean": False,
            "arena_score": None,
        }
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
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
    usage = dict(getattr(result, "usage", None) or {})
    inn = int(usage.get("input_tokens") or usage.get("prompt_tokens") or lra_t1.estimate_tokens(json.dumps(state)))
    out = int(usage.get("output_tokens") or usage.get("completion_tokens") or 0)
    line = ledger.record("jev", input_tokens=inn, output_tokens=out, model=lra_t1.JEV_MODEL_ID)
    best = (getattr(result, "choices", None) or {}).get("next_line")
    pick_id = str(getattr(best, "choice", None) or "c0")
    probs = dict(getattr(best, "probabilities", None) or {})
    ranked_ids = sorted(criteria.keys(), key=lambda key: float(probs.get(key) or 0.0), reverse=True)
    if pick_id in criteria and pick_id in ranked_ids:
        ranked_ids.remove(pick_id)
        ranked_ids.insert(0, pick_id)
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

    if nxt == STOP_TOKEN:
        return prefix
    src = nxt
    if original and original.strip() == nxt.strip():
        src = original
    if not prefix.strip():
        return src if src[:1] in {" ", "\t"} else f"  {src.strip()}"
    if src[:1] in {" ", "\t"}:
        return prefix.rstrip() + "\n" + src.rstrip()
    stripped = src.strip()
    case_indent = 2
    last = ""
    for line in prefix.splitlines():
        if line.strip().startswith("case "):
            case_indent = len(line) - len(line.lstrip())
        if line.strip():
            last = line
    if stripped.startswith("case "):
        return prefix.rstrip() + "\n" + (" " * case_indent) + stripped
    indent = len(last) - len(last.lstrip()) if last else case_indent + 2
    if last.strip().startswith("case "):
        indent = case_indent + 2
    return prefix.rstrip() + "\n" + (" " * indent) + stripped


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
    lines = tactics.splitlines()
    for index, line in enumerate(lines):
        if _BARE_SIMP_ALL.match(line):
            del lines[index]
            return "\n".join(lines)
    return None


def drop_last_bare_simp_all(tactics: str) -> Optional[str]:
    """Drop the last standalone ``simp_all`` / ``. simp_all`` line (not ``<;> simp_all``)."""

    lines = tactics.splitlines()
    for index in range(len(lines) - 1, -1, -1):
        if _BARE_SIMP_ALL.match(lines[index]):
            del lines[index]
            return "\n".join(lines)
    return None


def repair_no_progress_simp_all(tactics: str, errors: Sequence[Mapping[str, Any]]) -> Optional[str]:
    blob = "\n".join(str(item.get("data") or "") for item in errors)
    if "simp_all made no progress" not in blob:
        return None
    return drop_last_bare_simp_all(tactics)


def join_consecutive_exacts(tactics: str) -> str:
    lines = tactics.splitlines()
    out: list[str] = []
    index = 0
    while index < len(lines):
        if (
            lines[index].strip().startswith("exact ")
            and index + 1 < len(lines)
            and lines[index + 1].strip().startswith("exact ")
        ):
            indent = lines[index][: len(lines[index]) - len(lines[index].lstrip())]
            out.append(f"{indent}{lines[index].strip()} <;> {lines[index + 1].strip()}")
            index += 2
            continue
        out.append(lines[index])
        index += 1
    return "\n".join(out)


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
        if not body:
            return
        text = body.strip("\n")
        if not text or text in seen:
            return
        present = {line.strip() for line in text.splitlines()}
        if any(have.strip() not in present for have in haves):
            return
        seen.add(text)
        out.append((name, text))

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
    out: list[str] = []
    for line in reference.splitlines():
        if line.strip().startswith("case "):
            break
        if line.strip().startswith("have "):
            out.append(line)
    return out


def insert_haves_before_induction(draft: str, haves: Sequence[str]) -> str:
    present = {line.strip() for line in draft.splitlines()}
    missing = [line for line in haves if line.strip() not in present]
    if not missing:
        return draft
    out: list[str] = []
    inserted = False
    for line in draft.splitlines():
        if not inserted and line.strip().startswith("induction "):
            out.extend(missing)
            inserted = True
        out.append(line)
    if not inserted:
        out = list(missing) + out
    return "\n".join(out)


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

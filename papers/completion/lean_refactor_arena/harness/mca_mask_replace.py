#!/usr/bin/env python3
"""Mask MCA residual spans, keep the PCA skeleton, fill holes, lake-check.

Principal structure (induction, ``case`` arms, closing exact/constructor) stays.
Minor residuals (simp-at runs, have/rename_i, rw chains) become holes.

Fills:
- deterministic compiler templates (dead_code / strength_reduction / algebraic)
- one hosted Labs Leanstral pass over the masked skeleton
- optional Track 1 grok-4.6 few-shot + one lake-error repair (max 2 grok calls)

TypeSafe ranks the reassembled candidates. Lake is the oracle.
Never docker0. Never LOCK_EX. Not official Track 2. Not an Arena ranking.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping, Optional, Sequence

HERE = Path(__file__).resolve().parent
PAPER_ROOT = HERE.parent
OUT_DEFAULT = PAPER_ROOT / "evidence" / "canaries"
DEFAULT_STATE = Path.home() / ".local/state/ipfs_accelerate_py/vericodegen-2026-lra/track1-lake"
LAKE_READY = (
    "CallElimCorrect.substOldPostSubset",
    "CallElimCorrect.extractedOldExprInVars",
    "Core.InitsUpdatesComm",
    "Cslib.LambdaCalculus.LocallyNameless.Fsub.Typing.progress",
    "Cslib.SKI.parallelReduction_diamond",
    "Cslib.CCS.bisimilarity_congr_choice",
    "fundamental_theorem_of_variational_calculus'",
    "Electromagnetism.ElectromagneticPotential.time_deriv_time_deriv_electricField_of_isExtrema",
    "FieldSpecification.WickAlgebra.ι_timeOrderF_superCommuteF_eq_time",
    "Binius.BinaryBasefold.fiberwise_dist_lt_imp_dist_lt_unique_decoding_radius",
    "Binius.BinaryBasefold.fold_advances_evaluation_poly",
    "interleaved_affine_gaps_imply_tensor_gaps",
)

if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
import draft_fanout as lra_fan  # noqa: E402
import pca_mca_fanout as lra_pca  # noqa: E402
import run_warmup as lra_loop  # noqa: E402
import splice as lra_splice  # noqa: E402
import track1_keepbest as lra_kb  # noqa: E402
import track1_ledger as lra_t1  # noqa: E402
import track1_mistral_leanstral as lra_mistral  # noqa: E402

PROTOCOL = "LRA/v1"
PR_ID = "PR-9d"
HARDWARE_CLASS = "mistral_labs_api"
GROK_HARDWARE_CLASS = "grok_cli"
GROK_MAX_NEW_TOKENS = 900
GROK_TIMEOUT_SECONDS = 300.0
_SIMP_AT = lra_fan._SIMP_AT
_RW = lra_pca._RW_BRACKET
_RENAME = lra_pca._RENAME
_HAVE = lra_pca._HAVE
_HOLE = re.compile(r"<<<MCA_(\d+) family=([a-z_]+)>>>")
SKELETON_PREFIXES = (
    "induction ",
    "case ",
    "exact ",
    "constructor",
    "exists ",
    "refine ",
    "intro ",
    "intros ",
    "ext ",
    "funext",
    "by_cases",
    "rcases ",
    "obtain ",
)


@dataclass(frozen=True)
class Hole:
    hole_id: str
    family: str
    start: int
    end: int
    original: str
    indent: str


def find_holes(tactics: str) -> list[Hole]:
    """Residual MCA spans: simp-at runs, rw runs, rename_i, have."""

    lines = tactics.splitlines(keepends=True)
    holes: list[Hole] = []
    index = 0
    offset = 0
    while index < len(lines):
        line = lines[index]
        stripped = line.strip()
        start = offset
        if _SIMP_AT.match(line.rstrip("\n")):
            run = index
            while run < len(lines) and _SIMP_AT.match(lines[run].rstrip("\n")):
                offset += len(lines[run])
                run += 1
            if run - index >= 2:
                original = "".join(lines[index:run]).rstrip("\n")
                indent = re.match(r" *", line).group(0) if re.match(r" *", line) else ""
                holes.append(
                    Hole(
                        hole_id=f"MCA_{len(holes)}",
                        family="strength_reduction",
                        start=start,
                        end=start + len(original),
                        original=original,
                        indent=indent,
                    )
                )
            index = run
            continue
        if _RW.match(line.rstrip("\n")):
            run = index
            while run < len(lines) and _RW.match(lines[run].rstrip("\n")):
                offset += len(lines[run])
                run += 1
            if run - index >= 2:
                original = "".join(lines[index:run]).rstrip("\n")
                indent = re.match(r" *", line).group(0) if re.match(r" *", line) else ""
                holes.append(
                    Hole(
                        hole_id=f"MCA_{len(holes)}",
                        family="algebraic_simplification",
                        start=start,
                        end=start + len(original),
                        original=original,
                        indent=indent,
                    )
                )
            index = run
            continue
        if _RENAME.match(line.rstrip("\n")) or _HAVE.match(line.rstrip("\n")):
            original = line.rstrip("\n")
            indent = re.match(r" *", line).group(0) if re.match(r" *", line) else ""
            family = "dead_code" if _RENAME.match(line.rstrip("\n")) else "loop_invariant"
            holes.append(
                Hole(
                    hole_id=f"MCA_{len(holes)}",
                    family=family,
                    start=start,
                    end=start + len(original),
                    original=original,
                    indent=indent,
                )
            )
        offset += len(line)
        index += 1
    return holes


def mask_skeleton(tactics: str, holes: Sequence[Hole]) -> str:
    """Replace MCA spans with hole markers. PCA skeleton (case/induction) stays."""

    if not holes:
        return tactics
    parts: list[str] = []
    cursor = 0
    for hole in holes:
        parts.append(tactics[cursor : hole.start])
        parts.append(f"{hole.indent}<<<{hole.hole_id} family={hole.family}>>>")
        cursor = hole.end
    parts.append(tactics[cursor:])
    return "".join(parts)


def template_fill(hole: Hole) -> str:
    if hole.family == "strength_reduction":
        # Drop the simp-at run; a following simp_all is the PCA glue.
        return ""
    if hole.family == "algebraic_simplification":
        lemmas = []
        for line in hole.original.splitlines():
            match = _RW.match(line)
            if match:
                lemmas.extend(part.strip() for part in match.group(2).split(",") if part.strip())
        if lemmas:
            return f"{hole.indent}simp [{', '.join(lemmas)}]"
        if "calc" in hole.original:
            return f"{hole.indent}simp_all"
        return f"{hole.indent}omega"
    if hole.family in {"dead_code", "loop_invariant"}:
        return ""  # drop the residual line
    return hole.original


def apply_fills(tactics: str, holes: Sequence[Hole], fills: Mapping[str, str]) -> str:
    masked = mask_skeleton(tactics, holes)
    out = masked
    for hole in holes:
        marker = f"{hole.indent}<<<{hole.hole_id} family={hole.family}>>>"
        fill = fills.get(hole.hole_id, hole.original)
        out = out.replace(marker, fill, 1)
    # drop leftover empty lines from deleted holes
    lines = [line for line in out.splitlines() if line.strip() or True]
    cleaned: list[str] = []
    blank = 0
    for line in lines:
        if not line.strip():
            blank += 1
            if blank <= 1:
                cleaned.append(line)
            continue
        blank = 0
        cleaned.append(line)
    return "\n".join(cleaned).strip("\n")


def parse_leanstral_fills(text: str, holes: Sequence[Hole]) -> dict[str, str]:
    """Accept either per-hole blocks or a full tactic block."""

    fills: dict[str, str] = {}
    for hole in holes:
        pattern = re.compile(
            rf"<<<{re.escape(hole.hole_id)}(?: family={re.escape(hole.family)})?>>>\s*(.*?)(?=<<<MCA_|\Z)",
            re.S,
        )
        match = pattern.search(text)
        if match:
            body = match.group(1).strip("\n")
            if body:
                fills[hole.hole_id] = body
    if fills:
        return fills
    tactics = lra_loop.extract_generated_tactics(text)
    if tactics.strip():
        # Whole-block fill: treat as replacing the original (caller may ignore).
        fills["__full__"] = tactics
    return fills


def leanstral_prompt(record: Mapping[str, Any], skeleton: str, holes: Sequence[Hole]) -> str:
    hole_docs = []
    for hole in holes[:6]:
        hole_docs.append(
            f"{hole.hole_id} family={hole.family}\nORIGINAL:\n{hole.original}\n"
        )
    return (
        "Lean Refactor Arena hole-fill. The skeleton is the PCA principal structure "
        "(induction and case arms). Fill each <<<MCA_i family=...>>> hole only.\n"
        "Keep every case header. Same indentation as ORIGINAL. No sorry, no theorem, no open.\n"
        "Prefer simp_all for strength_reduction holes, drop dead rename_i/have, simp for rw chains.\n\n"
        f"Problem: {record.get('name')}\n"
        f"Statement:\n{record.get('statement')}\n\n"
        f"SKELETON:\n{skeleton}\n\n"
        f"HOLES:\n{''.join(hole_docs)}\n"
        "Reply as:\n<<<MCA_0 family=...>>>\n<tactics>\n<<<MCA_1 family=...>>>\n<tactics>\n"
    )


def one_hole_prompt(record: Mapping[str, Any], tactics: str, hole: Hole) -> str:
    skeleton = mask_skeleton(tactics, [hole])
    return (
        "Lean Refactor Arena: replace ONE residual span. Keep the PCA skeleton "
        "(induction, every case header, exact/constructor). Fill the hole with "
        "1-4 Lean tactic lines that are STRICTLY SHORTER than ORIGINAL, same indent.\n"
        "Do not emit sorry, theorem, lemma, import, or open. Do not drop case arms.\n"
        "Prefer: simp [lemmas], simp_all, omega, ring, linarith, exact <hyp>.\n\n"
        f"Problem: {record.get('name')}\n"
        f"Statement:\n{str(record.get('statement') or '')[:600]}\n\n"
        f"ORIGINAL hole {hole.hole_id} family={hole.family} ({len(hole.original.split())} words):\n"
        f"{hole.original}\n\n"
        f"SKELETON (hole marked <<<{hole.hole_id} family={hole.family}>>>):\n"
        f"{skeleton[:2800]}\n\n"
        f"Reply with only the replacement tactics, or:\n<<<{hole.hole_id} family={hole.family}>>>\n<tactics>\n"
    )


SHOT_NAMES = (
    "CallElimCorrect.substOldPostSubset",
    "CallElimCorrect.extractedOldExprInVars",
)


def few_shot_example(record: Mapping[str, Any]) -> dict[str, Any]:
    tactics = lra_fan.tactic_block(record)
    holes = find_holes(tactics)
    fills = {hole.hole_id: template_fill(hole) for hole in holes}
    filled = apply_fills(tactics, holes, fills)
    return {
        "name": record.get("name"),
        "ref_tokens": lra_loop.token_count(tactics),
        "filled_tokens": lra_loop.token_count(filled),
        "n_holes": len(holes),
        "families": [hole.family for hole in holes],
        "skeleton": mask_skeleton(tactics, holes),
        "reference": tactics,
        "filled": filled,
        "ratio": round(lra_loop.token_count(filled) / max(1, lra_loop.token_count(tactics)), 4),
    }


def few_shot_prompt(target: Mapping[str, Any], shots: Sequence[Mapping[str, Any]]) -> str:
    blocks = []
    for index, shot in enumerate(shots, 1):
        blocks.append(
            f"EXAMPLE {index}: {shot['name']}\n"
            f"Score: {shot['filled_tokens']}/{shot['ref_tokens']} tokens (ratio {shot['ratio']}), "
            f"holes={shot['n_holes']} families={shot['families']}. Lake-valid after deleting MCA residuals.\n"
            f"PCA skeleton (induction/case kept):\n{shot['skeleton'][:900]}\n\n"
            f"BEFORE ({shot['ref_tokens']} tokens):\n{shot['reference'][:700]}\n\n"
            f"AFTER ({shot['filled_tokens']} tokens, smallest lake-valid):\n{shot['filled'][:700]}\n"
        )
    tactics = lra_fan.tactic_block(target)
    holes = find_holes(tactics)
    skeleton = mask_skeleton(tactics, holes)
    return (
        "You are refactoring a Lean 4 proof for Lean Refactor Arena. "
        "PCA principal structure = induction and every case arm (keep and connect these). "
        "MCA residuals = simp-at runs, rename_i, have after induction, rw chains (delete or replace with shorter tactics).\n"
        "Goal: the SMALLEST lake-valid tactic block. No sorry, no theorem/lemma/import/open. "
        "Do not drop case headers. Match indentation.\n\n"
        + "\n".join(blocks)
        + f"\nTARGET: {target.get('name')}\n"
        f"Statement:\n{str(target.get('statement') or '')[:700]}\n\n"
        f"PCA skeleton with MCA holes marked:\n{skeleton[:1800]}\n\n"
        f"CURRENT tactics ({lra_loop.token_count(tactics)} tokens):\n{tactics[:1600]}\n\n"
        "Reply with ONLY the refactored tactic block after := by.\n"
    )


def shot_examples(records: Sequence[Mapping[str, Any]], *, skip_name: str) -> list[dict[str, Any]]:
    shots: list[dict[str, Any]] = []
    for shot_name in SHOT_NAMES:
        if shot_name == skip_name:
            continue
        shot_rec = next((item for item in records if item.get("name") == shot_name), None)
        if shot_rec is not None:
            shots.append(few_shot_example(shot_rec))
    return shots


def _kind_needs_hammer(kind: str) -> bool:
    key = str(kind or "")
    return key.startswith(("leanstral", "grok", "mca_leanstral", "tactician", "hybrid", "pca_"))


def _identity_dict(identity: Any) -> Optional[dict[str, Any]]:
    if identity is None:
        return None
    if hasattr(identity, "requested_provider"):
        return {
            "requested_provider": identity.requested_provider,
            "requested_model": identity.requested_model,
            "resolved_provider": identity.resolved_provider,
            "resolved_model": identity.resolved_model,
            "fallback_used": bool(identity.fallback_used),
            "arena_score": None,
        }
    if isinstance(identity, Mapping):
        return dict(identity)
    return {"repr": str(identity), "arena_score": None}


def _flatten_tactics(reference: str, text: str) -> str:
    return lra_kb.flatten_overindent(
        reference, lra_kb.match_reference_indent(reference, lra_loop.extract_generated_tactics(text))
    )


def _compile_row(item: Mapping[str, Any], compiled: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "kind": item["kind"],
        "generator": item.get("generator"),
        "n_chars": len(str(item.get("tactics") or "")),
        "tactics_head": str(item.get("tactics") or "")[:240],
        "n_holes": len(item.get("holes") or []),
        **{k: compiled.get(k) for k in ("ok", "theorem_ok", "module_exit_0", "exit_code", "token_count", "errors", "wall_ms")},
    }


def _hammer_passes(
    *,
    kind: str,
    tactics_now: str,
    reference: str,
    errors: Sequence[Mapping[str, Any]],
    record: Mapping[str, Any],
    state_root: Path,
    timeout: float,
    restore: bytes,
    generator: str,
) -> tuple[list[dict[str, Any]], str, list[Any], bool]:
    rows: list[dict[str, Any]] = []
    current = tactics_now
    current_errors = list(errors)
    ok = False
    for pass_i in (1, 2, 3):
        repaired = hammer_repair(current, reference, current_errors)
        if repaired == current:
            break
        compiled_h = lra_kb.compile_tactics(
            record,
            repaired,
            state_root=state_root,
            timeout=timeout,
            restore=restore,
        )
        rows.append(
            _compile_row(
                {
                    "kind": f"{kind}_hammer{pass_i}",
                    "generator": generator,
                    "tactics": repaired,
                    "holes": [],
                },
                compiled_h,
            )
        )
        if compiled_h.get("theorem_ok"):
            ok = True
            current = repaired
            current_errors = compiled_h.get("errors") or []
            break
        current = repaired
        current_errors = compiled_h.get("errors") or []
    return rows, current, current_errors, ok


# Cslib scripts use ``grind`` / ``grind only [→ wf]``. Never rewrite grind
# unless the lake error is specifically "unknown tactic grind" (Strata).
_UNKNOWN_TACTICS = frozenset(
    {
        "aesop",
        "exact?",
        "apply?",
        "hint",
        "native_decide",
        "decide+",
        "tauto",
        "linarith",
        "nlinarith",
        "ring_nf",
    }
)


def hammer_repair(draft: str, reference: str, errors: Sequence[Mapping[str, Any]]) -> str:
    """Local tactician: restore PCA glue, drop illegal tactics, then simp_all/omega.

    Strata/CSLib lake projects do not depend on Aesop. Portable closers are
    ``simp_all`` and ``omega``. Aesop is only safe on Putnam's Mathlib+Aesop lake.
    """

    blob = "\n".join(str(item.get("data") or "") for item in errors)
    out = draft
    for ident in re.findall(r"Unknown identifier `([^`]+)`", blob):
        restore_lines = [line for line in reference.splitlines() if ident in line.split()]
        if not restore_lines:
            restore_lines = [line for line in reference.splitlines() if ident in line]
        present = {line.strip() for line in out.splitlines()}
        haveish = next((line for line in restore_lines if "have " in line or ":=" in line), None)
        pick = haveish or (restore_lines[0] if restore_lines else "")
        if pick and pick.strip() not in present:
            out = pick + "\n" + out
    for tac in re.findall(r"unknown tactic[:\s]*[`']?([A-Za-z_?][A-Za-z0-9_?]*)", blob, re.I):
        if tac.lower() in {"case", "induction", "simp", "simp_all", "intro", "intros", "exact", "apply"}:
            continue
        out = re.sub(rf"\b{re.escape(tac)}\b", "simp_all", out)
    for tag in re.findall(r"Case tag `([^`]+)` not found", blob):
        out = re.sub(rf"(?m)^[ \t]*case {re.escape(tag)}\b.*$", "", out)
    ref_ind = [line for line in reference.splitlines() if line.strip().startswith("induction ")]
    if ref_ind and not any(line.strip().startswith("induction ") for line in out.splitlines()):
        out = ref_ind[0] + "\n" + out
    cleaned: list[str] = []
    for line in out.splitlines():
        stripped = line.strip()
        head = stripped.split()[0] if stripped else ""
        if head.rstrip(";") in _UNKNOWN_TACTICS or stripped.rstrip(";") in _UNKNOWN_TACTICS:
            indent = line[: len(line) - len(line.lstrip())]
            cleaned.append(f"{indent}simp_all")
            continue
        cleaned.append(line)
    out = "\n".join(cleaned)
    if re.search(r"unknown tactic[:\s]*[`']?grind", blob, re.I):
        out = re.sub(r"\bgrind\b", "simp_all", out)
    out = re.sub(r"\bexact\?", "simp_all", out)
    out = re.sub(r"\bapply\?", "simp_all", out)
    if "unknown tactic" in blob.lower():
        # Error often omits the name; drop leftover non-Lean tokens on their own line.
        again: list[str] = []
        for line in out.splitlines():
            token = line.strip().split()[0] if line.strip() else ""
            if token.rstrip(";") in _UNKNOWN_TACTICS:
                continue
            again.append(line)
        out = "\n".join(again)
    if "simp_all made no progress" in blob:
        out = re.sub(r"(?m)^[ \t]*simp_all(?:\s*;\s*)?$", "", out, count=1)
    if "Type mismatch" in blob:
        for ident in re.findall(r"`([^`]+)`", blob):
            restore_lines = [line for line in reference.splitlines() if ident in line]
            present = {line.strip() for line in out.splitlines()}
            pick = next((line for line in restore_lines if "have " in line or "rw " in line), None)
            if pick and pick.strip() not in present:
                out = pick + "\n" + out
        # Grok often substitutes `exact InitStatesNotDefined` for a longer rw chain.
        if "InitStatesNotDefined" in blob and "unzip_zip" in reference and "unzip_zip" not in out:
            out = out.replace("exact InitStatesNotDefined Hinit", "rw [List.unzip_zip] <;> simp_all")
        if re.search(r"exact ih\.2\.2", out) and "apply (ih Hinit" in reference:
            out = re.sub(r"exact ih\.2\.2", "apply (ih Hinit ?_ ?_).2.2", out)
    if "No goals to be solved" in blob:
        out = re.sub(r"(?m)^[ \t]*all_goals try simp_all\s*$", "", out)
        out = re.sub(r"(?m)^[ \t]*try omega\s*$", "", out)
        # Drop a trailing extra simp_all that closed the last goal too early.
        lines = out.splitlines()
        while lines and lines[-1].strip() in {"simp_all", "try omega", "all_goals try simp_all"}:
            lines.pop()
        out = "\n".join(lines)
    elif "unsolved goals" in blob.lower() or "unknown tactic" in blob.lower() or "Unknown identifier" in blob:
        if "all_goals try simp_all" not in out:
            out = out.rstrip() + "\n  all_goals try simp_all\n  try omega"
    return out


def case_tag(label: str) -> str:
    return str(label or "").split()[0]


def replace_case_from(dst: str, src: str, tag: str) -> str:
    """Replace one top-level ``case`` arm in ``dst`` with the matching arm from ``src``."""

    want = case_tag(tag)
    dst_span = next((span for span in lra_fan.case_spans(dst) if case_tag(span.label) == want), None)
    src_span = next((span for span in lra_fan.case_spans(src) if case_tag(span.label) == want), None)
    if dst_span is None or src_span is None:
        return dst
    return dst[: dst_span.start] + src[src_span.start : src_span.end] + dst[dst_span.end :]


def drop_bare_simp_all(tactics: str) -> str:
    return re.sub(r"(?m)^[ \t]*simp_all\s*$", "", tactics)


def try_simp_all(tactics: str) -> str:
    return re.sub(r"(?m)^([ \t]*)simp_all\s*$", r"\1try simp_all", tactics)


def grok_tactician_variants(grok: str, reference: str) -> list[dict[str, Any]]:
    """Deterministic repairs of a grok file draft. Jev does not write these."""

    rows: list[dict[str, Any]] = []
    seen: set[str] = {grok.strip("\n")}

    def push(kind: str, body: str, *ops: str) -> None:
        text = body.strip("\n")
        if not text or text in seen:
            return
        seen.add(text)
        rows.append(
            {
                "kind": kind,
                "generator": "tactician",
                "tactics": text,
                "holes": [],
                "ops": list(ops),
                "source": "grok-file+tactician",
            }
        )

    push("tactician_drop_simp_all", drop_bare_simp_all(grok), "drop_bare_simp_all")
    push("tactician_try_simp_all", try_simp_all(grok), "try_simp_all")
    import inits_updates_shorten as lra_ius

    push("tactician_inits_replay_ref", lra_ius.replay(reference), "inits_replay_ref")
    push("tactician_inits_replay", lra_ius.replay(grok), "inits_replay")
    for item in lra_ius.propose(grok)[:8]:
        push(f"tactician_{item['kind']}", item["tactics"], item["kind"])
    hammered = hammer_repair(
        grok,
        reference,
        [{"data": "simp_all made no progress"}, {"data": "Type mismatch `InitStatesNotDefined`"}],
    )
    push("tactician_hammer_seed", hammered, "hammer_seed")
    grok_tags = [case_tag(span.label) for span in lra_fan.case_spans(grok)]
    ref_tags = [case_tag(span.label) for span in lra_fan.case_spans(reference)]
    for tag in grok_tags:
        if tag in ref_tags:
            push(f"hybrid_ref_case_{tag}", replace_case_from(grok, reference, tag), "hybrid_ref_case", tag)
            push(f"hybrid_grok_case_{tag}", replace_case_from(reference, grok, tag), "hybrid_grok_case", tag)
    return rows


MAX_GROK_FANOUT = 14


def assemble_candidates(
    record: Mapping[str, Any],
    tactics: str,
    holes: Sequence[Hole],
    *,
    leanstral_text: Optional[str],
) -> list[dict[str, Any]]:
    template_fills = {hole.hole_id: template_fill(hole) for hole in holes}
    template_tactics = apply_fills(tactics, holes, template_fills)
    import inits_updates_shorten as lra_ius

    rows = [
        {"kind": "reference", "generator": "pca_skeleton", "tactics": tactics, "holes": []},
        {
            "kind": "inits_replay",
            "generator": "inits_updates_shorten",
            "tactics": lra_ius.replay(tactics),
            "holes": [],
        },
        {
            "kind": "mca_template_fill",
            "generator": "deterministic",
            "tactics": template_tactics,
            "holes": [asdict(hole) | {"fill": template_fills[hole.hole_id]} for hole in holes],
        },
    ]
    strength_fills = {
        hole.hole_id: template_fill(hole) if hole.family == "strength_reduction" else hole.original
        for hole in holes
    }
    strength_tactics = apply_fills(tactics, holes, strength_fills)
    if strength_tactics != tactics and strength_tactics != template_tactics:
        rows.append(
            {
                "kind": "mca_template_strength_only",
                "generator": "deterministic",
                "tactics": strength_tactics,
                "holes": [
                    asdict(hole) | {"fill": strength_fills[hole.hole_id]}
                    for hole in holes
                    if hole.family == "strength_reduction"
                ],
            }
        )
    if leanstral_text:
        fills = parse_leanstral_fills(leanstral_text, holes)
        if "__full__" in fills and len(fills) == 1:
            filled = lra_kb.match_reference_indent(tactics, fills["__full__"])
            filled = lra_kb.flatten_overindent(tactics, filled)
            rows.append(
                {
                    "kind": "mca_leanstral_full",
                    "generator": "labs-leanstral-1-5",
                    "tactics": filled,
                    "holes": [],
                }
            )
        else:
            merged = {hole.hole_id: fills.get(hole.hole_id, template_fills[hole.hole_id]) for hole in holes}
            filled = apply_fills(tactics, holes, merged)
            filled = lra_kb.flatten_overindent(tactics, lra_kb.match_reference_indent(tactics, filled))
            rows.append(
                {
                    "kind": "mca_leanstral_holes",
                    "generator": "labs-leanstral-1-5",
                    "tactics": filled,
                    "holes": [asdict(hole) | {"fill": merged[hole.hole_id]} for hole in holes],
                }
            )
    return rows


def prioritize_holes(holes: Sequence[Hole], *, cap: int = 6) -> list[Hole]:
    rank = {"strength_reduction": 0, "algebraic_simplification": 1, "dead_code": 2, "loop_invariant": 3}
    ordered = sorted(
        holes,
        key=lambda hole: (rank.get(hole.family, 9), -len(hole.original), hole.hole_id),
    )
    return ordered[: max(0, int(cap))]


def ablate_holes(
    record: Mapping[str, Any],
    tactics: str,
    holes: Sequence[Hole],
    *,
    state_root: Path,
    timeout: float,
    restore: bytes,
) -> list[dict[str, Any]]:
    """Drop one MCA hole at a time, then combine lake-valid drops."""

    rows: list[dict[str, Any]] = []
    droppable: list[Hole] = []
    for hole in holes:
        fills = {item.hole_id: (template_fill(item) if item.hole_id == hole.hole_id else item.original) for item in holes}
        tactics_one = apply_fills(tactics, holes, fills)
        compiled = lra_kb.compile_tactics(
            record, tactics_one, state_root=state_root, timeout=timeout, restore=restore
        )
        ok = bool(compiled.get("theorem_ok"))
        rows.append(
            {
                "kind": f"ablate_{hole.hole_id}",
                "generator": "deterministic",
                "n_chars": len(tactics_one),
                "tactics_head": tactics_one[:240],
                "hole_id": hole.hole_id,
                "family": hole.family,
                **{k: compiled.get(k) for k in ("ok", "theorem_ok", "module_exit_0", "exit_code", "token_count", "errors", "wall_ms")},
            }
        )
        if ok:
            droppable.append(hole)
    if len(droppable) >= 2:
        fills = {item.hole_id: (template_fill(item) if item in droppable else item.original) for item in holes}
        combined = apply_fills(tactics, holes, fills)
        compiled = lra_kb.compile_tactics(
            record, combined, state_root=state_root, timeout=timeout, restore=restore
        )
        rows.append(
            {
                "kind": "ablate_combine_droppable",
                "generator": "deterministic",
                "n_chars": len(combined),
                "tactics_head": combined[:240],
                "n_droppable": len(droppable),
                "droppable_ids": [hole.hole_id for hole in droppable],
                **{k: compiled.get(k) for k in ("ok", "theorem_ok", "module_exit_0", "exit_code", "token_count", "errors", "wall_ms")},
            }
        )
    return rows


def typesafe_rank_fanout(
    record: Mapping[str, Any],
    drafts: Sequence[dict[str, Any]],
    *,
    ledger: Optional[Any],
) -> dict[str, Any]:
    """One Jev Choice over tactician/PCA drafts. Jev does not write Lean."""

    if not drafts:
        return {"skipped": True, "reason": "no_drafts", "arena_score": None}
    lra_pca.load_keyfile()
    lra_pca.pin_typesafe_path()
    from ipfs_accelerate_py.typesafe_inference import Choice, TypeSafeClient, typesafe_configured

    if not typesafe_configured():
        return {"skipped": True, "reason": "no_key", "arena_score": None}
    criteria = {
        str(item["kind"]): f"{item.get('generator')}; ops={item.get('ops')}; {len(item.get('tactics') or '')} chars"
        for item in drafts[:20]
    }
    state = {
        "problem": {"name": record.get("name"), "source": record.get("source")},
        "statement": str(record.get("statement") or "")[:700],
        "goal": "Repair a grok-written tactic file. Keep every case arm. Prefer the shortest lake-valid draft.",
        "drafts": [
            {
                "id": item["kind"],
                "ops": item.get("ops"),
                "n_chars": len(item.get("tactics") or ""),
                "head": str(item.get("tactics") or "")[:220],
            }
            for item in drafts[:20]
        ],
    }
    questions = {
        "best_first_draft": Choice(
            instructions=(
                "Which draft id should lake-compile first to repair this grok file? "
                "Prefer restoring a truncated case arm from the reference, then dropping a "
                "no-progress simp_all. Never delete a case header. Do not write Lean."
            ),
            criteria=criteria,
        )
    }
    started = time.perf_counter()
    client = TypeSafeClient(timeout=60.0)
    try:
        result = client.system_one(state, questions)
    except Exception as exc:
        return {"skipped": True, "reason": str(exc)[:400], "arena_score": None}
    usage = dict(getattr(result, "usage", None) or {})
    if ledger is not None:
        inn = int(usage.get("input_tokens") or usage.get("prompt_tokens") or lra_t1.estimate_tokens(json.dumps(state)))
        out = int(usage.get("output_tokens") or usage.get("completion_tokens") or 0)
        ledger.record("jev", input_tokens=inn, output_tokens=out, model=lra_t1.JEV_MODEL_ID)
    best = (getattr(result, "choices", None) or {}).get("best_first_draft")
    return lra_pca.redact(
        {
            "skipped": False,
            "reason": "routed",
            "best_first_draft": getattr(best, "choice", None),
            "best_confidence": getattr(best, "confidence", None),
            "top": list(dict(getattr(best, "probabilities", None) or {})),
            "usage": usage,
            "wall_ms": (time.perf_counter() - started) * 1000.0,
            "jev_generated_lean": False,
            "arena_score": None,
        }
    )


def load_grok_tactics_file(path: Path) -> str:
    text = Path(path).read_text(encoding="utf-8")
    return lra_loop.extract_generated_tactics(text)


def run_problem(
    name: str,
    *,
    state_root: Path,
    timeout: float,
    call_leanstral: bool,
    ablate: bool = False,
    one_hole: bool = False,
    few_shot: bool = False,
    grok_few_shot: bool = False,
    grok_generate: Optional[Callable[..., str]] = None,
    grok_trace: Optional[Callable[[], Mapping[str, Any]]] = None,
    grok_tactics_paths: Sequence[Path] = (),
    typesafe_fanout: bool = False,
) -> dict[str, Any]:
    _raw, digest, records = lra_splice.load_warmup_records()
    record = next(item for item in records if item.get("name") == name)
    tactics = lra_fan.tactic_block(record)
    holes = find_holes(tactics)
    skeleton = mask_skeleton(tactics, holes)
    leanstral_text = None
    identity = None
    ledger = None
    grok_skip_reason = ""
    if grok_few_shot:
        # Grok smoke never falls back to hosted Leanstral or docker0.
        call_leanstral = False
    fill_holes = [hole for hole in holes if hole.family in {"strength_reduction", "algebraic_simplification"}]
    one_hole_fills: list[dict[str, Any]] = []
    few_shot_row: Optional[dict[str, Any]] = None
    grok_few_shot_row: Optional[dict[str, Any]] = None
    grok_tactics_current = ""
    grok_errors_current: list[Any] = []
    grok_workspace: Optional[Path] = None
    grok_file_meta: list[dict[str, Any]] = []
    grok_file_rows: list[dict[str, Any]] = []
    typesafe_meta: Optional[dict[str, Any]] = None
    if grok_tactics_paths:
        grok_few_shot = False
        call_leanstral = False
        if ledger is None:
            ledger = lra_t1.ProblemLedger(name=f"{name}#grok-file-fanout")
        for path in grok_tactics_paths:
            loaded = load_grok_tactics_file(path)
            filled = _flatten_tactics(tactics, loaded)
            grok_file_rows.append(
                {
                    "kind": f"grok_file_{Path(path).stem[:48]}",
                    "generator": "grok-file",
                    "tactics": filled,
                    "holes": [],
                    "source": str(path),
                    "chat_ignored": True,
                }
            )
    if grok_few_shot:
        shots = shot_examples(records, skip_name=name)
        ledger = lra_t1.ProblemLedger(name=f"{name}#grok-few-shot")
        if grok_generate is None and not lra_t1.grok_callable():
            grok_skip_reason = "no_key"
            ledger.skipped = True
            ledger.reason = "no_key"
        else:
            grok_workspace = lra_t1.prepare_grok_workspace()
            prompt = lra_t1.grok_file_prompt(few_shot_prompt(record, shots))
            try:
                grok_result = lra_t1.generate_grok_file(
                    prompt,
                    ledger,
                    workspace=grok_workspace,
                    max_new_tokens=GROK_MAX_NEW_TOKENS,
                    timeout=GROK_TIMEOUT_SECONDS,
                    generate=grok_generate,
                    fixture=grok_generate is not None,
                    reset_stub=True,
                )
            except lra_t1.Track1LedgerError as exc:
                grok_skip_reason = str(exc)
            else:
                identity = grok_result.identity
                filled = _flatten_tactics(tactics, grok_result.tactics)
                grok_file_meta.append({"call": "draft", **grok_result.as_dict()})
                grok_few_shot_row = {
                    "kind": "grok_few_shot",
                    "generator": "grok-4.6",
                    "tactics": filled,
                    "holes": [],
                    "n_shots": len(shots),
                    "source": "tactics.lean",
                    "tactics_path": grok_result.tactics_path,
                    "chat_ignored": True,
                    "shot_scores": [
                        {
                            "name": shot["name"],
                            "ratio": shot["ratio"],
                            "filled_tokens": shot["filled_tokens"],
                            "ref_tokens": shot["ref_tokens"],
                        }
                        for shot in shots
                    ],
                }
                grok_tactics_current = filled
    elif few_shot and call_leanstral:
        shots = shot_examples(records, skip_name=name)
        lra_mistral.load_keyfiles()
        lra_mistral.pin_paths()
        ledger = lra_t1.ProblemLedger(name=f"{name}#few-shot")
        prompt = few_shot_prompt(record, shots)
        text, identity, _line = lra_mistral.generate_mistral(
            prompt, ledger, max_new_tokens=900, timeout=180.0
        )
        filled = _flatten_tactics(tactics, text)
        few_shot_row = {
            "kind": "leanstral_few_shot",
            "generator": "labs-leanstral-1-5",
            "tactics": filled,
            "holes": [],
            "n_shots": len(shots),
            "shot_scores": [
                {"name": shot["name"], "ratio": shot["ratio"], "filled_tokens": shot["filled_tokens"], "ref_tokens": shot["ref_tokens"]}
                for shot in shots
            ],
        }
    elif call_leanstral and one_hole:
        targets = prioritize_holes(fill_holes or holes, cap=2)
        if targets:
            lra_mistral.load_keyfiles()
            lra_mistral.pin_paths()
            ledger = lra_t1.ProblemLedger(name=f"{name}#mca-one-hole")
            for hole in targets:
                prompt = one_hole_prompt(record, tactics, hole)
                try:
                    text, identity, _line = lra_mistral.generate_mistral(
                        prompt, ledger, max_new_tokens=256, timeout=120.0
                    )
                except lra_mistral.Track1MistralError:
                    break
                parsed = parse_leanstral_fills(text, [hole])
                fill = parsed.get(hole.hole_id) or parsed.get("__full__") or ""
                if not fill.strip():
                    fill = lra_loop.extract_generated_tactics(text)
                fills = {item.hole_id: (fill if item.hole_id == hole.hole_id else item.original) for item in holes}
                filled = apply_fills(tactics, holes, fills)
                filled = lra_kb.flatten_overindent(tactics, lra_kb.match_reference_indent(tactics, filled))
                one_hole_fills.append(
                    {
                        "kind": f"leanstral_one_{hole.hole_id}",
                        "generator": "labs-leanstral-1-5",
                        "tactics": filled,
                        "holes": [asdict(hole) | {"fill": fill[:400]}],
                    }
                )
    elif call_leanstral and fill_holes:
        lra_mistral.load_keyfiles()
        lra_mistral.pin_paths()
        ledger = lra_t1.ProblemLedger(name=f"{name}#mca-mask")
        prompt = leanstral_prompt(record, mask_skeleton(tactics, fill_holes), fill_holes)
        leanstral_text, identity, _line = lra_mistral.generate_mistral(
            prompt, ledger, max_new_tokens=700, timeout=180.0
        )
        holes_for_leanstral = fill_holes
    else:
        holes_for_leanstral = holes
    candidates = assemble_candidates(record, tactics, holes, leanstral_text=None)
    if leanstral_text:
        extra = assemble_candidates(record, tactics, holes_for_leanstral, leanstral_text=leanstral_text)
        kinds = {item["kind"] for item in candidates}
        for item in extra:
            if item["kind"] not in kinds:
                candidates.append(item)
    candidates.extend(one_hole_fills)
    if few_shot_row is not None:
        candidates.append(few_shot_row)
    if grok_few_shot_row is not None:
        candidates.append(grok_few_shot_row)
    candidates.extend(grok_file_rows)
    grok_seeds = [item for item in candidates if str(item.get("kind") or "").startswith("grok")]
    if typesafe_fanout and grok_seeds:
        seed = grok_seeds[0]["tactics"]
        extras = grok_tactician_variants(seed, tactics)
        _raw, _digest, warmup_records = lra_splice.load_warmup_records()
        rows_feat = [lra_pca.feature_row(item) for item in warmup_records]
        model = lra_pca.fit_pca_mca(rows_feat)
        public_model = {key: value for key, value in model.items() if key not in {"zscore", "vt"}}
        features = lra_pca.count_tactics(seed)
        families = lra_pca.amenable_families(features, public_model)
        for draft in lra_pca.guided_drafts(seed, families, features):
            extras.append(
                {
                    "kind": f"pca_{draft.draft_id}_{draft.family}",
                    "generator": "pca_mca_fanout",
                    "tactics": draft.tactics,
                    "holes": [],
                    "ops": list(draft.ops),
                    "source": "grok-file+pca_mca",
                }
            )
        typesafe_meta = typesafe_rank_fanout(record, extras, ledger=ledger)
        pick = str((typesafe_meta or {}).get("best_first_draft") or "")
        ordered = []
        seen_kind = set()
        if pick:
            for item in extras:
                if item["kind"] == pick:
                    ordered.append(item)
                    seen_kind.add(item["kind"])
        for item in extras:
            if item["kind"] in seen_kind:
                continue
            seen_kind.add(item["kind"])
            ordered.append(item)
            if len(ordered) >= MAX_GROK_FANOUT:
                break
        candidates.extend(ordered)
    clone = lra_kb.lra_cw.clone_dir(str(record["url"]), state_root)
    dest = clone / lra_kb.lra_cw.source_relpath(record)
    restore = dest.read_bytes() if dest.is_file() else b""
    rows = []
    grok_ok = False
    for item in candidates:
        compiled = lra_kb.compile_tactics(
            record,
            item["tactics"],
            state_root=state_root,
            timeout=timeout,
            restore=restore,
        )
        rows.append(_compile_row(item, compiled))
        kind = str(item.get("kind") or "")
        if kind.startswith("grok"):
            if compiled.get("theorem_ok"):
                grok_ok = True
            else:
                grok_tactics_current = item["tactics"]
                grok_errors_current = compiled.get("errors") or []
        if _kind_needs_hammer(kind) and not compiled.get("theorem_ok"):
            hammer_gen = "grok+simp_all/omega" if kind.startswith("grok") else "leanstral+simp_all/omega"
            hammer_rows, current, current_errors, hammer_ok = _hammer_passes(
                kind=kind,
                tactics_now=item["tactics"],
                reference=tactics,
                errors=compiled.get("errors") or [],
                record=record,
                state_root=state_root,
                timeout=timeout,
                restore=restore,
                generator=hammer_gen,
            )
            rows.extend(hammer_rows)
            if kind.startswith("grok"):
                grok_tactics_current = current
                grok_errors_current = current_errors
                grok_ok = grok_ok or hammer_ok
            elif compiled.get("errors"):
                grok_errors_current = grok_errors_current or list(compiled.get("errors") or [])
    if grok_few_shot and grok_few_shot_row is not None and not grok_ok and ledger is not None:
        prompt = lra_t1.grok_file_prompt(
            lra_kb.repair_prompt(
                record,
                failed=grok_tactics_current or grok_few_shot_row["tactics"],
                errors=grok_errors_current,
                reference=tactics,
            )
        )
        try:
            grok_result = lra_t1.generate_grok_file(
                prompt,
                ledger,
                workspace=grok_workspace or lra_t1.prepare_grok_workspace(),
                max_new_tokens=GROK_MAX_NEW_TOKENS,
                timeout=GROK_TIMEOUT_SECONDS,
                generate=grok_generate,
                fixture=grok_generate is not None,
                reset_stub=False,
            )
        except lra_t1.Track1LedgerError as exc:
            grok_skip_reason = grok_skip_reason or str(exc)
            rows.append(
                {
                    "kind": "grok_few_shot_repair",
                    "generator": "grok-4.6",
                    "n_chars": 0,
                    "tactics_head": "",
                    "n_holes": 0,
                    "ok": False,
                    "theorem_ok": False,
                    "module_exit_0": False,
                    "exit_code": None,
                    "token_count": None,
                    "errors": [{"pos": None, "data": str(exc)}],
                    "wall_ms": None,
                    "skipped": True,
                    "reason": str(exc),
                    "source": "tactics.lean",
                    "chat_ignored": True,
                }
            )
        else:
            identity = grok_result.identity
            grok_file_meta.append({"call": "repair", **grok_result.as_dict()})
            repaired_tactics = _flatten_tactics(tactics, grok_result.tactics)
            compiled_r = lra_kb.compile_tactics(
                record,
                repaired_tactics,
                state_root=state_root,
                timeout=timeout,
                restore=restore,
            )
            rows.append(
                _compile_row(
                    {
                        "kind": "grok_few_shot_repair",
                        "generator": "grok-4.6",
                        "tactics": repaired_tactics,
                        "holes": [],
                    },
                    compiled_r,
                )
            )
            if compiled_r.get("theorem_ok"):
                grok_ok = True
            else:
                hammer_rows, _, _, hammer_ok = _hammer_passes(
                    kind="grok_few_shot_repair",
                    tactics_now=repaired_tactics,
                    reference=tactics,
                    errors=compiled_r.get("errors") or [],
                    record=record,
                    state_root=state_root,
                    timeout=timeout,
                    restore=restore,
                    generator="grok+simp_all/omega",
                )
                rows.extend(hammer_rows)
                grok_ok = grok_ok or hammer_ok
    if ablate and holes:
        rows.extend(
            ablate_holes(
                record,
                tactics,
                prioritize_holes(holes, cap=6),
                state_root=state_root,
                timeout=timeout,
                restore=restore,
            )
        )
    valid = [row for row in rows if row.get("theorem_ok")]
    kept = None
    if valid:
        kept = sorted(
            valid,
            key=lambda row: (
                int(row.get("token_count") or 10**9),
                0 if row.get("kind") == "reference" else 1,
            ),
        )[0]
    ref_tokens = lra_loop.token_count(tactics)
    kept_tokens = None if kept is None else kept.get("token_count")
    beats_reference = bool(
        kept is not None
        and kept.get("kind") != "reference"
        and kept.get("theorem_ok")
        and kept_tokens is not None
        and int(kept_tokens) < ref_tokens
    )
    return lra_pca.redact(
        {
            "schema": "lra-mca-mask-replace/v1",
            "name": name,
            "warmup_jsonl_sha256": digest,
            "n_holes": len(holes),
            "holes": [asdict(hole) for hole in holes],
            "skeleton_head": skeleton[:800],
            "called_docker0": False,
            "used_prototype_endpoint": False,
            "hardware_class": GROK_HARDWARE_CLASS if (grok_few_shot or grok_tactics_paths) else HARDWARE_CLASS,
            "leanstral_identity": None if grok_few_shot else identity,
            "grok_identity": _identity_dict(identity) if grok_few_shot else None,
            "grok_few_shot": grok_few_shot,
            "grok_ok": grok_ok,
            "grok_skip_reason": grok_skip_reason or None,
            "grok_used_file": True if grok_few_shot else False,
            "grok_chat_ignored": True if grok_few_shot else False,
            "grok_workspace": None if grok_workspace is None else str(grok_workspace),
            "grok_file_calls": grok_file_meta,
            "typesafe_fanout": typesafe_meta,
            "reference_token_count": ref_tokens,
            "beats_reference": beats_reference,
            "ledger": None if ledger is None else ledger.as_dict(),
            "candidates": rows,
            "kept": None
            if kept is None
            else {
                "kind": kept["kind"],
                "theorem_ok": kept.get("theorem_ok"),
                "token_count": kept.get("token_count"),
            },
            "arena_score": None,
            "official_track2": False,
        }
    )


def self_check() -> dict[str, Any]:
    tactics = (
        "  induction post <;> simp [substOld]\n"
        "  case fvar =>\n"
        "    intros x Hin\n"
        "    simp at m\n"
        "    simp at name\n"
        "    simp_all\n"
        "  case op =>\n"
        "    rename_i foo\n"
        "    exact h\n"
    )
    holes = find_holes(tactics)
    skeleton = mask_skeleton(tactics, holes)
    fills = {hole.hole_id: template_fill(hole) for hole in holes}
    filled = apply_fills(tactics, holes, fills)
    return {
        "ok": len(holes) >= 2
        and "<<<MCA_0" in skeleton
        and "induction post" in skeleton
        and "case fvar" in skeleton
        and "simp at m" not in filled
        and "rename_i" not in filled,
        "n_holes": len(holes),
        "families": [hole.family for hole in holes],
        "arena_score": None,
    }


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-check", action="store_true")
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--no-leanstral", action="store_true")
    parser.add_argument("--ablate", action="store_true", help="lake-check dropping one MCA hole at a time")
    parser.add_argument("--one-hole", action="store_true", help="hosted Leanstral fills one MCA hole at a time")
    parser.add_argument("--few-shot", action="store_true", help="few-shot Leanstral from scored MCA hole examples")
    parser.add_argument(
        "--grok-few-shot",
        action="store_true",
        help="few-shot grok-4.6 + one lake-error repair (max 2 grok calls, no Leanstral)",
    )
    parser.add_argument(
        "--grok-tactics",
        default="",
        help="comma-separated grok tactics.lean files to repair (no new grok calls)",
    )
    parser.add_argument(
        "--typesafe-fanout",
        action="store_true",
        help="TypeSafe Choice + PCA/MCA/tactician fan-out over grok file drafts",
    )
    parser.add_argument("--names", default=",".join(LAKE_READY))
    parser.add_argument("--state-root", type=Path, default=DEFAULT_STATE)
    parser.add_argument("--timeout", type=float, default=180.0)
    parser.add_argument("--out", type=Path, default=OUT_DEFAULT)
    args = parser.parse_args(list(argv) if argv is not None else None)
    if args.few_shot and args.grok_few_shot:
        raise SystemExit("use either --few-shot (Leanstral) or --grok-few-shot, not both")
    if args.self_check or not args.live:
        report = self_check()
        json.dump(report, sys.stdout, indent=2, sort_keys=True)
        sys.stdout.write("\n")
        return 0 if report["ok"] else 1
    os.environ.setdefault("IPFS_ACCELERATE_LLAMA_CPP_AUTOSTART", "0")
    names = [item.strip() for item in str(args.names).split(",") if item.strip()]
    grok_paths = [Path(item.strip()) for item in str(args.grok_tactics).split(",") if item.strip()]
    started = time.perf_counter()
    reports = [
        run_problem(
            name,
            state_root=args.state_root,
            timeout=args.timeout,
            call_leanstral=not args.no_leanstral and not args.grok_few_shot and not grok_paths,
            ablate=args.ablate,
            one_hole=args.one_hole,
            few_shot=args.few_shot,
            grok_few_shot=args.grok_few_shot,
            grok_tactics_paths=grok_paths,
            typesafe_fanout=args.typesafe_fanout,
        )
        for name in names
    ]
    payload = {
        "schema": "lra-mca-mask-replace-batch/v1",
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "protocol": PROTOCOL,
        "pr": PR_ID,
        "called_docker0": False,
        "grok_few_shot": bool(args.grok_few_shot),
        "typesafe_fanout": bool(args.typesafe_fanout),
        "arena_score": None,
        "wall_ms": (time.perf_counter() - started) * 1000.0,
        "problems": reports,
    }
    text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if "apikey_" in text:
        raise SystemExit("refusing to write a receipt that contains an API key")
    args.out.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = args.out / f"mca-mask-{stamp}.json"
    latest = args.out / "mca-mask-latest.json"
    path.write_text(text, encoding="utf-8")
    latest.write_text(text, encoding="utf-8")
    copied = []
    for item in reports:
        for call in item.get("grok_file_calls") or []:
            src = Path(str(call.get("tactics_path") or ""))
            if not src.is_file():
                continue
            dest = args.out / f"grok-{item.get('name')}-{call.get('call')}-{stamp}.lean"
            dest.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
            copied.append(str(dest))
    print(
        json.dumps(
            {
                "ok": True,
                "latest": str(latest),
                "kept": [{"name": item.get("name"), "kept": item.get("kept"), "n_holes": item.get("n_holes")} for item in reports],
                "grok_tactics_files": copied,
                "arena_score": None,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

#!/usr/bin/env python3
"""Mask MCA residual spans, keep the PCA skeleton, fill holes, lake-check.

Principal structure (induction, ``case`` arms, closing exact/constructor) stays.
Minor residuals (simp-at runs, have/rename_i, rw chains) become holes.

Fills:
- deterministic compiler templates (dead_code / strength_reduction / algebraic)
- one hosted Labs Leanstral pass over the masked skeleton

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
from typing import Any, Mapping, Optional, Sequence

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


def assemble_candidates(
    record: Mapping[str, Any],
    tactics: str,
    holes: Sequence[Hole],
    *,
    leanstral_text: Optional[str],
) -> list[dict[str, Any]]:
    template_fills = {hole.hole_id: template_fill(hole) for hole in holes}
    template_tactics = apply_fills(tactics, holes, template_fills)
    rows = [
        {"kind": "reference", "generator": "pca_skeleton", "tactics": tactics, "holes": []},
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


def run_problem(
    name: str,
    *,
    state_root: Path,
    timeout: float,
    call_leanstral: bool,
    ablate: bool = False,
    one_hole: bool = False,
    few_shot: bool = False,
) -> dict[str, Any]:
    _raw, digest, records = lra_splice.load_warmup_records()
    record = next(item for item in records if item.get("name") == name)
    tactics = lra_fan.tactic_block(record)
    holes = find_holes(tactics)
    skeleton = mask_skeleton(tactics, holes)
    leanstral_text = None
    identity = None
    ledger = None
    fill_holes = [hole for hole in holes if hole.family in {"strength_reduction", "algebraic_simplification"}]
    one_hole_fills: list[dict[str, Any]] = []
    few_shot_row: Optional[dict[str, Any]] = None
    if few_shot and call_leanstral:
        shots = []
        for shot_name in SHOT_NAMES:
            if shot_name == name:
                continue
            shot_rec = next((item for item in records if item.get("name") == shot_name), None)
            if shot_rec is not None:
                shots.append(few_shot_example(shot_rec))
        lra_mistral.load_keyfiles()
        lra_mistral.pin_paths()
        ledger = lra_t1.ProblemLedger(name=f"{name}#few-shot")
        prompt = few_shot_prompt(record, shots)
        text, identity, _line = lra_mistral.generate_mistral(
            prompt, ledger, max_new_tokens=900, timeout=180.0
        )
        filled = lra_kb.flatten_overindent(
            tactics, lra_kb.match_reference_indent(tactics, lra_loop.extract_generated_tactics(text))
        )
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
    clone = lra_kb.lra_cw.clone_dir(str(record["url"]), state_root)
    dest = clone / lra_kb.lra_cw.source_relpath(record)
    restore = dest.read_bytes() if dest.is_file() else b""
    rows = []
    for item in candidates:
        compiled = lra_kb.compile_tactics(
            record,
            item["tactics"],
            state_root=state_root,
            timeout=timeout,
            restore=restore,
        )
        rows.append(
            {
                "kind": item["kind"],
                "generator": item["generator"],
                "n_chars": len(item["tactics"]),
                "tactics_head": item["tactics"][:240],
                "n_holes": len(item.get("holes") or []),
                **{k: compiled.get(k) for k in ("ok", "theorem_ok", "module_exit_0", "exit_code", "token_count", "errors", "wall_ms")},
            }
        )
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
            "hardware_class": HARDWARE_CLASS,
            "leanstral_identity": identity,
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
    parser.add_argument("--names", default=",".join(LAKE_READY))
    parser.add_argument("--state-root", type=Path, default=DEFAULT_STATE)
    parser.add_argument("--timeout", type=float, default=180.0)
    parser.add_argument("--out", type=Path, default=OUT_DEFAULT)
    args = parser.parse_args(list(argv) if argv is not None else None)
    if args.self_check or not args.live:
        report = self_check()
        json.dump(report, sys.stdout, indent=2, sort_keys=True)
        sys.stdout.write("\n")
        return 0 if report["ok"] else 1
    os.environ.setdefault("IPFS_ACCELERATE_LLAMA_CPP_AUTOSTART", "0")
    names = [item.strip() for item in str(args.names).split(",") if item.strip()]
    started = time.perf_counter()
    reports = [
        run_problem(
            name,
            state_root=args.state_root,
            timeout=args.timeout,
            call_leanstral=not args.no_leanstral,
            ablate=args.ablate,
            one_hole=args.one_hole,
            few_shot=args.few_shot,
        )
        for name in names
    ]
    payload = {
        "schema": "lra-mca-mask-replace-batch/v1",
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "protocol": PROTOCOL,
        "pr": PR_ID,
        "called_docker0": False,
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
    print(
        json.dumps(
            {
                "ok": True,
                "latest": str(latest),
                "kept": [{"name": item.get("name"), "kept": item.get("kept"), "n_holes": item.get("n_holes")} for item in reports],
                "arena_score": None,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

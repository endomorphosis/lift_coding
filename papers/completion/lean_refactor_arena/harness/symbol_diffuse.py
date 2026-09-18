#!/usr/bin/env python3
"""Mask Lean symbols/operators, fill, TypeSafe-rank.

Diffusion here is discrete denoising over tactic tokens, not neural SGD.

- Mask operators (``$``, ``<;>``, ``?_``, ``‹_›``, ``←``) and symbols
  (tactics/lemmas/hyps) while keeping the PCA skeleton (induction / ``·`` arms).
- TypeSafe Score (``cfg_mask``) picks how many holes and how long each span
  is. Higher score = more / longer masks. PCA control-flow stays unmasked.
- ``--sweep`` walks a small (n_masks × span × n_shots) grid. Closed-vocab
  multi-hole fills and optional few-shot Leanstral fills are all passed to
  TypeSafe Choice.
- ``llm=off``: fill from a closed Lean vocab. No model call.
- ``llm=on``: hosted Labs Leanstral few-shot multi-hole fill. Never docker0.
- Lake is the oracle. Jev does not write Lean.

Not official Track 2. Not an Arena ranking.
"""
from __future__ import annotations

import argparse
import json
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

if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
import pca_mca_fanout as lra_pca  # noqa: E402
import run_warmup as lra_loop  # noqa: E402
import splice as lra_splice  # noqa: E402
import track1_keepbest as lra_kb  # noqa: E402
import track1_ledger as lra_t1  # noqa: E402

PROTOCOL = "LRA/v1"
PR_ID = "PR-9f"
HARDWARE_CLASS = "spark_gb10"
LEANSTRAL_HARDWARE = "mistral_labs_api"
MARKER = re.compile(r"<<<SYM_(\d+)(?: kind=([a-z_]+))?>>>")

# Longest-first so ‹_› / <;> / ?_ mask as one hole.
# Skip := / · — their closed alts are not strictly shorter.
OPERATORS: tuple[str, ...] = (
    "<;>",
    "‹_›",
    "?_",
    "←",
    "|>.",
    "<|",
    "$",
)
OPERATOR_ALTS: dict[str, tuple[str, ...]] = {
    "$": ("",),
    "<;>": (";",),
    "?_": ("_",),
    "‹_›": ("this", "trivial", "rfl"),
    "←": ("",),
    "|>.": (".",),
    "<|": ("$", ""),
}
# Phrase rewrites using Lean's own operators/tactics (llm=off).
PHRASE_ALTS: tuple[tuple[str, str], ...] = (
    ("apply And.intro", "constructor"),
    ("intros Hin", "intro"),
    # After `apply`, keep a qualified head. `apply .update_some` does not elaborate.
    ("apply UpdateStates.update_some", "refine .update_some"),
    ("split at this <;> simp_all", "split at this\n          all_goals simp_all"),
    ("<;> simp_all", "\n          all_goals simp_all"),
    ("(by simp_all [isDefined])", "(UpdateStatesDefined Hups)"),
    ("$ by simp_all", "$ UpdateStatesLength Hups"),
    ("simp [isDefined, Option.isSome] at this", "simp_all [isDefined, Option.isSome]"),
    ("exact Hst", "assumption"),
    ("InitStatesSomeMonotone (by assumption)", "InitStatesSomeMonotone ‹_›"),
)
LEAN_TACTICS: tuple[str, ...] = (
    "simp",
    "simp_all",
    "rw",
    "exact",
    "apply",
    "refine",
    "constructor",
    "assumption",
    "intro",
    "intros",
    "split",
    "all_goals",
    "have",
    "exists",
    "rfl",
    "trivial",
    "grind",
    "omega",
    "decide",
)
STRUCTURE = frozenset(
    {
        "induction",
        "case",
        "rename_i",
        "generalizing",
    }
)
PCA_KEEP_PREFIXES = ("induction ", "case ", "exists ", "intros ")

# TypeSafe Score rubric: index = CFG aggressiveness. Higher → more/longer masks.
CFG_MASK_CRITERIA: tuple[str, ...] = (
    "2 masks of 1 token; keep PCA induction/dot arms",
    "3 masks of 2 tokens",
    "4 masks of 3 tokens",
    "6 masks of 4 tokens",
    "8 masks of 6 tokens",
)
# cfg_scale is classifier-free guidance: 0 = no few-shot (uncond), >0 = k shots.
CFG_SCHEDULES: tuple[dict[str, Any], ...] = (
    {"id": "cfg0", "n_masks": 2, "span": 1, "n_shots": 0, "cfg_scale": 0.0},
    {"id": "cfg1", "n_masks": 3, "span": 2, "n_shots": 2, "cfg_scale": 1.0},
    {"id": "cfg2", "n_masks": 4, "span": 3, "n_shots": 4, "cfg_scale": 1.5},
    {"id": "cfg3", "n_masks": 6, "span": 4, "n_shots": 6, "cfg_scale": 2.0},
    {"id": "cfg4", "n_masks": 8, "span": 6, "n_shots": 8, "cfg_scale": 3.0},
)
# One hole at a time; vary span; multi-shot fills. Score index = span bucket.
ONE_HOLE_SPANS: tuple[int, ...] = (1, 2, 3, 4, 6)
ONE_HOLE_CRITERIA: tuple[str, ...] = (
    "1-token hole (operator / ident)",
    "2-token hole",
    "3-token hole (short phrase)",
    "4-token hole",
    "6-token hole (kernel-sized span)",
)
ONE_HOLE_SCHEDULES: tuple[dict[str, Any], ...] = tuple(
    {"id": f"span{span}", "n_masks": 1, "span": span, "n_shots": 6, "cfg_scale": 1.5}
    for span in ONE_HOLE_SPANS
)


@dataclass(frozen=True)
class SymbolHole:
    hole_id: str
    kind: str  # operator | ident | phrase | span
    start: int
    end: int
    original: str
    n_tokens: int = 1


def find_symbol_holes(tactics: str, *, max_holes: int = 24) -> list[SymbolHole]:
    """Mask operators first, then leftover identifiers that are not PCA structure."""

    holes: list[SymbolHole] = []
    occupied: list[tuple[int, int]] = []

    def free(start: int, end: int) -> bool:
        return all(end <= a or start >= b for a, b in occupied)

    for phrase, _alt in PHRASE_ALTS:
        if len(holes) >= max_holes:
            break
        start = 0
        while True:
            found = tactics.find(phrase, start)
            if found < 0:
                break
            end = found + len(phrase)
            if free(found, end):
                holes.append(
                    SymbolHole(
                        hole_id=f"SYM_{len(holes)}",
                        kind="phrase",
                        start=found,
                        end=end,
                        original=phrase,
                    )
                )
                occupied.append((found, end))
            start = found + 1
            if len(holes) >= max_holes:
                break

    for op in OPERATORS:
        if len(holes) >= max_holes:
            break
        start = 0
        while True:
            found = tactics.find(op, start)
            if found < 0:
                break
            end = found + len(op)
            if free(found, end):
                holes.append(
                    SymbolHole(
                        hole_id=f"SYM_{len(holes)}",
                        kind="operator",
                        start=found,
                        end=end,
                        original=op,
                    )
                )
                occupied.append((found, end))
            start = found + 1
            if len(holes) >= max_holes:
                break

    for match in lra_loop._TOKEN.finditer(tactics):
        if len(holes) >= max_holes:
            break
        token = match.group(0)
        if not re.match(r"[A-Za-z][A-Za-z0-9_']*$", token):
            continue
        if token in STRUCTURE or token in LEAN_TACTICS:
            continue
        start, end = match.span()
        line_start = tactics.rfind("\n", 0, start) + 1
        line = tactics[line_start : tactics.find("\n", start)]
        stripped = line.lstrip()
        if any(stripped.startswith(prefix) for prefix in PCA_KEEP_PREFIXES):
            continue
        if not free(start, end):
            continue
        holes.append(
            SymbolHole(
                hole_id=f"SYM_{len(holes)}",
                kind="ident",
                start=start,
                end=end,
                original=token,
            )
        )
        occupied.append((start, end))
    holes.sort(key=lambda hole: hole.start)
    return holes[:max_holes]


def is_pca_line(tactics: str, pos: int) -> bool:
    line_start = tactics.rfind("\n", 0, pos) + 1
    line_end = tactics.find("\n", pos)
    if line_end < 0:
        line_end = len(tactics)
    stripped = tactics[line_start:line_end].lstrip()
    if any(stripped.startswith(prefix) for prefix in PCA_KEEP_PREFIXES):
        return True
    return stripped in {"·", "."}


def cfg_schedule_for_score(score: Any, *, one_hole: bool = False) -> dict[str, Any]:
    """Map a TypeSafe Score (0..len-1, may be fractional) onto a mask schedule."""

    table = ONE_HOLE_SCHEDULES if one_hole else CFG_SCHEDULES
    try:
        value = float(score)
    except (TypeError, ValueError):
        value = 0.0
    index = int(round(value))
    index = max(0, min(len(table) - 1, index))
    return dict(table[index])


def _rehole(hole: SymbolHole, index: int) -> SymbolHole:
    return SymbolHole(
        hole_id=f"SYM_{index}",
        kind=hole.kind,
        start=hole.start,
        end=hole.end,
        original=hole.original,
        n_tokens=hole.n_tokens,
    )


def all_span_windows(tactics: str, span: int, *, stride: Optional[int] = None) -> list[SymbolHole]:
    """Token windows of ``span``. Default stride=span (tile). stride=1 overlaps."""

    span = max(1, int(span))
    step = span if stride is None else max(1, int(stride))
    tokens = list(lra_loop._TOKEN.finditer(tactics))
    windows: list[SymbolHole] = []
    index = 0
    while index < len(tokens):
        if is_pca_line(tactics, tokens[index].start()):
            index += 1
            continue
        group = []
        cursor = index
        while cursor < len(tokens) and len(group) < span:
            if is_pca_line(tactics, tokens[cursor].start()):
                break
            group.append(tokens[cursor])
            cursor += 1
        if len(group) == span:
            start, end = group[0].start(), group[-1].end()
            original = tactics[start:end]
            windows.append(
                SymbolHole(
                    hole_id=f"SYM_{len(windows)}",
                    kind="span",
                    start=start,
                    end=end,
                    original=original,
                    n_tokens=span,
                )
            )
            index += step
        else:
            index += 1
    return windows


def schedule_holes(tactics: str, *, n_masks: int, span: int) -> list[SymbolHole]:
    """Non-overlapping token windows of ``span``, skipping PCA control-flow lines."""

    n_masks = max(1, int(n_masks))
    windows = all_span_windows(tactics, span)
    if not windows:
        fallback = find_symbol_holes(tactics, max_holes=n_masks)
        return [_rehole(hole, i) for i, hole in enumerate(fallback[:n_masks])]
    if len(windows) <= n_masks:
        return [_rehole(hole, i) for i, hole in enumerate(windows)]
    step = len(windows) / float(n_masks)
    picked: list[SymbolHole] = []
    occupied: list[tuple[int, int]] = []
    for i in range(n_masks):
        window = windows[min(len(windows) - 1, int(i * step))]
        if any(window.end > a and window.start < b for a, b in occupied):
            continue
        occupied.append((window.start, window.end))
        picked.append(window)
    if not picked:
        picked = windows[:n_masks]
    return [_rehole(hole, i) for i, hole in enumerate(picked)]


def _window_priority(hole: SymbolHole) -> int:
    score = 0
    for src, _dst in PHRASE_ALTS:
        if src in hole.original:
            score += 10 + len(src)
    for op in OPERATORS:
        if op in hole.original:
            score += 3
    return score


def prefer_one_holes(tactics: str, span: int, *, max_pos: int = 2) -> list[SymbolHole]:
    """One hole of ``span`` tokens, preferring phrase/operator-aligned windows."""

    windows = all_span_windows(tactics, span, stride=1)
    if not windows:
        return schedule_holes(tactics, n_masks=1, span=span)
    ranked = sorted(windows, key=lambda hole: (-_window_priority(hole), hole.start))
    picked: list[SymbolHole] = []
    occupied: list[tuple[int, int]] = []
    for window in ranked:
        if any(window.end > start and window.start < end for start, end in occupied):
            continue
        occupied.append((window.start, window.end))
        picked.append(window)
        if len(picked) >= max(1, int(max_pos)):
            break
    return [_rehole(hole, 0) for hole in picked]


def one_hole_shots(*, span: int, n_shots: int = 6) -> list[dict[str, Any]]:
    """Single-hole few-shot fills whose original length is close to ``span``."""

    scored: list[tuple[int, int, str, str]] = []
    for src, dst in PHRASE_ALTS:
        n_tok = lra_loop.token_count(src)
        scored.append((abs(n_tok - int(span)), n_tok, src, dst))
    scored.sort()
    shots: list[dict[str, Any]] = []
    for _dist, n_tok, src, dst in scored:
        shots.append(
            {
                "note": f"one-hole span~{n_tok}: {src} -> {dst}",
                "skeleton": "    <<<SYM_0 kind=span>>>",
                "fills": {"SYM_0": dst},
                "holes": [{"id": "SYM_0", "kind": "span", "original": src, "fill": dst}],
                "n_holes": 1,
            }
        )
        if len(shots) >= n_shots:
            break
    if int(span) <= 2:
        for op, alts in OPERATOR_ALTS.items():
            if len(shots) >= n_shots:
                break
            fill = alts[0] if alts else ""
            if fill == op:
                continue
            shown = repr(fill) if fill else "drop"
            shots.append(
                {
                    "note": f"one-hole operator {op!r} -> {shown}",
                    "skeleton": "    <<<SYM_0 kind=operator>>>",
                    "fills": {"SYM_0": fill},
                    "holes": [{"id": "SYM_0", "kind": "operator", "original": op, "fill": fill}],
                    "n_holes": 1,
                }
            )
    return shots[:n_shots]


def one_hole_closed_rows(tactics: str, *, max_pos: int = 2) -> list[dict[str, Any]]:
    """Closed-vocab fill of one hole per span, a few phrase-aligned positions."""

    rows: list[dict[str, Any]] = []
    for span in ONE_HOLE_SPANS:
        for index, hole in enumerate(prefer_one_holes(tactics, span, max_pos=max_pos)):
            row = closed_multihole(tactics, [hole], schedule_id=f"span{span}_p{index}")
            if not row:
                continue
            row["span"] = span
            row["n_masks"] = 1
            row["n_shots"] = 6
            row["cfg_scale"] = 1.5
            row["original"] = hole.original
            rows.append(row)
    return rows


def kernel_one_hole_rows(tactics: str) -> list[dict[str, Any]]:
    """One catalog kernel per candidate: a single aligned span of varying length."""

    try:
        import inits_updates_shorten as lra_ius
    except Exception:
        return []
    current_tok = lra_loop.token_count(tactics)
    rows: list[dict[str, Any]] = []
    for item in lra_ius.propose(tactics):
        body = str(item.get("tactics") or "").strip("\n")
        tok = lra_loop.token_count(body)
        if not body or tok >= current_tok:
            continue
        cut = current_tok - tok
        span = 6
        for option in ONE_HOLE_SPANS:
            if cut <= option:
                span = option
                break
        rows.append(
            {
                "kind": f"kernel_{item['kind']}",
                "hole_id": str(item["kind"]),
                "hole_kind": "span",
                "original": str(item.get("note") or item["kind"]),
                "fill": str(item["kind"]),
                "tactics": body,
                "token_count": tok,
                "generator": "closed_lean_vocab",
                "llm": "off",
                "n_masks": 1,
                "n_shots": 6,
                "span": span,
                "cfg_scale": 1.5,
                "schedule_id": f"kernel_{item['kind']}",
                "family": item.get("family"),
            }
        )
    return rows


def catalog_shots(tactics: str, *, n_shots: int = 4) -> list[dict[str, Any]]:
    """Few-shot multi-hole fills from the cataloged 268→139 phrase cuts."""

    present = [(src, dst) for src, dst in PHRASE_ALTS if src in tactics]
    pool = present or list(PHRASE_ALTS)
    shots: list[dict[str, Any]] = []
    if len(pool) >= 2:
        pairs = pool[:3]
        items: list[tuple[int, int, int, str, str]] = []
        used: list[tuple[int, int]] = []
        for i, (src, dst) in enumerate(pairs):
            found = tactics.find(src) if src in tactics else -1
            if found < 0:
                excerpt = f"    {src}"
                items.append((0, len(excerpt), i, src, dst))
                continue
            end = found + len(src)
            if any(end > a and found < b for a, b in used):
                continue
            used.append((found, end))
            items.append((found, end, i, src, dst))
        in_script = [item for item in items if item[3] in tactics]
        if len(in_script) >= 2:
            skeleton = tactics
            fills: dict[str, str] = {}
            holes: list[dict[str, Any]] = []
            spans = [(start, end) for start, end, _i, _src, _dst in in_script]
            for start, end, i, src, dst in sorted(in_script, key=lambda row: row[0], reverse=True):
                hid = f"SYM_{i}"
                skeleton = skeleton[:start] + f"<<<{hid} kind=phrase>>>" + skeleton[end:]
                fills[hid] = dst
                holes.append({"id": hid, "kind": "phrase", "original": src, "fill": dst})
            lo = max(0, min(span[0] for span in spans) - 80)
            hi = min(len(skeleton), max(span[1] for span in spans) + 80 + 40)
            shots.append(
                {
                    "note": "multi-hole phrase fills from the 268→139 catalog",
                    "skeleton": skeleton[lo:hi],
                    "fills": fills,
                    "holes": list(reversed(holes)),
                    "n_holes": len(holes),
                }
            )
    for src, dst in pool:
        if len(shots) >= n_shots:
            break
        shots.append(
            {
                "note": f"{src} -> {dst}",
                "skeleton": f"    <<<SYM_0 kind=phrase>>>",
                "fills": {"SYM_0": dst},
                "holes": [{"id": "SYM_0", "kind": "phrase", "original": src, "fill": dst}],
                "n_holes": 1,
            }
        )
    return shots[:n_shots]


def few_shot_prompt(
    record: Mapping[str, Any],
    skeleton: str,
    holes: Sequence[SymbolHole],
    shots: Sequence[Mapping[str, Any]],
) -> str:
    blocks = []
    for index, shot in enumerate(shots, 1):
        fill_lines = []
        for hole in shot.get("holes") or []:
            hid = hole.get("id") or hole.get("hole_id")
            kind = hole.get("kind") or "phrase"
            fill_lines.append(f"<<<{hid} kind={kind}>>>\n{hole.get('fill')}\n")
        skel = str(shot.get("skeleton") or "")
        if len(skel) > 1200:
            skel = skel[:600] + "\n...\n" + skel[-400:]
        blocks.append(
            f"EXAMPLE {index} ({shot.get('note')}): {shot.get('n_holes')} holes, lake-valid shorter fill.\n"
            f"SKELETON:\n{skel}\n"
            f"FILLS:\n{''.join(fill_lines)}"
        )
    docs = []
    for hole in holes:
        docs.append(
            f"{hole.hole_id} kind={hole.kind} n_tokens={hole.n_tokens} ORIGINAL={hole.original!r}\n"
        )
    return (
        "Lean 4 tactic multi-hole fill. Each <<<SYM_i kind=...>>> is a masked span. "
        "Fill with a SHORTER Lean operator/symbol/phrase (constructor, intro, .update_some, "
        "all_goals simp_all, UpdateStatesDefined Hups, assumption, or empty to drop). "
        "Keep induction and every · / case arm. No sorry, no theorem, no open.\n\n"
        + "\n".join(blocks)
        + f"\nTARGET: {record.get('name')}\n"
        f"SKELETON:\n{skeleton}\n\n"
        f"HOLES:\n{''.join(docs)}\n"
        "Reply as:\n<<<SYM_0 kind=...>>>\n<fill>\n<<<SYM_1 kind=...>>>\n<fill>\n"
    )


def script_idents(tactics: str) -> list[str]:
    found: list[str] = []
    seen: set[str] = set()
    for match in lra_loop._TOKEN.finditer(tactics):
        token = match.group(0)
        if re.match(r"[A-Za-z][A-Za-z0-9_']*$", token) and token not in seen:
            seen.add(token)
            found.append(token)
    return found


def closed_fills(hole: SymbolHole, tactics: str) -> list[str]:
    """Lean-language fills. No model. Prefer strictly shorter replacements."""

    fills: list[str] = [hole.original]
    if hole.kind == "phrase":
        for src, dst in PHRASE_ALTS:
            if src == hole.original:
                fills.append(dst)
    elif hole.kind == "operator":
        fills.extend(OPERATOR_ALTS.get(hole.original, ()))
    elif hole.kind == "span":
        for src, dst in PHRASE_ALTS:
            if src == dst:
                continue
            if src in hole.original:
                if src == "apply UpdateStates.update_some" or (
                    src.endswith("update_some") and "apply " in hole.original
                ):
                    fills.append(hole.original.replace(src, "refine .update_some", 1))
                else:
                    fills.append(hole.original.replace(src, dst, 1))
        for op, alts in OPERATOR_ALTS.items():
            if op in hole.original:
                for alt in alts:
                    fills.append(hole.original.replace(op, alt, 1))
        tokens = list(lra_loop._TOKEN.finditer(hole.original))
        if len(tokens) >= 2:
            fills.append(hole.original[: tokens[-1].start()].rstrip())
    else:
        fills.extend(["this", "assumption", "trivial", "rfl", "constructor", "simp_all"])
        for ident in script_idents(tactics):
            if ident != hole.original and len(ident) <= len(hole.original):
                fills.append(ident)
                if len(fills) >= 8:
                    break
    out: list[str] = []
    seen: set[str] = set()
    for fill in fills:
        if fill not in seen:
            seen.add(fill)
            out.append(fill)
    return out[:8]


def mask_skeleton(tactics: str, holes: Sequence[SymbolHole]) -> str:
    out = tactics
    for hole in sorted(holes, key=lambda item: item.start, reverse=True):
        out = out[: hole.start] + f"<<<{hole.hole_id} kind={hole.kind}>>>" + out[hole.end :]
    return out


def apply_fill(tactics: str, hole: SymbolHole, fill: str) -> str:
    return tactics[: hole.start] + fill + tactics[hole.end :]


def closed_candidates(
    tactics: str, *, max_candidates: int = 32, include_replay: bool = True
) -> list[dict[str, Any]]:
    """One-hole closed-vocab edits that are strictly shorter."""

    holes = find_symbol_holes(tactics)
    current_tok = lra_loop.token_count(tactics)
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for hole in holes:
        for fill in closed_fills(hole, tactics):
            if fill == hole.original:
                continue
            body = apply_fill(tactics, hole, fill).strip("\n")
            tok = lra_loop.token_count(body)
            if tok >= current_tok or body in seen:
                continue
            seen.add(body)
            rows.append(
                {
                    "kind": f"{hole.hole_id}_{hole.kind}_{fill[:24] or 'drop'}",
                    "hole_id": hole.hole_id,
                    "hole_kind": hole.kind,
                    "original": hole.original,
                    "fill": fill,
                    "tactics": body,
                    "token_count": tok,
                    "generator": "closed_lean_vocab",
                    "llm": "off",
                }
            )
            if len(rows) >= max_candidates:
                break
    if include_replay:
        try:
            import inits_updates_shorten as lra_ius

            replayed = lra_ius.replay(tactics).strip("\n")
            tok = lra_loop.token_count(replayed)
            if replayed not in seen and tok < current_tok:
                rows.insert(
                    0,
                    {
                        "kind": "inits_replay",
                        "hole_id": "replay",
                        "hole_kind": "phrase",
                        "original": "full-script",
                        "fill": "268→139 kernel sequence",
                        "tactics": replayed,
                        "token_count": tok,
                        "generator": "closed_lean_vocab",
                        "llm": "off",
                    },
                )
        except Exception:
            pass
    return rows[:max_candidates]


def closed_multihole(tactics: str, holes: Sequence[SymbolHole], *, schedule_id: str = "cfg") -> Optional[dict[str, Any]]:
    """Apply one shorter closed fill at every selected span together."""

    if not holes:
        return None
    body = tactics
    fills: dict[str, str] = {}
    for hole in sorted(holes, key=lambda item: item.start, reverse=True):
        alts = [fill for fill in closed_fills(hole, tactics) if fill != hole.original]
        if not alts:
            continue
        fill = min(alts, key=lambda text: (lra_loop.token_count(text), len(text)))
        body = body[: hole.start] + fill + body[hole.end :]
        fills[hole.hole_id] = fill
    body = body.strip("\n")
    tok = lra_loop.token_count(body)
    if not fills or tok >= lra_loop.token_count(tactics):
        return None
    return {
        "kind": f"sweep_{schedule_id}_closed",
        "hole_id": schedule_id,
        "hole_kind": "span",
        "original": ",".join(hole.original[:24] for hole in holes),
        "fill": ",".join(f"{hid}->{val[:16] or 'drop'}" for hid, val in fills.items()),
        "tactics": body,
        "token_count": tok,
        "generator": "closed_lean_vocab",
        "llm": "off",
        "n_masks": len(holes),
        "fills": fills,
        "schedule_id": schedule_id,
    }


def parse_leanstral_fills(text: str, holes: Sequence[SymbolHole]) -> dict[str, str]:
    fills: dict[str, str] = {}
    for hole in holes:
        pattern = re.compile(
            rf"<<<{re.escape(hole.hole_id)}(?: kind={re.escape(hole.kind)})?>>>\s*(.*?)(?=<<<SYM_|\Z)",
            re.S,
        )
        match = pattern.search(text)
        if match:
            fills[hole.hole_id] = match.group(1).strip()
    return fills


def leanstral_prompt(
    record: Mapping[str, Any],
    skeleton: str,
    holes: Sequence[SymbolHole],
    shots: Sequence[Mapping[str, Any]] = (),
) -> str:
    if shots:
        return few_shot_prompt(record, skeleton, holes, shots)
    docs = []
    for hole in holes[:8]:
        docs.append(f"{hole.hole_id} kind={hole.kind} ORIGINAL={hole.original!r}\n")
    return (
        "Lean 4 tactic hole-fill. Each <<<SYM_i kind=...>>> is one operator or symbol. "
        "Fill with a SHORTER Lean operator/symbol from the language (constructor, simp_all, $, "
        "‹_›, all_goals, intro, .update_some, a hyp already in the proof). "
        "Keep induction and every · / case arm. No sorry, no theorem, no open.\n\n"
        f"Problem: {record.get('name')}\n"
        f"SKELETON:\n{skeleton}\n\n"
        f"HOLES:\n{''.join(docs)}\n"
        "Reply as:\n<<<SYM_0 kind=...>>>\n<fill>\n<<<SYM_1 kind=...>>>\n<fill>\n"
    )


def leanstral_candidates(
    record: Mapping[str, Any],
    tactics: str,
    holes: Sequence[SymbolHole],
    *,
    ledger: Optional[Any] = None,
    shots: Sequence[Mapping[str, Any]] = (),
    schedule_id: str = "leanstral",
    n_shots: int = 0,
) -> list[dict[str, Any]]:
    import track1_mistral_leanstral as lra_mistral

    lra_mistral.load_keyfiles()
    if not holes:
        holes = [hole for hole in find_symbol_holes(tactics) if hole.kind in ("operator", "phrase")][:8]
    holes = list(holes)[:8]
    if not holes:
        return []
    use_shots = list(shots)[: max(0, int(n_shots))]
    if not use_shots and n_shots:
        use_shots = catalog_shots(tactics, n_shots=n_shots)
    skeleton = mask_skeleton(tactics, holes)
    prompt = leanstral_prompt(record, skeleton, holes, use_shots)
    raw = lra_mistral.chat_completions(prompt, max_tokens=600, temperature=0.3, n=1)
    text = str(raw.get("text") or "")
    if not text:
        nested = ((raw.get("choices") or [{}])[0] if isinstance(raw.get("choices"), list) else {})
        text = str(((nested.get("message") or {}) if isinstance(nested, dict) else {}).get("content") or "")
    if ledger is not None:
        usage = dict(raw.get("usage") or {})
        inn = int(
            raw.get("input_tokens")
            or usage.get("prompt_tokens")
            or usage.get("input_tokens")
            or 200
        )
        out = int(
            raw.get("output_tokens")
            or usage.get("completion_tokens")
            or usage.get("output_tokens")
            or 0
        )
        ledger.record(
            "mistral",
            input_tokens=inn,
            output_tokens=out,
            model=str(raw.get("model") or lra_mistral.REQUESTED_MODEL),
        )
    fills = parse_leanstral_fills(text, holes)
    if not fills:
        extracted = lra_loop.extract_generated_tactics(text) if text else ""
        if extracted and "<<<SYM_" not in extracted and "<<<" not in extracted:
            tok = lra_loop.token_count(extracted.strip("\n"))
            if tok < lra_loop.token_count(tactics):
                return [
                    {
                        "kind": f"leanstral_{schedule_id}_fullblock",
                        "tactics": extracted.strip("\n"),
                        "token_count": tok,
                        "generator": "labs_leanstral",
                        "llm": "on",
                        "raw_head": text[:240],
                        "n_shots": len(use_shots),
                        "n_masks": len(holes),
                        "schedule_id": schedule_id,
                        "few_shot": bool(use_shots),
                    }
                ]
        return [
            {
                "kind": f"leanstral_{schedule_id}_unparsed",
                "generator": "labs_leanstral",
                "llm": "on",
                "raw_head": text[:240],
                "n_shots": len(use_shots),
                "schedule_id": schedule_id,
                "few_shot": bool(use_shots),
            }
        ]
    body = tactics
    for hole in sorted(holes, key=lambda item: item.start, reverse=True):
        fill = fills.get(hole.hole_id)
        if fill is None:
            continue
        body = body[: hole.start] + fill + body[hole.end :]
    body = body.strip("\n")
    tok = lra_loop.token_count(body)
    if tok >= lra_loop.token_count(tactics) or "<<<" in body:
        return []
    return [
        {
            "kind": f"leanstral_{schedule_id}_shot{len(use_shots)}",
            "tactics": body,
            "token_count": tok,
            "generator": "labs_leanstral",
            "llm": "on",
            "fills": fills,
            "raw_head": text[:240],
            "n_shots": len(use_shots),
            "n_masks": len(holes),
            "schedule_id": schedule_id,
            "few_shot": bool(use_shots),
        }
    ]


def typesafe_rank(
    record: Mapping[str, Any],
    drafts: Sequence[Mapping[str, Any]],
    *,
    ledger: Optional[Any] = None,
) -> dict[str, Any]:
    if not drafts:
        return {"skipped": True, "reason": "no_drafts", "arena_score": None}
    lra_pca.load_keyfile()
    lra_pca.pin_typesafe_path()
    from ipfs_accelerate_py.typesafe_inference import Choice, Noul, Score, TypeSafeClient, typesafe_configured

    if not typesafe_configured():
        return {"skipped": True, "reason": "no_key", "arena_score": None}
    criteria = {
        str(item["kind"]): (
            f"{item.get('generator')}; sched={item.get('schedule_id')}; "
            f"shots={item.get('n_shots')}; masks={item.get('n_masks')}; "
            f"{item.get('original')!s} -> {item.get('fill')!s}; "
            f"{item.get('token_count')} tok"
        )[:180]
        for item in drafts[:16]
    }
    state = {
        "problem": record.get("name"),
        "goal": (
            "Rank masked-operator fills, including few-shot Leanstral multi-hole "
            "fills and closed-vocab CFG-schedule fills. Prefer the shortest "
            "candidate that still lake-compiles. Do not write Lean."
        ),
        "drafts": [
            {
                "id": item["kind"],
                "head": str(item.get("tactics") or "")[:220],
                "tokens": item.get("token_count"),
                "schedule_id": item.get("schedule_id"),
                "n_shots": item.get("n_shots"),
                "n_masks": item.get("n_masks"),
                "few_shot": item.get("few_shot"),
            }
            for item in drafts[:16]
        ],
    }
    questions: dict[str, Any] = {
        "best_fill": Choice(
            instructions=(
                "Which fill id is most likely to lake-compile AND use fewer tokens? "
                "Prefer constructor/$/all_goals/intro/.update_some and catalog "
                "few-shot multi-hole fills over dropping hyps. Do not write Lean."
            ),
            criteria=criteria,
        ),
        "cfg_mask": Score(
            instructions=(
                "How aggressively should the next denoise step mask this proof? "
                "Higher = more holes and longer token spans. Never mask induction "
                "or · / case arms. Do not write Lean."
            ),
            criteria=list(CFG_MASK_CRITERIA),
        ),
    }
    if any(item.get("llm") == "on" or item.get("few_shot") for item in drafts):
        questions["prefer_few_shot"] = Noul(
            instructions=(
                "Is a few-shot multi-hole Leanstral fill more likely to lake-compile "
                "AND cut tokens than the closed-vocab fills? true means the few-shot "
                "fill is the wrong bet."
            )
        )
    started = time.perf_counter()
    result = TypeSafeClient(timeout=45.0).system_one(state, questions)
    usage = dict(getattr(result, "usage", None) or {})
    if ledger is not None:
        inn = int(usage.get("input_tokens") or usage.get("prompt_tokens") or 200)
        out = int(usage.get("output_tokens") or usage.get("completion_tokens") or 0)
        ledger.record("jev", input_tokens=inn, output_tokens=out, model=lra_t1.JEV_MODEL_ID)
    best = (getattr(result, "choices", None) or {}).get("best_fill")
    cfg_answer = (getattr(result, "scores", None) or {}).get("cfg_mask")
    noul_answer = (getattr(result, "nouls", None) or {}).get("prefer_few_shot")
    cfg_score = getattr(cfg_answer, "score", None)
    return {
        "skipped": False,
        "best_fill": getattr(best, "choice", None),
        "confidence": getattr(best, "confidence", None),
        "probabilities": dict(getattr(best, "probabilities", None) or {}),
        "cfg_score": cfg_score,
        "cfg_schedule": cfg_schedule_for_score(cfg_score if cfg_score is not None else 0),
        "prefer_few_shot_noul": getattr(noul_answer, "noul", None),
        "usage": usage,
        "wall_ms": (time.perf_counter() - started) * 1000.0,
        "jev_generated_lean": False,
        "arena_score": None,
    }


def typesafe_cfg_score(
    record: Mapping[str, Any],
    tactics: str,
    *,
    ledger: Optional[Any] = None,
    one_hole: bool = False,
) -> dict[str, Any]:
    """Ask TypeSafe Score/Choice how many masks and how long they should be."""

    table = ONE_HOLE_SCHEDULES if one_hole else CFG_SCHEDULES
    rubric = ONE_HOLE_CRITERIA if one_hole else CFG_MASK_CRITERIA
    lra_pca.load_keyfile()
    lra_pca.pin_typesafe_path()
    from ipfs_accelerate_py.typesafe_inference import Choice, Score, TypeSafeClient, typesafe_configured

    if not typesafe_configured():
        return {"skipped": True, "reason": "no_key", "cfg_schedule": dict(table[0]), "one_hole": one_hole}
    eligible = {
        f"span_{span}": len(all_span_windows(tactics, span))
        for span in ONE_HOLE_SPANS
    }
    criteria = {
        str(item["id"]): (
            f"{item['n_masks']} hole(s) × {item['span']} tokens; "
            f"{item['n_shots']} few-shot; cfg_scale={item['cfg_scale']}; "
            f"eligible_span_{item['span']}={eligible.get(f'span_{item['span']}', 0)}"
        )
        for item in table
    }
    state = {
        "problem": record.get("name"),
        "tokens": lra_loop.token_count(tactics),
        "eligible_spans": eligible,
        "one_hole": one_hole,
        "goal": (
            "Pick a ONE-HOLE span length for discrete text diffusion. "
            "Higher CFG score means a longer masked span. Keep induction and · arms. "
            "Do not write Lean."
            if one_hole
            else (
                "Pick a mask schedule for discrete text diffusion. Higher CFG score "
                "means more/longer masks. Keep induction and · arms. Do not write Lean."
            )
        ),
        "head": tactics[:400],
    }
    started = time.perf_counter()
    result = TypeSafeClient(timeout=45.0).system_one(
        state,
        {
            "cfg_mask": Score(
                instructions=(
                    "How long should the single masked span be? Higher = more tokens "
                    "in that one hole. Stay off PCA induction/· / case. Do not write Lean."
                    if one_hole
                    else (
                        "How aggressively should we mask this Lean proof? Higher = more "
                        "holes and longer spans. Stay off PCA induction/· / case. Do not write Lean."
                    )
                ),
                criteria=list(rubric),
            ),
            "best_schedule": Choice(
                instructions=(
                    "Which one-hole span length should Leanstral / closed-vocab fill next? "
                    "Prefer a span that matches a remaining rewrite phrase. Do not write Lean."
                    if one_hole
                    else (
                        "Which mask schedule should Leanstral / closed-vocab fill next? "
                        "Prefer a schedule whose span length matches remaining rewrite "
                        "phrases. Do not write Lean."
                    )
                ),
                criteria=criteria,
            ),
        },
    )
    usage = dict(getattr(result, "usage", None) or {})
    if ledger is not None:
        inn = int(usage.get("input_tokens") or usage.get("prompt_tokens") or 200)
        out = int(usage.get("output_tokens") or usage.get("completion_tokens") or 0)
        ledger.record("jev", input_tokens=inn, output_tokens=out, model=lra_t1.JEV_MODEL_ID)
    cfg_answer = (getattr(result, "scores", None) or {}).get("cfg_mask")
    choice = (getattr(result, "choices", None) or {}).get("best_schedule")
    cfg_score = getattr(cfg_answer, "score", None)
    picked = getattr(choice, "choice", None)
    schedule = next((dict(item) for item in table if item["id"] == picked), None)
    if schedule is None:
        schedule = cfg_schedule_for_score(
            cfg_score if cfg_score is not None else 0, one_hole=one_hole
        )
    return {
        "skipped": False,
        "one_hole": one_hole,
        "cfg_score": cfg_score,
        "cfg_confidence": getattr(cfg_answer, "confidence", None),
        "best_schedule": picked,
        "schedule_probabilities": dict(getattr(choice, "probabilities", None) or {}),
        "cfg_schedule": schedule,
        "eligible_spans": eligible,
        "usage": usage,
        "wall_ms": (time.perf_counter() - started) * 1000.0,
        "jev_generated_lean": False,
        "arena_score": None,
    }


def pca_mca_ops(tactics: str) -> list[tuple[str, str, tuple[str, ...]]]:
    rows: list[tuple[str, str, tuple[str, ...]]] = []
    # Phrase/kernel fills only. Blind span windows on Cslib/CallElim break syntax.
    for item in closed_candidates(tactics, max_candidates=8, include_replay=True):
        kind = str(item.get("kind") or "")
        if item.get("hole_kind") == "phrase" or kind == "inits_replay":
            rows.append(
                (
                    "symbol_diffuse",
                    str(item["tactics"]),
                    ("symbol_diffuse", kind, "closed_vocab"),
                )
            )
    for item in kernel_one_hole_rows(tactics)[:8]:
        rows.append(
            (
                "symbol_diffuse",
                str(item["tactics"]),
                ("symbol_diffuse", str(item.get("kind") or "kernel"), "one_hole"),
            )
        )
    return rows


def self_check() -> dict[str, Any]:
    import inits_updates_shorten as lra_ius

    src = lra_ius.original_tactics()
    holes = find_symbol_holes(src)
    cands = closed_candidates(src)
    replay = lra_ius.replay(src)
    kinds = {item["kind"] for item in cands}
    has_ctor = any("constructor" in str(item.get("fill") or "") or "And.intro" in str(item.get("original") or "") for item in cands)
    has_dollar = any(item.get("original") == "$" or item.get("fill") == "$" for item in cands)
    shots = catalog_shots(src, n_shots=4)
    span_holes = schedule_holes(src, n_masks=4, span=3)
    multi = closed_multihole(src, span_holes, schedule_id="cfg2")
    oh_shots = one_hole_shots(span=3, n_shots=4)
    oh_windows = prefer_one_holes(src, 4, max_pos=3) + prefer_one_holes(src, 3, max_pos=3)
    oh_rows = one_hole_closed_rows(src, max_pos=1)
    prompt = few_shot_prompt({"name": lra_ius.PROBLEM}, mask_skeleton(src, span_holes), span_holes, shots)
    cfg0 = cfg_schedule_for_score(0)
    cfg4 = cfg_schedule_for_score(4)
    return {
        "ok": (
            len(holes) >= 3
            and len(cands) >= 3
            and lra_loop.token_count(replay) == 139
            and (has_ctor or has_dollar or any("intro" in str(item.get("fill") or "") for item in cands))
            and any(int(shot.get("n_holes") or 0) >= 2 for shot in shots)
            and "EXAMPLE" in prompt
            and "constructor" in prompt
            and len(span_holes) >= 1
            and cfg0["n_masks"] == 2
            and cfg4["span"] == 6
            and (multi is None or int(multi["token_count"]) < lra_loop.token_count(src))
            and oh_shots
            and all(int(shot.get("n_holes") or 0) == 1 for shot in oh_shots)
            and any(
                "And.intro" in hole.original or "intros Hin" in hole.original or ".update_some" in hole.original
                for hole in oh_windows
            )
            and any(int(row["token_count"]) < lra_loop.token_count(src) for row in oh_rows)
            and any(
                item["kind"].startswith("kernel_")
                for item in kernel_one_hole_rows(src)
            )
        ),
        "n_holes": len(holes),
        "n_closed_candidates": len(cands),
        "n_catalog_shots": len(shots),
        "n_span_holes": len(span_holes),
        "multi_hole_tokens": None if multi is None else multi["token_count"],
        "hole_kinds": sorted({hole.kind for hole in holes}),
        "sample_kinds": sorted(kinds)[:12],
        "llm": "off",
        "called_docker0": False,
        "arena_score": None,
        "replay_tokens": lra_loop.token_count(replay),
    }


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-check", action="store_true")
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--llm", choices=("off", "on"), default="off")
    parser.add_argument("--names", default="Core.InitsUpdatesComm")
    parser.add_argument("--timeout", type=float, default=180.0)
    parser.add_argument("--out", type=Path, default=OUT_DEFAULT)
    parser.add_argument("--lake-top", type=int, default=4)
    parser.add_argument("--rounds", type=int, default=1)
    parser.add_argument("--init-file", type=Path, default=None)
    parser.add_argument("--sweep", action="store_true", help="parameter sweep over CFG mask schedules")
    parser.add_argument("--few-shot", action="store_true", help="force few-shot Leanstral (default on when --llm on)")
    parser.add_argument("--no-few-shot", action="store_true", help="zero-shot Leanstral even if --llm on")
    parser.add_argument("--no-replay", action="store_true", help="omit the 268→139 kernel dump from candidates")
    parser.add_argument("--cfg-schedules", default="cfg0,cfg1,cfg2,cfg3,cfg4")
    parser.add_argument("--leanstral-top", type=int, default=2, help="max hosted Leanstral calls per round")
    parser.add_argument("--one-hole", action="store_true", help="one hole per step; vary span; multi-shot fills")
    parser.add_argument("--one-hole-spans", default="1,2,3,4,6", help="comma-separated token spans for --one-hole")
    args = parser.parse_args(argv)
    few_shot = (args.llm == "on" or args.few_shot) and not args.no_few_shot
    one_hole = bool(args.one_hole)
    if one_hole:
        span_wanted = []
        for part in str(args.one_hole_spans).split(","):
            part = part.strip()
            if part:
                span_wanted.append(int(part))
        grid = [dict(item) for item in ONE_HOLE_SCHEDULES if item["span"] in span_wanted] or [
            dict(item) for item in ONE_HOLE_SCHEDULES
        ]
    else:
        wanted_ids = [part.strip() for part in str(args.cfg_schedules).split(",") if part.strip()]
        grid = [dict(item) for item in CFG_SCHEDULES if item["id"] in wanted_ids] or [dict(item) for item in CFG_SCHEDULES]
    if args.self_check or not args.live:
        payload = self_check()
        print(json.dumps(payload, indent=2, sort_keys=True))
        if args.self_check and not args.live:
            return 0 if payload["ok"] else 1
        if not args.live:
            return 0 if payload["ok"] else 1
    import inits_updates_shorten as lra_ius

    _raw, digest, records = lra_splice.load_warmup_records()
    name = str(args.names).split(",")[0].strip()
    record = next(item for item in records if item.get("name") == name)
    import draft_fanout as lra_fan
    import mcmc_beam as lra_mcmc

    if args.init_file and Path(args.init_file).is_file():
        tactics = Path(args.init_file).read_text(encoding="utf-8").strip("\n")
    elif name == lra_ius.PROBLEM:
        tactics = lra_ius.original_tactics()
    else:
        tactics = lra_fan.tactic_block(record)
    ledger = lra_t1.ProblemLedger(
        name=f"{name}#symbol-diffuse",
        max_jev_calls=max(12, int(args.rounds) * 3 + 4),
        max_mistral_calls=max(6, int(args.rounds) * max(1, int(args.leanstral_top)) + 2),
    )
    clone = lra_kb.lra_cw.clone_dir(str(record["url"]), DEFAULT_STATE)
    dest = clone / lra_kb.lra_cw.source_relpath(record)
    restore = dest.read_bytes() if dest.is_file() else b""
    best = {
        "kind": "init",
        "token_count": lra_loop.token_count(tactics),
        "theorem_ok": True,
        "tactics": tactics,
    }
    lake_rows: list[dict[str, Any]] = []
    ranked_rows: list[dict[str, Any]] = []
    cfg_rows: list[dict[str, Any]] = []
    current = tactics
    ranked: dict[str, Any] = {}
    last_closed: list[dict[str, Any]] = []
    for round_i in range(max(1, int(args.rounds))):
        cfg = typesafe_cfg_score(record, current, ledger=ledger, one_hole=one_hole)
        cfg["round"] = round_i
        cfg_rows.append(cfg)
        picked = dict(cfg.get("cfg_schedule") or (grid[0] if grid else CFG_SCHEDULES[0]))
        schedules = list(grid) if (args.sweep or one_hole) else [picked]
        if not any(item["id"] == picked["id"] for item in schedules):
            schedules.insert(0, picked)
        candidates: list[dict[str, Any]] = []
        if not args.no_replay:
            for item in closed_candidates(current, max_candidates=4, include_replay=True):
                if item.get("kind") == "inits_replay":
                    candidates.append(item)
                    break
        phrase_rows = closed_candidates(current, max_candidates=8, include_replay=False)[:6]
        kernel_rows = kernel_one_hole_rows(current) if one_hole else []
        # Catalog one-step kernels, then phrase one-holes, so lake_top sees
        # drop_not_intro / fold_init / constructor before blind span windows.
        candidates.extend(kernel_rows)
        candidates.extend(phrase_rows)
        if one_hole:
            candidates.extend(one_hole_closed_rows(current, max_pos=2))
        else:
            for sched in schedules:
                span_holes = schedule_holes(current, n_masks=int(sched["n_masks"]), span=int(sched["span"]))
                row = closed_multihole(current, span_holes, schedule_id=str(sched["id"]))
                if row:
                    row["span"] = sched["span"]
                    row["n_shots"] = sched["n_shots"]
                    row["cfg_scale"] = sched["cfg_scale"]
                    candidates.append(row)
        if args.llm == "on":
            if one_hole:
                lean_schedules = [picked]
                for extra in schedules:
                    if extra["id"] == picked["id"]:
                        continue
                    lean_schedules.append(extra)
                    if len(lean_schedules) >= max(1, int(args.leanstral_top)):
                        break
                lean_schedules = lean_schedules[: max(1, int(args.leanstral_top))]
            else:
                lean_schedules = [picked]
                if args.sweep:
                    zero = next((item for item in schedules if int(item.get("n_shots") or 0) == 0), None)
                    if zero is not None and zero["id"] != picked["id"]:
                        lean_schedules.append(zero)
                lean_schedules = lean_schedules[: max(1, int(args.leanstral_top))]
            for sched in lean_schedules:
                span = int(sched["span"])
                if one_hole:
                    span_holes = prefer_one_holes(current, span, max_pos=1)
                    n_shots = int(sched["n_shots"] or 0) if few_shot else 0
                    shots = one_hole_shots(span=span, n_shots=n_shots) if n_shots else []
                else:
                    span_holes = schedule_holes(
                        current, n_masks=int(sched["n_masks"]), span=span
                    )
                    n_shots = int(sched["n_shots"] or 0) if few_shot else 0
                    shots = catalog_shots(current, n_shots=n_shots) if n_shots else []
                try:
                    rows = leanstral_candidates(
                        record,
                        current,
                        span_holes,
                        ledger=ledger,
                        shots=shots,
                        schedule_id=str(sched["id"]),
                        n_shots=n_shots,
                    )
                    candidates = rows + candidates
                except Exception as exc:  # noqa: BLE001
                    ranked_rows.append(
                        {
                            "round": round_i,
                            "leanstral_error": str(exc)[:300],
                            "schedule_id": sched["id"],
                        }
                    )
        last_closed = candidates
        if not candidates:
            ranked_rows.append({"round": round_i, "skipped": "no_candidates"})
            break
        ranked = typesafe_rank(record, candidates, ledger=ledger)
        ranked["round"] = round_i
        ranked_rows.append(ranked)
        order = [ranked.get("best_fill")] if ranked.get("best_fill") else []
        if one_hole:
            order.extend(item["kind"] for item in kernel_rows)
            order.extend(item["kind"] for item in phrase_rows)
        order.extend(item["kind"] for item in candidates)
        by_kind = {item["kind"]: item for item in candidates if "tactics" in item}
        accepted = None
        tried = 0
        seen_kind: set[str] = set()
        ok_hits: list[tuple[int, str, str]] = []
        for kind in order:
            if kind in seen_kind or kind not in by_kind:
                continue
            seen_kind.add(str(kind))
            body = str(by_kind[kind]["tactics"])
            compiled = lra_mcmc.compile_one(
                record, body, state_root=DEFAULT_STATE, timeout=args.timeout, restore=restore
            )
            row = {
                "round": round_i,
                "kind": kind,
                "ok": bool(compiled.get("theorem_ok")),
                "tokens": compiled.get("token_count"),
                "schedule_id": by_kind[kind].get("schedule_id"),
                "n_shots": by_kind[kind].get("n_shots"),
                "errors": (compiled.get("errors") or [])[:1],
            }
            lake_rows.append(row)
            tried += 1
            if row["ok"] and int(row["tokens"] or 999) < int(best["token_count"]):
                ok_hits.append((int(row["tokens"]), str(kind), body))
                if not (args.sweep or one_hole):
                    break
            if tried >= int(args.lake_top):
                break
        if ok_hits:
            ok_hits.sort(key=lambda item: item[0])
            tok, kind, body = ok_hits[0]
            best = {
                "kind": f"r{round_i}_{kind}",
                "token_count": tok,
                "theorem_ok": True,
                "tactics": body,
            }
            accepted = body
        if not accepted:
            ranked_rows.append({"round": round_i, "stopped": "no_shorter_lake_ok"})
            break
        current = accepted
    holes = find_symbol_holes(current)
    args.out.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema": "lra-symbol-diffuse/v1",
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "name": name,
        "llm": args.llm,
        "few_shot": few_shot,
        "one_hole": one_hole,
        "sweep": bool(args.sweep) or one_hole,
        "rounds": int(args.rounds),
        "n_holes": len(holes),
        "n_closed": len([item for item in last_closed if item.get("llm") == "off"]),
        "cfg": cfg_rows,
        "ranked": ranked,
        "ranked_rows": ranked_rows,
        "lake": lake_rows,
        "best": {k: best[k] for k in best if k != "tactics"},
        "source_tokens": lra_loop.token_count(tactics),
        "called_docker0": False,
        "official_track2": False,
        "arena_score": None,
        "warmup_jsonl_sha256": digest,
        "ledger": ledger.as_dict() if hasattr(ledger, "as_dict") else {"jev_calls": getattr(ledger, "jev_calls", 0)},
    }
    if best.get("tactics") and int(best["token_count"]) < lra_loop.token_count(tactics):
        (args.out / f"symbol-diffuse-best-{best['token_count']}.lean").write_text(str(best["tactics"]) + "\n")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = args.out / f"symbol-diffuse-{stamp}.json"
    text = json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n"
    path.write_text(text)
    (args.out / "symbol-diffuse-latest.json").write_text(text)
    print(json.dumps(payload, indent=2, sort_keys=True, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

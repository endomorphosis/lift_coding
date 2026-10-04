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
import sys
import time
from dataclasses import asdict, dataclass

from pathlib import Path
from typing import Any, Mapping, Optional, Sequence

HERE = Path(__file__).resolve().parent
PAPER_ROOT = HERE.parent
OUT_DEFAULT = PAPER_ROOT / "evidence" / "canaries"

if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
import _jevops_path  # noqa: E402,F401
import pca_mca_fanout as lra_pca  # noqa: E402
import run_warmup as lra_loop  # noqa: E402
import splice as lra_splice  # noqa: E402
import track1_keepbest as lra_kb  # noqa: E402
import track1_ledger as lra_t1  # noqa: E402

PR_ID = "PR-9f"
from jevops.catalogs import DEFAULT_TRACK1_STATE as DEFAULT_STATE
from jevops.catalogs import HARDWARE_CLASS_SPARK as HARDWARE_CLASS
from jevops.catalogs import MISTRAL_HARDWARE_CLASS as LEANSTRAL_HARDWARE
from jevops.catalogs import PROTOCOL
from jevops.tactics import SYM_HOLE as MARKER

# Longest-first so ‹_› / <;> / ?_ mask as one hole.
# Skip := / · — their closed alts are not strictly shorter.
from jevops.tactics import LEAN_TACTICS
from jevops.tactics import OPERATORS
from jevops.tactics import OPERATOR_ALTS
from jevops.tactics import PCA_KEEP_PREFIXES
from jevops.tactics import PHRASE_ALTS
from jevops.tactics import STRUCTURE
# Phrase/operator/tactic vocab lives in jevops.tactics.

from jevops.catalogs import CFG_MASK_CRITERIA
from jevops.catalogs import CFG_MULTI_CHOICE
from jevops.catalogs import CFG_MULTI_GOAL
from jevops.catalogs import CFG_MULTI_SCORE
from jevops.catalogs import CFG_ONE_HOLE_CHOICE
from jevops.catalogs import CFG_ONE_HOLE_GOAL
from jevops.catalogs import CFG_ONE_HOLE_SCORE
from jevops.catalogs import CFG_SCHEDULES
from jevops.catalogs import ONE_HOLE_CRITERIA
from jevops.catalogs import ONE_HOLE_SCHEDULES
from jevops.catalogs import ONE_HOLE_SPANS
from jevops.catalogs import RANK_FILL_BEST
from jevops.catalogs import RANK_FILL_CFG
from jevops.catalogs import RANK_FILL_FEW_SHOT
from jevops.catalogs import RANK_FILL_GOAL


@dataclass(frozen=True)
class SymbolHole:
    hole_id: str
    kind: str  # operator | ident | phrase | span
    start: int
    end: int
    original: str
    n_tokens: int = 1


def _as_row(item: SymbolHole) -> dict[str, Any]:
    return {
        "hole_id": item.hole_id,
        "kind": item.kind,
        "start": item.start,
        "end": item.end,
        "original": item.original,
        "n_tokens": item.n_tokens,
    }


def _from_row(row: Mapping[str, Any]) -> SymbolHole:
    from jevops.outer import drive_hole_from_row

    return drive_hole_from_row(row, cls=SymbolHole)


def find_symbol_holes(tactics: str, *, max_holes: int = 24) -> list[SymbolHole]:
    """Mask operators first, then leftover identifiers that are not PCA structure."""

    from jevops.mask import collect_literal_holes
    from jevops.tactics import ident_holes

    return collect_literal_holes(
        tactics,
        phrases=[src for src, _dst in PHRASE_ALTS],
        operators=OPERATORS,
        ident_fn=lambda text, occupied, max_holes, id_prefix: ident_holes(
            text,
            token_re=lra_loop._TOKEN,
            occupied=occupied,
            skip_tokens=tuple(STRUCTURE) + tuple(LEAN_TACTICS),
            pca_prefixes=PCA_KEEP_PREFIXES,
            max_holes=max_holes,
            id_prefix=id_prefix,
        ),
        from_row_fn=_from_row,
        rehole_fn=_rehole,
        max_holes=max_holes,
        id_prefix="SYM_",
    )


def is_pca_line(tactics: str, pos: int) -> bool:
    from jevops.tactics import is_pca_line as _fn

    return _fn(tactics, pos)


def cfg_schedule_for_score(score: Any, *, one_hole: bool = False) -> dict[str, Any]:
    """Map a TypeSafe Score (0..len-1, may be fractional) onto a mask schedule."""

    from jevops.mask import drive_score_schedule

    return drive_score_schedule(
        score,
        one_hole=one_hole,
        one_table=ONE_HOLE_SCHEDULES,
        multi_table=CFG_SCHEDULES,
    )


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

    from jevops.mask import drive_span_holes

    return drive_span_holes(
        tactics,
        span,
        stride=stride,
        tokens_fn=lambda text: list(lra_loop._TOKEN.finditer(text)),
        skip_fn=is_pca_line,
        from_row=_from_row,
    )


def schedule_holes(tactics: str, *, n_masks: int, span: int) -> list[SymbolHole]:
    """Non-overlapping token windows of ``span``, skipping PCA control-flow lines."""

    from jevops.mask import drive_schedule_holes

    return drive_schedule_holes(
        tactics,
        n_masks=n_masks,
        span=span,
        windows_fn=all_span_windows,
        holes_fn=lambda text, count: find_symbol_holes(text, max_holes=count),
        from_row=_from_row,
        rehole=_rehole,
        as_row=_as_row,
    )


def _window_priority(hole: SymbolHole) -> int:
    from jevops.outer import drive_hit_sum

    return drive_hit_sum(hole.original, ((PHRASE_ALTS, 10, True), (OPERATORS, 3, False)))


def prefer_one_holes(tactics: str, span: int, *, max_pos: int = 2) -> list[SymbolHole]:
    """One hole of ``span`` tokens, preferring phrase/operator-aligned windows."""

    from jevops.mask import drive_prefer_holes

    return drive_prefer_holes(
        tactics,
        span,
        max_pos=max_pos,
        windows_fn=lambda text, width: all_span_windows(text, width, stride=1),
        score_fn=lambda row: _window_priority(_from_row(row)),
        schedule_fn=lambda text, width: schedule_holes(text, n_masks=1, span=width),
        from_row=_from_row,
        rehole=_rehole,
        as_row=_as_row,
    )


def one_hole_shots(*, span: int, n_shots: int = 6) -> list[dict[str, Any]]:
    """Single-hole few-shot fills whose original length is close to ``span``."""

    from jevops.mask import one_hole_shots as _fn

    return _fn(
        phrase_alts=PHRASE_ALTS,
        operator_alts=OPERATOR_ALTS,
        span=span,
        n_shots=n_shots,
        token_fn=lra_loop.token_count,
    )


def one_hole_closed_rows(tactics: str, *, max_pos: int = 2) -> list[dict[str, Any]]:
    """Closed-vocab fill of one hole per span, a few phrase-aligned positions."""

    from jevops.mask import collect_one_hole_closed_rows

    return collect_one_hole_closed_rows(
        tactics,
        ONE_HOLE_SPANS,
        prefer_fn=lambda text, span: prefer_one_holes(text, span, max_pos=max_pos),
        closed_fn=closed_multihole,
    )


def kernel_one_hole_rows(tactics: str) -> list[dict[str, Any]]:
    """One catalog kernel per candidate: a single aligned span of varying length."""

    from jevops.mask import kernel_one_hole_rows as _fn
    from jevops.outer import call_or_empty

    def _import() -> Any:
        import inits_updates_shorten as lra_ius

        return lra_ius

    return call_or_empty(
        _import,
        lambda mod: _fn(
            tactics,
            propose_fn=mod.propose,
            token_fn=lra_loop.token_count,
            spans=ONE_HOLE_SPANS,
        ),
    )


def catalog_shots(tactics: str, *, n_shots: int = 4) -> list[dict[str, Any]]:
    """Few-shot multi-hole fills from the cataloged 268→139 phrase cuts."""

    from jevops.mask import catalog_shots as _fn
    from jevops.outer import head_seq

    return _fn(
        tactics,
        phrase_alts=PHRASE_ALTS,
        n_shots=n_shots,
        head_fn=head_seq,
    )


def few_shot_prompt(
    record: Mapping[str, Any],
    skeleton: str,
    holes: Sequence[SymbolHole],
    shots: Sequence[Mapping[str, Any]],
) -> str:
    from jevops.mask import shot_fill_prompt

    return shot_fill_prompt(
        record,
        skeleton,
        holes,
        shots,
        preamble=(
            "Lean 4 tactic multi-hole fill. Each <<<SYM_i kind=...>>> is a masked span. "
            "Fill with a SHORTER Lean operator/symbol/phrase (constructor, intro, .update_some, "
            "all_goals simp_all, UpdateStatesDefined Hups, assumption, or empty to drop). "
            "Keep induction and every · / case arm. No sorry, no theorem, no open.\n\n"
        ),
        reply="Reply as:\n<<<SYM_0 kind=...>>>\n<fill>\n<<<SYM_1 kind=...>>>\n<fill>\n",
    )


def script_idents(tactics: str) -> list[str]:
    from jevops.tactics import script_idents as _fn

    return _fn(tactics, token_re=lra_loop._TOKEN)


def closed_fills(hole: SymbolHole, tactics: str) -> list[str]:
    """Lean-language fills. No model. Prefer strictly shorter replacements."""

    from jevops.tactics import drive_hole_fills

    return drive_hole_fills(
        hole,
        tactics,
        as_row=_as_row,
        phrase_alts=PHRASE_ALTS,
        operator_alts=OPERATOR_ALTS,
        token_re=lra_loop._TOKEN,
    )


def mask_skeleton(tactics: str, holes: Sequence[SymbolHole]) -> str:
    from jevops.mask import drive_mask_rows

    return drive_mask_rows(tactics, holes, as_row=_as_row)


def apply_fill(tactics: str, hole: SymbolHole, fill: str) -> str:
    from jevops.mask import drive_apply_row

    return drive_apply_row(tactics, hole, fill, as_row=_as_row)


def closed_candidates(
    tactics: str, *, max_candidates: int = 32, include_replay: bool = True
) -> list[dict[str, Any]]:
    """One-hole closed-vocab edits that are strictly shorter."""

    from jevops.mask import drive_closed_candidates

    def _replay() -> Any:
        import inits_updates_shorten as lra_ius

        return lra_ius.replay

    return drive_closed_candidates(
        tactics,
        include_replay=include_replay,
        replay_loader=_replay,
        holes_fn=find_symbol_holes,
        fills_fn=lambda item, text: closed_fills(_from_row(item), text),
        token_fn=lra_loop.token_count,
        as_row_fn=_as_row,
        max_candidates=max_candidates,
        generator="closed_lean_vocab",
    )


def closed_multihole(tactics: str, holes: Sequence[SymbolHole], *, schedule_id: str = "cfg") -> Optional[dict[str, Any]]:
    """Apply one shorter closed fill at every selected span together."""

    from jevops.mask import closed_multihole_row

    return closed_multihole_row(
        tactics,
        holes,
        schedule_id=schedule_id,
        fills_fn=lambda item, text: closed_fills(_from_row(item), text),
        token_fn=lra_loop.token_count,
        as_row_fn=_as_row,
    )


def parse_leanstral_fills(text: str, holes: Sequence[SymbolHole]) -> dict[str, str]:
    from jevops.mask import parse_marked_fills

    return parse_marked_fills(text, holes, attr="kind")


def leanstral_prompt(
    record: Mapping[str, Any],
    skeleton: str,
    holes: Sequence[SymbolHole],
    shots: Sequence[Mapping[str, Any]] = (),
) -> str:
    from jevops.outer import drive_prompt_or_plain

    return drive_prompt_or_plain(
        shots,
        shot_fn=lambda: few_shot_prompt(record, skeleton, holes, shots),
        plain_fn=lambda: _leanstral_plain_prompt(record, skeleton, holes),
    )


def _leanstral_plain_prompt(
    record: Mapping[str, Any],
    skeleton: str,
    holes: Sequence[SymbolHole],
) -> str:
    from jevops.lean import plain_hole_prompt

    return plain_hole_prompt(record, skeleton, holes)


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
    from jevops.mask import drive_leanstral_fills

    return drive_leanstral_fills(
        record,
        tactics,
        holes,
        ledger=ledger,
        shots=shots,
        schedule_id=schedule_id,
        n_shots=n_shots,
        load_keys_fn=lra_mistral.load_keyfiles,
        find_fn=find_symbol_holes,
        catalog_fn=catalog_shots,
        skeleton_fn=mask_skeleton,
        prompt_fn=leanstral_prompt,
        chat_fn=lra_mistral.chat_completions,
        parse_fn=parse_leanstral_fills,
        token_fn=lra_loop.token_count,
        extract_fn=lra_loop.extract_generated_tactics,
        default_model=lra_mistral.REQUESTED_MODEL,
    )


def typesafe_rank(
    record: Mapping[str, Any],
    drafts: Sequence[Mapping[str, Any]],
    *,
    ledger: Optional[Any] = None,
) -> dict[str, Any]:
    from jevops.jev import drive_fill_rank

    return drive_fill_rank(
        record,
        drafts,
        ledger=ledger,
        setup=(lra_pca.load_keyfile, lra_pca.pin_typesafe_path),
        goal=RANK_FILL_GOAL,
        best_instructions=RANK_FILL_BEST,
        cfg_instructions=RANK_FILL_CFG,
        few_shot_instructions=RANK_FILL_FEW_SHOT,
        cfg_criteria=CFG_MASK_CRITERIA,
        schedule_fn=cfg_schedule_for_score,
        model_id=lra_t1.JEV_MODEL_ID,
    )


def typesafe_cfg_score(
    record: Mapping[str, Any],
    tactics: str,
    *,
    ledger: Optional[Any] = None,
    one_hole: bool = False,
) -> dict[str, Any]:
    """Ask TypeSafe Score/Choice how many masks and how long they should be."""

    from jevops.jev import drive_cfg_score

    return drive_cfg_score(
        record,
        tactics,
        ledger=ledger,
        one_hole=one_hole,
        setup=(lra_pca.load_keyfile, lra_pca.pin_typesafe_path),
        one_schedules=ONE_HOLE_SCHEDULES,
        multi_schedules=CFG_SCHEDULES,
        one_criteria=ONE_HOLE_CRITERIA,
        multi_criteria=CFG_MASK_CRITERIA,
        spans=ONE_HOLE_SPANS,
        windows_fn=all_span_windows,
        token_fn=lra_loop.token_count,
        one_goal=CFG_ONE_HOLE_GOAL,
        multi_goal=CFG_MULTI_GOAL,
        one_score=CFG_ONE_HOLE_SCORE,
        multi_score=CFG_MULTI_SCORE,
        one_choice=CFG_ONE_HOLE_CHOICE,
        multi_choice=CFG_MULTI_CHOICE,
        schedule_fn=cfg_schedule_for_score,
        model_id=lra_t1.JEV_MODEL_ID,
    )


def pca_mca_ops(tactics: str) -> list[tuple[str, str, tuple[str, ...]]]:
    from jevops.tactics import drive_symbol_ops

    return drive_symbol_ops(
        tactics,
        closed_fn=lambda text: closed_candidates(text, max_candidates=8, include_replay=True),
        rows_fn=kernel_one_hole_rows,
        family="symbol_diffuse",
        cap=8,
    )


def self_check() -> dict[str, Any]:
    import inits_updates_shorten as lra_ius
    from jevops.outer import any_in, any_pred, call_if, first_int, first_truthy, get_str, head_seq, text_or

    src = lra_ius.original_tactics()
    holes = find_symbol_holes(src)
    cands = closed_candidates(src)
    replay = lra_ius.replay(src)
    kinds = {item["kind"] for item in cands}
    has_ctor = any_pred(
        lambda item: any_in(get_str(item, "fill") + get_str(item, "original"), ("constructor", "And.intro")),
        cands,
    )
    has_dollar = any_pred(lambda item: "$" in (item.get("original"), item.get("fill")), cands)
    shots = catalog_shots(src, n_shots=4)
    span_holes = schedule_holes(src, n_masks=4, span=3)
    multi = closed_multihole(src, span_holes, schedule_id="cfg2")
    oh_shots = one_hole_shots(span=3, n_shots=4)
    oh_windows = prefer_one_holes(src, 4, max_pos=3) + prefer_one_holes(src, 3, max_pos=3)
    oh_rows = one_hole_closed_rows(src, max_pos=1)
    prompt = few_shot_prompt({"name": lra_ius.PROBLEM}, mask_skeleton(src, span_holes), span_holes, shots)
    cfg0 = cfg_schedule_for_score(0)
    cfg4 = cfg_schedule_for_score(4)
    from jevops.outer import all_rows, any_row, finalize_ok

    return finalize_ok(
        {
            "n_holes": len(holes),
            "n_closed_candidates": len(cands),
            "n_catalog_shots": len(shots),
            "n_span_holes": len(span_holes),
            "multi_hole_tokens": call_if(multi, lambda: multi["token_count"]),
            "hole_kinds": sorted({hole.kind for hole in holes}),
            "sample_kinds": head_seq(sorted(kinds), 12),
            "llm": "off",
            "called_docker0": False,
            "arena_score": None,
            "replay_tokens": lra_loop.token_count(replay),
        },
        len(holes) >= 3,
        len(cands) >= 3,
        lra_loop.token_count(replay) == 139,
        bool(first_truthy(has_ctor, has_dollar, any("intro" in get_str(item, "fill") for item in cands), default=False)),
        any(first_int(shot.get("n_holes")) >= 2 for shot in shots),
        "EXAMPLE" in prompt,
        "constructor" in prompt,
        len(span_holes) >= 1,
        cfg0["n_masks"] == 2,
        cfg4["span"] == 6,
        multi is None or int(multi["token_count"]) < lra_loop.token_count(src),
        bool(oh_shots),
        all_rows(oh_shots, lambda shot: first_int(shot.get("n_holes")) == 1),
        any_pred(lambda hole: any_in(hole.original, ("And.intro", "intros Hin", ".update_some")), oh_windows),
        any_row(oh_rows, lambda row: first_int(row.get("token_count")) < lra_loop.token_count(src)),
        any_row(kernel_one_hole_rows(src), lambda item: get_str(item, "kind").startswith("kernel_")),
    )


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
    from jevops.outer import exc_head, first_csv, head_seq, lookup_named, or_list, split_csv

    if one_hole:
        span_wanted = split_csv(args.one_hole_spans, cast=int)
        grid = or_list(
            [dict(item) for item in ONE_HOLE_SCHEDULES if item["span"] in span_wanted],
            [dict(item) for item in ONE_HOLE_SCHEDULES],
        )
    else:
        wanted_ids = split_csv(args.cfg_schedules)
        grid = or_list(
            [dict(item) for item in CFG_SCHEDULES if item["id"] in wanted_ids],
            [dict(item) for item in CFG_SCHEDULES],
        )
    if args.self_check or not args.live:
        from jevops.outer import print_ok

        payload = self_check()
        code = print_ok(payload)
        if args.self_check and not args.live:
            return code
        if not args.live:
            return code
    import inits_updates_shorten as lra_ius

    _raw, digest, records = lra_splice.load_warmup_records()
    name = first_csv(args.names)
    record = lookup_named(
        records, name, error_cls=RuntimeError, miss=f"unknown warm-up problem: {name}"
    )
    import draft_fanout as lra_fan
    import mcmc_beam as lra_mcmc

    from jevops.outer import call_if, first_not_none, read_text

    tactics = first_not_none(
        call_if(args.init_file and Path(args.init_file).is_file(), lambda: read_text(args.init_file).strip("\n")),
        call_if(name == lra_ius.PROBLEM, lra_ius.original_tactics),
        factory=lambda: lra_fan.tactic_block(record),
    )
    ledger = lra_t1.ProblemLedger(
        name=f"{name}#symbol-diffuse",
        max_jev_calls=max(12, first_int(args.rounds) * 3 + 4),
        max_mistral_calls=max(6, first_int(args.rounds) * max(1, first_int(args.leanstral_top)) + 2),
    )
    from jevops.outer import call_if, first_int, first_truthy, get_str, read_bytes_if, replace_if, text_or

    clone = lra_kb.lra_cw.clone_dir(get_str(record, "url"), DEFAULT_STATE)
    dest = clone / lra_kb.lra_cw.source_relpath(record)

    restore = read_bytes_if(dest)
    from jevops.search import pack_keep

    best = pack_keep(kind="init", tactics=tactics, token_count=lra_loop.token_count(tactics))
    lake_rows: list[dict[str, Any]] = []
    ranked_rows: list[dict[str, Any]] = []
    cfg_rows: list[dict[str, Any]] = []
    current = tactics
    ranked: dict[str, Any] = {}
    last_closed: list[dict[str, Any]] = []
    for round_i in range(max(1, first_int(args.rounds))):
        cfg = typesafe_cfg_score(record, current, ledger=ledger, one_hole=one_hole)
        cfg["round"] = round_i
        cfg_rows.append(cfg)
        picked = dict(first_truthy(cfg.get("cfg_schedule"), call_if(grid, lambda: grid[0]), CFG_SCHEDULES[0]))
        schedules = replace_if(args.sweep or one_hole, list(grid), [picked])
        if not any(item["id"] == picked["id"] for item in schedules):
            schedules.insert(0, picked)
        candidates: list[dict[str, Any]] = []
        if not args.no_replay:
            for item in closed_candidates(current, max_candidates=4, include_replay=True):
                if item.get("kind") == "inits_replay":
                    candidates.append(item)
                    break
        phrase_rows = head_seq(closed_candidates(current, max_candidates=8, include_replay=False), 6)
        kernel_rows = call_if(one_hole, lambda: kernel_one_hole_rows(current), default=[])
        # Catalog one-step kernels, then phrase one-holes, so lake_top sees
        # drop_not_intro / fold_init / constructor before blind span windows.
        candidates.extend(kernel_rows)
        candidates.extend(phrase_rows)
        if one_hole:
            candidates.extend(one_hole_closed_rows(current, max_pos=2))
        else:
            for sched in schedules:
                span_holes = schedule_holes(current, n_masks=first_int(sched.get("n_masks")), span=first_int(sched.get("span")))
                row = closed_multihole(current, span_holes, schedule_id=get_str(sched, "id"))
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
                    if len(lean_schedules) >= max(1, first_int(args.leanstral_top)):
                        break
                lean_schedules = lean_schedules[: max(1, first_int(args.leanstral_top))]
            else:
                lean_schedules = [picked]
                if args.sweep:
                    from jevops.outer import first_where

                    zero = first_where(schedules, lambda item: first_int(item.get("n_shots")) == 0)
                    if zero is not None and zero["id"] != picked["id"]:
                        lean_schedules.append(zero)
                lean_schedules = lean_schedules[: max(1, first_int(args.leanstral_top))]
            for sched in lean_schedules:
                span = first_int(sched.get("span"))
                if one_hole:
                    span_holes = prefer_one_holes(current, span, max_pos=1)
                    n_shots = call_if(few_shot, lambda: first_int(sched.get("n_shots")), default=0)
                    shots = call_if(n_shots, lambda: one_hole_shots(span=span, n_shots=n_shots), default=[])
                else:
                    span_holes = schedule_holes(
                        current, n_masks=first_int(sched.get("n_masks")), span=span
                    )
                    n_shots = call_if(few_shot, lambda: first_int(sched.get("n_shots")), default=0)
                    shots = call_if(n_shots, lambda: catalog_shots(current, n_shots=n_shots), default=[])
                try:
                    rows = leanstral_candidates(
                        record,
                        current,
                        span_holes,
                        ledger=ledger,
                        shots=shots,
                        schedule_id=get_str(sched, "id"),
                        n_shots=n_shots,
                    )
                    candidates = rows + candidates
                except Exception as exc:  # noqa: BLE001
                    ranked_rows.append(
                        {
                            "round": round_i,
                            "leanstral_error": exc_head(exc),
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
        order = call_if(ranked.get("best_fill"), lambda: [ranked.get("best_fill")], default=[])
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
            if first_truthy(kind in seen_kind, kind not in by_kind):
                continue
            seen_kind.add(text_or(kind))
            body = get_str(by_kind[kind], "tactics")
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
                "errors": head_seq(compiled.get("errors"), 1),
            }
            lake_rows.append(row)
            tried += 1
            if row["ok"] and first_int(row.get("tokens"), 999) < first_int(best.get("token_count")):
                ok_hits.append((first_int(row.get("tokens")), text_or(kind), body))
                if not (args.sweep or one_hole):
                    break
            if tried >= first_int(args.lake_top):
                break
        if ok_hits:
            ok_hits.sort(key=lambda item: item[0])
            tok, kind, body = ok_hits[0]
            best = pack_keep(kind=f"r{round_i}_{kind}", tactics=body, token_count=tok)
            accepted = body
        if not accepted:
            ranked_rows.append({"round": round_i, "stopped": "no_shorter_lake_ok"})
            break
        current = accepted
    holes = find_symbol_holes(current)
    args.out.mkdir(parents=True, exist_ok=True)
    from jevops.outer import utc_stamp, write_json_pair

    payload = {
        "schema": "lra-symbol-diffuse/v1",
        "observed_at": utc_stamp(),
        "name": name,
        "llm": args.llm,
        "few_shot": few_shot,
        "one_hole": one_hole,
        "sweep": bool(args.sweep) or one_hole,
        "rounds": first_int(args.rounds),
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
        "ledger": call_if(
            hasattr(ledger, "as_dict"),
            lambda: ledger.as_dict(),
            default={"jev_calls": getattr(ledger, "jev_calls", 0)},
        ),
    }
    if best.get("tactics") and first_int(best.get("token_count")) < lra_loop.token_count(tactics):
        (args.out / f"symbol-diffuse-best-{best['token_count']}.lean").write_text(get_str(best, "tactics") + "\n")
    write_json_pair(
        args.out,
        payload,
        prefix="symbol-diffuse",
        latest="symbol-diffuse-latest.json",
    )
    from jevops.outer import print_json

    print_json(payload, default=str)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

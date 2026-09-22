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
MARKER = re.compile(r"<<<SYM_(\d+)(?: kind=([a-z_]+))?>>>")

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
    from jevops.outer import first_int, get_str

    return SymbolHole(
        hole_id=get_str(row, "hole_id", default="SYM_0"),
        kind=get_str(row, "kind", default="span"),
        start=first_int(row["start"]),
        end=first_int(row["end"]),
        original=get_str(row, "original"),
        n_tokens=first_int(row.get("n_tokens"), default=1),
    )


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

    from jevops.mask import schedule_for_score
    from jevops.outer import either

    table = either(one_hole, lambda: ONE_HOLE_SCHEDULES, lambda: CFG_SCHEDULES)
    return schedule_for_score(score, table)


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

    from jevops.mask import span_windows

    rows = span_windows(
        tactics,
        span,
        stride=stride,
        tokens=list(lra_loop._TOKEN.finditer(tactics)),
        skip_fn=is_pca_line,
    )
    return [_from_row(row) for row in rows]


def schedule_holes(tactics: str, *, n_masks: int, span: int) -> list[SymbolHole]:
    """Non-overlapping token windows of ``span``, skipping PCA control-flow lines."""

    from jevops.mask import pick_nonoverlapping
    from jevops.outer import either, or_int

    n_masks = or_int(n_masks, 1, floor=1)
    windows = all_span_windows(tactics, span)
    return either(
        windows,
        lambda: [
            _from_row(row)
            for row in pick_nonoverlapping([_as_row(item) for item in windows], n=n_masks)
        ],
        lambda: [
            _rehole(hole, i)
            for i, hole in enumerate(find_symbol_holes(tactics, max_holes=n_masks)[:n_masks])
        ],
    )


def _window_priority(hole: SymbolHole) -> int:
    from jevops.outer import count_hits

    return count_hits(hole.original, PHRASE_ALTS, weight=10, add_len=True) + count_hits(
        hole.original, OPERATORS, weight=3
    )


def prefer_one_holes(tactics: str, span: int, *, max_pos: int = 2) -> list[SymbolHole]:
    """One hole of ``span`` tokens, preferring phrase/operator-aligned windows."""

    from jevops.mask import pick_scored
    from jevops.outer import either, or_int

    windows = all_span_windows(tactics, span, stride=1)
    return either(
        windows,
        lambda: [
            _rehole(_from_row(row), 0)
            for row in pick_scored(
                [_as_row(hole) for hole in windows],
                n=or_int(max_pos, 1, floor=1),
                score_fn=lambda row: _window_priority(_from_row(row)),
                reindex=False,
            )
        ],
        lambda: schedule_holes(tactics, n_masks=1, span=span),
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

    try:
        import inits_updates_shorten as lra_ius
    except Exception:
        return []
    from jevops.mask import kernel_one_hole_rows as _fn

    return _fn(
        tactics,
        propose_fn=lra_ius.propose,
        token_fn=lra_loop.token_count,
        spans=ONE_HOLE_SPANS,
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

    from jevops.tactics import closed_fills as _fn

    return _fn(
        _as_row(hole),
        tactics,
        phrase_alts=PHRASE_ALTS,
        operator_alts=OPERATOR_ALTS,
        token_re=lra_loop._TOKEN,
    )


def mask_skeleton(tactics: str, holes: Sequence[SymbolHole]) -> str:
    from jevops.mask import mask_skeleton as _fn

    return _fn(tactics, [_as_row(item) for item in holes])


def apply_fill(tactics: str, hole: SymbolHole, fill: str) -> str:
    from jevops.mask import apply_fill as _fn

    return _fn(tactics, _as_row(hole), fill)


def closed_candidates(
    tactics: str, *, max_candidates: int = 32, include_replay: bool = True
) -> list[dict[str, Any]]:
    """One-hole closed-vocab edits that are strictly shorter."""

    from jevops.mask import closed_with_replay
    from jevops.outer import call_if, ignore_error

    def _replay() -> Any:
        import inits_updates_shorten as lra_ius

        return lra_ius.replay

    replay_fn = call_if(include_replay, lambda: ignore_error(_replay))
    return closed_with_replay(
        tactics,
        find_symbol_holes(tactics),
        fills_fn=lambda item, text: closed_fills(_from_row(item), text),
        token_fn=lra_loop.token_count,
        as_row_fn=_as_row,
        replay_fn=replay_fn,
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
    from jevops.outer import call_if, first_not_none

    return first_not_none(
        call_if(shots, lambda: few_shot_prompt(record, skeleton, holes, shots)),
        factory=lambda: _leanstral_plain_prompt(record, skeleton, holes),
    )


def _leanstral_plain_prompt(
    record: Mapping[str, Any],
    skeleton: str,
    holes: Sequence[SymbolHole],
) -> str:
    from jevops.outer import get_str, head_seq

    docs = []
    for hole in head_seq(holes, 8):
        docs.append(f"{hole.hole_id} kind={hole.kind} ORIGINAL={hole.original!r}\n")
    return (
        "Lean 4 tactic hole-fill. Each <<<SYM_i kind=...>>> is one operator or symbol. "
        "Fill with a SHORTER Lean operator/symbol from the language (constructor, simp_all, $, "
        "‹_›, all_goals, intro, .update_some, a hyp already in the proof). "
        "Keep induction and every · / case arm. No sorry, no theorem, no open.\n\n"
        f"Problem: {get_str(record, 'name')}\n"
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
    from jevops.outer import call_if, cap_or_fill, generate_text_and_usage, get_str, head_chars, head_seq
    from jevops.search import holes_or_find

    lra_mistral.load_keyfiles()
    holes = holes_or_find(
        holes,
        lambda: find_symbol_holes(tactics),
        kinds=("operator", "phrase"),
        n=8,
        head_fn=head_seq,
    )
    def _fill() -> list[dict[str, Any]]:
        use_shots = cap_or_fill(shots, n_shots, lambda: catalog_shots(tactics, n_shots=n_shots))
        skeleton = mask_skeleton(tactics, holes)
        prompt = leanstral_prompt(record, skeleton, holes, use_shots)
        raw = lra_mistral.chat_completions(prompt, max_tokens=600, temperature=0.3, n=1)
        text, inn, out = generate_text_and_usage(raw, fallback_in=200)
        call_if(
            ledger is not None,
            lambda: ledger.record(
                "mistral",
                input_tokens=inn,
                output_tokens=out,
                model=get_str(raw, "model", default=lra_mistral.REQUESTED_MODEL),
            ),
        )
        fills = parse_leanstral_fills(text, holes)
        from jevops.mask import pack_leanstral_fill_rows

        return pack_leanstral_fill_rows(
            tactics=tactics,
            holes=holes,
            text=text,
            fills=fills,
            token_fn=lra_loop.token_count,
            extract_fn=lra_loop.extract_generated_tactics,
            schedule_id=schedule_id,
            n_shots=len(use_shots),
            head_fn=head_chars,
        )

    return call_if(holes, _fill, default=[])


def typesafe_rank(
    record: Mapping[str, Any],
    drafts: Sequence[Mapping[str, Any]],
    *,
    ledger: Optional[Any] = None,
) -> dict[str, Any]:
    from jevops.jev import skipped
    from jevops.outer import first_call, head_chars, pin_calls

    from jevops.outer import call_if, first_not_none

    early = first_call((not drafts, lambda: skipped("no_drafts", arena_score=None)))

    def _rank() -> dict[str, Any]:
        from jevops.jev import typesafe_session

        loaded, no_key = typesafe_session(
            setup=(lra_pca.load_keyfile, lra_pca.pin_typesafe_path),
            fallback=False,
            arena_score=None,
        )
        Choice = None if loaded is None else loaded["Choice"]
        Noul = None if loaded is None else loaded["Noul"]
        Score = None if loaded is None else loaded["Score"]
        TypeSafeClient = None if loaded is None else loaded["TypeSafeClient"]

        def _ask() -> dict[str, Any]:
            from jevops.jev import fill_rank_criteria, fill_rank_state
            from jevops.outer import any_pred, first_truthy, or_list, set_if

            criteria = fill_rank_criteria(drafts, head_fn=head_chars)
            state = fill_rank_state(
                record,
                drafts,
                head_fn=head_chars,
                goal=RANK_FILL_GOAL,
            )
            questions: dict[str, Any] = {
                "best_fill": Choice(
                    instructions=RANK_FILL_BEST,
                    criteria=criteria,
                ),
                "cfg_mask": Score(
                    instructions=RANK_FILL_CFG,
                    criteria=or_list(CFG_MASK_CRITERIA, []),
                ),
            }
            set_if(
                questions,
                any_pred(lambda item: first_truthy(item.get("llm") == "on", item.get("few_shot"), default=False), drafts),
                "prefer_few_shot",
                Noul(instructions=RANK_FILL_FEW_SHOT),
            )
            from jevops.jev import charge_packed, invoke_system_one, invoke_then_project, pack_fill_rank

            def _project(result: Any, wall_ms: float) -> dict[str, Any]:
                return charge_packed(
                    pack_fill_rank(result, wall_ms, schedule_fn=cfg_schedule_for_score),
                    ledger,
                    model=lra_t1.JEV_MODEL_ID,
                )

            return invoke_then_project(
                invoke_fn=lambda: invoke_system_one(TypeSafeClient(timeout=45.0), state, questions),
                project_fn=_project,
            )

        return first_not_none(no_key, factory=_ask)

    return first_not_none(early, factory=_rank)


def typesafe_cfg_score(
    record: Mapping[str, Any],
    tactics: str,
    *,
    ledger: Optional[Any] = None,
    one_hole: bool = False,
) -> dict[str, Any]:
    """Ask TypeSafe Score/Choice how many masks and how long they should be."""

    from jevops.outer import either

    table = either(one_hole, lambda: ONE_HOLE_SCHEDULES, lambda: CFG_SCHEDULES)
    rubric = either(one_hole, lambda: ONE_HOLE_CRITERIA, lambda: CFG_MASK_CRITERIA)
    from jevops.outer import pin_calls

    from jevops.jev import typesafe_session
    from jevops.outer import overlay_map

    loaded, skip = typesafe_session(
        setup=(lra_pca.load_keyfile, lra_pca.pin_typesafe_path),
        fallback=False,
        cfg_schedule=overlay_map(table[0]),
        one_hole=one_hole,
    )
    if skip is not None:
        return skip
    Choice = loaded["Choice"]
    Score = loaded["Score"]
    TypeSafeClient = loaded["TypeSafeClient"]

    from jevops.outer import first_not_none, head_chars, or_list

    def _ask() -> dict[str, Any]:
        from jevops.jev import cfg_score_criteria, cfg_score_state
        from jevops.search import eligible_span_counts

        eligible = eligible_span_counts(tactics, ONE_HOLE_SPANS, all_span_windows)
        criteria = cfg_score_criteria(table, eligible)
        state = cfg_score_state(
            record,
            tactics,
            token_fn=lra_loop.token_count,
            eligible=eligible,
            one_hole=one_hole,
            head_fn=head_chars,
            goal=either(one_hole, lambda: CFG_ONE_HOLE_GOAL, lambda: CFG_MULTI_GOAL),
        )
        from jevops.jev import charge_packed, invoke_system_one, invoke_then_project, pack_cfg_score

        questions = {
            "cfg_mask": Score(
                instructions=either(one_hole, lambda: CFG_ONE_HOLE_SCORE, lambda: CFG_MULTI_SCORE),
                criteria=or_list(rubric, []),
            ),
            "best_schedule": Choice(
                instructions=either(one_hole, lambda: CFG_ONE_HOLE_CHOICE, lambda: CFG_MULTI_CHOICE),
                criteria=criteria,
            ),
        }
        return invoke_then_project(
            invoke_fn=lambda: invoke_system_one(TypeSafeClient(timeout=45.0), state, questions),
            project_fn=lambda result, wall_ms: charge_packed(
                pack_cfg_score(
                    result,
                    wall_ms,
                    table=table,
                    schedule_fn=cfg_schedule_for_score,
                    one_hole=one_hole,
                    eligible=eligible,
                ),
                ledger,
                model=lra_t1.JEV_MODEL_ID,
            ),
        )

    return _ask()


def pca_mca_ops(tactics: str) -> list[tuple[str, str, tuple[str, ...]]]:
    from jevops.tactics import collect_symbol_ops

    return collect_symbol_ops(
        closed_candidates(tactics, max_candidates=8, include_replay=True),
        kernel_one_hole_rows(tactics),
        family="symbol_diffuse",
        kernel_cap=8,
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

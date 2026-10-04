#!/usr/bin/env python3
"""Randomize warmup canaries and analyze proofs for MCA refactoring.

Fits PCA/MCA on the frozen 15-problem warmup, samples ``k`` proofs with a
seeded RNG, lists residual holes (simp-at runs, have/rename_i, rw chains,
one-hole spans), asks TypeSafe which family/draft to try, and optionally
lakes a few randomized drops.

Original manuscripts are not rewritten. Lake is the oracle on ``--live``.
Not an Arena ranking. Not official Track 2. Never docker0.
"""
from __future__ import annotations

import argparse
import json
import random
import sys

from pathlib import Path
from typing import Any, Mapping, Optional, Sequence

HERE = Path(__file__).resolve().parent
PAPER_ROOT = HERE.parent
OUT_DEFAULT = PAPER_ROOT / "evidence" / "canaries"
CANARY_139 = OUT_DEFAULT / "cascade-best-139.lean"

if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
import _jevops_path  # noqa: E402,F401
import draft_fanout as lra_fan  # noqa: E402
import mca_mask_replace as lra_mask  # noqa: E402
import pca_mca_fanout as lra_pca  # noqa: E402
import run_warmup as lra_loop  # noqa: E402
import splice as lra_splice  # noqa: E402
import symbol_diffuse as lra_sym  # noqa: E402
import binder_use as lra_bind  # noqa: E402
import portable_rewrites as lra_port  # noqa: E402
import track1_keepbest as lra_kb  # noqa: E402
import track1_ledger as lra_t1  # noqa: E402

PR_ID = "PR-9h"
from jevops.catalogs import BEAM_K
from jevops.catalogs import DEFAULT_CANARY_K as DEFAULT_K
from jevops.catalogs import DEFAULT_CANARY_SEED as DEFAULT_SEED
from jevops.catalogs import DEFAULT_TRACK1_STATE as DEFAULT_STATE
from jevops.catalogs import PROTOCOL
from jevops.catalogs import CONFIDENT
from jevops.catalogs import EPSILON
from jevops.catalogs import FIRE_T
from jevops.catalogs import FIRE_T_LEAF
from jevops.catalogs import FIRE_T_RESIDUAL
from jevops.catalogs import HIGH_STAKES
from jevops.catalogs import INNER_MAX_STEPS
from jevops.catalogs import MAX_LIVE_TOKENS
from jevops.catalogs import NEST_MAX_DEPTH
from jevops.catalogs import RESIDUAL_TO_SKILL
from jevops.catalogs import UNCERTAIN
from jevops.catalogs import FAMILY_BLURB
from jevops.catalogs import FAMILY_STRUCTURED
from jevops.catalogs import INTENT_NEST_INSTRUCTIONS
from jevops.catalogs import INTENT_QUESTION_SPEC
from jevops.catalogs import INTENT_TOOL_INSTRUCTIONS
from jevops.catalogs import PICK_FAIL_CRITERIA
from jevops.catalogs import PICK_GOAL
from jevops.catalogs import PICK_LEAF_FOCUS
from jevops.catalogs import PICK_QUESTION_SPEC


def _tags(record: Mapping[str, Any]) -> list[Any]:
    from jevops.jev import list_field

    return list_field(record, "version_info")


def analyze_proof(
    record: Mapping[str, Any],
    *,
    tactics: Optional[str] = None,
    model: Optional[Mapping[str, Any]] = None,
) -> dict[str, Any]:
    from jevops.pick import drive_analyze_proof

    return drive_analyze_proof(
        record,
        tactics=tactics,
        model=model,
        tactic_fn=lra_fan.tactic_block,
        count_fn=lra_pca.count_tactics,
        family_fn=lra_pca.amenable_families,
        holes_fn=lra_mask.find_holes,
        spans=lra_sym.ONE_HOLE_SPANS,
        windows_fn=lambda text, span: lra_sym.all_span_windows(text, span, stride=1),
        phrases=lra_sym.PHRASE_ALTS,
        cases_fn=lra_fan.case_spans,
        token_fn=lra_loop.token_count,
        used_fn=lra_bind.binders_used_later,
        safe_fn=lra_bind.safe_to_drop_span,
        tags_fn=_tags,
    )


def random_drafts(
    tactics: str,
    rng: random.Random,
    *,
    n: int = 6,
    families: Sequence[Mapping[str, Any]] = (),
    counts: Optional[Mapping[str, float]] = None,
    name: str = "",
    memory: Optional[Mapping[str, Any]] = None,
    allow_families: Optional[set[str]] = None,
) -> list[dict[str, Any]]:
    """Seeded random MCA drops and one-hole closed fills. No LLM.

    Binder drops are gated: a ``rename_i`` / ``have`` is skipped when its
    names still appear later (the substOldPostSubset ``trigger1`` failure).
    """

    from jevops.tactics import drive_random_drafts

    return drive_random_drafts(
        tactics,
        rng,
        n=n,
        families=families,
        counts=counts,
        name=name,
        memory=memory,
        allow_families=allow_families,
        token_fn=lra_loop.token_count,
        pipeline=lra_port.PIPELINE,
        blacklist_fn=lra_bind.is_blacklisted,
        failed_fn=lra_bind.failed_skill_stems,
        portable_fn=lra_port.portable_drafts,
        spans=lra_sym.ONE_HOLE_SPANS,
        prefer_fn=lra_sym.prefer_one_holes,
        phrase_alts=lra_sym.PHRASE_ALTS,
        operators=lra_sym.OPERATORS,
        closed_fn=lra_sym.closed_multihole,
        guided_fn=lra_pca.guided_drafts,
        safe_drop_fn=lra_bind.safe_to_drop_span,
    )


from jevops.pick import draft_tree as kernel_draft_tree  # noqa: E402
from jevops.pick import geo_mean  # noqa: E402
from jevops.pick import leftover_sort_key  # noqa: E402  # re-export
from jevops.pick import sample_records  # noqa: E402


def draft_tree(drafts: Sequence[Mapping[str, Any]]) -> dict[str, dict[str, str]]:
    from jevops.pick import drive_blurb_tree

    return drive_blurb_tree(
        drafts,
        FAMILY_STRUCTURED,
        FAMILY_BLURB,
        empty_tree={"pca_keep": {"keep": "No shorter draft"}},
    )


def typesafe_pick(
    record: Mapping[str, Any],
    analysis: Mapping[str, Any],
    drafts: Sequence[Mapping[str, Any]],
    *,
    ledger: Optional[Any] = None,
    memory: Optional[Mapping[str, Any]] = None,
) -> dict[str, Any]:
    from jevops.pick import drive_typesafe_pick

    return drive_typesafe_pick(
        record,
        analysis,
        drafts,
        ledger=ledger,
        memory=memory,
        setup=(lra_pca.load_keyfile, lra_pca.pin_typesafe_path),
        spec=PICK_QUESTION_SPEC,
        structured=FAMILY_STRUCTURED,
        blurbs=FAMILY_BLURB,
        fail_criteria=PICK_FAIL_CRITERIA,
        leaf_focus=PICK_LEAF_FOCUS,
        goal=PICK_GOAL,
        failed_stems_fn=lra_bind.failed_skill_stems,
        model_id=lra_t1.JEV_MODEL_ID,
        beam_k=BEAM_K,
        fire_t=FIRE_T,
        fire_t_leaf=FIRE_T_LEAF,
        confident=CONFIDENT,
        uncertain=UNCERTAIN,
        epsilon=EPSILON,
    )


def typesafe_autoresearch(
    record: Mapping[str, Any],
    analysis: Mapping[str, Any],
    *,
    tactics: str = "",
    ledger: Optional[Any] = None,
    memory: Optional[Mapping[str, Any]] = None,
    allow_families: Optional[set[str]] = None,
    allow_skills: Optional[set[str]] = None,
    tree_node: str = "root",
) -> dict[str, Any]:
    """Entry point: AutoResearch features (Score+Noul on residuals) then route skills.

    Cookbook: numeric features from TypeSafe answers drive what code generates and
    composes. Jev does not write Lean.
    """

    return typesafe_intent(
        record,
        analysis,
        tactics=tactics,
        ledger=ledger,
        memory=memory,
        extra_residual_qs=True,
        allow_families=allow_families,
        allow_skills=allow_skills,
        tree_node=tree_node,
    )


from jevops.walk import bias_compose_no_drafts  # noqa: E402


def typesafe_intent(
    record: Mapping[str, Any],
    analysis: Mapping[str, Any],
    *,
    tactics: str = "",
    ledger: Optional[Any] = None,
    memory: Optional[Mapping[str, Any]] = None,
    extra_residual_qs: bool = True,
    allow_families: Optional[set[str]] = None,
    allow_skills: Optional[set[str]] = None,
    tree_node: str = "root",
) -> dict[str, Any]:
    """Intent routing + AutoResearch residual features."""

    import typesafe_tools as lra_tools
    from jevops.jev import drive_typesafe_intent

    return drive_typesafe_intent(
        record,
        analysis,
        tactics=tactics,
        ledger=ledger,
        memory=memory,
        extra_residual_qs=extra_residual_qs,
        allow_families=allow_families,
        allow_skills=allow_skills,
        tree_node=tree_node,
        setup=(lra_pca.load_keyfile, lra_pca.pin_typesafe_path),
        families=set(FAMILY_BLURB),
        structured=FAMILY_STRUCTURED,
        residual_fn=lra_port.analyze_residuals,
        prior_fn=lra_bind.prior_research,
        propose_fn=lra_bind.propose_skill_from_research,
        skills_fn=lra_port.available_skills,
        tree_fn=lra_port.decision_tree,
        blocked_fn=lra_bind.is_blacklisted,
        spec=INTENT_QUESTION_SPEC,
        tool_criteria=lra_tools.TOOL_CRITERIA,
        subloops=lra_tools.SUBLOOPS,
        nest_instructions=INTENT_NEST_INSTRUCTIONS,
        tool_instructions=INTENT_TOOL_INSTRUCTIONS,
        residual_to_skill=RESIDUAL_TO_SKILL,
        fire_t_residual=FIRE_T_RESIDUAL,
        fire_t=FIRE_T,
        fire_t_leaf=FIRE_T_LEAF,
        confident=CONFIDENT,
        uncertain=UNCERTAIN,
        high_stakes=set(HIGH_STAKES),
        model_id=lra_t1.JEV_MODEL_ID,
    )


def self_check() -> dict[str, Any]:
    _raw, digest, records = lra_splice.load_warmup_records()
    rows = [lra_pca.feature_row(item) for item in records]
    model = lra_pca.fit_pca_mca(rows)
    sampled = sample_records(records, k=2, seed=1)
    analyses = [analyze_proof(item, model=model) for item in sampled]
    from jevops.outer import or_list

    drafts = random_drafts(
        lra_fan.tactic_block(sampled[0]),
        random.Random(1),
        n=4,
        families=or_list(analyses[0].get("families"), []),
        counts=analyses[0].get("counts"),
    )
    from jevops.outer import all_rows, finalize_ok

    return finalize_ok(
        {
            "n_records": len(records),
            "warmup_jsonl_sha256": digest,
            "sample_names": [item.get("name") for item in sampled],
            "n_random_drafts": len(drafts),
            "called_docker0": False,
            "arena_score": None,
            "official_track2": False,
        },
        digest == lra_splice.FROZEN_WARMUP_SHA256,
        len(records) == lra_splice.WARMUP_N,
        len(sampled) == 2,
        sample_records(records, k=2, seed=1)[0].get("name") == sampled[0].get("name"),
        all_rows(analyses, lambda item: int(item["n_tokens"]) > 0),
        all_rows(analyses, lambda item: isinstance(item.get("families"), list)),
        abs(geo_mean([0.81, 0.81]) - 0.81) < 1e-9,
    )


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-check", action="store_true")
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--k", type=int, default=DEFAULT_K)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--timeout", type=float, default=180.0)
    parser.add_argument("--lake-top", type=int, default=3)
    parser.add_argument("--drafts", type=int, default=6)
    parser.add_argument("--rounds", type=int, default=1, help="denoise rounds per canary (accept shorter lake-ok, remask)")
    parser.add_argument("--out", type=Path, default=OUT_DEFAULT)
    parser.add_argument("--include-inits", action="store_true", help="force Core.InitsUpdatesComm into the sample")
    parser.add_argument("--init-139", action="store_true", help="analyze the 139-token InitsUpdatesComm cut as extra row")
    parser.add_argument(
        "--all-small",
        action="store_true",
        help=f"use every warmup proof with ≤{MAX_LIVE_TOKENS} tokens instead of a random k",
    )
    parser.add_argument(
        "--from-best",
        action="store_true",
        help="start each canary from its shortest random-best-*.lean if present",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="write evidence files but do not print the full payload",
    )
    parser.add_argument(
        "--nest-depth",
        type=int,
        default=NEST_MAX_DEPTH,
        help="max TypeSafe recursive skill-tree nest depth",
    )
    args = parser.parse_args(argv)
    if args.self_check or not args.live:
        from jevops.outer import print_ok

        payload = self_check()
        code = print_ok(payload)
        if args.self_check and not args.live:
            return code
        if not args.live:
            return code

    payload = run_live(args)
    if not getattr(args, "quiet", False):
        from jevops.outer import print_json

        print_json(payload, default=str)
    return 0


def rank_live_records(
    records: Sequence[Mapping[str, Any]],
    *,
    out: Path,
    from_best: bool,
    memory: Optional[Mapping[str, Any]] = None,
    warmup: Optional[Mapping[str, int]] = None,
    keep: Optional[Mapping[str, int]] = None,
) -> list[Mapping[str, Any]]:
    """Leftover un-blacklisted drafts first, then remaining_cut (warmup - keep)."""

    import typesafe_inner as lra_inner
    import board_graph as lra_board
    import skill_improve_loop as lra_sk
    import nca_rankers as lra_rank
    from jevops.pick import drive_rank_live

    return drive_rank_live(
        records,
        out=out,
        from_best=from_best,
        memory=memory,
        warmup=warmup,
        keep=keep,
        warmup_fn=lra_board.warmup_token_map,
        keep_fn=lra_sk.keep_best_board,
        start_fn=lra_inner.starting_tactics,
        prior_fn=lra_bind.prior_research,
        drafts_fn=lra_port.portable_drafts,
        blocked_fn=lra_bind.is_blacklisted,
        residual_map=lra_port.SKILL_RESIDUAL,
        fire_t=FIRE_T_RESIDUAL,
        score_fn=lra_rank.score_record,
    )


def run_live(args: argparse.Namespace) -> dict[str, Any]:
    """AutoResearch entry + lake on sampled canaries. Writes evidence; returns payload."""

    import typesafe_nca as lra_nca_live
    import board_graph as lra_board_live
    import skill_improve_loop as lra_sk_board
    import typesafe_inner as lra_inner
    from jevops.outer import read_text
    from jevops.walk import drive_live_canaries

    return drive_live_canaries(
        args,
        load_records_fn=lra_splice.load_warmup_records,
        feature_fn=lra_pca.feature_row,
        fit_fn=lra_pca.fit_pca_mca,
        analyze_fn=analyze_proof,
        sample_fn=sample_records,
        load_memory_fn=lra_bind.load_memory,
        save_memory_fn=lra_bind.save_memory,
        rank_fn=rank_live_records,
        ledger_cls=lra_t1.ProblemLedger,
        seed_fn=lra_board_live.seed_nca_from_board,
        overlay_fn=lra_board_live.overlay_live_board,
        keepbest_fn=lambda mem: lra_board_live.seed_keepbest_theorems(
            mem, lra_sk_board.keep_best_board(args.out), warmup=lra_board_live.warmup_token_map()
        ),
        halt_fn=lra_nca_live.should_halt,
        nested_fn=lra_inner.run_nested_canary,
        gap_fn=lra_bind.skill_gap_report,
        inits_name="Core.InitsUpdatesComm",
        canary_139=CANARY_139,
        read_fn=read_text,
        max_live_tokens=MAX_LIVE_TOKENS,
        inner_max_steps=INNER_MAX_STEPS,
        rng_cls=random.Random,
    )


if __name__ == "__main__":
    raise SystemExit(main())

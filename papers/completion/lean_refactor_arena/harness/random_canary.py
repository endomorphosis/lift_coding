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
    from jevops.outer import any_get, attrs_of, call_if, head_seq, if_none, stripped_or, substrings_in
    from jevops.pick import analysis_row
    from jevops.pick import hole_rows

    body = stripped_or(if_none(tactics, factory=lambda: lra_fan.tactic_block(record)), "")
    counts = lra_pca.count_tactics(body)
    families = call_if(model, lambda: lra_pca.amenable_families(counts, model), default=[])
    mca_holes = lra_mask.find_holes(body)
    from jevops.search import eligible_span_counts

    spans = eligible_span_counts(
        body,
        lra_sym.ONE_HOLE_SPANS,
        lambda text, span: lra_sym.all_span_windows(text, span, stride=1),
    )
    phrases = substrings_in(body, lra_sym.PHRASE_ALTS)
    cases = attrs_of(lra_fan.case_spans(body), "label")
    holes = hole_rows(
        mca_holes,
        token_fn=lra_loop.token_count,
        used_fn=lambda start, end, original: lra_bind.binders_used_later(body, start, end, original),
        safe_fn=lambda start, end, original: lra_bind.safe_to_drop_span(body, start, end, original),
    )
    return analysis_row(
        record,
        n_tokens=lra_loop.token_count(body),
        counts=counts,
        families=families,
        holes=holes,
        extra={
            "n_tags": len(_tags(record)),
            "eligible_spans": spans,
            "catalog_phrases_present": phrases,
            "case_labels": head_seq(cases, 12),
            "n_cases": len(cases),
            "pca_keep": any_get(counts, "n_induction", "n_cases"),
        },
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

    from jevops.tactics import collect_random_draft_extras, random_mca_drafts as _fn

    body = tactics.strip("\n")
    from jevops.outer import allow_pred, any_pred, maybe_set, or_list, overlay_map

    allow = maybe_set(allow_families)
    wanted = allow_pred(allow)

    portable_items: list[Mapping[str, Any]] = []
    if any_pred(wanted, ("search_space", "algebraic_simplification", "dead_code")):
        from jevops.binders import blocked_port_stems

        blocked = blocked_port_stems(
            memory,
            name,
            lra_port.PIPELINE,
            blacklist_fn=lra_bind.is_blacklisted,
            failed_fn=lra_bind.failed_skill_stems,
        )
        portable_items = list(
            lra_port.portable_drafts(body, skip=blocked, memory=overlay_map(memory), name=name)
        )
    early, late = collect_random_draft_extras(
        body,
        rng,
        wanted_fn=wanted,
        portable_items=portable_items,
        symbol_spans=list(lra_sym.ONE_HOLE_SPANS),
        prefer_fn=lra_sym.prefer_one_holes,
        phrase_alts=lra_sym.PHRASE_ALTS,
        operators=lra_sym.OPERATORS,
        closed_fn=lra_sym.closed_multihole,
        pca_drafts=lra_pca.guided_drafts(body, or_list(families, [{"family": "dead_code"}]), counts),
    )

    def _blacklist(mem: Mapping[str, Any], problem: str, kind: str, nxt: str = "") -> bool:
        return lra_bind.is_blacklisted(mem, problem, kind, tactics=nxt)

    return _fn(
        tactics,
        rng,
        n=n,
        token_fn=lra_loop.token_count,
        allow_families=allow,
        name=name,
        memory=memory,
        safe_drop_fn=lra_bind.safe_to_drop_span,
        blacklist_fn=_blacklist,
        early_extras=early,
        late_extras=late,
    )


from jevops.pick import draft_tree as kernel_draft_tree  # noqa: E402
from jevops.pick import geo_mean  # noqa: E402
from jevops.pick import leftover_sort_key  # noqa: E402  # re-export
from jevops.pick import sample_records  # noqa: E402


def draft_tree(drafts: Sequence[Mapping[str, Any]]) -> dict[str, dict[str, str]]:
    from jevops.outer import overlay_attr

    blurbs = overlay_attr(FAMILY_BLURB, FAMILY_STRUCTURED, attr="what")
    return kernel_draft_tree(
        drafts,
        blurbs=blurbs,
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
    from jevops.jev import typesafe_session

    loaded, skip = typesafe_session(
        setup=(lra_pca.load_keyfile, lra_pca.pin_typesafe_path),
        fallback=False,
    )
    if skip is not None:
        return skip
    Choice = loaded["Choice"]
    Noul = loaded["Noul"]
    Score = loaded["Score"]
    TypeSafeClient = loaded["TypeSafeClient"]
    tree = draft_tree(drafts)
    from jevops.pick import family_criteria as _family_criteria

    family_criteria = _family_criteria(tree, structured=FAMILY_STRUCTURED, blurbs=FAMILY_BLURB)
    from jevops.jev import expand_questions, instantiate_questions

    questions = instantiate_questions(
        PICK_QUESTION_SPEC,
        choice=Choice,
        noul=Noul,
        score=Score,
        criteria_overlay={"family": family_criteria},
    )
    questions.update(
        expand_questions(
            [item for item in drafts if item.get("kind")],
            ctor=Noul,
            name_fn=lambda item: f"fail_{item.get('kind')}",
            instructions_fn=lambda item: {
                "question": f"Will draft `{item.get('kind')}` fail lake compile?",
                "inspect": f"`drafts` entry `{item.get('kind')}`",
                "focus": "true = P(wrong) for this field (SDE per-field battery).",
            },
            criteria=PICK_FAIL_CRITERIA,
            limit=6,
        )
    )
    from jevops.pick import leaf_choice_questions
    from jevops.pick import pick_state

    questions.update(
        leaf_choice_questions(
            tree,
            ctor=Choice,
            focus=PICK_LEAF_FOCUS,
        )
    )
    state = pick_state(
        record,
        analysis,
        drafts=drafts,
        memory=memory,
        extra={"goal": PICK_GOAL},
    )
    from jevops.jev import choice_head, invoke_system_one, invoke_then_project, noul_attr, record_usage, unpack_response
    from jevops import pick as lra_pick
    from jevops.outer import get_str, head_seq, if_none

    def _project(_result: Any, wall_ms: float, choices: Any, nouls: Any, scores: Any, usage: Any) -> dict[str, Any]:
        _fam_ans, fam_probs, family_conf, fam_choice = choice_head(choices, "family")
        leaf_qs = lra_pick.leaf_qs_from_choices(tree, choices, family_conf=family_conf)
        cut = scores.get("likely_token_cut")
        return lra_pick.rank_from_answers(
            tree=tree,
            fam_probs=fam_probs,
            family_conf=family_conf,
            leaf_qs=leaf_qs,
            drafts=drafts,
            noul_fail=noul_attr(nouls, "will_fail_compile"),
            noul_pca=noul_attr(nouls, "breaks_pca"),
            per_leaf_fail=lra_pick.noul_map(
                nouls, [item.get("kind") for item in head_seq(drafts, 6)], prefix="fail_"
            ),
            failed_stems=lra_bind.failed_skill_stems(if_none(memory, default={}), get_str(record, "name")),
            cut_score=getattr(cut, "score", None),
            usage=usage,
            wall_ms=wall_ms,
            greedy_fam_fallback=fam_choice,
            beam_k=BEAM_K,
            fire_t=FIRE_T,
            fire_t_leaf=FIRE_T_LEAF,
            confident=CONFIDENT,
            uncertain=UNCERTAIN,
            epsilon=EPSILON,
        )

    return invoke_then_project(
        invoke_fn=lambda: invoke_system_one(TypeSafeClient(timeout=45.0), state, questions),
        record_fn=lambda usage, model: record_usage(ledger, usage, model=model),
        unpack_fn=unpack_response,
        model=lra_t1.JEV_MODEL_ID,
        project_fn=_project,
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

    routed = typesafe_intent(
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
    return routed


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

    from jevops.memory import named_success_kinds
    from jevops.memory import port_wins
    from jevops.pick import filter_catalog
    from jevops.walk import COMPOSE_CRITERIA
    from jevops.walk import intent_window

    from jevops.outer import call_if, either, get_list, get_str, if_none, optional_fn, or_list, overlay_map

    from jevops.jev import typesafe_session

    loaded, skip = typesafe_session(
        setup=(lra_pca.load_keyfile, lra_pca.pin_typesafe_path),
        fallback=False,
        families=set(FAMILY_BLURB),
    )
    if skip is not None:
        return skip
    Choice = loaded["Choice"]
    Noul = loaded["Noul"]
    Score = loaded["Score"]
    TypeSafeClient = loaded["TypeSafeClient"]
    from jevops.jev import intent_state
    from jevops.outer import head_chars
    from jevops.pick import family_criteria as _family_criteria
    from jevops.pick import present_families

    mem = if_none(memory, default={})
    name = get_str(record, "name")
    present = present_families(analysis)
    criteria = _family_criteria(present, structured=FAMILY_STRUCTURED, require_structured=True)
    state = intent_state(
        record,
        analysis,
        residuals=call_if(tactics, lambda: lra_port.analyze_residuals(tactics), default={}),
        memory_view={"success_kinds": named_success_kinds(mem, name)},
        window=intent_window(memory),
        extra={
            "head": head_chars(get_list(analysis, "case_labels"), 200),
            "tree_node": tree_node,
            "allow_families": sorted(or_list(allow_families, [])),
            "prior_research": lra_bind.prior_research(mem, name),
            "proposed_skill": lra_bind.propose_skill_from_research(mem, name),
            "memory_wins": port_wins(memory),
        },
    )
    skills = either(
        tactics,
        lambda: lra_port.available_skills(tactics, memory=overlay_map(mem), name=name),
        lambda: {"keep": "No tactics"},
    )
    tree = call_if(
        tactics,
        lambda: lra_port.decision_tree(tactics, memory=overlay_map(mem), name=name),
        default={},
    )
    skills, tree = filter_catalog(
        skills,
        tree,
        allow_skills=allow_skills,
        allow_families=allow_families,
        is_blocked=optional_fn(
            memory is not None, lambda kind: lra_bind.is_blacklisted(memory, name, kind)
        ),
    )
    from jevops.jev import instantiate_questions

    questions = instantiate_questions(
        INTENT_QUESTION_SPEC,
        choice=Choice,
        noul=Noul,
        score=Score,
        criteria_overlay={
            "intent": criteria,
            "compose": overlay_map(COMPOSE_CRITERIA),
            "skill": skills,
        },
    )
    import typesafe_tools as lra_tools
    from jevops.outer import set_if
    from jevops.walk import nest_criteria as _nest_criteria

    nest_criteria = _nest_criteria(
        tree,
        tools=lra_tools.TOOL_CRITERIA,
        subloops=lra_tools.SUBLOOPS,
    )

    set_if(
        questions,
        extra_residual_qs and nest_criteria,
        "nest_child",
        Choice(
            instructions=INTENT_NEST_INSTRUCTIONS,
            criteria=nest_criteria,
        ),
    )
    set_if(
        questions,
        extra_residual_qs,
        "tool_name",
        Choice(
            instructions=INTENT_TOOL_INSTRUCTIONS,
            criteria=lra_tools.TOOL_CRITERIA,
        ),
    )
    residuals = overlay_map(state.get("residuals"))
    from jevops.jev import with_residual_questions

    questions = with_residual_questions(
        questions,
        extra=extra_residual_qs,
        residuals=residuals,
        skills=skills,
        noul_ctor=Noul,
        score_ctor=Score,
        unsafe_instructions_fn=lambda kv: {
            "question": (
                f"Is cutting residual `{kv[0]}` (count={kv[1]}) lake-unsafe "
                "on this script?"
            ),
            "focus": "true = P(wrong to cut). AutoResearch presence feature.",
        },
        help_instructions_fn=lambda kv: f"How much would a *safe* cut of `{kv[0]}` help token count?",
        fail_instructions_fn=lambda sk: {
            "question": f"Will skill `{sk}` fail lake compile?",
            "focus": "true = P(wrong). Do not invoke a fired skill.",
        },
        unsafe_criteria={
            "true": "The residual is required (used binder, extra goals, motive cast, Join witness)",
            "false": "A closed fold of this residual has laked on this or a similar proof",
        },
        help_criteria=[
            "No safe cut",
            "A few tokens",
            "A clear local shortening",
        ],
        fail_criteria={
            "true": "Type mismatch, unknown identifier, or unsolved goals",
            "false": "A binder-safe fold that already laked on this or a similar proof",
        },
    )
    from jevops.jev import invoke_system_one, invoke_then_project, record_usage, unpack_response
    from jevops.pick import intent_from_answers

    return invoke_then_project(
        invoke_fn=lambda: invoke_system_one(TypeSafeClient(timeout=45.0), state, questions),
        record_fn=lambda usage, model: record_usage(ledger, usage, model=model),
        unpack_fn=unpack_response,
        model=lra_t1.JEV_MODEL_ID,
        project_fn=lambda _result, wall_ms, choices, nouls, scores, _usage: intent_from_answers(
            choices=choices,
            scores=scores,
            nouls=nouls,
            skills=skills,
            tree=tree,
            residuals=residuals,
            residual_to_skill=RESIDUAL_TO_SKILL,
            fire_t_residual=FIRE_T_RESIDUAL,
            fire_t=FIRE_T,
            fire_t_leaf=FIRE_T_LEAF,
            confident=CONFIDENT,
            uncertain=UNCERTAIN,
            high_stakes=get_str(record, "name") in HIGH_STAKES,
            tree_node=tree_node,
            wall_ms=wall_ms,
            memory=memory,
            name=name,
            criteria=criteria,
        ),
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

    from jevops.outer import overlay_map

    mem = overlay_map(memory)
    from jevops.outer import ignore_error

    def _warmup() -> dict[str, int]:
        import board_graph as lra_board

        return lra_board.warmup_token_map()

    def _kept() -> dict[str, int]:
        import skill_improve_loop as lra_sk

        return lra_sk.keep_best_board(out)

    from jevops.outer import or_load

    warm = or_load(warmup, lambda: ignore_error(_warmup, default={}))
    kept = or_load(keep, lambda: ignore_error(_kept, default={}))
    from jevops.pick import filter_unsafe_drafts
    from jevops.pick import rank_leftover

    def _drafts(rec: Mapping[str, Any]) -> list[Mapping[str, Any]]:
        from jevops.outer import get_str

        name = get_str(rec, "name")
        body = lra_inner.starting_tactics(rec, out=out, from_best=from_best)
        prior = lra_bind.prior_research(mem, name)
        return filter_unsafe_drafts(
            lra_port.portable_drafts(body, memory=mem, name=name),
            is_blocked=lambda kind: lra_bind.is_blacklisted(mem, name, kind),
            unsafe=overlay_map(prior.get("unsafe")),
            residual_map=lra_port.SKILL_RESIDUAL,
            fire_t=FIRE_T_RESIDUAL,
        )

    def _rf(drafts: list[Mapping[str, Any]], rec: Mapping[str, Any], cut: int) -> float:
        from jevops.outer import first_truthy, get_str

        name = get_str(rec, "name")
        import nca_rankers as lra_rank

        return float(
            first_truthy(
                lra_rank.score_record(drafts, memory=mem, name=name, remaining_cut=cut),
                default=0.0,
            )
        )

    return rank_leftover(
        records,
        drafts_fn=_drafts,
        rf_fn=_rf,
        memory=mem,
        warmup=warm,
        keep=kept,
    )


def run_live(args: argparse.Namespace) -> dict[str, Any]:
    """AutoResearch entry + lake on sampled canaries. Writes evidence; returns payload."""

    _raw, digest, records = lra_splice.load_warmup_records()
    from jevops.outer import arg_value, begin_live_sample, first_int, or_int
    from jevops.pick import ensure_named
    from jevops.pick import filter_by_tokens

    model, landscape, sampled = begin_live_sample(
        records,
        feature_fn=lra_pca.feature_row,
        fit_fn=lra_pca.fit_pca_mca,
        analyze_fn=analyze_proof,
        all_small=args.all_small,
        filter_fn=lambda recs, land: filter_by_tokens(recs, land, cap=MAX_LIVE_TOKENS),
        sample_fn=lambda: sample_records(
            records, k=or_int(arg_value(args, "k", 1, cast=int), 1, floor=1), seed=first_int(args.seed)
        ),
        include=args.include_inits,
        ensure_fn=lambda rows, recs: ensure_named(
            rows, recs, name="Core.InitsUpdatesComm", k=or_int(arg_value(args, "k", 1, cast=int), 1, floor=1)
        ),
    )
    memory = lra_bind.load_memory()
    from jevops.walk import reset_pass_flags
    from jevops.outer import pin_calls

    pin_calls(lambda: reset_pass_flags(memory), lambda: lra_bind.save_memory(memory))()
    sampled = rank_live_records(
        sampled,
        out=args.out,
        from_best=bool(arg_value(args, "from_best", False)),
        memory=memory,
    )

    n_rounds = or_int(arg_value(args, "rounds", 1, cast=int), 1, floor=1)
    from jevops.outer import jev_budget

    ledger = lra_t1.ProblemLedger(
        name="warmup#random-canary",
        max_jev_calls=jev_budget(len(sampled), n_rounds, INNER_MAX_STEPS),
        max_mistral_calls=0,
    )
    rng = random.Random(first_int(args.seed))
    import typesafe_nca as lra_nca_live
    import board_graph as lra_board_live
    import skill_improve_loop as lra_sk_board
    from jevops.outer import memory_counts as _memory_counts
    from jevops.outer import seed_runtime

    seed_runtime(
        memory,
        seed_fn=lra_board_live.seed_nca_from_board,
        overlay_fn=lra_board_live.overlay_live_board,
        keepbest_fn=lambda mem: lra_board_live.seed_keepbest_theorems(
            mem, lra_sk_board.keep_best_board(args.out), warmup=lra_board_live.warmup_token_map()
        ),
    )

    from jevops.outer import call_if, lookup_named, read_text, stripped_or

    def _extra_139() -> dict[str, Any]:
        inits = lookup_named(
            records,
            "Core.InitsUpdatesComm",
            error_cls=RuntimeError,
            miss="unknown warm-up problem: Core.InitsUpdatesComm",
        )
        from jevops.outer import with_key

        return with_key(
            analyze_proof(
                inits,
                tactics=stripped_or(read_text(CANARY_139), ""),
                model=model,
            ),
            "cut",
            "cascade-best-139",
        )

    from jevops.outer import call_if_file

    extra_139 = call_if(args.init_139, lambda: call_if_file(CANARY_139, _extra_139))

    import typesafe_inner as lra_inner
    from jevops.walk import run_sampled

    canaries, lake_rows = run_sampled(
        sampled,
        memory=memory,
        halt_fn=lra_nca_live.should_halt,
        run_fn=lambda rec: lra_inner.run_nested_canary(
            rec,
            args=args,
            memory=memory,
            ledger=ledger,
            rng=rng,
            model=model,
        ),
    )

    mem_path = lra_bind.save_memory(memory)
    gaps = lra_bind.skill_gap_report(memory)
    from jevops.nca import live_status
    from jevops.outer import overlay_map, safe_call

    nca_status = overlay_map(safe_call(live_status, memory, default={}))
    from jevops.jev import canary_live_payload
    from jevops.outer import finish_live_write, write_json, write_json_pair

    return finish_live_write(
        args.out,
        canary_live_payload(
            digest=digest,
            seed=first_int(args.seed),
            k=first_int(args.k),
            n_records=len(records),
            landscape=landscape,
            model=model,
            extra_139=extra_139,
            canaries=canaries,
            lake=lake_rows,
            gaps=gaps,
            mem_path=mem_path,
            memory=_memory_counts(memory),
            nca_status=nca_status,
            ledger=ledger,
        ),
        prefix="random-canary",
        latest="random-canary-latest.json",
        gaps=gaps,
        nca_status=nca_status,
        write_fn=write_json,
        pair_fn=write_json_pair,
    )


if __name__ == "__main__":
    raise SystemExit(main())

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
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence

HERE = Path(__file__).resolve().parent
PAPER_ROOT = HERE.parent
OUT_DEFAULT = PAPER_ROOT / "evidence" / "canaries"
DEFAULT_STATE = Path.home() / ".local/state/ipfs_accelerate_py/vericodegen-2026-lra/track1-lake"
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

PROTOCOL = "LRA/v1"
PR_ID = "PR-9h"
DEFAULT_SEED = 20260917
DEFAULT_K = 3
MAX_LIVE_TOKENS = 700
# Hierarchical + confidence cookbooks (cascade_edits / docs.typesafe.ai).
CONFIDENT = 0.55
FIRE_T = 0.7
FIRE_T_RESIDUAL = 0.5  # AutoResearch: skip a residual skill before it hits lake twice
FIRE_T_LEAF = 0.45  # ident-shorten Noul was ~0.49 and still laked; skip earlier
BEAM_K = 3
EPSILON = 1e-9
UNCERTAIN = 0.60  # consistency cookbook: max-prob floor before acting
HIGH_STAKES = frozenset(
    {"Core.InitsUpdatesComm", "Cslib.CCS.bisimilarity_congr_choice"}
)
NEST_MAX_DEPTH = 3  # TypeSafe recursive skill-tree nests
INNER_MAX_STEPS = 8  # TypeSafe keep-looping steps per canary (shared with nests)
FAMILY_BLURB = {
    "dead_code": "Drop unused have/obtain/rename_i or simp-at-before-simp_all",
    "search_space": "Shrink intros/apply search; never delete a case arm",
    "loop_invariant": "Drop have-facts after induction",
    "strength_reduction": "Replace simp-at runs with simp_all",
    "algebraic_simplification": "Collapse rw/calc/ring/omega into simp or omega",
    "symbol_diffuse": "Closed Lean operator/phrase fill; keep induction/case",
    "pca_keep": "Do not edit; the current script is already locally minimal",
}
FAMILY_STRUCTURED = {
    "dead_code": {
        "what": "Unused rename_i/have whose binders do not appear later",
        "not_for": "Binders still used (trigger1, Hup, destructuring ⟨s2'⟩)",
        "examples": ["drop_unused_binders", "drop_dead_code_MCA_*"],
    },
    "search_space": {
        "what": "Shorter intro/exact/constructor that keeps every case arm",
        "not_for": "Deleting a case arm or applying constructor to a non-inductive goal",
        "examples": ["port_exact_hin_assumption", "port_ski_double_par"],
    },
    "loop_invariant": {
        "what": "Drop a have after induction that is not simp_all fuel",
        "not_for": "Prefix haves before induction (Hk/Hlen) or have ⟨a,b⟩",
        "examples": ["drop_loop_invariant_MCA_*"],
    },
    "strength_reduction": {
        "what": "simp at hyp immediately before simp_all",
        "not_for": "Rewriting rw/omega chains",
        "examples": ["collapse_simp_at"],
    },
    "algebraic_simplification": {
        "what": "Collapse consecutive rw [lemmas] or pack constructor/exact",
        "not_for": "Blind span masks or dropping binders",
        "examples": ["collapse_rw", "port_ski_double_par"],
    },
    "symbol_diffuse": {
        "what": "A phrase already in this script (constructor, intro, <;> simp_all)",
        "not_for": "Random token windows on Cslib/CallElim",
        "examples": ["inits_replay", "SYM_*_phrase_*"],
    },
    "pca_keep": {
        "what": "Leave the current lake-valid script unchanged",
        "not_for": "Any edit",
        "examples": ["keep"],
    },
}


def _tags(record: Mapping[str, Any]) -> list[Any]:
    from jevops.jev import list_field

    return list_field(record, "version_info")


def analyze_proof(
    record: Mapping[str, Any],
    *,
    tactics: Optional[str] = None,
    model: Optional[Mapping[str, Any]] = None,
) -> dict[str, Any]:
    from jevops.pick import analysis_row
    from jevops.pick import hole_rows

    body = (tactics if tactics is not None else lra_fan.tactic_block(record)).strip("\n")
    counts = lra_pca.count_tactics(body)
    families = lra_pca.amenable_families(counts, model) if model else []
    mca_holes = lra_mask.find_holes(body)
    spans = {
        f"span_{span}": len(lra_sym.all_span_windows(body, span, stride=1))
        for span in lra_sym.ONE_HOLE_SPANS
    }
    phrases = [src for src, _dst in lra_sym.PHRASE_ALTS if src in body]
    cases = [span.label for span in lra_fan.case_spans(body)]
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
            "case_labels": cases[:12],
            "n_cases": len(cases),
            "pca_keep": bool(counts.get("n_induction") or counts.get("n_cases")),
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

    from jevops.mask import drop_span
    from jevops.pick import pin_prefix
    from jevops.pick import shorter_bag

    body = tactics.strip("\n")
    push, rows = shorter_bag(body, token_fn=lra_loop.token_count)

    allow = set(allow_families) if allow_families else None

    def wanted(fam: str) -> bool:
        return allow is None or fam in allow

    if wanted("dead_code"):
        unused = lra_bind.drop_unused_binders(body)
        push("drop_unused_binders", unused, {"family": "dead_code", "n_masks": 1})
    if wanted("strength_reduction"):
        simp_at = lra_fan.drop_redundant_simp_at(body)
        push("collapse_simp_at", simp_at, {"family": "strength_reduction"})
    if wanted("algebraic_simplification"):
        rw = lra_pca.collapse_rw_to_simp(body)
        push("collapse_rw", rw, {"family": "algebraic_simplification"})
    if wanted("search_space") or wanted("algebraic_simplification") or wanted("dead_code"):
        blocked = {
            key
            for key, _fn in lra_port.PIPELINE
            if memory is not None and lra_bind.is_blacklisted(memory, name, f"port_{key}")
        }
        if memory is not None:
            blocked |= lra_bind.failed_skill_stems(memory, name)
        for item in lra_port.portable_drafts(
            body, skip=blocked, memory=dict(memory or {}), name=name
        ):
            fam = str(item.get("family") or "search_space")
            kind = str(item["kind"])
            if memory is not None and lra_bind.is_blacklisted(memory, name, kind):
                continue
            extra = {"family": fam, "generator": "portable_rewrites"}
            push(kind, str(item["tactics"]), extra)

    holes = list(lra_mask.find_holes(body))
    rng.shuffle(holes)
    for hole in holes:
        if not wanted(hole.family):
            continue
        kind = f"drop_{hole.family}_{hole.hole_id}"
        nxt = drop_span(body, hole.start, hole.end)
        if memory is not None and lra_bind.is_blacklisted(memory, name, kind, tactics=nxt):
            continue
        if hole.original.strip().startswith(("rename_i ", "have ")) and not lra_bind.safe_to_drop_span(
            body, hole.start, hole.end, hole.original
        ):
            continue
        push(kind, nxt, {"family": hole.family, "n_masks": 1})
        if len(rows) >= n:
            break

    spans = list(lra_sym.ONE_HOLE_SPANS)
    rng.shuffle(spans)
    for span in spans:
        if not wanted("symbol_diffuse"):
            break
        windows = lra_sym.prefer_one_holes(body, span, max_pos=3)
        if not windows:
            continue
        hole = rng.choice(windows)
        if not any(src in hole.original for src, _dst in lra_sym.PHRASE_ALTS) and not any(
            op in hole.original for op in lra_sym.OPERATORS
        ):
            continue
        row = lra_sym.closed_multihole(body, [hole], schedule_id=f"rand_s{span}")
        if row:
            kind = str(row["kind"])
            body_txt = str(row["tactics"])
            if memory is not None and lra_bind.is_blacklisted(memory, name, kind, tactics=body_txt):
                continue
            push(kind, body_txt, {"family": "symbol_diffuse", "span": span})

    for draft in lra_pca.guided_drafts(body, list(families) or [{"family": "dead_code"}], counts):
        if not wanted(str(draft.family)):
            continue
        kind = f"pca_{draft.family}_{draft.draft_id}"
        if memory is not None and lra_bind.is_blacklisted(
            memory, name, kind, tactics=str(draft.tactics)
        ):
            continue
        push(kind, draft.tactics, {"family": draft.family})
        if len(rows) >= n:
            break
    return pin_prefix(rows, n=n, shuffle_fn=rng.shuffle)


from jevops.pick import draft_tree as kernel_draft_tree  # noqa: E402
from jevops.pick import geo_mean  # noqa: E402
from jevops.pick import leftover_sort_key  # noqa: E402  # re-export
from jevops.pick import sample_records  # noqa: E402


def draft_tree(drafts: Sequence[Mapping[str, Any]]) -> dict[str, dict[str, str]]:
    blurbs = dict(FAMILY_BLURB)
    for fam, spec in FAMILY_STRUCTURED.items():
        what = spec.get("what")
        if what:
            blurbs[fam] = str(what)
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
    lra_pca.load_keyfile()
    lra_pca.pin_typesafe_path()
    from ipfs_accelerate_py.typesafe_inference import Choice, Noul, Score, TypeSafeClient, typesafe_configured

    if not typesafe_configured():
        from jevops.jev import skipped

        return skipped("no_key")
    tree = draft_tree(drafts)
    from jevops.pick import family_criteria as _family_criteria

    family_criteria = _family_criteria(tree, structured=FAMILY_STRUCTURED, blurbs=FAMILY_BLURB)
    questions: dict[str, Any] = {
        "family": Choice(
            instructions={
                "question": "Which edit family is the best next step on this lake-valid Lean 4 proof?",
                "focus": "Classify the residual, not every tactic present. Do not write Lean.",
            },
            criteria=family_criteria,
        ),
        "likely_token_cut": Score(
            instructions={
                "question": "How large a token cut if the best family is applied?",
                "note": "Judge expected lake-valid shortening, not the raw string length.",
            },
            criteria=list(lra_fan.LIKELY_SHORTER_CRITERIA),
        ),
        "breaks_pca": Noul(
            instructions={
                "question": "Would the best family drop an induction or case arm?",
                "focus": "true means the edit is the wrong bet.",
            },
            criteria={
                "true": "Deletes induction/case structure",
                "false": "Keeps the PCA skeleton",
            },
        ),
        "will_fail_compile": Noul(
            instructions={
                "question": "Will the greedy leaf fail `lake` compile?",
                "focus": "true = P(wrong); escalate away from that leaf (SDE cascade).",
            },
            criteria={
                "true": {
                    "what": "Unknown identifier, type mismatch, unsolved goals, or dropped case",
                    "examples": ["sweep_rand spans", "port_dot_ctor_apply", "exact ih"],
                },
                "false": {
                    "what": "Used-binder-safe closed fold that previously laked",
                    "examples": ["drop_unused_binders", "collapse_simp_at", "port_intro_x_hin"],
                },
            },
        ),
    }
    from jevops.jev import expand_questions

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
            criteria={
                "true": "Likely unknown identifier, type mismatch, or unsolved goals",
                "false": "A binder-safe fold or a kernel that already laked on this problem",
            },
            limit=6,
        )
    )
    from jevops.pick import leaf_choice_questions
    from jevops.pick import pick_state

    questions.update(
        leaf_choice_questions(
            tree,
            ctor=Choice,
            focus="Prefer drop_unused_binders, collapse_simp_at, port_* over sweep_rand spans.",
        )
    )
    state = pick_state(
        record,
        analysis,
        drafts=drafts,
        memory=memory,
        extra={"goal": "Keep induction/case. Do not write Lean."},
    )
    from jevops.jev import invoke_system_one
    from jevops.jev import record_usage

    result, wall_ms = invoke_system_one(TypeSafeClient(timeout=45.0), state, questions)
    from jevops.jev import choice_head
    from jevops.jev import noul_attr
    from jevops.jev import unpack_response

    choices, nouls, scores, usage = unpack_response(result)
    record_usage(ledger, usage, model=lra_t1.JEV_MODEL_ID)
    fam_ans, fam_probs, family_conf, fam_choice = choice_head(choices, "family")
    from jevops import pick as lra_pick

    leaf_qs = lra_pick.leaf_qs_from_choices(tree, choices, family_conf=family_conf)
    noul_fail = noul_attr(nouls, "will_fail_compile")
    noul_pca = noul_attr(nouls, "breaks_pca")
    per_leaf_fail = lra_pick.noul_map(
        nouls, [item.get("kind") for item in drafts[:6]], prefix="fail_"
    )
    cut = scores.get("likely_token_cut")
    return lra_pick.rank_from_answers(
        tree=tree,
        fam_probs=fam_probs,
        family_conf=family_conf,
        leaf_qs=leaf_qs,
        drafts=drafts,
        noul_fail=noul_fail,
        noul_pca=noul_pca,
        per_leaf_fail=per_leaf_fail,
        failed_stems=lra_bind.failed_skill_stems(memory or {}, str(record.get("name") or "")),
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


# Residual name -> pipeline skill to skip when Noul says cutting it is unsafe.
RESIDUAL_TO_SKILL: dict[str, tuple[str, ...]] = {
    "intros_x_Hin": ("unused_intros",),
    "intro_then_simp_all": ("drop_intro_before_simp_all",),
    "try_simp_all": ("drop_try_simp_all",),
    "apply_semi_assumption": ("semi_assumption",),
    "use_then_exact": ("use_exact", "use_exact_reuse"),
    "have": (),  # drop_unused_binders is a named skill, not a port_ fold
    "ctor_lone": ("ctor_pair_exacts",),
    "grind": ("repeat_par_grind", "grind_only_to_grind"),
    "repeated_simp_list": ("hoist_repeated_simp",),
    "inner_simp_subset": ("redundant_inner_simp",),
    "trailing_tuple_comma": ("trailing_tuple_comma",),
}


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

    lra_pca.load_keyfile()
    lra_pca.pin_typesafe_path()
    from ipfs_accelerate_py.typesafe_inference import Choice, Noul, Score, TypeSafeClient, typesafe_configured

    if not typesafe_configured():
        from jevops.jev import skipped

        return skipped("no_key", families=set(FAMILY_BLURB))
    from jevops.jev import intent_state
    from jevops.pick import family_criteria as _family_criteria
    from jevops.pick import present_families

    present = present_families(analysis)
    criteria = _family_criteria(present, structured=FAMILY_STRUCTURED, require_structured=True)
    state = intent_state(
        record,
        analysis,
        residuals=lra_port.analyze_residuals(tactics) if tactics else {},
        memory_view={"success_kinds": named_success_kinds(memory or {}, str(record.get("name") or ""))},
        window=intent_window(memory),
        extra={
            "head": str(analysis.get("case_labels") or [])[:200],
            "tree_node": tree_node,
            "allow_families": sorted(allow_families or []),
            "prior_research": lra_bind.prior_research(memory or {}, str(record.get("name") or "")),
            "proposed_skill": lra_bind.propose_skill_from_research(
                memory or {}, str(record.get("name") or "")
            ),
            "memory_wins": port_wins(memory),
        },
    )
    skills = (
        lra_port.available_skills(tactics, memory=dict(memory or {}), name=str(record.get("name") or ""))
        if tactics
        else {"keep": "No tactics"}
    )
    tree = lra_port.decision_tree(
        tactics, memory=dict(memory or {}), name=str(record.get("name") or "")
    ) if tactics else {}
    name = str(record.get("name") or "")
    skills, tree = filter_catalog(
        skills,
        tree,
        allow_skills=allow_skills,
        allow_families=allow_families,
        is_blocked=(lambda kind: lra_bind.is_blacklisted(memory, name, kind)) if memory is not None else None,
    )
    questions: dict[str, Any] = {
            "intent": Choice(
                instructions={
                    "question": "Which tactic family should the next denoise step generate drafts for?",
                    "focus": "Route to one handler. pca_keep means skip lake. Do not write Lean.",
                },
                criteria=criteria,
            ),
            "complexity": Score(
                instructions="How hard is a safe shorter fold on this script?",
                criteria=[
                    "One-line portable fold (intro/assumption/simp_at)",
                    "A few local MCA drops",
                    "No remaining lake-valid cut",
                ],
            ),
            "already_minimal": Noul(
                instructions={
                    "question": "Is this script already locally minimal (no lake-valid shorter fold)?",
                    "focus": "true = skip lake this round.",
                },
                criteria={
                    "true": "Every remaining edit drops a used binder or breaks a case arm",
                    "false": "A closed fold such as unused intros or exact→assumption remains",
                },
            ),
            "compose": Choice(
                instructions={
                    "question": "Apply one skill, the pipeline, or nest a TypeSafe loop on a child of the skill decision tree?",
                    "focus": "nest opens a recursive inner loop on one family/skill. Do not write Lean.",
                },
                criteria=dict(COMPOSE_CRITERIA),
            ),
            "skill": Choice(
                instructions={
                    "question": "Which named kernel should code invoke next (skill suggestion)?",
                    "focus": "keep if none is lake-safe. Do not write Lean.",
                },
                criteria=skills,
            ),
        }
    import typesafe_tools as _lra_tools_tree
    from jevops.walk import nest_criteria as _nest_criteria

    nest_criteria = _nest_criteria(
        tree,
        tools=_lra_tools_tree.TOOL_CRITERIA,
        subloops=_lra_tools_tree.SUBLOOPS,
    )
    if extra_residual_qs and nest_criteria:
        questions["nest_child"] = Choice(
            instructions={
                "question": "If compose is nest/spawn, which child of the skill decision tree or named subloop should run?",
                "focus": "A family, named skill, or registered subloop. Do not write Lean.",
            },
            criteria=nest_criteria,
        )
    import typesafe_tools as lra_tools

    if extra_residual_qs:
        questions["tool_name"] = Choice(
            instructions={
                "question": "If compose is analyze, which static-analysis tool should TypeSafe run?",
                "focus": "Navigate skills; do not write Lean; do not call docker0.",
            },
            criteria=lra_tools.TOOL_CRITERIA,
        )
    residuals = dict(state.get("residuals") or {})
    from jevops.jev import expand_questions

    if extra_residual_qs:
        questions.update(
            expand_questions(
                list(residuals.items()),
                ctor=Noul,
                name_fn=lambda kv: f"unsafe_{kv[0]}",
                instructions_fn=lambda kv: {
                    "question": (
                        f"Is cutting residual `{kv[0]}` (count={kv[1]}) lake-unsafe "
                        "on this script?"
                    ),
                    "focus": "true = P(wrong to cut). AutoResearch presence feature.",
                },
                criteria={
                    "true": "The residual is required (used binder, extra goals, motive cast, Join witness)",
                    "false": "A closed fold of this residual has laked on this or a similar proof",
                },
                limit=6,
            )
        )
        questions.update(
            expand_questions(
                list(residuals.items()),
                ctor=Score,
                name_fn=lambda kv: f"help_{kv[0]}",
                instructions_fn=lambda kv: f"How much would a *safe* cut of `{kv[0]}` help token count?",
                criteria=[
                    "No safe cut",
                    "A few tokens",
                    "A clear local shortening",
                ],
                limit=6,
            )
        )
    questions.update(
        expand_questions(
            list(skills),
            ctor=Noul,
            name_fn=lambda sk: f"fail_skill_{sk}",
            instructions_fn=lambda sk: {
                "question": f"Will skill `{sk}` fail lake compile?",
                "focus": "true = P(wrong). Do not invoke a fired skill.",
            },
            criteria={
                "true": "Type mismatch, unknown identifier, or unsolved goals",
                "false": "A binder-safe fold that already laked on this or a similar proof",
            },
            limit=6,
            skip=("keep",),
        )
    )
    from jevops.jev import invoke_system_one
    from jevops.jev import record_usage
    from jevops.jev import unpack_response
    from jevops.pick import intent_from_answers

    result, wall_ms = invoke_system_one(TypeSafeClient(timeout=45.0), state, questions)
    usage = dict(getattr(result, "usage", None) or {})
    record_usage(ledger, usage, model=lra_t1.JEV_MODEL_ID)
    choices, nouls, scores, _usage = unpack_response(result)
    return intent_from_answers(
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
        high_stakes=record.get("name") in HIGH_STAKES,
        tree_node=tree_node,
        wall_ms=wall_ms,
        memory=memory,
        name=str(record.get("name") or ""),
        criteria=criteria,
    )


def self_check() -> dict[str, Any]:
    _raw, digest, records = lra_splice.load_warmup_records()
    rows = [lra_pca.feature_row(item) for item in records]
    model = lra_pca.fit_pca_mca(rows)
    sampled = sample_records(records, k=2, seed=1)
    analyses = [analyze_proof(item, model=model) for item in sampled]
    drafts = random_drafts(
        lra_fan.tactic_block(sampled[0]),
        random.Random(1),
        n=4,
        families=analyses[0].get("families") or [],
        counts=analyses[0].get("counts"),
    )
    return {
        "ok": (
            digest == lra_splice.FROZEN_WARMUP_SHA256
            and len(records) == lra_splice.WARMUP_N
            and len(sampled) == 2
            and sample_records(records, k=2, seed=1)[0].get("name") == sampled[0].get("name")
            and all(int(item["n_tokens"]) > 0 for item in analyses)
            and all(isinstance(item.get("families"), list) for item in analyses)
            and abs(geo_mean([0.81, 0.81]) - 0.81) < 1e-9
        ),
        "n_records": len(records),
        "warmup_jsonl_sha256": digest,
        "sample_names": [item.get("name") for item in sampled],
        "n_random_drafts": len(drafts),
        "called_docker0": False,
        "arena_score": None,
        "official_track2": False,
    }


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
        payload = self_check()
        print(json.dumps(payload, indent=2, sort_keys=True))
        if args.self_check and not args.live:
            return 0 if payload["ok"] else 1
        if not args.live:
            return 0 if payload["ok"] else 1

    payload = run_live(args)
    if not getattr(args, "quiet", False):
        print(json.dumps(payload, indent=2, sort_keys=True, default=str))
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

    mem = dict(memory or {})
    warm = dict(warmup or {})
    kept = dict(keep or {})
    if not warm:
        try:
            import board_graph as lra_board

            warm = lra_board.warmup_token_map()
        except Exception:
            warm = {}
    if not kept:
        try:
            import skill_improve_loop as lra_sk

            kept = lra_sk.keep_best_board(out)
        except Exception:
            kept = {}
    from jevops.pick import filter_unsafe_drafts
    from jevops.pick import rank_leftover

    def _drafts(rec: Mapping[str, Any]) -> list[Mapping[str, Any]]:
        name = str(rec.get("name") or "")
        body = lra_inner.starting_tactics(rec, out=out, from_best=from_best)
        prior = lra_bind.prior_research(mem, name)
        return filter_unsafe_drafts(
            lra_port.portable_drafts(body, memory=mem, name=name),
            is_blocked=lambda kind: lra_bind.is_blacklisted(mem, name, kind),
            unsafe=dict(prior.get("unsafe") or {}),
            residual_map=lra_port.SKILL_RESIDUAL,
            fire_t=FIRE_T_RESIDUAL,
        )

    def _rf(drafts: list[Mapping[str, Any]], rec: Mapping[str, Any], cut: int) -> float:
        name = str(rec.get("name") or "")
        import nca_rankers as lra_rank

        return float(lra_rank.score_record(drafts, memory=mem, name=name, remaining_cut=cut) or 0.0)

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
    rows = [lra_pca.feature_row(item) for item in records]
    model = lra_pca.fit_pca_mca(rows)
    from jevops.pick import ensure_named
    from jevops.pick import filter_by_tokens

    landscape = [analyze_proof(item, model=model) for item in records]
    if args.all_small:
        sampled = filter_by_tokens(records, landscape, cap=MAX_LIVE_TOKENS)
    else:
        sampled = sample_records(records, k=max(1, int(args.k)), seed=int(args.seed))
    if args.include_inits:
        sampled = ensure_named(sampled, records, name="Core.InitsUpdatesComm", k=max(1, int(args.k)))
    memory = lra_bind.load_memory()
    from jevops.walk import reset_pass_flags

    reset_pass_flags(memory)
    lra_bind.save_memory(memory)
    sampled = rank_live_records(
        sampled,
        out=args.out,
        from_best=bool(getattr(args, "from_best", False)),
        memory=memory,
    )

    n_rounds = max(1, int(args.rounds))
    ledger = lra_t1.ProblemLedger(
        name="warmup#random-canary",
        max_jev_calls=max(8, len(sampled) * max(n_rounds, INNER_MAX_STEPS) * 3 + 2),
        max_mistral_calls=0,
    )
    rng = random.Random(int(args.seed))
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

    extra_139 = None
    if args.init_139 and CANARY_139.is_file():
        inits = next(item for item in records if item.get("name") == "Core.InitsUpdatesComm")
        extra_139 = analyze_proof(
            inits,
            tactics=CANARY_139.read_text(encoding="utf-8").strip("\n"),
            model=model,
        )
        extra_139["cut"] = "cascade-best-139"

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

    args.out.mkdir(parents=True, exist_ok=True)
    mem_path = lra_bind.save_memory(memory)
    gaps = lra_bind.skill_gap_report(memory)
    from jevops.nca import live_status
    from jevops.outer import closed_evidence
    from jevops.outer import landscape_rows
    from jevops.outer import safe_call
    from jevops.outer import write_json_pair

    nca_status = safe_call(live_status, memory, default={}) or {}
    (args.out / "skill-analysis.json").write_text(
        json.dumps({"schema": "lra-skill-analysis/v1", "gaps": gaps, "nca_status": nca_status}, indent=2, sort_keys=True)
        + "\n"
    )
    payload = {
        "schema": "lra-random-canary/v1",
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "seed": int(args.seed),
        "k": int(args.k),
        "warmup_jsonl_sha256": digest,
        "n_records": len(records),
        "n_tag_cells": sum(int(item["n_tags"]) for item in landscape),
        "pca": {
            "explained_ratio": (model.get("explained_ratio") or [])[:6],
            "principal0": (model.get("principal") or [{}])[0].get("loadings"),
        },
        "landscape": landscape_rows(landscape),
        "inits_139": extra_139,
        "canaries": canaries,
        "lake": lake_rows,
        "skill_analysis": gaps,
        "memory_path": str(mem_path),
        "memory": _memory_counts(memory),
        "nca_status": nca_status,
        **closed_evidence(),
        "ledger": ledger.as_dict() if hasattr(ledger, "as_dict") else {"jev_calls": ledger.jev_calls},
    }
    write_json_pair(args.out, payload, prefix="random-canary", latest="random-canary-latest.json")
    return payload


if __name__ == "__main__":
    raise SystemExit(main())

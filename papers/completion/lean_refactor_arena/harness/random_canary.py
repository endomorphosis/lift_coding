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
import time
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
    raw = record.get("version_info")
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except json.JSONDecodeError:
            return []
    return list(raw) if isinstance(raw, list) else []


def analyze_proof(
    record: Mapping[str, Any],
    *,
    tactics: Optional[str] = None,
    model: Optional[Mapping[str, Any]] = None,
) -> dict[str, Any]:
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
    return {
        "name": record.get("name"),
        "source": record.get("source"),
        "n_tags": len(_tags(record)),
        "n_tokens": lra_loop.token_count(body),
        "n_lines": counts["n_lines"],
        "counts": {k: int(v) for k, v in counts.items()},
        "families": families,
        "mca_holes": [
            {
                "id": hole.hole_id,
                "family": hole.family,
                "n_tokens": lra_loop.token_count(hole.original),
                "head": hole.original.strip()[:80],
                "used_binders": lra_bind.binders_used_later(body, hole.start, hole.end, hole.original),
                "safe_to_drop": lra_bind.safe_to_drop_span(body, hole.start, hole.end, hole.original),
            }
            for hole in mca_holes
        ],
        "n_mca_holes": len(mca_holes),
        "eligible_spans": spans,
        "catalog_phrases_present": phrases,
        "case_labels": cases[:12],
        "n_cases": len(cases),
        "pca_keep": bool(counts.get("n_induction") or counts.get("n_cases")),
    }


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

    body = tactics.strip("\n")
    base = lra_loop.token_count(body)
    rows: list[dict[str, Any]] = []
    seen: set[str] = {body}

    def push(kind: str, nxt: str, extra: Optional[dict[str, Any]] = None) -> None:
        nxt = nxt.strip("\n")
        if not nxt or nxt in seen:
            return
        tok = lra_loop.token_count(nxt)
        if tok >= base:
            return
        seen.add(nxt)
        item = {
            "kind": kind,
            "tactics": nxt,
            "token_count": tok,
            "generator": "random_canary",
            "llm": "off",
        }
        if extra:
            item.update(extra)
        rows.append(item)

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
        nxt = (body[: hole.start] + body[hole.end :]).strip("\n")
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
    portable = [row for row in rows if str(row.get("kind") or "").startswith("port_")]
    others = [row for row in rows if row not in portable]
    rng.shuffle(others)
    pinned = portable + others
    return pinned[: max(n, len(portable))]


def geo_mean(probs: Sequence[float]) -> float:
    live = [max(float(p), EPSILON) for p in probs]
    prod = 1.0
    for item in live:
        prod *= item
    return prod ** (1.0 / max(1, len(live)))


def draft_tree(drafts: Sequence[Mapping[str, Any]]) -> dict[str, dict[str, str]]:
    tree: dict[str, dict[str, str]] = {}
    for item in drafts:
        fam = str(item.get("family") or "search_space")
        kind = str(item.get("kind") or "")
        if not kind:
            continue
        blurb = FAMILY_STRUCTURED.get(fam, {}).get("what", FAMILY_BLURB.get(fam, fam))
        tree.setdefault(fam, {})[kind] = f"{kind}; {item.get('token_count')} tok; {blurb}"
    if not tree:
        tree = {"pca_keep": {"keep": "No shorter draft"}}
    return tree


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
        return {"skipped": True, "reason": "no_key"}
    tree = draft_tree(drafts)
    family_criteria = {
        fam: FAMILY_STRUCTURED.get(fam, {"what": FAMILY_BLURB.get(fam, fam)})
        for fam in tree
    }
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
    for item in list(drafts)[:6]:
        kind = str(item.get("kind") or "")
        if not kind:
            continue
        questions[f"fail_{kind}"] = Noul(
            instructions={
                "question": f"Will draft `{kind}` fail lake compile?",
                "inspect": f"`drafts` entry `{kind}`",
                "focus": "true = P(wrong) for this field (SDE per-field battery).",
            },
            criteria={
                "true": "Likely unknown identifier, type mismatch, or unsolved goals",
                "false": "A binder-safe fold or a kernel that already laked on this problem",
            },
        )
    for fam, kids in tree.items():
        if len(kids) == 1:
            continue
        questions[f"leaf_{fam}"] = Choice(
            instructions={
                "question": f"Inside `{fam}`, which leaf is most likely to lake-compile AND cut tokens?",
                "focus": "Prefer drop_unused_binders, collapse_simp_at, port_* over sweep_rand spans.",
            },
            criteria=dict(kids),
        )
    state = {
        "problem": {"name": record.get("name"), "source": record.get("source")},
        "n_tokens": analysis.get("n_tokens"),
        "n_mca_holes": analysis.get("n_mca_holes"),
        "counts": analysis.get("counts"),
        "holes": analysis.get("mca_holes"),
        "families": analysis.get("families"),
        "drafts": [
            {"kind": item.get("kind"), "family": item.get("family"), "tokens": item.get("token_count")}
            for item in drafts[:16]
        ],
        "memory": {
            "success_kinds": sorted(
                {str(item.get("kind")) for item in (memory or {}).get("successes") or [] if item.get("name") == record.get("name")}
            )[:12],
            "blacklist": [
                key
                for key in (memory or {}).get("blacklist") or []
                if str(key).startswith(str(record.get("name") or ""))
            ][:12],
        },
        "goal": "Keep induction/case. Do not write Lean.",
    }
    started = time.perf_counter()
    result = TypeSafeClient(timeout=45.0).system_one(state, questions)
    usage = dict(getattr(result, "usage", None) or {})
    if ledger is not None:
        inn = int(usage.get("input_tokens") or usage.get("prompt_tokens") or 200)
        out = int(usage.get("output_tokens") or usage.get("completion_tokens") or 0)
        ledger.record("jev", input_tokens=inn, output_tokens=out, model=lra_t1.JEV_MODEL_ID)
    choices = getattr(result, "choices", None) or {}
    scores = getattr(result, "scores", None) or {}
    nouls = getattr(result, "nouls", None) or {}
    fam_ans = choices.get("family")
    fam_probs = dict(getattr(fam_ans, "probabilities", None) or {})
    family_conf = float(getattr(fam_ans, "confidence", None) or 0.0)
    leaf_qs: dict[str, dict[str, Any]] = {}
    for fam, kids in tree.items():
        if len(kids) == 1:
            only = next(iter(kids))
            leaf_qs[fam] = {"choice": only, "confidence": 1.0, "probabilities": {only: 1.0}}
            continue
        ans = choices.get(f"leaf_{fam}")
        probs = dict(getattr(ans, "probabilities", None) or {})
        leaf_qs[fam] = {
            "choice": getattr(ans, "choice", None),
            "confidence": float(getattr(ans, "confidence", None) or 0.0),
            "probabilities": {k: float(probs.get(k) or 0.0) for k in kids},
        }
    fam_rank = sorted(tree, key=lambda fam: float(fam_probs.get(fam) or 0.0), reverse=True)
    paths: list[dict[str, Any]] = []
    for fam in fam_rank[:BEAM_K]:
        leaf_q = leaf_qs.get(fam) or {}
        for leaf, _desc in tree[fam].items():
            score = geo_mean(
                [float(fam_probs.get(fam) or 0.0), float((leaf_q.get("probabilities") or {}).get(leaf) or 0.0)]
            )
            paths.append(
                {
                    "family": fam,
                    "leaf": leaf,
                    "path_score": score,
                    "family_p": float(fam_probs.get(fam) or 0.0),
                    "leaf_p": float((leaf_q.get("probabilities") or {}).get(leaf) or 0.0),
                    "family_confidence": family_conf,
                    "leaf_confidence": float(leaf_q.get("confidence") or 0.0),
                }
            )
    paths.sort(key=lambda item: item["path_score"], reverse=True)
    top = paths[0]["path_score"] if paths else 0.0
    second = paths[1]["path_score"] if len(paths) > 1 else EPSILON
    greedy_leaf = paths[0]["leaf"] if paths else None
    noul_fail = float(getattr(nouls.get("will_fail_compile"), "noul", 0.0) or 0.0)
    noul_pca = float(getattr(nouls.get("breaks_pca"), "noul", 0.0) or 0.0)
    per_leaf_fail = {
        str(item.get("kind")): float(getattr(nouls.get(f"fail_{item.get('kind')}"), "noul", 0.0) or 0.0)
        for item in drafts[:6]
        if item.get("kind")
    }
    failed_stems = lra_bind.failed_skill_stems(memory or {}, str(record.get("name") or ""))
    fired_leaves = set()
    for kind, prob in per_leaf_fail.items():
        if prob > FIRE_T:
            fired_leaves.add(kind)
        elif prob > FIRE_T_LEAF and (
            kind in failed_stems or kind.replace("port_", "") in failed_stems
        ):
            fired_leaves.add(kind)
    fired = noul_fail > FIRE_T or noul_pca > FIRE_T or bool(fired_leaves)
    beam_kinds = [item["leaf"] for item in paths if item["leaf"] and item["leaf"] not in fired_leaves]
    if not beam_kinds:
        beam_kinds = [item["leaf"] for item in paths if item["leaf"]]
    if fired and greedy_leaf in beam_kinds and (noul_fail > FIRE_T or greedy_leaf in fired_leaves):
        beam_kinds = [k for k in beam_kinds if k != greedy_leaf]
    cut = scores.get("likely_token_cut")
    cut_norm = min(1.0, float(getattr(cut, "score", None) or 0.0) / 2.0)
    for path in paths:
        noul = float(per_leaf_fail.get(str(path["leaf"]), noul_fail) or 0.0)
        path["composite"] = (
            0.45 * (1.0 - noul)
            + 0.25 * float(path["leaf_p"])
            + 0.20 * float(path["family_p"])
            + 0.10 * cut_norm
        )
    paths.sort(key=lambda item: float(item.get("composite") or 0.0), reverse=True)
    beam_kinds = [item["leaf"] for item in paths if item["leaf"] and item["leaf"] not in fired_leaves]
    leaf_p = float(paths[0]["leaf_p"]) if paths else 0.0
    leaf_conf = float(paths[0]["leaf_confidence"]) if paths else 0.0
    abstain = family_conf < CONFIDENT or max(leaf_p, leaf_conf) < UNCERTAIN
    if abstain:
        safe = [k for k in ("drop_unused_binders", "collapse_simp_at") if any(item.get("kind") == k for item in drafts)]
        beam_kinds = safe + [k for k in beam_kinds if k not in safe]
    greedy_fam = paths[0]["family"] if paths else getattr(fam_ans, "choice", None)
    return {
        "skipped": False,
        "best_family": greedy_fam,
        "family_confidence": family_conf,
        "family_probabilities": {k: float(fam_probs.get(k) or 0.0) for k in tree},
        "best_draft": greedy_leaf,
        "draft_confidence": paths[0]["leaf_confidence"] if paths else None,
        "draft_probabilities": (leaf_qs.get(str(greedy_fam)) or {}).get("probabilities") or {},
        "likely_token_cut": getattr(cut, "score", None),
        "beam_kinds": beam_kinds[:8],
        "path_score": top,
        "separation": top / max(second, EPSILON),
        "abstain": abstain,
        "noul_fail": noul_fail,
        "noul_pca": noul_pca,
        "per_leaf_fail": per_leaf_fail,
        "fired_leaves": sorted(fired_leaves),
        "fired": fired,
        "usage": usage,
        "wall_ms": (time.perf_counter() - started) * 1000.0,
        "jev_generated_lean": False,
        "arena_score": None,
        "composite": (paths[0].get("composite") if paths else None),
    }


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


def bias_compose_no_drafts(
    compose: str,
    *,
    memory: Optional[Mapping[str, Any]] = None,
    skills: Optional[Mapping[str, Any]] = None,
    skill: str = "keep",
    name: str = "",
) -> str:
    """When drafts are exhausted and budget is alive, program NCA instruct next."""

    obs = dict((memory or {}).get("observations") or {})
    tree = (obs.get("no_drafts_tree_by") or {}).get(name)
    instructed = (obs.get("no_drafts_instructed_by") or {}).get(name)
    if not tree or instructed:
        return compose
    if compose in {"instruct", "heal", "return", "call", "nest", "spawn"}:
        return compose
    portable = [key for key in (skills or {}) if key != "keep"]
    if portable and str(skill or "keep") not in {"keep", "None", ""}:
        return compose
    return "instruct"


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

    lra_pca.load_keyfile()
    lra_pca.pin_typesafe_path()
    from ipfs_accelerate_py.typesafe_inference import Choice, Noul, Score, TypeSafeClient, typesafe_configured

    if not typesafe_configured():
        return {"skipped": True, "families": set(FAMILY_BLURB), "reason": "no_key"}
    present = {str(item.get("family")) for item in analysis.get("families") or []}
    present.update({"dead_code", "search_space", "pca_keep"})
    criteria = {fam: FAMILY_STRUCTURED.get(fam, {"what": FAMILY_BLURB.get(fam, fam)}) for fam in present if fam in FAMILY_STRUCTURED}
    state = {
        "problem": {"name": record.get("name"), "source": record.get("source")},
        "n_tokens": analysis.get("n_tokens"),
        "counts": analysis.get("counts"),
        "n_mca_holes": analysis.get("n_mca_holes"),
        "safe_holes": [h for h in analysis.get("mca_holes") or [] if h.get("safe_to_drop")],
        "residuals": lra_port.analyze_residuals(tactics) if tactics else {},
        "memory": {
            "success_kinds": sorted(
                {
                    str(item.get("kind"))
                    for item in (memory or {}).get("successes") or []
                    if item.get("name") == record.get("name")
                }
            )[:8],
        },
        "tape_window": list((memory or {}).get("_tape_window") or [])[:16],
        "stack_top": list((memory or {}).get("_stack_top") or [])[:3],
        "board_window": list(((memory or {}).get("nca") or {}).get("board_window") or [])[:8],
        "head": str(analysis.get("case_labels") or [])[:200],
        "tree_node": tree_node,
        "allow_families": sorted(allow_families or []),
        "prior_research": lra_bind.prior_research(memory or {}, str(record.get("name") or "")),
        "proposed_skill": lra_bind.propose_skill_from_research(
            memory or {}, str(record.get("name") or "")
        ),
        "memory_wins": {
            str(row.get("kind")): 1
            for row in (memory or {}).get("successes") or []
            if str(row.get("kind") or "").startswith("port_")
        },
    }
    skills = (
        lra_port.available_skills(tactics, memory=dict(memory or {}), name=str(record.get("name") or ""))
        if tactics
        else {"keep": "No tactics"}
    )
    if allow_skills:
        skills = {
            key: val
            for key, val in skills.items()
            if key == "keep" or key in allow_skills or key.replace("port_", "") in allow_skills
        }
    tree = lra_port.decision_tree(
        tactics, memory=dict(memory or {}), name=str(record.get("name") or "")
    ) if tactics else {}
    if allow_families:
        tree = {fam: kids for fam, kids in tree.items() if fam in allow_families}
        allowed_kinds = {kid for kids in tree.values() for kid in kids}
        skills = {key: val for key, val in skills.items() if key == "keep" or key in allowed_kinds}
    if memory is not None:
        skills = {
            key: val
            for key, val in skills.items()
            if key == "keep" or not lra_bind.is_blacklisted(memory, str(record.get("name") or ""), key)
        }
        if not skills:
            skills = {"keep": "No remaining un-blacklisted skill"}
    started = time.perf_counter()
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
                criteria={
                    "keep": {"what": "No skill; pop this tree node", "not_for": "When a shorter closed fold exists"},
                    "single": {"what": "Apply only the winning skill at this node", "not_for": "When two skills commute and both shorten"},
                    "pipeline": {
                        "what": "Compose un-blacklisted skills in memory-weighted order (keep-structure first)",
                        "not_for": "When a step is Noul-fired or binder-unsafe",
                    },
                    "nest": {
                        "what": "Open a nested TypeSafe loop on one child family/skill of the decision tree, then keep looping here",
                        "not_for": "When this node is already a leaf or already_minimal",
                    },
                    "spawn": {
                        "what": "Spawn a callable named subloop and join its return (skill_walk, analyze, diffuse)",
                        "not_for": "When no registered subloop exists",
                    },
                    "analyze": {
                        "what": "Run a static-analysis tool (kg/ast/exports/mcp/diffuse/tree) then keep looping; no llm_router",
                        "not_for": "When the next step is a lake apply",
                    },
                    "self_improve": {
                        "what": "Mint/expand keep-structure skills from memory without llm_router",
                        "not_for": "When a lake-valid portable draft is already in hand",
                    },
                    "invoke_router": {
                        "what": "Autonomously call llm_router grok for a closed skill action",
                        "not_for": "The default TypeSafe self-improve path",
                    },
                    "return": {
                        "what": "Pop this subloop and return tactics/observations to the parent",
                        "not_for": "The root walker unless the outer Grok step is done",
                    },
                    "tick": {
                        "what": "NCA tick: feed each cell its last state + neighbors + TypeSafe scores",
                        "not_for": "When no grid has been seeded",
                    },
                    "fork": {
                        "what": "Fork high-energy cells as returnable subagent subloops (cap 4)",
                        "not_for": "Unbounded nested grok",
                    },
                    "mutate": {
                        "what": "Gated mutation of pipeline/skills/tactics from NCA energy",
                        "not_for": "Arbitrary repo file rewrites",
                    },
                    "hook": {
                        "what": "Hook, walk, and evaluate a harness module (AST/import/tests)",
                        "not_for": "Paths outside the paper harness",
                    },
                    "call": {
                        "what": "CALL ptr://skill|theorem|module|tool|cell|subloop|mcpplusplus|goal|task|codepath/…; child injects context on RETURN",
                        "not_for": "Unknown pointers, live P2P, docker0, or depth > 3",
                    },
                    "instruct": {
                        "what": "Compile NCA IR (datasets autoencoder/compiler if present) and program work ops; hosted Leanstral JSON only, never docker0",
                        "not_for": "Letting Leanstral write Lean without lake",
                    },
                    "heal": {
                        "what": "Diagnose malformed NCA/tape/stack/program_state and apply closed TypeSafe-ranked repairs",
                        "not_for": "Healthy state or rewriting Lean",
                    },
                },
            ),
            "skill": Choice(
                instructions={
                    "question": "Which named kernel should code invoke next (skill suggestion)?",
                    "focus": "keep if none is lake-safe. Do not write Lean.",
                },
                criteria=skills,
            ),
        }
    nest_criteria = {
        fam: {"what": f"Nested TypeSafe loop over {fam}: {', '.join(kids)[:160]}"}
        for fam, kids in tree.items()
        if kids
    }
    for kids in tree.values():
        for kid in kids[:8]:
            nest_criteria.setdefault(kid, {"what": f"Nested TypeSafe loop on skill {kid}"})
    import typesafe_tools as _lra_tools_tree

    nest_criteria.setdefault("skill_walk", {"what": "Spawn the TypeSafe skill-walk subloop and join its return"})
    for tool_name, spec in _lra_tools_tree.TOOL_CRITERIA.items():
        nest_criteria.setdefault(tool_name, spec)
    for sub_name in _lra_tools_tree.SUBLOOPS:
        nest_criteria.setdefault(sub_name, {"what": f"Spawn registered subloop {sub_name}"})
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
    if extra_residual_qs:
        for residual, count in list(residuals.items())[:6]:
            questions[f"unsafe_{residual}"] = Noul(
                instructions={
                    "question": (
                        f"Is cutting residual `{residual}` (count={count}) lake-unsafe "
                        "on this script?"
                    ),
                    "focus": "true = P(wrong to cut). AutoResearch presence feature.",
                },
                criteria={
                    "true": "The residual is required (used binder, extra goals, motive cast, Join witness)",
                    "false": "A closed fold of this residual has laked on this or a similar proof",
                },
            )
            questions[f"help_{residual}"] = Score(
                instructions=f"How much would a *safe* cut of `{residual}` help token count?",
                criteria=[
                    "No safe cut",
                    "A few tokens",
                    "A clear local shortening",
                ],
            )
    for sk in list(skills)[:6]:
        if sk == "keep":
            continue
        questions[f"fail_skill_{sk}"] = Noul(
            instructions={
                "question": f"Will skill `{sk}` fail lake compile?",
                "focus": "true = P(wrong). Do not invoke a fired skill.",
            },
            criteria={
                "true": "Type mismatch, unknown identifier, or unsolved goals",
                "false": "A binder-safe fold that already laked on this or a similar proof",
            },
        )
    result = TypeSafeClient(timeout=45.0).system_one(state, questions)
    usage = dict(getattr(result, "usage", None) or {})
    if ledger is not None:
        inn = int(usage.get("input_tokens") or usage.get("prompt_tokens") or 200)
        out = int(usage.get("output_tokens") or usage.get("completion_tokens") or 0)
        ledger.record("jev", input_tokens=inn, output_tokens=out, model=lra_t1.JEV_MODEL_ID)
    choices = getattr(result, "choices", None) or {}
    scores = getattr(result, "scores", None) or {}
    nouls = getattr(result, "nouls", None) or {}
    intent = choices.get("intent")
    picked = str(getattr(intent, "choice", None) or "search_space")
    conf = float(getattr(intent, "confidence", None) or 0.0)
    probs = dict(getattr(intent, "probabilities", None) or {})
    minimal = float(getattr(nouls.get("already_minimal"), "noul", 0.0) or 0.0)
    complexity = float(getattr(scores.get("complexity"), "score", None) or 0.0)
    floor = 0.85 if record.get("name") in HIGH_STAKES else CONFIDENT
    compose_ans = choices.get("compose")
    compose = str(getattr(compose_ans, "choice", None) or "single")
    skill_ans = choices.get("skill")
    skill = str(getattr(skill_ans, "choice", None) or "keep")
    if compose == "pipeline" and skill == "keep":
        skill = next((key for key in skills if str(key).startswith("port_pipeline")), "keep")
    skill_conf = float(getattr(skill_ans, "confidence", None) or 0.0)
    fail_skill = float(getattr(nouls.get(f"fail_skill_{skill}"), "noul", 0.0) or 0.0)
    skip = bool(minimal > FIRE_T and conf >= CONFIDENT)
    if picked == "pca_keep" and len([k for k in skills if k != "keep"]) == 0:
        skip = True
    if skill == "keep" and skill_conf >= UNCERTAIN and minimal > FIRE_T:
        skip = True
    if fail_skill > FIRE_T_LEAF and skill != "keep":
        skill = "keep"
    nest_ans = choices.get("nest_child")
    nest_child = str(getattr(nest_ans, "choice", None) or "")
    tool_ans = choices.get("tool_name")
    tool_name = str(getattr(tool_ans, "choice", None) or "")
    CONTROL = {
        "nest",
        "spawn",
        "analyze",
        "self_improve",
        "invoke_router",
        "return",
        "tick",
        "fork",
        "mutate",
        "hook",
        "call",
        "instruct",
        "heal",
    }
    compose = bias_compose_no_drafts(
        compose,
        memory=memory,
        skills=skills,
        skill=skill,
        name=str(record.get("name") or ""),
    )
    if compose in CONTROL:
        skip = False
        if not nest_child:
            nest_child = picked if picked in tree else (skill if skill != "keep" else "")
    skip_skills: set[str] = set()
    residual_unsafe: dict[str, float] = {}
    residual_help: dict[str, float] = {}
    for residual in residuals:
        unsafe = float(getattr(nouls.get(f"unsafe_{residual}"), "noul", 0.0) or 0.0)
        residual_unsafe[residual] = unsafe
        help_ans = scores.get(f"help_{residual}")
        residual_help[residual] = float(getattr(help_ans, "score", None) or 0.0)
        if unsafe > FIRE_T_RESIDUAL:
            skip_skills.update(RESIDUAL_TO_SKILL.get(residual, ()))
    allow = {picked}
    if conf < floor:
        allow = {"dead_code", "strength_reduction", "search_space"}
        # High-stakes still generate safe families; only skip lake when already_minimal fired.
    second = sorted(probs, key=lambda fam: float(probs.get(fam) or 0.0), reverse=True)
    if len(second) > 1 and float(probs.get(second[1]) or 0.0) >= 0.2:
        allow.add(second[1])
    return {
        "skipped": False,
        "intent": picked,
        "confidence": conf,
        "probabilities": {k: float(probs.get(k) or 0.0) for k in criteria},
        "already_minimal": minimal,
        "complexity": complexity,
        "allow_families": allow,
        "skip_lake": skip,
        "uncertain": conf < floor,
        "skill": skill,
        "skill_confidence": skill_conf,
        "compose": compose,
        "nest_child": nest_child,
        "tool_name": tool_name,
        "tree": {fam: list(kids) for fam, kids in tree.items()},
        "tree_node": tree_node,
        "fail_skill": fail_skill,
        "skip_skills": sorted(skip_skills),
        "residual_unsafe": residual_unsafe,
        "residual_help": residual_help,
        "wall_ms": (time.perf_counter() - started) * 1000.0,
        "jev_generated_lean": False,
    }


def sample_records(
    records: Sequence[Mapping[str, Any]],
    *,
    k: int,
    seed: int,
    exclude: Sequence[str] = (),
) -> list[Mapping[str, Any]]:
    pool = [item for item in records if item.get("name") not in set(exclude)]
    rng = random.Random(int(seed))
    if k >= len(pool):
        picked = list(pool)
        rng.shuffle(picked)
        return picked
    return rng.sample(pool, int(k))


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
    scored: list[tuple[int, int, str, Mapping[str, Any]]] = []
    for rec in records:
        name = str(rec.get("name") or "")
        body = lra_inner.starting_tactics(rec, out=out, from_best=from_best)
        prior = lra_bind.prior_research(mem, name)
        unsafe = dict(prior.get("unsafe") or {})
        drafts = []
        for item in lra_port.portable_drafts(body, memory=mem, name=name):
            kind = str(item.get("kind") or "")
            if lra_bind.is_blacklisted(mem, name, kind):
                continue
            stem = kind[len("port_") :] if kind.startswith("port_") else kind
            residual = lra_port.SKILL_RESIDUAL.get(stem, "")
            if residual and float(unsafe.get(residual) or 0.0) >= FIRE_T_RESIDUAL:
                continue
            drafts.append(item)
        cut = max(0, int(warm.get(name) or 0) - int(kept.get(name) or 0))
        rf_score = 0.0
        try:
            import nca_rankers as lra_rank

            rf_score = float(
                lra_rank.score_record(drafts, memory=mem, name=name, remaining_cut=cut) or 0.0
            )
        except Exception:
            rf_score = 0.0
        scored.append((-len(drafts), -cut, -rf_score, name, rec))
        try:
            import typesafe_nca as lra_nca

            cid = f"ptr://theorem/{name}"
            lra_nca.upsert_from_event(mem, ptr=cid, kind="theorem", energy=0.55)
            grid = ((mem.get("nca") or {}).get("grid") or {})
            if isinstance(grid.get(cid), dict):
                grid[cid]["leftover_drafts"] = len(drafts)
                grid[cid]["remaining_cut"] = cut
                if name in warm:
                    grid[cid]["warmup_tokens"] = int(warm[name])
                if name in kept:
                    grid[cid]["tokens"] = int(kept[name])
        except Exception:
            pass
    scored.sort()
    return [row[-1] for row in scored]


def run_live(args: argparse.Namespace) -> dict[str, Any]:
    """AutoResearch entry + lake on sampled canaries. Writes evidence; returns payload."""

    _raw, digest, records = lra_splice.load_warmup_records()
    rows = [lra_pca.feature_row(item) for item in records]
    model = lra_pca.fit_pca_mca(rows)
    landscape = [analyze_proof(item, model=model) for item in records]
    if args.all_small:
        sampled = [
            rec
            for rec, row in zip(records, landscape)
            if int(row.get("n_tokens") or 0) <= MAX_LIVE_TOKENS
        ]
    else:
        sampled = sample_records(records, k=max(1, int(args.k)), seed=int(args.seed))
    if args.include_inits:
        inits = next(item for item in records if item.get("name") == "Core.InitsUpdatesComm")
        if all(item.get("name") != inits.get("name") for item in sampled):
            sampled = [inits, *sampled][: max(1, int(args.k))]
    memory = lra_bind.load_memory()
    obs = memory.setdefault("observations", {})
    obs.pop("no_drafts_tree", None)
    obs.pop("no_drafts_instructed", None)
    obs["no_drafts_tree_by"] = {}
    obs["no_drafts_instructed_by"] = {}
    nca = memory.setdefault("nca", {})
    nca.setdefault("program_state", {})["last_ran"] = []
    nca["journal"] = [
        row
        for row in (nca.get("journal") or [])
        if str(row.get("event") or "") not in {"call", "instruct", "jev", "jev_pick", "grok"}
    ]
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
    canaries: list[dict[str, Any]] = []
    lake_rows: list[dict[str, Any]] = []
    import typesafe_nca as lra_nca_live
    try:
        import board_graph as lra_board_live

        lra_board_live.seed_nca_from_board(memory)
        lra_board_live.overlay_live_board(memory)
        try:
            import skill_improve_loop as lra_sk_board

            lra_board_live.seed_keepbest_theorems(
                memory,
                lra_sk_board.keep_best_board(args.out),
                warmup=lra_board_live.warmup_token_map(),
            )
        except Exception:
            pass
    except Exception:
        pass

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

    for record in sampled:
        try:
            halt = lra_nca_live.should_halt(memory)
        except Exception:
            halt = {}
        if halt.get("budget_dead"):
                canaries.append(
                    {
                        "analysis": {"name": record.get("name")},
                        "n_drafts": 0,
                        "draft_kinds": [],
                        "ranked": {"skipped": True, "reason": "nca_budget"},
                        "lake": [{"name": record.get("name"), "skipped": "nca_budget"}],
                        "trace": [{"action": "nca_budget"}],
                        "clone_exists": False,
                        "n_steps": 0,
                    }
                )
                lake_rows.append({"name": record.get("name"), "skipped": "nca_budget"})
                continue
        nested = lra_inner.run_nested_canary(
            record,
            args=args,
            memory=memory,
            ledger=ledger,
            rng=rng,
            model=model,
        )
        lake = list(nested.get("lake") or [])
        lake_rows.extend(lake)
        canaries.append(
            {
                "analysis": nested.get("analysis") or {},
                "n_drafts": nested.get("n_drafts") or 0,
                "draft_kinds": nested.get("draft_kinds") or [],
                "ranked": nested.get("ranked") or {},
                "lake": lake,
                "trace": nested.get("trace") or [],
                "clone_exists": bool(nested.get("clone_exists")),
                "n_steps": nested.get("n_steps"),
            }
        )

    args.out.mkdir(parents=True, exist_ok=True)
    mem_path = lra_bind.save_memory(memory)
    gaps = lra_bind.skill_gap_report(memory)
    nca_status: dict[str, Any] = {}
    try:
        import board_graph as lra_board_status
        import typesafe_nca as lra_nca_status

        nca_status = dict(lra_nca_status.should_halt(memory))
        nca_status["board_window"] = lra_board_status.board_window(memory)
        nca_status["n_edges"] = len(((memory.get("nca") or {}).get("board_edges")) or [])
        nca_status["last_ran"] = list((((memory.get("nca") or {}).get("program_state") or {}).get("last_ran")) or [])[:8]
    except Exception:
        nca_status = {}
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
        "landscape": [
            {
                "name": item["name"],
                "source": item["source"],
                "n_tokens": item["n_tokens"],
                "n_mca_holes": item["n_mca_holes"],
                "n_have": item["counts"].get("n_have"),
                "n_simp_at": item["counts"].get("n_simp_at"),
                "n_rw": item["counts"].get("n_rw"),
                "n_induction": item["counts"].get("n_induction"),
                "top_family": (item["families"][0]["family"] if item["families"] else None),
            }
            for item in landscape
        ],
        "inits_139": extra_139,
        "canaries": canaries,
        "lake": lake_rows,
        "skill_analysis": gaps,
        "memory_path": str(mem_path),
        "memory": {
            "n_successes": len(memory.get("successes") or []),
            "n_failures": len(memory.get("failures") or []),
            "n_blacklist": len(memory.get("blacklist") or []),
        },
        "nca_status": nca_status,
        "called_docker0": False,
        "official_track2": False,
        "arena_score": None,
        "ledger": ledger.as_dict() if hasattr(ledger, "as_dict") else {"jev_calls": ledger.jev_calls},
    }
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    text = json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n"
    (args.out / f"random-canary-{stamp}.json").write_text(text)
    (args.out / "random-canary-latest.json").write_text(text)
    return payload


if __name__ == "__main__":
    raise SystemExit(main())

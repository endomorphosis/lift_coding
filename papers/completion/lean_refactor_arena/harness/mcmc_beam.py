#!/usr/bin/env python3
"""TypeSafe Metropolis-Hastings over a constrained beam of Lean tactic scripts.

Each chain starts from the original (lake-valid) proof. A proposal is a
local edit from a closed set (drop a mutable line, swap in a closer, drop
a trailing simp_all). TypeSafe Choice ranks proposals; lake is the accept
oracle. Metropolis may accept a longer still-valid script with
``exp(-Δtokens / T)``. Invalid lake results are rejected.

This is MCMC on the beam, not neural sampling. Prefix ``have``s that
``simp_all`` consumes stay locked (Hk / Hlen1 / Hlen2 on InitsUpdatesComm).
Proposal kernels: closed deletions, ``refine``/``ih`` rewrites, optional
one-line local Leanstral replacements. Not official Track 2. Not an Arena ranking.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import math
import os
import random
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
TS_PATH = Path("/home/barberb/lift_coding/external/ipfs_accelerate/ipfs_accelerate_py/typesafe_inference.py")
HARDWARE_CLASS = "spark_gb10"
PROTOCOL = "LRA/v1"
PR_ID = "PR-9g"
LOCKED_HEADS = ("intros ", "exists ", "induction ", "case ")
CLOSERS = ("simp_all", "omega", "constructor", "rfl")
MAX_PROPOSALS = 8
MAX_JEV = 24
MAX_LEANSTRAL = 4
IH_APPLY = "apply (ih Hinit ?_ ?_).2.2"
IH_APPLY_SHORT = "apply (ih Hinit).2.2"
IH_EXACT = "exact (ih Hinit ?_ ?_).2.2"
REFINE_RFL = "refine ⟨rfl, ?_, ?_⟩"
HND_BLOCK = (
    "          have Hnd := InitStatesNotDefined Hinit\n"
    "          simp [isNotDefined, isDefined] at *\n"
    "          intros Hin\n"
    "          simp_all"
)
HND_REPLACEMENTS = (
    (
        "hnd_intro_simp",
        "          intros Hin\n"
        "          simp [InitStatesNotDefined Hinit, isNotDefined, isDefined] at *",
        "Hnd block -> intros Hin + combined simp",
    ),
    (
        "hnd_simp_only",
        "          simp [InitStatesNotDefined Hinit, isNotDefined, isDefined]",
        "Hnd block -> one simp of InitStatesNotDefined",
    ),
    (
        "hnd_intro_exact",
        "          intro Hin\n"
        "          simp [isNotDefined, isDefined, InitStatesNotDefined] at *",
        "Hnd block -> intro Hin + InitStatesNotDefined simp",
    ),
)

if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
import constrained_beam as lra_cb  # noqa: E402
import draft_fanout as lra_fan  # noqa: E402
import inits_updates_shorten as lra_ius  # noqa: E402
import pca_mca_fanout as lra_pca  # noqa: E402
import run_warmup as lra_loop  # noqa: E402
import splice as lra_splice  # noqa: E402
import track1_keepbest as lra_kb  # noqa: E402
import track1_ledger as lra_t1  # noqa: E402


@dataclass
class Chain:
    tactics: str
    tokens: int
    theorem_ok: bool
    trace: list[dict[str, Any]] = field(default_factory=list)


def locked_have_names(reference: str) -> set[str]:
    return {lra_cb.have_binder_name(line.strip()) for line in lra_cb.prefix_have_lines(reference)} - {""}


def mutable_indices(tactics: str, locked_haves: set[str]) -> list[int]:
    out: list[int] = []
    for index, line in enumerate(tactics.splitlines()):
        stripped = line.strip()
        if not stripped:
            continue
        if any(stripped.startswith(head) for head in LOCKED_HEADS):
            continue
        if stripped.startswith("have ") and lra_cb.have_binder_name(stripped) in locked_haves:
            continue
        out.append(index)
    return out


def apply_drop(tactics: str, index: int) -> str:
    lines = tactics.splitlines()
    if index < 0 or index >= len(lines):
        return tactics
    del lines[index]
    return "\n".join(lines)


def apply_replace(tactics: str, index: int, nxt: str) -> str:
    lines = tactics.splitlines()
    if index < 0 or index >= len(lines):
        return tactics
    indent = lines[index][: len(lines[index]) - len(lines[index].lstrip())]
    lines[index] = indent + nxt.strip()
    return "\n".join(lines)


def join_consecutive_applies(tactics: str) -> str:
    lines = tactics.splitlines()
    out: list[str] = []
    index = 0
    while index < len(lines):
        a = lines[index]
        if (
            index + 1 < len(lines)
            and a.strip().startswith("apply ")
            and lines[index + 1].strip().startswith("apply ")
            and (len(a) - len(a.lstrip())) == (len(lines[index + 1]) - len(lines[index + 1].lstrip()))
        ):
            indent = a[: len(a) - len(a.lstrip())]
            out.append(f"{indent}{a.strip()} <;> {lines[index + 1].strip()}")
            index += 2
            continue
        out.append(a)
        index += 1
    return "\n".join(out)


def drop_last_duplicate_lines(tactics: str, locked_haves: set[str]) -> list[tuple[int, str, str]]:
    """Drop the last extra copy of a stripped line that appears more than once."""

    lines = tactics.splitlines()
    mutable = set(mutable_indices(tactics, locked_haves))
    counts: dict[str, list[int]] = {}
    for index, line in enumerate(lines):
        counts.setdefault(line.strip(), []).append(index)
    out: list[tuple[int, str, str]] = []
    for stripped, idxs in counts.items():
        if len(idxs) < 2 or not stripped:
            continue
        last = idxs[-1]
        if last not in mutable:
            continue
        out.append((last, stripped, apply_drop(tactics, last)))
    return out


def collapse_ih_simps(tactics: str) -> Optional[str]:
    """Fold the two simp bullets after ``apply (ih …).2.2`` into ``<;> simp_all``."""

    lines = tactics.splitlines()
    for index, line in enumerate(lines):
        if IH_APPLY not in line:
            continue
        indent = line[: len(line) - len(line.lstrip())]
        nxt = lines[index + 1].strip() if index + 1 < len(lines) else ""
        nxt2 = lines[index + 2].strip() if index + 2 < len(lines) else ""
        if nxt.startswith(". simp") and nxt2.startswith(". simp"):
            folded = indent + IH_APPLY + " <;> simp_all"
            return "\n".join(lines[:index] + [folded] + lines[index + 3 :])
    return None


def propose_edits(
    tactics: str,
    reference: str,
    rng: random.Random,
    extra: Optional[Sequence[dict[str, str]]] = None,
    limit: Optional[int] = MAX_PROPOSALS,
) -> list[dict[str, str]]:
    locked = locked_have_names(reference)
    idxs = mutable_indices(tactics, locked)
    proposals: list[dict[str, str]] = []
    seen: set[str] = {tactics.strip("\n")}

    def push(kind: str, body: str, note: str, *, lock: bool = True) -> None:
        text = body.strip("\n")
        if not text or text in seen:
            return
        # Must keep locked prefix have *names* (simp_all fuel), not the
        # original type ascription text.
        if lock:
            present_names = {lra_cb.have_binder_name(line.strip()) for line in text.splitlines()}
            for have in lra_cb.prefix_have_lines(reference):
                name = lra_cb.have_binder_name(have.strip())
                if name and name not in present_names:
                    return
        seen.add(text)
        proposals.append({"kind": kind, "tactics": text, "note": note})

    if extra:
        for item in extra:
            push(str(item.get("kind") or "extra"), str(item.get("tactics") or ""), str(item.get("note") or "extra"))
    for item in lra_ius.propose(tactics):
        push(item["kind"], item["tactics"], item["note"], lock=False)
    push(
        "inits_replay",
        lra_ius.replay(tactics),
        "apply the full Core.InitsUpdatesComm 268→139 kernel sequence",
        lock=False,
    )
    if HND_BLOCK in tactics:
        for kind, repl, note in HND_REPLACEMENTS:
            push(kind, tactics.replace(HND_BLOCK, repl, 1), note)
    none_and = "    apply And.intro\n"
    if none_and in tactics:
        push("drop_and_intro", tactics.replace(none_and, "", 1), "drop apply And.intro before refine updatedStatesInit")
    nested = "          . simp_all\n          . apply UpdateStateNotDefMonotone'"
    if nested in tactics:
        push(
            "drop_nested_init_simp",
            tactics.replace(nested, "          . apply UpdateStateNotDefMonotone'", 1),
            "drop nested . simp_all under apply updatedStatesInit",
        )
    if REFINE_RFL in tactics:
        push("rewrite_refine_constructor", tactics.replace(REFINE_RFL, "constructor", 1), "refine ⟨rfl,?_,?_⟩ -> constructor")
    if IH_APPLY in tactics:
        push("rewrite_ih_short", tactics.replace(IH_APPLY, IH_APPLY_SHORT, 1), "ih ?_ ?_ -> ih")
        push("rewrite_ih_exact", tactics.replace(IH_APPLY, IH_EXACT, 1), "apply ih -> exact ih")
        folded = collapse_ih_simps(tactics)
        if folded:
            push("collapse_ih_simps", folded, "ih apply <;> simp_all, drop two simp bullets")
    joined_app = join_consecutive_applies(tactics)
    push("join_applies", joined_app, "join consecutive apply")
    for _index, stripped, body in drop_last_duplicate_lines(tactics, locked):
        push("drop_duplicate", body, f"drop duplicate {stripped[:60]}")
    dropped = lra_cb.drop_last_bare_simp_all(tactics)
    if dropped:
        push("drop_last_simp_all", dropped, "drop last bare simp_all")
    lines = tactics.splitlines()
    has_not_intro = any("Not.intro" in line for line in lines)
    has_specialize_hnd = any("specialize Hnd" in line for line in lines)
    for index, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("intros Hin") and not has_not_intro:
            push("drop_orphan_intros_hin", apply_drop(tactics, index), "drop orphan intros Hin")
        if stripped.startswith("have Hnd") and not has_specialize_hnd:
            push("drop_orphan_hnd", apply_drop(tactics, index), "drop orphan have Hnd")
        if "isNotDefined" in stripped and not has_specialize_hnd:
            push("drop_isnotdefined_simp", apply_drop(tactics, index), "drop isNotDefined simp")
    if idxs:
        pick = rng.sample(idxs, k=min(1, len(idxs)))
        for index in pick:
            line = tactics.splitlines()[index].strip()
            push("drop_line", apply_drop(tactics, index), f"drop {line[:60]}")
            closer = rng.choice(CLOSERS)
            push("swap_closer", apply_replace(tactics, index, closer), f"swap {line[:40]} -> {closer}")
    joined = lra_cb.join_consecutive_exacts(tactics)
    push("join_exacts", joined, "join consecutive exacts")
    if len(idxs) >= 2:
        first, second = rng.sample(idxs, 2)
        body = tactics
        for index in sorted((first, second), reverse=True):
            body = apply_drop(body, index)
        a = tactics.splitlines()[first].strip()[:30]
        b = tactics.splitlines()[second].strip()[:30]
        push("drop_two", body, f"drop {a} AND {b}")
    none_refine = (
        "    refine updatedStatesInit Hlen1 ?_ ?_\n"
        "    exact InitStatesNotDefined Hinit\n"
        "    exact InitStatesNodup Hinit"
    )
    none_folded = "    exact updatedStatesInit Hlen1 (InitStatesNotDefined Hinit) (InitStatesNodup Hinit)"
    if none_refine in tactics:
        push("fold_init_exacts", tactics.replace(none_refine, none_folded, 1), "refine+two exacts -> one exact updatedStatesInit")
    some_apply = (
        "    . apply updatedStatesInit Hlen1\n"
        "      apply UpdateStateNotDefMonotone' ?_ Hup\n"
        "      apply UpdateStatesNotDefMonotone' ?_ Hups\n"
        "      exact InitStatesNotDefined Hinit\n"
        "      exact InitStatesNodup Hinit"
    )
    some_term = (
        "    . exact updatedStatesInit Hlen1\n"
        "        (UpdateStateNotDefMonotone' (UpdateStatesNotDefMonotone' (InitStatesNotDefined Hinit) Hups) Hup)\n"
        "        (InitStatesNodup Hinit)"
    )
    if some_apply in tactics:
        push("fold_some_init_term", tactics.replace(some_apply, some_term, 1), "update_some apply chain -> term updatedStatesInit")
    nested_apply = (
        "          apply updatedStatesInit\n"
        "          . simp_all\n"
        "          . apply UpdateStateNotDefMonotone' ?_ Hup\n"
        "            apply UpdateStatesNotDefMonotone' ?_ Hups\n"
        "            apply InitStatesNotDefined Hinit\n"
        "          . exact InitStatesNodup Hinit"
    )
    nested_term = (
        "          exact updatedStatesInit Hlen1\n"
        "            (UpdateStateNotDefMonotone' (UpdateStatesNotDefMonotone' (InitStatesNotDefined Hinit) Hups) Hup)\n"
        "            (InitStatesNodup Hinit)"
    )
    if nested_apply in tactics:
        push("fold_nested_init_term", tactics.replace(nested_apply, nested_term, 1), "nested apply updatedStatesInit -> term with Hlen1")
    none_and = (
        "    apply And.intro\n"
        "    exact updatedStatesInit Hlen1 (InitStatesNotDefined Hinit) (InitStatesNodup Hinit)\n"
        "    simp [InitStatesUpdated Hinit]\n"
        "    constructor"
    )
    none_and_term = (
        "    exact ⟨updatedStatesInit Hlen1 (InitStatesNotDefined Hinit) (InitStatesNodup Hinit),\n"
        "      by simp [InitStatesUpdated Hinit]; constructor⟩"
    )
    if none_and in tactics:
        push("fold_none_and", tactics.replace(none_and, none_and_term, 1), "And.intro+exact+simp+constructor -> one exact")
    if "    apply And.intro\n" in tactics:
        push(
            "and_intro_constructor",
            tactics.replace("    apply And.intro\n", "    constructor\n", 1),
            "apply And.intro -> constructor",
        )
    some_bullet = (
        "    refine ⟨rfl, ?_, ?_⟩\n"
        "    . exact updatedStatesInit Hlen1\n"
        "        (UpdateStateNotDefMonotone' (UpdateStatesNotDefMonotone' (InitStatesNotDefined Hinit) Hups) Hup)\n"
        "        (InitStatesNodup Hinit)\n"
        "    . apply UpdateStates.update_some"
    )
    some_filled = (
        "    refine ⟨rfl, (updatedStatesInit Hlen1\n"
        "        (UpdateStateNotDefMonotone' (UpdateStatesNotDefMonotone' (InitStatesNotDefined Hinit) Hups) Hup)\n"
        "        (InitStatesNodup Hinit)), ?_⟩\n"
        "    . apply UpdateStates.update_some"
    )
    if some_bullet in tactics:
        push("fill_refine_init", tactics.replace(some_bullet, some_filled, 1), "put updatedStatesInit term into refine ⟨rfl, ·, ?_⟩")
    none_ctor = (
        "    constructor\n"
        "    exact updatedStatesInit Hlen1 (InitStatesNotDefined Hinit) (InitStatesNodup Hinit)\n"
        "    simp [InitStatesUpdated Hinit]\n"
        "    constructor"
    )
    none_ctor_term = (
        "    exact ⟨updatedStatesInit Hlen1 (InitStatesNotDefined Hinit) (InitStatesNodup Hinit),\n"
        "      by simp [InitStatesUpdated Hinit]; constructor⟩"
    )
    if none_ctor in tactics:
        push("fold_none_ctor", tactics.replace(none_ctor, none_ctor_term, 1), "constructor+exact+simp+constructor -> one exact")
    refine_paren = (
        "    refine ⟨rfl, (updatedStatesInit Hlen1\n"
        "        (UpdateStateNotDefMonotone' (UpdateStatesNotDefMonotone' (InitStatesNotDefined Hinit) Hups) Hup)\n"
        "        (InitStatesNodup Hinit)), ?_⟩\n"
    )
    nested_exact = (
        "          exact updatedStatesInit Hlen1\n"
        "            (UpdateStateNotDefMonotone' (UpdateStatesNotDefMonotone' (InitStatesNotDefined Hinit) Hups) Hup)\n"
        "            (InitStatesNodup Hinit)"
    )
    if refine_paren in tactics and nested_exact in tactics:
        shared = (
            "    have Hst := updatedStatesInit Hlen1\n"
            "      (UpdateStateNotDefMonotone' (UpdateStatesNotDefMonotone' (InitStatesNotDefined Hinit) Hups) Hup)\n"
            "      (InitStatesNodup Hinit)\n"
            "    refine ⟨rfl, Hst, ?_⟩\n"
        )
        push(
            "share_init_term",
            tactics.replace(refine_paren, shared, 1).replace(nested_exact, "          exact Hst", 1),
            "have Hst := duplicated updatedStatesInit term; reuse twice",
        )
        push(
            "drop_refine_parens",
            tactics.replace(refine_paren, "    refine ⟨rfl, updatedStatesInit Hlen1\n        (UpdateStateNotDefMonotone' (UpdateStatesNotDefMonotone' (InitStatesNotDefined Hinit) Hups) Hup)\n        (InitStatesNodup Hinit), ?_⟩\n", 1),
            "drop extra parens around updatedStatesInit in refine",
        )
    hk_typed = "  have Hk : (isDefined σ' ks) := UpdateStatesDefined Hup"
    hk_short = "  have Hk := UpdateStatesDefined Hup"
    if hk_typed in tactics:
        push("drop_hk_type", tactics.replace(hk_typed, hk_short, 1), "drop Hk type ascription")
    named_sigma = "(σ':=updatedStates σ₀ ks' vs')"
    if named_sigma in tactics:
        push(
            "drop_named_sigma",
            tactics.replace(named_sigma, "", 1),
            "drop named σ' := updatedStates argument",
        )
        push(
            "positional_update_some",
            tactics.replace(named_sigma, "(updatedStates σ₀ ks' vs')", 1),
            "named σ' arg -> positional",
        )
    named_val = "(v':=val)"
    if named_val in tactics:
        push("drop_named_val", tactics.replace(" (v':=val)", "", 1), "drop named v' := val argument")
        push("drop_named_val_space", tactics.replace(named_val, "", 1), "drop named v' := val leaving a space")
    simp_opt = "simp [isDefined, Option.isSome] at Hdef"
    if simp_opt in tactics:
        push("simp_hdef_defined", tactics.replace(simp_opt, "simp [isDefined] at Hdef", 1), "drop Option.isSome from Hdef simp")
        push("simp_hdef_bare", tactics.replace(simp_opt, "simp at Hdef", 1), "bare simp at Hdef")
    simp_upd = "simp [UpdateStateUpdated Hup, updatedStates]"
    if simp_upd in tactics:
        push("simp_upd_only", tactics.replace(simp_upd, "simp [UpdateStateUpdated Hup]", 1), "drop updatedStates from simp")
        push("simp_states_only", tactics.replace(simp_upd, "simp [updatedStates]", 1), "drop UpdateStateUpdated from simp")
    simp_nd = "simp [isNotDefined, isDefined] at *"
    if simp_nd in tactics:
        push("simp_nd_only", tactics.replace(simp_nd, "simp [isNotDefined] at *", 1), "drop isDefined from Hnd simp")
        push("simp_nd_bare", tactics.replace(simp_nd, "simp at *", 1), "bare simp at * in Hnd block")
    defined_chain = "simp [isDefined] at * <;> simp_all"
    if defined_chain in tactics:
        push(
            "collapse_defined_simp",
            tactics.replace(defined_chain, "simp_all", 1),
            "simp [isDefined] at * <;> simp_all -> simp_all",
        )
    hst_undef = "UpdateStatesNotDefMonotone' (InitStatesNotDefined Hinit) Hups"
    inner_hnd = "          have Hnd := InitStatesNotDefined Hinit\n"
    if hst_undef in tactics and inner_hnd in tactics:
        lifted = (
            tactics.replace(
                "    have Hst :=",
                "    have Hnd := InitStatesNotDefined Hinit\n    have Hst :=",
                1,
            )
            .replace(hst_undef, "UpdateStatesNotDefMonotone' Hnd Hups", 1)
            .replace(inner_hnd, "", 1)
        )
        push("lift_hnd", lifted, "lift have Hnd to the update_some case and reuse in Hst")
    none_simp_all = "    simp_all\n    constructor\n"
    if none_simp_all in tactics:
        push("drop_none_simp_all", tactics.replace(none_simp_all, "    constructor\n", 1), "drop leading simp_all in update_none")
    none_upd = "    simp [InitStatesUpdated Hinit]\n"
    if none_upd in tactics:
        push("drop_none_init_simp", tactics.replace(none_upd, "", 1), "drop simp [InitStatesUpdated] in update_none")
        push("none_init_simp_bare", tactics.replace(none_upd, "    simp\n", 1), "bare simp in update_none")
    if " generalizing σ''" in tactics:
        push("drop_generalizing", tactics.replace(" generalizing σ''", "", 1), "drop induction generalizing σ''")
    if "  have Hlen2 := UpdateStatesLength Hup\n" in tactics:
        push("drop_hlen2", tactics.replace("  have Hlen2 := UpdateStatesLength Hup\n", "", 1), "drop Hlen2", lock=False)
    if "  have Hk := UpdateStatesDefined Hup\n" in tactics:
        push("drop_hk", tactics.replace("  have Hk := UpdateStatesDefined Hup\n", "", 1), "drop Hk", lock=False)
    three = (
        "          apply updatedStateUpdate\n"
        "          apply InitStatesSomeMonotone heq\n"
        "          exact Hst"
    )
    if three in tactics:
        push(
            "fold_update_term",
            tactics.replace(three, "          exact updatedStateUpdate (InitStatesSomeMonotone heq Hst)", 1),
            "updatedStateUpdate + monotone + Hst -> one exact",
        )
    if "rw [← updatedStateComm']" in tactics:
        push("rw_comm_fwd", tactics.replace("rw [← updatedStateComm']", "rw [updatedStateComm']", 1), "drop ← on updatedStateComm'")
    ih_block = (
        "      . apply (ih Hinit ?_ ?_).2.2\n"
        "        . simp [isDefined] at * <;> simp_all\n"
        "        . simp_all"
    )
    if ih_block in tactics:
        push(
            "ih_by",
            tactics.replace(
                ih_block,
                "      . exact (ih Hinit (by simp [isDefined] at *; simp_all) (by simp_all)).2.2",
                1,
            ),
            "ih apply + two simp bullets -> exact (ih ... by ...)",
        )
        push(
            "ih_by_simp_all",
            tactics.replace(
                ih_block,
                "      . exact (ih Hinit (by simp_all) (by simp_all)).2.2",
                1,
            ),
            "ih apply + two simp bullets -> exact (ih by simp_all)",
        )
    if "next val heq =>" in tactics:
        push("drop_next_names", tactics.replace("next val heq =>", "next =>", 1), "drop next val heq binders")
    hnd_tail = (
        "          simp [isNotDefined, isDefined] at *\n"
        "          intros Hin\n"
        "          simp_all"
    )
    if hnd_tail in tactics:
        push(
            "hnd_merge_simp",
            tactics.replace(hnd_tail, "          intros Hin\n          simp_all [isNotDefined, isDefined]", 1),
            "merge Hnd simp at * into simp_all [isNotDefined, isDefined]",
        )
    case_hnd = "    have Hnd := InitStatesNotDefined Hinit\n"
    if case_hnd in tactics and "  induction Hup\n" in tactics:
        pre = tactics.replace("  induction Hup\n", "  have Hnd := InitStatesNotDefined Hinit\n  induction Hup\n", 1).replace(case_hnd, "", 1)
        pre = pre.replace(
            "exact updatedStatesInit Hlen1 (InitStatesNotDefined Hinit) (InitStatesNodup Hinit)",
            "exact updatedStatesInit Hlen1 Hnd (InitStatesNodup Hinit)",
            1,
        )
        push("lift_hnd_pre", pre, "move Hnd before induction; reuse in update_none")
    ih_by_line = "      . exact (ih Hinit (by simp [isDefined] at *; simp_all) (by simp_all)).2.2"
    if ih_by_line in tactics:
        push(
            "ih_simp_all_defined",
            tactics.replace(ih_by_line, "      . exact (ih Hinit (by simp_all [isDefined]) (by simp_all)).2.2", 1),
            "ih first by: simp_all [isDefined]",
        )
        push(
            "ih_simp_defined",
            tactics.replace(ih_by_line, "      . exact (ih Hinit (by simp [isDefined]) (by simp_all)).2.2", 1),
            "ih first by: simp [isDefined] only",
        )
        push(
            "ih_drop_at_star",
            tactics.replace(ih_by_line, "      . exact (ih Hinit (by simp [isDefined]; simp_all) (by simp_all)).2.2", 1),
            "ih first by: drop at *",
        )
    if "next val heq =>" in tactics:
        push("next_heq_only", tactics.replace("next val heq =>", "next _ heq =>", 1), "drop unused next val binder")
    none_pair = (
        "    simp_all\n"
        "    constructor\n"
        "    exact updatedStatesInit Hlen1 (InitStatesNotDefined Hinit) (InitStatesNodup Hinit)\n"
        "    simp [InitStatesUpdated Hinit]\n"
        "    constructor"
    )
    none_merged = (
        "    simp_all [InitStatesUpdated Hinit]\n"
        "    constructor\n"
        "    exact updatedStatesInit Hlen1 (InitStatesNotDefined Hinit) (InitStatesNodup Hinit)\n"
        "    constructor"
    )
    if none_pair in tactics:
        push("merge_none_simp", tactics.replace(none_pair, none_merged, 1), "fold InitStatesUpdated into leading simp_all")
        push(
            "none_only_simp_all",
            tactics.replace(none_pair, "    simp_all [InitStatesUpdated Hinit]", 1),
            "update_none body is just simp_all [InitStatesUpdated]",
        )
        push(
            "none_simp_all_lemmas",
            tactics.replace(
                none_pair,
                "    simp_all [updatedStatesInit, InitStatesNotDefined, InitStatesNodup, InitStatesUpdated]",
                1,
            ),
            "update_none: one simp_all of the four lemmas",
        )
        push(
            "none_drop_last_ctor",
            tactics.replace(
                none_pair,
                "    simp_all\n    constructor\n    exact updatedStatesInit Hlen1 (InitStatesNotDefined Hinit) (InitStatesNodup Hinit)\n    simp [InitStatesUpdated Hinit]",
                1,
            ),
            "drop trailing constructor in update_none",
        )
        push(
            "none_ctor_simp_all",
            tactics.replace(
                none_pair,
                "    constructor <;> simp_all [updatedStatesInit, InitStatesUpdated]",
                1,
            ),
            "update_none: constructor <;> simp_all lemmas",
        )
    none_hnd_pair = (
        "    simp_all\n"
        "    constructor\n"
        "    exact updatedStatesInit Hlen1 Hnd (InitStatesNodup Hinit)\n"
        "    simp [InitStatesUpdated Hinit]\n"
        "    constructor"
    )
    none_hnd_merged = (
        "    simp_all [InitStatesUpdated Hinit]\n"
        "    constructor\n"
        "    exact updatedStatesInit Hlen1 Hnd (InitStatesNodup Hinit)\n"
        "    constructor"
    )
    if none_hnd_pair in tactics:
        push("merge_none_simp", tactics.replace(none_hnd_pair, none_hnd_merged, 1), "fold InitStatesUpdated into leading simp_all")
        push(
            "none_only_simp_all",
            tactics.replace(none_hnd_pair, "    simp_all [InitStatesUpdated Hinit]", 1),
            "update_none body is just simp_all [InitStatesUpdated]",
        )
    hdef = "        . have Hdef := UpdateStateDefined' Hup\n"
    if hdef in tactics:
        push(
            "anon_hdef",
            tactics.replace(hdef, "        . have := UpdateStateDefined' Hup\n").replace("at Hdef", "at this"),
            "anonymous have for UpdateStateDefined'",
        )
    hnd_merged = (
        "          intros Hin\n"
        "          simp_all [isNotDefined, isDefined]"
    )
    if hnd_merged in tactics:
        push(
            "hnd_simp_all_only",
            tactics.replace(hnd_merged, "          intros Hin\n          simp_all", 1),
            "drop isNotDefined/isDefined args from trailing simp_all",
        )
        push(
            "hnd_intro_simp_all_nd",
            tactics.replace(hnd_merged, "          intro Hin; simp_all [isNotDefined, isDefined]", 1),
            "intro Hin; simp_all [..] on one line",
        )
    refine_hst = (
        "    refine ⟨rfl, Hst, ?_⟩\n"
        "    . apply UpdateStates.update_some"
    )
    ctor_hst = (
        "    constructor\n"
        "    exact rfl\n"
        "    exact Hst\n"
        "    apply UpdateStates.update_some"
    )
    if refine_hst in tactics:
        push("ctor_rfl_hst", tactics.replace(refine_hst, ctor_hst, 1), "refine ⟨rfl, Hst, ?_⟩ -> constructor; exact rfl; exact Hst")
    split_next = (
        "          split at this <;> simp_all\n"
        "          next val heq =>\n"
        "          exact updatedStateUpdate (InitStatesSomeMonotone heq Hst)"
    )
    if split_next in tactics:
        push(
            "split_assumption",
            tactics.replace(
                split_next,
                "          split at this <;> simp_all\n          exact updatedStateUpdate (InitStatesSomeMonotone (by assumption) Hst)",
                1,
            ),
            "drop next val heq; use by assumption",
        )
        push(
            "split_exact",
            tactics.replace(
                split_next,
                "          split at this <;> exact updatedStateUpdate (InitStatesSomeMonotone (by simp_all) Hst)",
                1,
            ),
            "split <;> exact updatedStateUpdate",
        )
    unzip = (
        "        . rw [List.unzip_zip] <;> simp_all\n"
        "          intros Hin\n"
        "          simp_all [isNotDefined, isDefined]"
    )
    if unzip in tactics:
        push(
            "unzip_no_first_simp_all",
            tactics.replace(
                unzip,
                "        . rw [List.unzip_zip]\n          intros Hin\n          simp_all [isNotDefined, isDefined]",
                1,
            ),
            "drop <;> simp_all after unzip_zip",
        )
    case_some = "  case update_some σ x v σ₀ xs vs σ₁ Hup Hups ih =>"
    case_short = "  case update_some _ x _ σ₀ _ _ _ Hup Hups ih =>"
    if case_some in tactics:
        push("case_underscores", tactics.replace(case_some, case_short, 1), "unused update_some binders -> _")
    case_x = "  case update_some _ x _ σ₀ _ _ _ Hup Hups ih =>"
    if case_x in tactics:
        push(
            "case_underscores_x",
            tactics.replace(case_x, "  case update_some _ _ _ σ₀ _ _ _ Hup Hups ih =>", 1),
            "drop unused x binder too",
        )
    refine_hst2 = (
        "    refine ⟨rfl, Hst, ?_⟩\n"
        "    . apply UpdateStates.update_some"
    )
    double_ctor = (
        "    constructor\n"
        "    rfl\n"
        "    constructor\n"
        "    exact Hst\n"
        "    . apply UpdateStates.update_some"
    )
    if refine_hst2 in tactics:
        push("double_ctor_hst", tactics.replace(refine_hst2, double_ctor, 1), "two constructors + rfl + exact Hst instead of refine")
    refine_hst_fill = (
        "    refine ⟨rfl, Hst, ?_⟩\n"
        "    . refine UpdateStates.update_some"
    )
    double_ctor_fill = (
        "    constructor\n"
        "    rfl\n"
        "    constructor\n"
        "    exact Hst\n"
        "    . refine UpdateStates.update_some"
    )
    if refine_hst_fill in tactics:
        push("double_ctor_hst", tactics.replace(refine_hst_fill, double_ctor_fill, 1), "two constructors + rfl + exact Hst instead of refine")
    apply_ih = (
        "    . apply UpdateStates.update_some (σ':=updatedStates σ₀ ks' vs')\n"
    )
    ih_line = "      . exact (ih Hinit (by simp_all [isDefined]) (by simp_all)).2.2"
    if apply_ih in tactics and ih_line in tactics:
        filled = tactics.replace(
            apply_ih,
            "    . refine UpdateStates.update_some (σ':=updatedStates σ₀ ks' vs') ?_ (ih Hinit (by simp_all [isDefined]) (by simp_all)).2.2\n",
            1,
        ).replace("\n" + ih_line, "", 1)
        push("fill_ih_arg", filled, "pass ih as the second argument of update_some")
    none_204 = (
        "    simp_all\n"
        "    constructor\n"
        "    exact updatedStatesInit Hlen1 (InitStatesNotDefined Hinit) (InitStatesNodup Hinit)\n"
        "    simp [InitStatesUpdated Hinit]\n"
        "    constructor"
    )
    if none_204 in tactics:
        push(
            "none_drop_last_ctor",
            tactics.replace(
                none_204,
                "    simp_all\n    constructor\n    exact updatedStatesInit Hlen1 (InitStatesNotDefined Hinit) (InitStatesNodup Hinit)\n    simp [InitStatesUpdated Hinit]",
                1,
            ),
            "drop last constructor in update_none",
        )
        push(
            "none_last_simp_all",
            tactics.replace(
                none_204,
                "    simp_all\n    constructor\n    exact updatedStatesInit Hlen1 (InitStatesNotDefined Hinit) (InitStatesNodup Hinit)\n    simp_all [InitStatesUpdated Hinit]",
                1,
            ),
            "last update_none tactics: simp_all [InitStatesUpdated] without constructor",
        )
        push(
            "none_exact_pair",
            tactics.replace(
                none_204,
                "    simp_all\n    exact ⟨updatedStatesInit Hlen1 (InitStatesNotDefined Hinit) (InitStatesNodup Hinit), by simp [InitStatesUpdated Hinit]; constructor⟩",
                1,
            ),
            "update_none And as one exact ⟨init, by simp; constructor⟩",
        )
    hnd_merged2 = (
        "          intros Hin\n"
        "          simp_all [isNotDefined, isDefined]"
    )
    if hnd_merged2 in tactics:
        push(
            "hnd_no_intros",
            tactics.replace(hnd_merged2, "          simp_all [isNotDefined, isDefined]", 1),
            "drop intros Hin before trailing simp_all",
        )
    split_assump = (
        "          split at this <;> simp_all\n"
        "          exact updatedStateUpdate (InitStatesSomeMonotone (by assumption) Hst)"
    )
    if split_assump in tactics:
        push(
            "split_no_simp_all",
            tactics.replace(
                split_assump,
                "          split at this\n          exact updatedStateUpdate (InitStatesSomeMonotone (by assumption) Hst)",
                1,
            ),
            "drop <;> simp_all after split",
        )
        push(
            "split_simp_all_exact",
            tactics.replace(
                split_assump,
                "          split at this <;> simp_all <;> exact updatedStateUpdate (InitStatesSomeMonotone (by assumption) Hst)",
                1,
            ),
            "split <;> simp_all <;> exact on one chain",
        )
    simp_this = "simp [isDefined, Option.isSome] at this"
    if simp_this in tactics:
        push("simp_this_defined", tactics.replace(simp_this, "simp [isDefined] at this", 1), "drop Option.isSome at this")
        push("simp_this_option", tactics.replace(simp_this, "simp [Option.isSome] at this", 1), "drop isDefined at this")
        push("simp_this_bare", tactics.replace(simp_this, "simp at this", 1), "bare simp at this")
    by_assump = "InitStatesSomeMonotone (by assumption) Hst"
    if by_assump in tactics:
        push(
            "monotone_this",
            tactics.replace(by_assump, "InitStatesSomeMonotone this Hst", 1),
            "by assumption -> this after split",
        )
        push(
            "monotone_star",
            tactics.replace(by_assump, "InitStatesSomeMonotone ‹_› Hst", 1),
            "by assumption -> ‹_›",
        )
    hole = "(σ':=updatedStates σ₀ ks' vs') ?_ (ih"
    if hole in tactics:
        push(
            "underscore_hole",
            tactics.replace(hole, "(σ':=updatedStates σ₀ ks' vs') _ (ih", 1),
            "refine hole ?_ -> _",
        )
    if "    exact Hst\n" in tactics:
        push("assumption_hst", tactics.replace("    exact Hst\n", "    assumption\n", 1), "exact Hst -> assumption")
    simp_nd_list = "simp_all [isNotDefined, isDefined]"
    if simp_nd_list in tactics:
        push("simp_all_hnd", tactics.replace(simp_nd_list, "simp_all [Hnd]", 1), "simp_all [Hnd] instead of isNotDefined/isDefined")
        push("simp_all_hnd_def", tactics.replace(simp_nd_list, "simp_all [Hnd, isDefined]", 1), "simp_all [Hnd, isDefined]")
    if "          intros Hin\n" in tactics:
        push(
            "hnd_no_intro",
            tactics.replace("          intros Hin\n", "", 1),
            "drop intros Hin",
        )
    if "    constructor\n    rfl\n    constructor\n    exact Hst\n" in tactics:
        push(
            "and_intro_rfl_hst",
            tactics.replace(
                "    constructor\n    rfl\n    constructor\n    exact Hst\n",
                "    refine ⟨rfl, Hst, ?_⟩\n",
                1,
            ),
            "revert double ctor (sanity; likely longer)",
        )
    case_hnd_have = "    have Hnd := InitStatesNotDefined Hinit\n"
    hst_hnd = "UpdateStatesNotDefMonotone' Hnd Hups"
    if case_hnd_have in tactics and hst_hnd in tactics:
        push(
            "inline_hnd",
            tactics.replace(case_hnd_have, "", 1).replace(
                hst_hnd,
                "UpdateStatesNotDefMonotone' (InitStatesNotDefined Hinit) Hups",
                1,
            ),
            "inline Hnd into Hst; drop have Hnd",
        )
    if "  have Hk := UpdateStatesDefined Hup\n" in tactics:
        push(
            "anon_hk",
            tactics.replace("  have Hk := UpdateStatesDefined Hup\n", "  have := UpdateStatesDefined Hup\n", 1),
            "anonymous have for Hk",
            lock=False,
        )
    none_last_ctor = "    simp [InitStatesUpdated Hinit]\n    constructor"
    if none_last_ctor in tactics:
        push(
            "none_update_none",
            tactics.replace(none_last_ctor, "    simp [InitStatesUpdated Hinit]\n    exact UpdateStates.update_none", 1),
            "last constructor -> exact UpdateStates.update_none",
        )
        push(
            "none_dot_update_none",
            tactics.replace(none_last_ctor, "    simp [InitStatesUpdated Hinit]\n    exact .update_none", 1),
            "last constructor -> exact .update_none",
        )
    simp_upd = "simp [UpdateStateUpdated Hup, updatedStates]"
    if simp_upd in tactics:
        push(
            "simp_upd_no_hup",
            tactics.replace(simp_upd, "simp [UpdateStateUpdated, updatedStates]", 1),
            "drop Hup arg from UpdateStateUpdated simp",
        )
    if limit is None:
        return proposals
    return proposals[: max(0, int(limit))]


def load_typesafe():
    lra_pca.load_keyfile()
    lra_pca.pin_typesafe_path()
    if not TS_PATH.is_file():
        return None
    spec = importlib.util.spec_from_file_location("lra_typesafe_inference_mcmc", TS_PATH)
    if spec is None or spec.loader is None:
        return None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    if not module.typesafe_configured():
        return None
    return module


def typesafe_rank_proposals(
    record: Mapping[str, Any],
    current: str,
    proposals: Sequence[dict[str, str]],
    *,
    ledger: lra_t1.ProblemLedger,
) -> dict[str, Any]:
    if not proposals:
        return {"skipped": True, "reason": "no_proposals", "order": []}
    module = load_typesafe()
    if module is None:
        return {"skipped": True, "reason": "no_key", "order": list(range(len(proposals)))}
    criteria = {
        f"p{index}": f"{item['kind']}: {item['note']}; {lra_loop.token_count(item['tactics'])} tok"
        for index, item in enumerate(proposals)
    }
    state = {
        "problem": record.get("name"),
        "current_tokens": lra_loop.token_count(current),
        "current_head": current[:400],
        "goal": "Pick the MCMC proposal most likely to lake-compile AND use fewer tokens. Do not write Lean.",
        "proposals": [{"id": key, "desc": val} for key, val in criteria.items()],
    }
    questions = {
        "next_edit": module.Choice(
            instructions=(
                "Which proposal id should this Metropolis chain try? Prefer a deletion that "
                "keeps every case header and the prefix haves Hk/Hlen1/Hlen2. Do not write Lean."
            ),
            criteria=criteria,
        ),
        "likely_compiles": module.Noul(instructions="Will the chosen edit still lake-compile?"),
        "likely_shorter": module.Score(
            instructions="How likely is a token cut if it compiles?",
            criteria=list(lra_fan.LIKELY_SHORTER_CRITERIA),
        ),
    }
    try:
        result = module.TypeSafeClient(timeout=45.0).system_one(state, questions)
    except Exception as exc:  # noqa: BLE001
        return {"skipped": True, "reason": str(exc)[:300], "order": list(range(len(proposals)))}
    usage = dict(getattr(result, "usage", None) or {})
    inn = int(usage.get("input_tokens") or usage.get("prompt_tokens") or lra_t1.estimate_tokens(json.dumps(state)))
    out = int(usage.get("output_tokens") or usage.get("completion_tokens") or 0)
    ledger.record("jev", input_tokens=inn, output_tokens=out, model=lra_t1.JEV_MODEL_ID)
    choice = (getattr(result, "choices", None) or {}).get("next_edit")
    pick = str(getattr(choice, "choice", None) or "p0")
    probs = dict(getattr(choice, "probabilities", None) or {})
    order = sorted(range(len(proposals)), key=lambda i: float(probs.get(f"p{i}") or 0.0), reverse=True)
    if pick.startswith("p") and pick[1:].isdigit():
        idx = int(pick[1:])
        if idx in order:
            order.remove(idx)
            order.insert(0, idx)
    nouls = getattr(result, "nouls", None) or {}
    scores = getattr(result, "scores", None) or {}
    return {
        "skipped": False,
        "pick": pick,
        "order": order,
        "likely_compiles": getattr(nouls.get("likely_compiles"), "noul", None),
        "likely_shorter": getattr(scores.get("likely_shorter"), "score", None),
        "confidence": getattr(choice, "confidence", None),
        "jev_generated_lean": False,
    }


def metropolis_accept(*, old_tok: int, new_tok: int, temperature: float, rng: random.Random) -> bool:
    if new_tok < old_tok:
        return True
    if temperature <= 0:
        return new_tok == old_tok
    delta = new_tok - old_tok
    return rng.random() < math.exp(-delta / max(temperature, 1e-6))


def leanstral_line_swap(
    record: Mapping[str, Any],
    tactics: str,
    rng: random.Random,
    locked_haves: set[str],
) -> Optional[dict[str, str]]:
    idxs = mutable_indices(tactics, locked_haves)
    if not idxs:
        return None
    index = rng.choice(idxs)
    lines = tactics.splitlines()
    target = lines[index]
    prompt = (
        "Replace ONE Lean 4 tactic line with a shorter equivalent. "
        "Reply with only that line. No sorry. Keep case/induction.\n\n"
        f"Problem: {record.get('name')}\n"
        f"Around:\n" + "\n".join(lines[max(0, index - 4) : index + 5]) + "\n\n"
        f"Replace this line:\n{target}\n\nReplacement:"
    )
    import docker0_client as lra_d0

    result = lra_d0.generate_as_client(
        prompt,
        max_new_tokens=48,
        timeout=90.0,
        source=str(record.get("source") or ""),
        allow_owner_exec=False,
    )
    if result.skipped or not result.text:
        return None
    nxt = lra_cb.parse_next_line(result.text)
    if nxt == lra_cb.STOP_TOKEN or not lra_cb.looks_like_tactic(nxt):
        return None
    if nxt.strip() == target.strip():
        return None
    body = apply_replace(tactics, index, nxt)
    return {
        "kind": "leanstral_swap",
        "tactics": body,
        "note": f"leanstral {target.strip()[:40]} -> {nxt.strip()[:40]}",
    }


def compile_one(
    record: Mapping[str, Any],
    tactics: str,
    *,
    state_root: Path,
    timeout: float,
    restore: bytes,
    memory: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    import nca_kernel as lra_kern

    def _run() -> dict[str, Any]:
        return dict(
            lra_kb.compile_tactics(
                record,
                tactics,
                state_root=state_root,
                timeout=timeout,
                restore=restore,
            )
        )

    return lra_kern.guarded_compile(
        memory,
        name=record.get("name"),
        kind="mcmc",
        tactics=tactics,
        compile_fn=_run,
    )


def run_mcmc(
    record: Mapping[str, Any],
    *,
    rounds: int,
    beam: int,
    temperature: float,
    seed: int,
    state_root: Path,
    timeout: float,
    init_tactics: Optional[str] = None,
    leanstral: bool = False,
    memory: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    reference = lra_fan.tactic_block(record)
    rng = random.Random(int(seed))
    ledger = lra_t1.ProblemLedger(
        name=f"{record.get('name')}#mcmc-beam",
        max_jev_calls=MAX_JEV,
        max_mistral_calls=0,
        max_grok_calls=0,
    )
    clone = lra_kb.lra_cw.clone_dir(str(record["url"]), state_root)
    dest = clone / lra_kb.lra_cw.source_relpath(record)
    restore = dest.read_bytes() if dest.is_file() else b""
    start = (init_tactics or reference).strip("\n")
    start_compiled = compile_one(
        record, start, state_root=state_root, timeout=timeout, restore=restore, memory=memory
    )
    start_tok = int(start_compiled.get("token_count") or lra_loop.token_count(start))
    start_ok = bool(start_compiled.get("theorem_ok"))
    ref_tok = lra_loop.token_count(reference)
    chains = [
        Chain(tactics=start, tokens=start_tok, theorem_ok=start_ok)
        for _ in range(max(1, int(beam)))
    ]
    best = {
        "kind": "init" if init_tactics else "reference",
        "tactics": start if start_ok else reference,
        "token_count": start_tok if start_ok else ref_tok,
        "theorem_ok": True if start_ok else bool(start_compiled.get("theorem_ok")),
    }
    if not start_ok:
        best = {"kind": "reference", "tactics": reference, "token_count": ref_tok, "theorem_ok": True}
    history: list[dict[str, Any]] = []
    lake_calls = 1
    leanstral_calls = 0
    locked = locked_have_names(reference)
    failed_bodies: set[str] = set()
    failed_kinds: set[str] = {
        "rewrite_refine_constructor",
        "rewrite_ih_short",
        "rewrite_ih_exact",
        "collapse_ih_simps",
        "drop_orphan_hnd",
        "drop_isnotdefined_simp",
        "drop_orphan_intros_hin",
    }
    sticky_fail = {
        "rewrite_refine_constructor",
        "rewrite_ih_short",
        "rewrite_ih_exact",
        "collapse_ih_simps",
        "drop_orphan_hnd",
        "drop_isnotdefined_simp",
        "drop_orphan_intros_hin",
    }
    for round_i in range(int(rounds)):
        if ledger.hard_stopped:
            break
        for chain_i, chain in enumerate(chains):
            extra: list[dict[str, str]] = []
            if leanstral and leanstral_calls < MAX_LEANSTRAL:
                swap = leanstral_line_swap(record, chain.tactics, rng, locked)
                leanstral_calls += 1
                if swap:
                    extra.append(swap)
            proposals = [
                item
                for item in propose_edits(chain.tactics, reference, rng, extra=extra)
                if item["tactics"] not in failed_bodies and item["kind"] not in failed_kinds
            ]
            if not proposals:
                history.append({"round": round_i, "chain": chain_i, "reason": "all_blacklisted"})
                continue
            ranked = typesafe_rank_proposals(record, chain.tactics, proposals, ledger=ledger)
            ranked_order = ranked.get("order") or list(range(len(proposals)))
            prefer = [
                i
                for i, item in enumerate(proposals)
                if str(item.get("kind") or "").startswith(("drop_duplicate", "join_applies", "leanstral_"))
            ]
            order = prefer[:2] + [i for i in ranked_order if i not in prefer[:2]]
            tried = None
            for idx in order[:3]:
                if idx >= len(proposals):
                    continue
                cand = proposals[idx]
                compiled = compile_one(
                    record,
                    cand["tactics"],
                    state_root=state_root,
                    timeout=timeout,
                    restore=restore,
                    memory=memory,
                )
                lake_calls += 1
                ok = bool(compiled.get("theorem_ok"))
                tok = int(compiled.get("token_count") or lra_loop.token_count(cand["tactics"]))
                accept = False
                reason = "reject_invalid"
                if ok:
                    accept = metropolis_accept(
                        old_tok=chain.tokens,
                        new_tok=tok,
                        temperature=temperature,
                        rng=rng,
                    )
                    reason = "accept" if accept else "reject_mh"
                    if tok < int(best["token_count"]):
                        best = {
                            "kind": f"mcmc_r{round_i}_c{chain_i}_{cand['kind']}",
                            "tactics": cand["tactics"],
                            "token_count": tok,
                            "theorem_ok": True,
                        }
                tried = {
                    "round": round_i,
                    "chain": chain_i,
                    "kind": cand["kind"],
                    "note": cand["note"],
                    "ok": ok,
                    "tokens": tok,
                    "accept": accept,
                    "reason": reason,
                    "typesafe": {k: ranked.get(k) for k in ("pick", "likely_compiles", "likely_shorter", "skipped")},
                    "errors": (compiled.get("errors") or [])[:1],
                }
                history.append(tried)
                if not ok:
                    failed_bodies.add(cand["tactics"])
                    if cand["kind"] in sticky_fail:
                        failed_kinds.add(cand["kind"])
                if accept and ok:
                    chain.tactics = cand["tactics"]
                    chain.tokens = tok
                    chain.theorem_ok = True
                    chain.trace.append(tried)
                    break
            if tried is None:
                history.append({"round": round_i, "chain": chain_i, "reason": "no_proposal"})
    return {
        "mode": "mcmc_beam",
        "rounds": int(rounds),
        "beam": max(1, int(beam)),
        "mh_temperature": float(temperature),
        "seed": int(seed),
        "lake_calls": lake_calls,
        "leanstral_calls": leanstral_calls,
        "best": {k: best[k] for k in ("kind", "token_count", "theorem_ok")},
        "best_tactics": str(best.get("tactics") or ""),
        "best_tactics_head": str(best.get("tactics") or "")[:400],
        "history": history,
        "ledger": ledger.as_dict(),
        "hardware_class": HARDWARE_CLASS,
        "called_docker0": False,
        "called_hosted_mistral": False,
        "official_track2": False,
        "arena_score": None,
        "jev_generated_lean": False,
    }


def self_check() -> dict[str, Any]:
    tactics = (
        "  intros H\n"
        "  have Hk := foo\n"
        "  induction H\n"
        "  case a =>\n"
        "    simp_all\n"
        "    exact bar\n"
        "    simp_all\n"
    )
    rng = random.Random(0)
    props = propose_edits(tactics, tactics, rng)
    mh_short = metropolis_accept(old_tok=10, new_tok=8, temperature=2.0, rng=random.Random(1))
    mh_long = metropolis_accept(old_tok=10, new_tok=12, temperature=0.0, rng=random.Random(1))
    stub = (
        "  have Hk := foo\n"
        "  induction H\n"
        "  case a =>\n"
        f"    {REFINE_RFL}\n"
        f"    {IH_APPLY}\n"
        "        . simp_all\n"
        "        . simp_all\n"
    )
    kinds = {item["kind"] for item in propose_edits(stub, stub, rng)}
    return {
        "ok": bool(props)
        and all("have Hk" in item["tactics"] for item in props)
        and all("induction H" in item["tactics"] for item in props)
        and mh_short
        and not mh_long
        and "case a" in props[0]["tactics"]
        and "rewrite_refine_constructor" in kinds
        and "rewrite_ih_short" in kinds
        and "collapse_ih_simps" in kinds,
        "n_proposals": len(props),
        "hardware_class": HARDWARE_CLASS,
        "called_docker0": False,
        "arena_score": None,
    }


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-check", action="store_true")
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--rounds", type=int, default=8)
    parser.add_argument("--beam", type=int, default=2)
    parser.add_argument("--temperature", type=float, default=3.0, help="Metropolis token temperature")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--init-file", type=Path, default=None, help="start chains from this tactic file instead of the original")
    parser.add_argument("--leanstral", action="store_true", help="add up to 4 local docker0 one-line swap proposals")
    parser.add_argument("--names", default="Core.InitsUpdatesComm")
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
    _raw, digest, records = lra_splice.load_warmup_records()
    names = [item.strip() for item in str(args.names).split(",") if item.strip()]
    started = time.perf_counter()
    problems = []
    for name in names:
        record = next(item for item in records if item.get("name") == name)
        init_text = None
        if args.init_file:
            init_text = Path(args.init_file).read_text(encoding="utf-8")
        search = run_mcmc(
            record,
            rounds=args.rounds,
            beam=args.beam,
            temperature=args.temperature,
            seed=args.seed,
            state_root=args.state_root,
            timeout=args.timeout,
            init_tactics=init_text,
            leanstral=bool(args.leanstral),
        )
        reference = lra_fan.tactic_block(record)
        clone = lra_kb.lra_cw.clone_dir(str(record["url"]), args.state_root)
        dest = clone / lra_kb.lra_cw.source_relpath(record)
        restore = dest.read_bytes() if dest.is_file() else b""
        rows = []
        for kind, body in (("reference", reference), ("mcmc_best", None)):
            text = reference if kind == "reference" else str(search.get("best_tactics") or reference)
            compiled = compile_one(
                record,
                text,
                state_root=args.state_root,
                timeout=args.timeout,
                restore=restore,
                memory=None,
            )
            rows.append(
                {
                    "kind": kind,
                    "n_chars": len(text),
                    **{
                        k: compiled.get(k)
                        for k in ("ok", "theorem_ok", "module_exit_0", "token_count", "errors", "wall_ms")
                    },
                }
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
        ref_tokens = lra_loop.token_count(reference)
        problems.append(
            lra_pca.redact(
                {
                    "name": name,
                    "warmup_jsonl_sha256": digest,
                    "search": search,
                    "candidates": rows,
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
                    "called_docker0": False,
                    "called_hosted_mistral": False,
                    "official_track2": False,
                    "arena_score": None,
                }
            )
        )
    payload = {
        "schema": "lra-mcmc-beam/v1",
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "protocol": PROTOCOL,
        "pr": PR_ID,
        "hardware_class": HARDWARE_CLASS,
        "called_docker0": False,
        "called_hosted_mistral": False,
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
    path = args.out / f"mcmc-beam-{stamp}.json"
    latest = args.out / "mcmc-beam-latest.json"
    path.write_text(text, encoding="utf-8")
    latest.write_text(text, encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "latest": str(latest),
                "kept": [{"name": item.get("name"), "kept": item.get("kept")} for item in problems],
                "arena_score": None,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

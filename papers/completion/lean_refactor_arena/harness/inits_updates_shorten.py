#!/usr/bin/env python3
"""Closed, LLM-free shortenings for ``Core.InitsUpdatesComm``.

The 268→139 path is a finite list of string kernels. ``replay()`` applies
them in order to the frozen warmup script. ``propose()`` / ``pca_mca_ops()``
expose the same kernels to TypeSafe Choice, PCA/MCA fan-out, MCMC, hammer,
and tactician so those loops can re-find the cuts without writing Lean.

Lake is still the accept oracle for ``--live``. Not an Arena ranking.
Not official Track 2.
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Optional

HERE = Path(__file__).resolve().parent
PAPER_ROOT = HERE.parent
OUT_DEFAULT = PAPER_ROOT / "evidence" / "canaries"
CANARY_174 = OUT_DEFAULT / "cascade-best-174.lean"
CANARY_BEST = OUT_DEFAULT / "cascade-best-139.lean"
TARGET_TOKENS = 139
PROBLEM = "Core.InitsUpdatesComm"

if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
import draft_fanout as lra_fan  # noqa: E402
import run_warmup as lra_loop  # noqa: E402
import splice as lra_splice  # noqa: E402


@dataclass(frozen=True)
class Kernel:
    kind: str
    family: str
    note: str
    apply: Callable[[str], str]


def _sub(old: str, new: str, text: str, count: int = 1) -> str:
    from jevops.memory import apply_literal_fold

    return apply_literal_fold(text, {"old": old, "new": new, "count": count})


def _kernel(kind: str, family: str, note: str, old: str, new: str, *, count: int = 1) -> Kernel:
    return Kernel(kind, family, note, lambda text, _o=old, _n=new, _c=count: _sub(_o, _n, text, _c))


# Ordered 268→174 path. Each step is a no-op if its pattern is already gone.
KERNELS: tuple[Kernel, ...] = (
    _kernel(
        "drop_not_intro_specialize",
        "drop",
        "Drop apply Not.intro and specialize Hnd _ Hin; keep intros Hin; simp_all.",
        "          apply Not.intro\n          intros Hin\n          specialize Hnd _ Hin\n          simp_all",
        "          intros Hin\n          simp_all",
    ),
    _kernel(
        "fold_init_exacts",
        "rewrite",
        "refine updatedStatesInit ?_ ?_ plus two exacts -> one exact.",
        "    refine updatedStatesInit Hlen1 ?_ ?_\n"
        "    exact InitStatesNotDefined Hinit\n"
        "    exact InitStatesNodup Hinit",
        "    exact updatedStatesInit Hlen1 (InitStatesNotDefined Hinit) (InitStatesNodup Hinit)",
    ),
    _kernel(
        "and_intro_constructor",
        "rewrite",
        "apply And.intro -> constructor.",
        "    apply And.intro\n",
        "    constructor\n",
    ),
    _kernel(
        "fold_nested_init_term",
        "rewrite",
        "Nested apply updatedStatesInit bullets -> one exact term with Hlen1.",
        "          apply updatedStatesInit\n"
        "          . simp_all\n"
        "          . apply UpdateStateNotDefMonotone' ?_ Hup\n"
        "            apply UpdateStatesNotDefMonotone' ?_ Hups\n"
        "            apply InitStatesNotDefined Hinit\n"
        "          . exact InitStatesNodup Hinit",
        "          exact updatedStatesInit Hlen1\n"
        "            (UpdateStateNotDefMonotone' (UpdateStatesNotDefMonotone' (InitStatesNotDefined Hinit) Hups) Hup)\n"
        "            (InitStatesNodup Hinit)",
    ),
    _kernel(
        "fold_some_init_term",
        "rewrite",
        "update_some apply updatedStatesInit chain -> one exact term.",
        "    . apply updatedStatesInit Hlen1\n"
        "      apply UpdateStateNotDefMonotone' ?_ Hup\n"
        "      apply UpdateStatesNotDefMonotone' ?_ Hups\n"
        "      exact InitStatesNotDefined Hinit\n"
        "      exact InitStatesNodup Hinit",
        "    . exact updatedStatesInit Hlen1\n"
        "        (UpdateStateNotDefMonotone' (UpdateStatesNotDefMonotone' (InitStatesNotDefined Hinit) Hups) Hup)\n"
        "        (InitStatesNodup Hinit)",
    ),
    _kernel(
        "fold_some_init_term_hole",
        "rewrite",
        "Same fold after one-hole ?_ -> _ denoise.",
        "    . apply updatedStatesInit Hlen1\n"
        "      apply UpdateStateNotDefMonotone' _ Hup\n"
        "      apply UpdateStatesNotDefMonotone' _ Hups\n"
        "      exact InitStatesNotDefined Hinit\n"
        "      exact InitStatesNodup Hinit",
        "    . exact updatedStatesInit Hlen1\n"
        "        (UpdateStateNotDefMonotone' (UpdateStatesNotDefMonotone' (InitStatesNotDefined Hinit) Hups) Hup)\n"
        "        (InitStatesNodup Hinit)",
    ),
    _kernel(
        "fill_refine_init",
        "rewrite",
        "Put the InitStates term into refine ⟨rfl, ·, ?_⟩; keep the · apply bullet.",
        "    refine ⟨rfl, ?_, ?_⟩\n"
        "    . exact updatedStatesInit Hlen1\n"
        "        (UpdateStateNotDefMonotone' (UpdateStatesNotDefMonotone' (InitStatesNotDefined Hinit) Hups) Hup)\n"
        "        (InitStatesNodup Hinit)\n"
        "    . apply UpdateStates.update_some",
        "    refine ⟨rfl, (updatedStatesInit Hlen1\n"
        "        (UpdateStateNotDefMonotone' (UpdateStatesNotDefMonotone' (InitStatesNotDefined Hinit) Hups) Hup)\n"
        "        (InitStatesNodup Hinit)), ?_⟩\n"
        "    . apply UpdateStates.update_some",
    ),
    Kernel(
        "share_init_term",
        "rewrite",
        "have Hst := the duplicated updatedStatesInit term; reuse twice.",
        lambda text: (
            text.replace(
                "    refine ⟨rfl, (updatedStatesInit Hlen1\n"
                "        (UpdateStateNotDefMonotone' (UpdateStatesNotDefMonotone' (InitStatesNotDefined Hinit) Hups) Hup)\n"
                "        (InitStatesNodup Hinit)), ?_⟩\n",
                "    have Hst := updatedStatesInit Hlen1\n"
                "      (UpdateStateNotDefMonotone' (UpdateStatesNotDefMonotone' (InitStatesNotDefined Hinit) Hups) Hup)\n"
                "      (InitStatesNodup Hinit)\n"
                "    refine ⟨rfl, Hst, ?_⟩\n",
                1,
            ).replace(
                "          exact updatedStatesInit Hlen1\n"
                "            (UpdateStateNotDefMonotone' (UpdateStatesNotDefMonotone' (InitStatesNotDefined Hinit) Hups) Hup)\n"
                "            (InitStatesNodup Hinit)",
                "          exact Hst",
                1,
            )
            if (
                "    refine ⟨rfl, (updatedStatesInit Hlen1\n"
                "        (UpdateStateNotDefMonotone' (UpdateStatesNotDefMonotone' (InitStatesNotDefined Hinit) Hups) Hup)\n"
                "        (InitStatesNodup Hinit)), ?_⟩\n"
                in text
                and "          exact updatedStatesInit Hlen1\n"
                "            (UpdateStateNotDefMonotone' (UpdateStatesNotDefMonotone' (InitStatesNotDefined Hinit) Hups) Hup)\n"
                "            (InitStatesNodup Hinit)"
                in text
            )
            else text
        ),
    ),
    _kernel(
        "drop_hk_type",
        "rewrite",
        "Drop the type ascription on have Hk.",
        "  have Hk : (isDefined σ' ks) := UpdateStatesDefined Hup",
        "  have Hk := UpdateStatesDefined Hup",
    ),
    _kernel(
        "drop_named_val",
        "drop",
        "Drop named (v':=val) on updatedStateUpdate.",
        "          apply updatedStateUpdate (v':=val)",
        "          apply updatedStateUpdate",
    ),
    Kernel(
        "lift_hnd",
        "rewrite",
        "Lift have Hnd to the update_some case and reuse it in Hst.",
        lambda text: (
            text.replace(
                "    have Hst :=",
                "    have Hnd := InitStatesNotDefined Hinit\n    have Hst :=",
                1,
            )
            .replace(
                "UpdateStatesNotDefMonotone' (InitStatesNotDefined Hinit) Hups",
                "UpdateStatesNotDefMonotone' Hnd Hups",
                1,
            )
            .replace("          have Hnd := InitStatesNotDefined Hinit\n", "", 1)
            if (
                "UpdateStatesNotDefMonotone' (InitStatesNotDefined Hinit) Hups" in text
                and "          have Hnd := InitStatesNotDefined Hinit\n" in text
                and "\n    have Hnd := InitStatesNotDefined Hinit\n" not in ("\n" + text + "\n")
            )
            else text
        ),
    ),
    _kernel(
        "drop_generalizing",
        "drop",
        "Drop induction generalizing σ''.",
        "  induction Hup generalizing σ''",
        "  induction Hup",
    ),
    _kernel(
        "ih_by",
        "rewrite",
        "ih apply plus two simp bullets -> exact (ih by ...).",
        "      . apply (ih Hinit ?_ ?_).2.2\n"
        "        . simp [isDefined] at * <;> simp_all\n"
        "        . simp_all",
        "      . exact (ih Hinit (by simp [isDefined] at *; simp_all) (by simp_all)).2.2",
    ),
    _kernel(
        "fold_update_term",
        "rewrite",
        "updatedStateUpdate + InitStatesSomeMonotone + Hst -> one exact.",
        "          apply updatedStateUpdate\n"
        "          apply InitStatesSomeMonotone heq\n"
        "          exact Hst",
        "          exact updatedStateUpdate (InitStatesSomeMonotone heq Hst)",
    ),
    _kernel(
        "hnd_merge_simp",
        "rewrite",
        "Merge Hnd simp at * into simp_all [isNotDefined, isDefined].",
        "          simp [isNotDefined, isDefined] at *\n"
        "          intros Hin\n"
        "          simp_all",
        "          intros Hin\n          simp_all [isNotDefined, isDefined]",
    ),
    _kernel(
        "ih_simp_all_defined",
        "rewrite",
        "ih first by: simp_all [isDefined].",
        "      . exact (ih Hinit (by simp [isDefined] at *; simp_all) (by simp_all)).2.2",
        "      . exact (ih Hinit (by simp_all [isDefined]) (by simp_all)).2.2",
    ),
    Kernel(
        "anon_hdef",
        "rewrite",
        "Anonymous have for UpdateStateDefined'; simp/split at this.",
        lambda text: (
            text.replace("        . have Hdef := UpdateStateDefined' Hup\n", "        . have := UpdateStateDefined' Hup\n")
            .replace("at Hdef", "at this")
            if "        . have Hdef := UpdateStateDefined' Hup\n" in text
            else text
        ),
    ),
    _kernel(
        "split_assumption",
        "rewrite",
        "Drop next val heq =>; use by assumption.",
        "          split at this <;> simp_all\n"
        "          next val heq =>\n"
        "          exact updatedStateUpdate (InitStatesSomeMonotone heq Hst)",
        "          split at this <;> simp_all\n"
        "          exact updatedStateUpdate (InitStatesSomeMonotone (by assumption) Hst)",
    ),
    Kernel(
        "fill_ih_arg",
        "rewrite",
        "Pass ih as the second argument of update_some.",
        lambda text: (
            text.replace(
                "    . apply UpdateStates.update_some (σ':=updatedStates σ₀ ks' vs')\n",
                "    . refine UpdateStates.update_some (σ':=updatedStates σ₀ ks' vs') ?_ "
                "(ih Hinit (by simp_all [isDefined]) (by simp_all)).2.2\n",
                1,
            ).replace(
                "\n      . exact (ih Hinit (by simp_all [isDefined]) (by simp_all)).2.2",
                "",
                1,
            )
            if (
                "    . apply UpdateStates.update_some (σ':=updatedStates σ₀ ks' vs')\n" in text
                and "      . exact (ih Hinit (by simp_all [isDefined]) (by simp_all)).2.2" in text
            )
            else text
        ),
    ),
    _kernel(
        "double_ctor_hst",
        "rewrite",
        "Two constructors + rfl + exact Hst instead of refine ⟨rfl, Hst, ?_⟩.",
        "    refine ⟨rfl, Hst, ?_⟩\n    . refine UpdateStates.update_some",
        "    constructor\n    rfl\n    constructor\n    exact Hst\n    . refine UpdateStates.update_some",
    ),
    _kernel(
        "assumption_hst",
        "rewrite",
        "exact Hst -> assumption.",
        "    exact Hst\n",
        "    assumption\n",
    ),
    _kernel(
        "monotone_star",
        "rewrite",
        "(by assumption) -> ‹_› on InitStatesSomeMonotone.",
        "InitStatesSomeMonotone (by assumption) Hst",
        "InitStatesSomeMonotone ‹_› Hst",
    ),
    _kernel(
        "anon_hk",
        "rewrite",
        "have Hk := -> have := for UpdateStatesDefined.",
        "  have Hk := UpdateStatesDefined Hup",
        "  have := UpdateStatesDefined Hup",
    ),
    Kernel(
        "anon_hnd",
        "rewrite",
        "Anonymous have for InitStatesNotDefined; use this in Hst.",
        lambda text: (
            text.replace(
                "    have Hnd := InitStatesNotDefined Hinit\n",
                "    have := InitStatesNotDefined Hinit\n",
                1,
            ).replace(
                "UpdateStatesNotDefMonotone' Hnd Hups",
                "UpdateStatesNotDefMonotone' this Hups",
                1,
            )
            if "    have Hnd := InitStatesNotDefined Hinit\n" in text
            else text
        ),
    ),
    _kernel(
        "exists_noparens",
        "rewrite",
        "exists (updatedStates ...) -> exists updatedStates ...",
        "exists (updatedStates σ ks' vs')",
        "exists updatedStates σ ks' vs'",
    ),
    _kernel(
        "dollar_nodup",
        "rewrite",
        "$ InitStatesNodup Hinit (last arg of updatedStatesInit).",
        "(InitStatesNodup Hinit)",
        "$ InitStatesNodup Hinit",
        count=2,
    ),
    _kernel(
        "dollar_update",
        "rewrite",
        "exact updatedStateUpdate $ InitStatesSomeMonotone ...",
        "exact updatedStateUpdate (InitStatesSomeMonotone ‹_› Hst)",
        "exact updatedStateUpdate $ InitStatesSomeMonotone ‹_› Hst",
    ),
    _kernel(
        "simp_all_hdef",
        "rewrite",
        "simp [isDefined, Option.isSome] at this -> simp_all [isDefined, Option.isSome].",
        "simp [isDefined, Option.isSome] at this",
        "simp_all [isDefined, Option.isSome]",
    ),
    _kernel(
        "ih_dollar_snd",
        "rewrite",
        "ih second by-arg: $ by simp_all.",
        "(ih Hinit (by simp_all [isDefined]) (by simp_all)).2.2",
        "(ih Hinit (by simp_all [isDefined]) $ by simp_all).2.2",
    ),
    _kernel(
        "sigma_hole",
        "rewrite",
        "updatedStates σ₀ ks' vs' -> updatedStates _ ks' vs' (σ₀ is two tokens).",
        "(σ':=updatedStates σ₀ ks' vs')",
        "(σ':=updatedStates _ ks' vs')",
    ),
    _kernel(
        "case_drop_unused",
        "drop",
        "Drop unused update_some constructor binders.",
        "  case update_some σ x v σ₀ xs vs σ₁ Hup Hups ih =>",
        "  case update_some Hup Hups ih =>",
    ),
    _kernel(
        "case_none_dot",
        "rewrite",
        "case update_none => -> ·",
        "  case update_none =>\n",
        "  ·\n",
    ),
    _kernel(
        "case_some_rename_i",
        "rewrite",
        "case update_some Hup Hups ih => -> · + rename_i.",
        "  case update_some Hup Hups ih =>\n",
        "  ·\n    rename_i Hup Hups ih\n",
    ),
    _kernel(
        "unzip_simp_all",
        "rewrite",
        "rw [List.unzip_zip] <;> simp_all -> simp_all [List.unzip_zip] (MCA strength_reduction).",
        "        . rw [List.unzip_zip] <;> simp_all",
        "        . simp_all [List.unzip_zip]",
    ),
    _kernel(
        "merge_unzip_nd",
        "rewrite",
        "Fold unzip simp_all into the trailing isNotDefined/isDefined simp_all.",
        "        . simp_all [List.unzip_zip]\n"
        "          intros Hin\n"
        "          simp_all [isNotDefined, isDefined]",
        "        . intros Hin\n"
        "          simp_all [List.unzip_zip, isNotDefined, isDefined]",
    ),
    _kernel(
        "split_all_goals",
        "rewrite",
        "split at this <;> simp_all -> split at this; all_goals simp_all.",
        "          split at this <;> simp_all",
        "          split at this\n          all_goals simp_all",
    ),
    _kernel(
        "dot_update_some",
        "rewrite",
        "UpdateStates.update_some -> .update_some (inductive constructor notation).",
        "refine UpdateStates.update_some",
        "refine .update_some",
    ),
    _kernel(
        "drop_named_sigma",
        "drop",
        "Drop (σ':=updatedStates _ ks' vs'); .update_some infers σ' from the expected type.",
        ". refine .update_some (σ':=updatedStates _ ks' vs') ?_ (ih Hinit (by simp_all [isDefined]) $ by simp_all).2.2",
        ". refine .update_some ?_ (ih Hinit (by simp_all [isDefined]) $ by simp_all).2.2",
    ),
    _kernel(
        "none_simp_ctor",
        "rewrite",
        "update_none: simp_all [InitStatesUpdated Hinit]; constructor (drop exact/simp/constructor).",
        "    simp_all\n"
        "    constructor\n"
        "    exact updatedStatesInit Hlen1 (InitStatesNotDefined Hinit) $ InitStatesNodup Hinit\n"
        "    simp [InitStatesUpdated Hinit]\n"
        "    constructor",
        "    simp_all [InitStatesUpdated Hinit]\n    constructor",
    ),
    _kernel(
        "drop_hin",
        "drop",
        "intros Hin -> intro; the binder name is unused (MCA search_space).",
        "        . intros Hin",
        "        . intro",
    ),
    _kernel(
        "ih_defined_hups",
        "rewrite",
        "ih first extra arg: UpdateStatesDefined Hups instead of by simp_all [isDefined].",
        "(ih Hinit (by simp_all [isDefined]) $ by simp_all).2.2",
        "(ih Hinit (UpdateStatesDefined Hups) $ by simp_all).2.2",
    ),
    _kernel(
        "ih_length_hups",
        "rewrite",
        "ih second extra arg: UpdateStatesLength Hups instead of by simp_all.",
        "(ih Hinit (UpdateStatesDefined Hups) $ by simp_all).2.2",
        "(ih Hinit (UpdateStatesDefined Hups) $ UpdateStatesLength Hups).2.2",
    ),
)


def family_tree() -> dict[str, dict[str, str]]:
    tree: dict[str, dict[str, str]] = {
        "keep": {"keep": "Do not edit. The current lake-valid script is already locally minimal."},
        "drop": {},
        "rewrite": {},
        "join": {},
    }
    for kernel in KERNELS:
        tree.setdefault(kernel.family, {})[kernel.kind] = kernel.note
    return tree


def apply_kernel(kind: str, tactics: str) -> str:
    for kernel in KERNELS:
        if kernel.kind == kind:
            return kernel.apply(tactics).strip("\n")
    return tactics.strip("\n")


def propose(tactics: str) -> list[dict[str, str]]:
    """One-step proposals for TypeSafe / MCMC / hammer (no lake, no LLM)."""

    from jevops.pick import unique_transforms

    out: list[dict[str, str]] = []
    for kernel, nxt in unique_transforms(
        tactics,
        KERNELS,
        apply_fn=lambda item, body: item.apply(body),
    ):
        out.append({"kind": kernel.kind, "tactics": nxt, "note": kernel.note, "family": kernel.family})
    return out


def pca_mca_ops(tactics: str) -> list[tuple[str, str, tuple[str, ...]]]:
    """PCA/MCA draft triples: ``(family, tactics, ops)``.

    Full ``inits_replay`` is first so TypeSafe/lake always see the 268→139 cut
    even when ``MAX_DRAFTS`` truncates one-step kernels.
    """

    current = tactics.strip("\n")
    rows: list[tuple[str, str, tuple[str, ...]]] = []
    replayed = replay(current)
    if replayed and replayed != current:
        rows.append(
            (
                "inits_replay",
                replayed,
                ("inits_replay", "mca", "no_llm"),
            )
        )
    for item in propose(current):
        rows.append(
            (
                str(item["family"]),
                str(item["tactics"]),
                (str(item["kind"]), "mca", "kernel"),
            )
        )
    return rows


def replay(tactics: str) -> str:
    """Apply every kernel in order. Original warmup script becomes the 174 cut."""

    from jevops.pick import compose_steps

    text, _applied = compose_steps(
        tactics,
        tuple((kernel.kind, kernel.apply) for kernel in KERNELS),
    )
    return text


def original_tactics() -> str:
    _raw, _digest, records = lra_splice.load_warmup_records()
    record = next(item for item in records if item.get("name") == PROBLEM)
    return lra_fan.tactic_block(record).strip("\n")


def expected_174() -> str:
    path = CANARY_BEST if CANARY_BEST.is_file() else CANARY_174
    if path.is_file():
        return path.read_text(encoding="utf-8").strip("\n")
    return replay(original_tactics())


def self_check() -> dict[str, object]:
    src = original_tactics()
    got = replay(src)
    want = expected_174() if CANARY_174.is_file() else got
    src_tok = lra_loop.token_count(src)
    got_tok = lra_loop.token_count(got)
    return {
        "ok": got == want and got_tok == TARGET_TOKENS and src_tok == 268,
        "source_tokens": src_tok,
        "replay_tokens": got_tok,
        "target_tokens": TARGET_TOKENS,
        "matches_canary": got == want,
        "n_kernels": len(KERNELS),
        "kinds": [kernel.kind for kernel in KERNELS],
        "warmup_jsonl_sha256": lra_splice.FROZEN_WARMUP_SHA256,
        "called_llm": False,
        "arena_score": None,
    }


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-check", action="store_true")
    parser.add_argument("--replay", action="store_true")
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--timeout", type=float, default=180.0)
    parser.add_argument("--out", type=Path, default=OUT_DEFAULT)
    args = parser.parse_args(argv)
    if args.self_check or not args.replay:
        payload = self_check()
        print(json.dumps(payload, indent=2, sort_keys=True))
        if args.self_check and not args.replay:
            return 0 if payload["ok"] else 1
        if not args.replay:
            return 0 if payload["ok"] else 1
    src = original_tactics()
    got = replay(src)
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "inits-updates-replay.lean").write_text(got + "\n", encoding="utf-8")
    receipt: dict[str, object] = {
        "schema": "lra-inits-updates-replay/v1",
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "name": PROBLEM,
        "source_tokens": lra_loop.token_count(src),
        "replay_tokens": lra_loop.token_count(got),
        "target_tokens": TARGET_TOKENS,
        "n_kernels": len(KERNELS),
        "called_llm": False,
        "arena_score": None,
        "official_track2": False,
        "hardware_class": "spark_gb10",
        "warmup_jsonl_sha256": lra_splice.FROZEN_WARMUP_SHA256,
    }
    if args.live:
        import mcmc_beam as lra_mcmc
        import track1_keepbest as lra_kb

        _raw, digest, records = lra_splice.load_warmup_records()
        record = next(item for item in records if item.get("name") == PROBLEM)
        clone = lra_kb.lra_cw.clone_dir(str(record["url"]), lra_mcmc.DEFAULT_STATE)
        dest = clone / lra_kb.lra_cw.source_relpath(record)
        restore = dest.read_bytes() if dest.is_file() else b""
        compiled = lra_mcmc.compile_one(
            record, got, state_root=lra_mcmc.DEFAULT_STATE, timeout=args.timeout, restore=restore
        )
        receipt["theorem_ok"] = bool(compiled.get("theorem_ok"))
        receipt["lake_tokens"] = compiled.get("token_count")
        receipt["errors"] = (compiled.get("errors") or [])[:1]
        receipt["warmup_jsonl_sha256"] = digest
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = args.out / f"inits-updates-replay-{stamp}.json"
    text = json.dumps(receipt, indent=2, sort_keys=True) + "\n"
    path.write_text(text, encoding="utf-8")
    (args.out / "inits-updates-replay-latest.json").write_text(text, encoding="utf-8")
    print(json.dumps(receipt, indent=2, sort_keys=True))
    if args.live and not receipt.get("theorem_ok"):
        return 1
    if lra_loop.token_count(got) != TARGET_TOKENS:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

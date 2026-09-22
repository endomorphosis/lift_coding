#!/usr/bin/env python3
"""SDE cascade + hierarchical Choice + confidence abstain for Lean MCMC edits.

Cookbooks:
  https://docs.typesafe.ai/cookbooks/sde_cascade
  https://docs.typesafe.ai/cookbooks/hierarchical_classification
  https://docs.typesafe.ai/cookbooks/classification_using_confidence

1. Hierarchical Choice: pick an edit *family*, then a leaf edit (beam K=2,
   geometric-mean path score).
2. Confidence: if the family Choice is below CONFIDENT, keep the current
   script (coarser answer = do nothing).
3. Cascade verify: per-edit Nouls with true=will-fail-lake; skip lake if any
   P(wrong) > FIRE_T. Lake is the expensive oracle.

Jev does not write Lean. Not Track 2. Not an Arena ranking.
"""
from __future__ import annotations

import argparse
import json
import os
import random
import sys
import time

from pathlib import Path
from typing import Any, Mapping, Optional

HERE = Path(__file__).resolve().parent
PAPER_ROOT = HERE.parent
OUT_DEFAULT = PAPER_ROOT / "evidence" / "canaries"
PR_ID = "PR-9i"

if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
import _jevops_path  # noqa: E402,F401
import inits_updates_shorten as lra_ius  # noqa: E402
from jevops.catalogs import CASCADE_BEAM_K as BEAM_K  # noqa: E402
from jevops.catalogs import CASCADE_MAX_JEV as MAX_JEV  # noqa: E402
from jevops.catalogs import DEFAULT_TRACK1_STATE as DEFAULT_STATE  # noqa: E402
from jevops.catalogs import CONFIDENT  # noqa: E402
from jevops.catalogs import EPSILON  # noqa: E402
from jevops.catalogs import FAIL_NOULS  # noqa: E402
from jevops.catalogs import FIRE_T  # noqa: E402
from jevops.catalogs import HARDWARE_CLASS_SPARK as HARDWARE_CLASS  # noqa: E402
from jevops.catalogs import PROTOCOL  # noqa: E402

FAMILY_TREE: dict[str, dict[str, str]] = lra_ius.family_tree()
FAMILY_TREE.setdefault("rewrite", {})["inits_replay"] = (
    "Apply the full Core.InitsUpdatesComm 268→139 kernel sequence (no LLM)."
)
FAMILY_TREE.setdefault("drop", {}).update(
    {
        "drop_duplicate": "Delete the last extra copy of a repeated exact/simp_all/apply.",
        "drop_and_intro": "Delete apply And.intro before refine updatedStatesInit.",
        "drop_nested_init_simp": "Delete the nested . simp_all under apply updatedStatesInit.",
        "drop_last_simp_all": "Delete the last bare simp_all that does no work.",
        "drop_orphan_intros_hin": "Delete an intros Hin that no later tactic uses.",
        "drop_orphan_hnd": "Delete have Hnd when specialize Hnd is gone.",
        "drop_isnotdefined_simp": "Delete the isNotDefined/isDefined simp at * after Hnd.",
    }
)
FAMILY_TREE.setdefault("join", {}).update(
    {
        "join_applies": "Join consecutive same-indent apply lines with <;> (often longer).",
        "join_exacts": "Join consecutive exact lines with <;>.",
    }
)

import mcmc_beam as lra_mcmc  # noqa: E402
import pca_mca_fanout as lra_pca  # noqa: E402
import run_warmup as lra_loop  # noqa: E402
import splice as lra_splice  # noqa: E402
import track1_keepbest as lra_kb  # noqa: E402
import track1_ledger as lra_t1  # noqa: E402


def load_typesafe():
    from jevops.jev import typesafe_namespace

    return typesafe_namespace(setup=(lra_pca.load_keyfile, lra_pca.pin_typesafe_path))


def geo_mean(probs: list[float]) -> float:
    from jevops.pick import geo_mean as _fn

    return _fn(probs, epsilon=EPSILON)


def make_client(module):
    from jevops.outer import client_kwargs

    return module.TypeSafeClient(**client_kwargs(module))


def _record_jev(ledger: lra_t1.ProblemLedger, result: Any, fallback: int = 200) -> None:
    from jevops.outer import result_usage

    inn, out = result_usage(result, fallback_in=fallback)
    ledger.record("jev", input_tokens=inn, output_tokens=out, model=lra_t1.JEV_MODEL_ID)


def is_unavailable(exc: BaseException) -> bool:
    from jevops.outer import is_unavailable as _fn

    return _fn(exc)


def call_with_retry(fn, *, attempts: int = 4):
    from jevops.outer import retry_call

    return retry_call(fn, attempts=attempts)


def available_tactics(current: str, reference: str, rng: random.Random) -> dict[str, str]:
    from jevops.outer import unique_kind_bodies

    return unique_kind_bodies(
        lra_mcmc.propose_edits(current, reference, rng, limit=None),
        keep={"keep": current},
        skip_eq=current,
    )


def load_failed_kinds(path: Path) -> set[str]:
    from jevops.outer import failed_leaves_from_history
    from jevops.outer import load_json_object

    return failed_leaves_from_history(load_json_object(path))


def live_tree(available: Mapping[str, str]) -> dict[str, dict[str, str]]:
    from jevops.pick import live_tree as _fn

    return _fn(FAMILY_TREE, available)


def classify_tree(
    module,
    state: Mapping[str, Any],
    tree: Mapping[str, Mapping[str, str]],
    *,
    ledger: lra_t1.ProblemLedger,
) -> dict[str, Any]:
    """One System One call: family Choice plus a leaf Choice per sibling set.

    Hierarchical cookbook: path_score = geo_mean of edge probabilities, beam K,
    separation = top / second. Confidence cookbook: if family confidence is
    below CONFIDENT, report the coarser parent (keep / do nothing).
    """
    from jevops.catalogs import CASCADE_FAMILY_INSTRUCTIONS
    from jevops.jev import tree_choice_questions

    questions = tree_choice_questions(
        tree,
        Choice=module.Choice,
        family_instructions=CASCADE_FAMILY_INSTRUCTIONS,
    )
    from jevops.jev import invoke_system_one

    result = call_with_retry(lambda: invoke_system_one(make_client(module), state, questions)[0])
    _record_jev(ledger, result)
    from jevops.outer import overlay_map
    from jevops.pick import classification_from_answers

    return classification_from_answers(
        tree,
        overlay_map(getattr(result, "choices", None)),
        beam_k=BEAM_K,
        confident=CONFIDENT,
        epsilon=EPSILON,
    )


def verify_fail(module, state: Mapping[str, Any], *, ledger: lra_t1.ProblemLedger) -> dict[str, float]:
    from jevops.jev import noul_questions

    questions = noul_questions(FAIL_NOULS, module.Noul)
    from jevops.outer import attr_map, overlay_map

    from jevops.jev import invoke_system_one

    result = call_with_retry(lambda: invoke_system_one(make_client(module), state, questions)[0])
    _record_jev(ledger, result)
    return attr_map(overlay_map(getattr(result, "nouls", None)), FAIL_NOULS, "noul")


def self_check() -> dict[str, Any]:
    dummy = live_tree({"keep": "x", "drop_duplicate": "y", "join_applies": "z"})
    from jevops.outer import finalize_ok

    return finalize_ok(
        {
            "families": list(FAMILY_TREE),
            "confident": CONFIDENT,
            "fire_t": FIRE_T,
            "beam_k": BEAM_K,
            "hardware_class": HARDWARE_CLASS,
            "called_docker0": False,
            "arena_score": None,
            "cookbooks": [
                "https://docs.typesafe.ai/cookbooks/sde_cascade",
                "https://docs.typesafe.ai/cookbooks/hierarchical_classification",
                "https://docs.typesafe.ai/cookbooks/classification_using_confidence",
            ],
        },
        abs(geo_mean([0.81, 0.81]) - 0.81) < 1e-9,
        "keep" in FAMILY_TREE,
        "drop" in dummy,
        "join" in dummy,
        CONFIDENT > 0,
        FIRE_T == 0.7,
        BEAM_K == 2,
    )


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-check", action="store_true")
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--rounds", type=int, default=6)
    parser.add_argument("--seed", type=int, default=9)
    parser.add_argument("--init-file", type=Path)
    parser.add_argument("--names", default="Core.InitsUpdatesComm")
    parser.add_argument("--state-root", type=Path, default=DEFAULT_STATE)
    parser.add_argument("--timeout", type=float, default=180.0)
    parser.add_argument("--out", type=Path, default=OUT_DEFAULT)
    from jevops.outer import list_or_none

    args = parser.parse_args(list_or_none(argv))
    if args.self_check or not args.live:
        from jevops.outer import print_ok

        return print_ok(self_check())
    from jevops.outer import pin_env

    pin_env({"IPFS_ACCELERATE_LLAMA_CPP_AUTOSTART": "0"}, overwrite=False)
    module = load_typesafe()
    if module is None:
        from jevops.outer import print_json

        print_json({"ok": False, "reason": "no_typesafe", "arena_score": None})
        return 1
    _raw, digest, records = lra_splice.load_warmup_records()
    from jevops.outer import first_csv

    name = first_csv(args.names)
    from jevops.outer import lookup_named

    record = lookup_named(
        records, name, error_cls=RuntimeError, miss=f"unknown warm-up problem: {name}"
    )
    import draft_fanout as lra_fan

    reference = lra_fan.tactic_block(record)
    from jevops.outer import call_if, first_int, get_str, read_text

    current = call_if(args.init_file, lambda: read_text(args.init_file).strip("\n"), default=reference)
    rng = random.Random(first_int(args.seed))
    ledger = lra_t1.ProblemLedger(name=f"{name}#cascade", max_jev_calls=MAX_JEV, max_mistral_calls=0, max_grok_calls=0)
    clone = lra_kb.lra_cw.clone_dir(get_str(record, "url"), args.state_root)
    dest = clone / lra_kb.lra_cw.source_relpath(record)
    from jevops.outer import read_bytes_if

    restore = read_bytes_if(dest)
    start = lra_mcmc.compile_one(record, current, state_root=args.state_root, timeout=args.timeout, restore=restore)
    from jevops.search import keep_beats, kept_view, start_keep

    best = start_keep(current, start, token_fn=lra_loop.token_count)
    history: list[dict[str, Any]] = []
    failed_kinds: set[str] = load_failed_kinds(args.out / "cascade-edits-latest.json")
    started = time.perf_counter()
    from jevops.search import run_cascade_rounds

    current, best = run_cascade_rounds(
        rounds=first_int(args.rounds),
        current=current,
        best=best,
        history=history,
        failed_kinds=failed_kinds,
        ledger=ledger,
        rng=rng,
        name=name,
        available_fn=lambda body: available_tactics(body, reference, rng),
        live_tree_fn=live_tree,
        classify_fn=lambda state, tree: classify_tree(module, state, tree, ledger=ledger),
        verify_fn=lambda state: verify_fail(module, state, ledger=ledger),
        compile_fn=lambda body: lra_mcmc.compile_one(
            record, body, state_root=args.state_root, timeout=args.timeout, restore=restore
        ),
        token_fn=lra_loop.token_count,
        unavailable_fn=is_unavailable,
        sleep_fn=time.sleep,
        confident=CONFIDENT,
        fire_t=FIRE_T,
    )
    from jevops.outer import elapsed_ms, utc_stamp, write_json_pair

    payload = {
        "schema": "lra-cascade-edits/v1",
        "observed_at": utc_stamp(),
        "protocol": PROTOCOL,
        "pr": PR_ID,
        "cookbooks": [
            "https://docs.typesafe.ai/cookbooks/sde_cascade",
            "https://docs.typesafe.ai/cookbooks/hierarchical_classification",
            "https://docs.typesafe.ai/cookbooks/classification_using_confidence",
        ],
        "name": name,
        "warmup_jsonl_sha256": digest,
        "confident": CONFIDENT,
        "fire_t": FIRE_T,
        "beam_k": BEAM_K,
        "failed_kinds": sorted(failed_kinds),
        "best": kept_view(best, ("kind", "token_count", "theorem_ok")),
        "best_tactics": best.get("tactics"),
        "history": history,
        "ledger": ledger.as_dict(),
        "reference_token_count": lra_loop.token_count(reference),
        "beats_reference": keep_beats(best, lra_loop.token_count(reference)),
        "hardware_class": HARDWARE_CLASS,
        "called_docker0": False,
        "official_track2": False,
        "arena_score": None,
        "jev_generated_lean": False,
        "wall_ms": elapsed_ms(started),
    }
    latest = write_json_pair(
        args.out,
        lra_pca.redact(payload),
        prefix="cascade-edits",
        latest="cascade-edits-latest.json",
        refuse="apikey_",
    )
    from jevops.outer import print_json, text_or

    print_json(
        {
            "ok": True,
            "latest": text_or(latest),
            "kept": payload["best"],
            "beats_reference": payload["beats_reference"],
            "arena_score": None,
        }
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

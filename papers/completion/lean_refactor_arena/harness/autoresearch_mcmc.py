#!/usr/bin/env python3
"""TypeSafe autoresearch features to rank MCMC Lean edits.

Follows https://docs.typesafe.ai/cookbooks/autoresearch_feature_discovery
at Lean-proof scale: many Noul/Score questions become numeric features;
code combines them (no CatBoost in this tree). Lake is the label.

Jev does not write Lean. Prefix haves stay locked. Not Track 2. Not Arena.
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
PR_ID = "PR-9h"

if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
import _jevops_path  # noqa: E402,F401
import mcmc_beam as lra_mcmc  # noqa: E402
import pca_mca_fanout as lra_pca  # noqa: E402
import run_warmup as lra_loop  # noqa: E402
import splice as lra_splice  # noqa: E402
import track1_keepbest as lra_kb  # noqa: E402
import track1_ledger as lra_t1  # noqa: E402
from jevops.catalogs import ALL_FEATURES  # noqa: E402
from jevops.catalogs import CASCADE_MAX_JEV as MAX_JEV  # noqa: E402
from jevops.catalogs import DEFAULT_TRACK1_STATE as DEFAULT_STATE  # noqa: E402
from jevops.catalogs import HARDWARE_CLASS_SPARK as HARDWARE_CLASS  # noqa: E402
from jevops.catalogs import MISS_FEATURES  # noqa: E402
from jevops.catalogs import PENALTY  # noqa: E402
from jevops.catalogs import PROTOCOL  # noqa: E402
from jevops.catalogs import SEED_FEATURES  # noqa: E402


def load_typesafe():
    from jevops.jev import typesafe_namespace

    return typesafe_namespace(setup=(lra_pca.load_keyfile, lra_pca.pin_typesafe_path))


def feature_questions(module) -> dict:
    from jevops.jev import questions_from_specs

    import draft_fanout as lra_fan

    return questions_from_specs(
        ALL_FEATURES,
        noul_ctor=module.Noul,
        score_ctor=module.Score,
        score_criteria=list(lra_fan.LIKELY_SHORTER_CRITERIA),
    )


def featurize_proposal(
    record: Mapping[str, Any],
    current: str,
    proposal: Mapping[str, str],
    *,
    ledger: lra_t1.ProblemLedger,
    module,
    weights: Mapping[str, float],
) -> dict[str, Any]:
    from jevops.jev import proposal_feature_state
    from jevops.outer import tail_chars

    state = proposal_feature_state(
        record,
        current,
        proposal,
        token_fn=lra_loop.token_count,
        tail_fn=tail_chars,
    )
    from jevops.jev import featurize_or_skip, invoke_system_one, skipped, unpack_response
    from jevops.outer import dumps_compact, exc_head, usage_tokens
    from jevops.rankers import signed_dot

    def _record(usage: Any) -> Any:
        inn, out = usage_tokens(
            usage, fallback_in=lra_t1.estimate_tokens(dumps_compact(state))
        )
        return ledger.record("jev", input_tokens=inn, output_tokens=out, model=lra_t1.JEV_MODEL_ID)

    return featurize_or_skip(
        invoke_fn=lambda: invoke_system_one(
            module.TypeSafeClient(timeout=45.0), state, feature_questions(module)
        ),
        skip_fn=lambda exc: skipped(exc_head(exc), score=0.0, features={}),
        unpack_fn=unpack_response,
        record_fn=_record,
        feature_names=[name for name, _kind, _q in ALL_FEATURES],
        weights=weights,
        signed_dot_fn=signed_dot,
        penalty=PENALTY,
    )


def update_weights(rows: list[dict[str, Any]], weights: dict[str, float]) -> dict[str, float]:
    """One autoresearch step: nudge weights from lake labels (ok vs fail)."""

    from jevops.rankers import update_feature_weights

    return update_feature_weights(
        rows,
        weights,
        features=[name for name, _kind, _q in ALL_FEATURES],
        penalty=PENALTY,
        lr=0.3,
        floor=0.05,
    )


def self_check() -> dict[str, Any]:
    names = [item[0] for item in ALL_FEATURES]
    return {
        "ok": "likely_compiles" in names
        and "opens_refine_2a" in names
        and "drops_second_exact" in names
        and len(ALL_FEATURES) >= 10,
        "n_features": len(ALL_FEATURES),
        "hardware_class": HARDWARE_CLASS,
        "called_docker0": False,
        "arena_score": None,
        "cookbook": "https://docs.typesafe.ai/cookbooks/autoresearch_feature_discovery",
    }


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-check", action="store_true")
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--rounds", type=int, default=5)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--init-file", type=Path, required=False)
    parser.add_argument("--names", default="Core.InitsUpdatesComm")
    parser.add_argument("--state-root", type=Path, default=DEFAULT_STATE)
    parser.add_argument("--timeout", type=float, default=180.0)
    parser.add_argument("--out", type=Path, default=OUT_DEFAULT)
    from jevops.outer import list_or_none

    args = parser.parse_args(list_or_none(argv))
    if args.self_check or not args.live:
        report = self_check()
        from jevops.outer import print_ok

        return print_ok(report)
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
    from jevops.outer import call_if, first_int, first_truthy, get_str, read_text, text_or

    init = call_if(args.init_file, lambda: read_text(args.init_file))
    import draft_fanout as lra_fan

    reference = lra_fan.tactic_block(record)
    current = text_or(first_truthy(init, reference)).strip("\n")
    rng = random.Random(first_int(args.seed))
    ledger = lra_t1.ProblemLedger(name=f"{name}#autoresearch-mcmc", max_jev_calls=MAX_JEV, max_mistral_calls=0, max_grok_calls=0)
    clone = lra_kb.lra_cw.clone_dir(get_str(record, "url"), args.state_root)
    dest = clone / lra_kb.lra_cw.source_relpath(record)
    from jevops.outer import read_bytes_if

    restore = read_bytes_if(dest)
    start = lra_mcmc.compile_one(record, current, state_root=args.state_root, timeout=args.timeout, restore=restore)
    from jevops.search import keep_beats, kept_view, start_keep

    best = start_keep(current, start, token_fn=lra_loop.token_count)
    weights = {name: 0.8 for name, _k, _q in ALL_FEATURES}
    weights.update(
        {
            "likely_compiles": 1.1,
            "likely_shorter": 0.15,
            "local_one_line": 0.2,
            "opens_refine_2a": 1.0,
            "semicolon_apply_longer": 1.0,
            "constructor_for_rfl_refine": 1.0,
            "drops_second_exact": 1.0,
        }
    )
    history: list[dict[str, Any]] = []
    labeled: list[dict[str, Any]] = []
    started = time.perf_counter()
    from jevops.search import run_autoresearch_rounds

    current, best, weights = run_autoresearch_rounds(
        rounds=first_int(args.rounds),
        current=current,
        best=best,
        history=history,
        labeled=labeled,
        weights=weights,
        ledger=ledger,
        propose_fn=lambda body: lra_mcmc.propose_edits(body, reference, rng),
        feature_fn=lambda body, proposal, wts: featurize_proposal(
            record, body, proposal, ledger=ledger, module=module, weights=wts
        ),
        compile_fn=lambda body: lra_mcmc.compile_one(
            record, body, state_root=args.state_root, timeout=args.timeout, restore=restore
        ),
        token_fn=lra_loop.token_count,
        update_fn=update_weights,
    )
    from jevops.outer import elapsed_ms, utc_stamp, write_json_pair

    payload = {
        "schema": "lra-autoresearch-mcmc/v1",
        "observed_at": utc_stamp(),
        "protocol": PROTOCOL,
        "pr": PR_ID,
        "cookbook": "https://docs.typesafe.ai/cookbooks/autoresearch_feature_discovery",
        "name": name,
        "warmup_jsonl_sha256": digest,
        "rounds": first_int(args.rounds),
        "features": [item[0] for item in ALL_FEATURES],
        "miss_features": [item[0] for item in MISS_FEATURES],
        "final_weights": weights,
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
        prefix="autoresearch-mcmc",
        latest="autoresearch-mcmc-latest.json",
        refuse="apikey_",
    )
    from jevops.outer import print_json, text_or

    print_json(
        {
            "ok": True,
            "latest": text_or(latest),
            "kept": {"kind": best.get("kind"), "token_count": best.get("token_count"), "theorem_ok": best.get("theorem_ok")},
            "beats_reference": payload["beats_reference"],
            "arena_score": None,
        }
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

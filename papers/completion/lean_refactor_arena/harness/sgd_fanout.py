#!/usr/bin/env python3
"""Jev-guided stochastic search over MCA holes with parallel hammers.

This is not neural SGD. Each round TypeSafe scores remaining hole-drops
(surrogate gradient). We sample the top Choice plus one random hole
(stochastic minibatch), apply the drop, then run identity / simp_all /
omega closers in parallel. Lake is the true loss. Leanstral is one
optional restart if no descent. Never docker0. Not official Track 2.
Not an Arena ranking.
"""
from __future__ import annotations

import argparse
import json
import os
import random
import sys
import time

from pathlib import Path
from typing import Any, Mapping, Optional, Sequence

HERE = Path(__file__).resolve().parent
PAPER_ROOT = HERE.parent
OUT_DEFAULT = PAPER_ROOT / "evidence" / "canaries"

if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
import _jevops_path  # noqa: E402,F401
import draft_fanout as lra_fan  # noqa: E402
import mca_mask_replace as lra_mask  # noqa: E402
import pca_mca_fanout as lra_pca  # noqa: E402
import run_warmup as lra_loop  # noqa: E402
import splice as lra_splice  # noqa: E402
import track1_keepbest as lra_kb  # noqa: E402
import track1_ledger as lra_t1  # noqa: E402
import track1_mistral_leanstral as lra_mistral  # noqa: E402

PR_ID = "PR-9e"
from jevops.catalogs import ACCEL_ROOT as ROOT_ACCEL
from jevops.catalogs import DEFAULT_TRACK1_STATE as DEFAULT_STATE
from jevops.catalogs import MISTRAL_HARDWARE_CLASS as HARDWARE_CLASS
from jevops.catalogs import PROTOCOL


def drop_subset(tactics: str, holes: Sequence[lra_mask.Hole], chosen: Sequence[str]) -> str:
    from jevops.tactics import drop_subset as _fn

    return _fn(tactics, holes, chosen)


def hammer_variants(tactics: str, reference: str) -> list[tuple[str, str]]:
    """Parallel tactician branches. Aesop is not a Strata/CSLib dep."""

    import inits_updates_shorten as lra_ius
    import symbol_diffuse as lra_sym
    from jevops.tactics import drive_hammer_variants

    return drive_hammer_variants(
        tactics,
        reference,
        replay_fn=lra_ius.replay,
        propose_fn=lra_ius.propose,
        closed_fn=lra_sym.closed_candidates,
    )


def jev_round(
    record: Mapping[str, Any],
    holes: Sequence[lra_mask.Hole],
    history: Sequence[Mapping[str, Any]],
    keep_tokens: int,
) -> dict[str, Any]:
    from jevops.catalogs import LIKELY_SHORTER_CRITERIA, SGD_HOLE_INSTRUCTIONS
    from jevops.jev import drive_hole_round

    return drive_hole_round(
        record,
        holes,
        history,
        keep_tokens,
        setup=(lra_pca.pin_typesafe_path,),
        best_instructions=SGD_HOLE_INSTRUCTIONS,
        shorter_criteria=LIKELY_SHORTER_CRITERIA,
        redact_fn=lra_pca.redact,
    )


def evaluate_tactics(
    record: Mapping[str, Any],
    tactics: str,
    *,
    state_root: Path,
    timeout: float,
    restore: bytes,
    reference: str,
    memory: Optional[dict[str, Any]] = None,
) -> list[dict[str, Any]]:
    import nca_kernel as lra_kern
    from jevops.kernel import drive_variant_evals

    # Lake splices one file; serialize compiles. "Parallel hammers" means
    # four closer variants per minibatch, not concurrent writes.
    return drive_variant_evals(
        record,
        tactics,
        state_root=state_root,
        timeout=timeout,
        restore=restore,
        reference=reference,
        memory=memory,
        variants_fn=hammer_variants,
        compile_fn=lra_kb.compile_tactics,
        guard_fn=lra_kern.guarded_compile,
    )


def sgd_search(
    name: str,
    *,
    state_root: Path,
    timeout: float,
    rounds: int,
    seed: int,
    use_leanstral: bool,
    memory: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    from jevops.search import drive_sgd

    return drive_sgd(
        name,
        state_root=state_root,
        timeout=timeout,
        rounds=rounds,
        seed=seed,
        use_leanstral=use_leanstral,
        memory=memory,
        rng_cls=random.Random,
        load_fn=lra_splice.load_warmup_records,
        clone_fn=lra_kb.lra_cw.clone_dir,
        relpath_fn=lra_kb.lra_cw.source_relpath,
        tactic_fn=lra_fan.tactic_block,
        holes_fn=lra_mask.find_holes,
        token_fn=lra_loop.token_count,
        key_fns=(lra_pca.load_keyfile, lra_pca.pin_typesafe_path),
        jev_fn=jev_round,
        drop_fn=drop_subset,
        eval_fn=evaluate_tactics,
        extract_fn=lra_loop.extract_generated_tactics,
        match_fn=lra_kb.match_reference_indent,
        flatten_fn=lra_kb.flatten_overindent,
        ledger_cls=lra_t1.ProblemLedger,
        shot_names=lra_mask.SHOT_NAMES,
        example_fn=lra_mask.few_shot_example,
        prompt_fn=lra_mask.few_shot_prompt,
        keyfile_fns=(lra_mistral.load_keyfiles, lra_mistral.pin_paths),
        generate_fn=lra_mistral.generate_mistral,
        hammer_fn=lra_mask.hammer_repair,
        redact_fn=lra_pca.redact,
        hardware_class=HARDWARE_CLASS,
        protocol=PROTOCOL,
        pr=PR_ID,
    )


def _accept(evals: Sequence[Mapping[str, Any]], keep_tokens: int) -> Optional[dict[str, Any]]:
    from jevops.search import accept_keepbest

    return accept_keepbest(evals, keep_tokens)


def diffuse_search(
    name: str,
    *,
    state_root: Path,
    timeout: float,
    rounds: int,
    seed: int,
    use_leanstral: bool,
    tau: float = 0.12,
) -> dict[str, Any]:
    """Exploit: drop all high-p holes at once. Explore: random subset + Leanstral noise.

    Denoise: hammer variants. This is bandit/coordinate search with a diffusion
    restart, not neural SGD or a trained denoiser.
    """

    from jevops.outer import head_chars, named_shots
    from jevops.search import drive_diffuse

    def _shrink(rec: Mapping[str, Any], body: str, tokens: int, recs: Sequence[Mapping[str, Any]], _name: str) -> str:
        return (
            f"Current lake-valid keep is {tokens} tokens "
            f"(reference {lra_loop.token_count(lra_fan.tactic_block(rec))}). "
            "Shrink it further. Keep induction and every case arm. "
            "Delete only residual simp-at/rename_i/have/rw. No sorry.\n\n"
            + lra_mask.few_shot_prompt(
                rec,
                named_shots(recs, lra_mask.SHOT_NAMES, skip_name=name, example_fn=lra_mask.few_shot_example),
            )
            + f"\nCURRENT KEEP ({tokens} tokens):\n{head_chars(body, 1800)}\n"
        )

    return drive_diffuse(
        name,
        state_root=state_root,
        timeout=timeout,
        rounds=rounds,
        seed=seed,
        use_leanstral=use_leanstral,
        tau=tau,
        load_records_fn=lra_splice.load_warmup_records,
        clone_fn=lra_kb.lra_cw.clone_dir,
        relpath_fn=lra_kb.lra_cw.source_relpath,
        tactic_fn=lra_fan.tactic_block,
        holes_fn=lra_mask.find_holes,
        token_fn=lra_loop.token_count,
        key_fns=(lra_pca.load_keyfile, lra_pca.pin_typesafe_path),
        leanstral_fns=(lra_mistral.load_keyfiles, lra_mistral.pin_paths),
        drop_fn=drop_subset,
        eval_fn=evaluate_tactics,
        jev_fn=jev_round,
        ledger_cls=lra_t1.ProblemLedger,
        one_prompt_fn=lra_mask.one_hole_prompt,
        shrink_prompt_fn=_shrink,
        generate_fn=lambda prompt, ledger: lra_mistral.generate_mistral(prompt, ledger, max_new_tokens=400, timeout=120.0),
        extract_fn=lra_loop.extract_generated_tactics,
        match_fn=lra_kb.match_reference_indent,
        flatten_over_fn=lra_kb.flatten_overindent,
        hammer_fn=lra_mask.hammer_repair,
        skip_exc=(lra_t1.Track1LedgerError, lra_mistral.Track1MistralError),
        redact_fn=lra_pca.redact,
        hardware_class=HARDWARE_CLASS,
        protocol=PROTOCOL,
        pr=PR_ID,
    )


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--names", default="CallElimCorrect.substOldPostSubset,Core.InitsUpdatesComm")
    parser.add_argument("--rounds", type=int, default=3)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--no-leanstral", action="store_true")
    parser.add_argument("--diffuse", action="store_true", help="multi-hole exploit + Leanstral noise/denoise")
    parser.add_argument("--state-root", type=Path, default=DEFAULT_STATE)
    parser.add_argument("--timeout", type=float, default=120.0)
    parser.add_argument("--out", type=Path, default=OUT_DEFAULT)
    from jevops.outer import list_or_none

    args = parser.parse_args(list_or_none(argv))
    from jevops.outer import pin_env

    pin_env({"IPFS_ACCELERATE_LLAMA_CPP_AUTOSTART": "0"}, overwrite=False)
    from jevops.outer import replace_if, split_csv

    names = split_csv(args.names)
    started = time.perf_counter()
    reports = [
        (
            replace_if(args.diffuse, diffuse_search, sgd_search)
        )(
            name,
            state_root=args.state_root,
            timeout=args.timeout,
            rounds=args.rounds,
            seed=args.seed,
            use_leanstral=not args.no_leanstral,
        )
        for name in names
    ]
    from jevops.outer import elapsed_ms, utc_stamp, write_json_pair

    payload = {
        "schema": "lra-sgd-fanout-batch/v1",
        "observed_at": utc_stamp(),
        "arena_score": None,
        "called_docker0": False,
        "wall_ms": elapsed_ms(started),
        "problems": reports,
    }
    latest = write_json_pair(
        args.out,
        payload,
        prefix="sgd-fanout",
        latest="sgd-fanout-latest.json",
        refuse="apikey_",
        refuse_msg="refusing to write a receipt that contains a secret",
    )
    from jevops.outer import print_json, text_or

    print_json(
        {
            "ok": True,
            "latest": text_or(latest),
            "results": [
                {
                    "name": item.get("name"),
                    "ref": item.get("ref_tokens"),
                    "keep": item.get("keep_tokens"),
                    "ratio": item.get("ratio"),
                    "dropped": item.get("dropped"),
                }
                for item in reports
            ],
            "arena_score": None,
        }
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

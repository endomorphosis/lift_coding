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
    from jevops.outer import head_seq, map_pairs
    from jevops.tactics import hammer_variants as _fn

    extras: list[tuple[str, str]] = [
        ("inits_replay", lra_ius.replay(reference)),
        ("inits_step", lra_ius.replay(tactics)),
    ]
    extras.extend(map_pairs(head_seq(lra_ius.propose(tactics), 8)))
    extras.extend(map_pairs(lra_sym.closed_candidates(tactics, max_candidates=6)))
    return _fn(tactics, reference, extras)


def jev_round(
    record: Mapping[str, Any],
    holes: Sequence[lra_mask.Hole],
    history: Sequence[Mapping[str, Any]],
    keep_tokens: int,
) -> dict[str, Any]:
    from jevops.jev import typesafe_session

    loaded, skip = typesafe_session(setup=(lra_pca.pin_typesafe_path,), fallback=False)
    if skip is not None:
        return skip
    Choice = loaded["Choice"]
    Noul = loaded["Noul"]
    Score = loaded["Score"]
    TypeSafeClient = loaded["TypeSafeClient"]

    from jevops.catalogs import LIKELY_SHORTER_CRITERIA, SGD_HOLE_INSTRUCTIONS
    from jevops.jev import (
        choice_questions,
        hole_criteria,
        hole_round_state,
        invoke_system_one,
        pack_choice_round,
        skipped,
    )

    from jevops.jev import complete_choice_round

    criteria = hole_criteria(holes)
    state = hole_round_state(record, holes, history, keep_tokens)
    questions = choice_questions(
        Choice=Choice,
        Noul=Noul,
        Score=Score,
        criteria=criteria,
        best_key="next_hole",
        best_instructions=SGD_HOLE_INSTRUCTIONS,
        nouls={"likely_compiles": "Will dropping that hole still compile?"},
        scores={
            "likely_token_cut": (
                "How large a token cut if that hole is dropped?",
                list(LIKELY_SHORTER_CRITERIA),
            )
        },
    )
    return complete_choice_round(
        configured=True,
        criteria=criteria,
        invoke_fn=lambda: invoke_system_one(TypeSafeClient(timeout=45.0), state, questions),
        pack_fn=lambda result, wall_ms, **_k: pack_choice_round(
            result,
            choice_key="next_hole",
            noul_key="likely_compiles",
            score_key="likely_token_cut",
            wall_ms=wall_ms,
        ),
        redact_fn=lra_pca.redact,
        skip_fn=lambda reason, **extra: skipped(reason, **extra),
        skip_extra={"choice": None, "probabilities": {}},
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
    from jevops.search import compile_variant_evals

    def _compile(label: str, body: str) -> dict[str, Any]:
        from jevops.outer import dict_call, get_str

        def _run() -> dict[str, Any]:
            return dict_call(
                lra_kb.compile_tactics,
                record,
                body,
                state_root=state_root,
                timeout=timeout,
                restore=restore,
            )

        return dict_call(
            lra_kern.guarded_compile,
            memory,
            name=get_str(record, "name"),
            kind=f"sgd:{label}",
            tactics=body,
            compile_fn=_run,
        )

    variants = hammer_variants(tactics, reference)
    # Lake splices one file; serialize compiles. "Parallel hammers" means
    # four closer variants per minibatch, not concurrent writes.
    return compile_variant_evals(variants, _compile)


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
    from jevops.outer import first_int

    rng = random.Random(first_int(seed))
    from jevops.outer import load_and_clone

    record, records, digest, _clone, _dest, restore = load_and_clone(
        lra_splice.load_warmup_records,
        name,
        state_root,
        clone_fn=lra_kb.lra_cw.clone_dir,
        relpath_fn=lra_kb.lra_cw.source_relpath,
        error_cls=RuntimeError,
        miss=f"unknown warm-up problem: {name}",
    )
    from jevops.outer import pin_calls
    from jevops.search import begin_keep_search, boxed_keepbest, coordinate_rounds

    started = begin_keep_search(
        record,
        tactic_fn=lra_fan.tactic_block,
        find_fn=lra_mask.find_holes,
        token_fn=lra_loop.token_count,
        pin_fn=pin_calls(lra_pca.load_keyfile, lra_pca.pin_typesafe_path),
    )
    from jevops.outer import head_errors, keep_box, take_keys

    reference, holes, keep, keep_tokens, history, dropped, jevs = take_keys(
        started, "reference", "holes", "keep", "keep_tokens", "history", "dropped", "jevs"
    )
    box = keep_box(keep_tokens, keep)

    def _choose(remaining: Sequence[Any], _dropped: set[str], _round: int) -> list[str]:
        from jevops.search import choose_minibatch

        jev = jev_round(record, remaining, history, box["tokens"])
        jevs.append(jev)
        return choose_minibatch(remaining, jev, rng, k=2)

    walked = coordinate_rounds(
        holes,
        rounds=rounds,
        choose_fn=_choose,
        trial_fn=lambda chosen: drop_subset(reference, holes, chosen),
        eval_fn=lambda trial: evaluate_tactics(
            record,
            trial,
            state_root=state_root,
            timeout=timeout,
            restore=restore,
            reference=reference,
            memory=memory,
        ),
        accept_fn=boxed_keepbest(box),
        keep_tokens=keep_tokens,
        keep_body=keep,
        history=history,
    )
    from jevops.search import attach_jev_rounds, maybe_leanstral_restart, sgd_payload, unpack_walked

    keep, keep_tokens, dropped, history = unpack_walked(walked)

    rounds_out = attach_jev_rounds(walked["rounds"], jevs, history)

    from jevops.repair import bind_align

    _align = bind_align(
        reference,
        extract_fn=lra_loop.extract_generated_tactics,
        match_fn=lra_kb.match_reference_indent,
        flatten_fn=lra_kb.flatten_overindent,
    )

    def _generate() -> tuple[str, Any, Any]:
        from jevops.outer import after_calls

        ledger = lra_t1.ProblemLedger(name=f"{name}#sgd")
        from jevops.outer import named_shots

        shots = named_shots(
            records, lra_mask.SHOT_NAMES, skip_name=name, example_fn=lra_mask.few_shot_example
        )
        prompt = lra_mask.few_shot_prompt(record, shots)
        text, identity, _line = after_calls(
            (lra_mistral.load_keyfiles, lra_mistral.pin_paths),
            lra_mistral.generate_mistral,
            prompt,
            ledger,
            max_new_tokens=700,
            timeout=180.0,
        )
        return text, identity, ledger

    keep, keep_tokens, leanstral = maybe_leanstral_restart(
        use=use_leanstral,
        keep=keep,
        keep_tokens=keep_tokens,
        ref_tokens=lra_loop.token_count(reference),
        generate_fn=_generate,
        flatten_fn=_align,
        eval_fn=lambda body: evaluate_tactics(
            record,
            body,
            state_root=state_root,
            timeout=timeout,
            restore=restore,
            reference=reference,
            memory=memory,
        ),
        hammer_fn=lambda filled, evals: lra_mask.hammer_repair(
            filled, reference, head_errors(evals)
        ),
        ledger_fn=lambda ledger: ledger.as_dict(),
    )

    ref_tokens = lra_loop.token_count(reference)
    return lra_pca.redact(
        sgd_payload(
            name=name,
            digest=digest,
            n_holes=len(holes),
            ref_tokens=ref_tokens,
            keep_tokens=keep_tokens,
            dropped=dropped,
            rounds=rounds_out,
            leanstral=leanstral,
            hardware_class=HARDWARE_CLASS,
            protocol=PROTOCOL,
            pr=PR_ID,
        )
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

    from jevops.outer import either, head_chars, load_and_clone, named_shots, pin_calls
    from jevops.repair import flatten_matched
    from jevops.search import diffuse_noise_step, run_diffuse_search

    held: dict[str, Any] = {}

    def _load(problem: str, *, error_cls: Any) -> tuple[Any, Any, str, Any, Any, bytes]:
        packed = load_and_clone(
            lra_splice.load_warmup_records,
            problem,
            state_root,
            clone_fn=lra_kb.lra_cw.clone_dir,
            relpath_fn=lra_kb.lra_cw.source_relpath,
            error_cls=error_cls,
            miss=f"unknown warm-up problem: {problem}",
        )
        held["restore"] = packed[5]
        return packed

    def _eval(record: Mapping[str, Any], body: str) -> list[dict[str, Any]]:
        return evaluate_tactics(
            record,
            body,
            state_root=state_root,
            timeout=timeout,
            restore=held["restore"],
            reference=lra_fan.tactic_block(record),
        )

    def _noise(
        round_i: int,
        remaining: Sequence[Any],
        keep: str,
        keep_tokens: int,
        record: Mapping[str, Any],
        records: Sequence[Mapping[str, Any]],
        rng: Any,
    ) -> tuple[Any, str, int]:
        return diffuse_noise_step(
            use_leanstral=use_leanstral,
            remaining=remaining,
            rng=rng,
            keep=keep,
            keep_tokens=keep_tokens,
            record=record,
            records=records,
            name=name,
            ledger_fn=lambda i: lra_t1.ProblemLedger(name=f"{name}#diffuse-r{i}"),
            one_hole_prompt_fn=lra_mask.one_hole_prompt,
            shrink_prompt_fn=lambda rec, body, tokens, recs, _name: (
                f"Current lake-valid keep is {tokens} tokens "
                f"(reference {lra_loop.token_count(lra_fan.tactic_block(rec))}). "
                "Shrink it further. Keep induction and every case arm. "
                "Delete only residual simp-at/rename_i/have/rw. No sorry.\n\n"
                + lra_mask.few_shot_prompt(
                    rec,
                    named_shots(recs, lra_mask.SHOT_NAMES, skip_name=name, example_fn=lra_mask.few_shot_example),
                )
                + f"\nCURRENT KEEP ({tokens} tokens):\n{head_chars(body, 1800)}\n"
            ),
            generate_fn=lambda prompt, ledger: lra_mistral.generate_mistral(
                prompt, ledger, max_new_tokens=400, timeout=120.0
            ),
            extract_fn=lra_loop.extract_generated_tactics,
            flatten_fn=flatten_matched(lra_kb.match_reference_indent, lra_kb.flatten_overindent),
            hammer_fn=lambda noisy, errors: lra_mask.hammer_repair(
                noisy, lra_fan.tactic_block(record), errors
            ),
            eval_fn=lambda body: _eval(record, body),
            skip_exc=(lra_t1.Track1LedgerError, lra_mistral.Track1MistralError),
            round_i=round_i,
        )

    return run_diffuse_search(
        name,
        load_fn=_load,
        tactic_fn=lra_fan.tactic_block,
        find_fn=lra_mask.find_holes,
        token_fn=lra_loop.token_count,
        pin_fn=pin_calls(
            lra_pca.load_keyfile,
            lra_pca.pin_typesafe_path,
            *either(use_leanstral, lambda: (lra_mistral.load_keyfiles, lra_mistral.pin_paths), lambda: ()),
        ),
        drop_fn=drop_subset,
        eval_fn=_eval,
        jev_fn=jev_round,
        noise_fn=_noise,
        rounds=rounds,
        seed=seed,
        tau=tau,
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

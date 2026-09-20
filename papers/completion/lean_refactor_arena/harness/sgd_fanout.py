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
ROOT_ACCEL = Path("/home/barberb/lift_coding/external/ipfs_accelerate")
OUT_DEFAULT = PAPER_ROOT / "evidence" / "canaries"
DEFAULT_STATE = Path.home() / ".local/state/ipfs_accelerate_py/vericodegen-2026-lra/track1-lake"

if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
import draft_fanout as lra_fan  # noqa: E402
import mca_mask_replace as lra_mask  # noqa: E402
import pca_mca_fanout as lra_pca  # noqa: E402
import run_warmup as lra_loop  # noqa: E402
import splice as lra_splice  # noqa: E402
import track1_keepbest as lra_kb  # noqa: E402
import track1_ledger as lra_t1  # noqa: E402
import track1_mistral_leanstral as lra_mistral  # noqa: E402

PROTOCOL = "LRA/v1"
PR_ID = "PR-9e"
HARDWARE_CLASS = "mistral_labs_api"


def drop_subset(tactics: str, holes: Sequence[lra_mask.Hole], chosen: Sequence[str]) -> str:
    from jevops.tactics import drop_subset as _fn

    return _fn(tactics, holes, chosen)


def hammer_variants(tactics: str, reference: str) -> list[tuple[str, str]]:
    """Parallel tactician branches. Aesop is not a Strata/CSLib dep."""

    import inits_updates_shorten as lra_ius
    import symbol_diffuse as lra_sym
    from jevops.outer import head_seq
    from jevops.tactics import hammer_variants as _fn

    extras: list[tuple[str, str]] = [
        ("inits_replay", lra_ius.replay(reference)),
        ("inits_step", lra_ius.replay(tactics)),
    ]
    extras.extend((str(item["kind"]), str(item["tactics"])) for item in head_seq(lra_ius.propose(tactics), 8))
    extras.extend(
        (str(item["kind"]), str(item["tactics"]))
        for item in lra_sym.closed_candidates(tactics, max_candidates=6)
    )
    return _fn(tactics, reference, extras)


def jev_round(
    record: Mapping[str, Any],
    holes: Sequence[lra_mask.Hole],
    history: Sequence[Mapping[str, Any]],
    keep_tokens: int,
) -> dict[str, Any]:
    lra_pca.pin_typesafe_path()
    from ipfs_accelerate_py.typesafe_inference import Choice, Noul, Score, TypeSafeClient, typesafe_configured

    from jevops.jev import (
        choice_questions,
        hole_criteria,
        hole_round_state,
        invoke_system_one,
        pack_choice_round,
        skipped,
    )

    if not typesafe_configured():
        return skipped("no_key", choice=None, probabilities={})
    criteria = hole_criteria(holes)
    if not criteria:
        return skipped("no_holes", choice=None, probabilities={})
    state = hole_round_state(record, holes, history, keep_tokens)
    questions = choice_questions(
        Choice=Choice,
        Noul=Noul,
        Score=Score,
        criteria=criteria,
        best_key="next_hole",
        best_instructions=(
            "Which hole id should we drop next in this stochastic descent? "
            "Prefer strength_reduction simp-at runs, then dead_code rename_i. "
            "Do not write Lean."
        ),
        nouls={"likely_compiles": "Will dropping that hole still compile?"},
        scores={
            "likely_token_cut": (
                "How large a token cut if that hole is dropped?",
                list(lra_fan.LIKELY_SHORTER_CRITERIA),
            )
        },
    )
    result, wall_ms = invoke_system_one(TypeSafeClient(timeout=45.0), state, questions)
    return lra_pca.redact(
        pack_choice_round(
            result,
            choice_key="next_hole",
            noul_key="likely_compiles",
            score_key="likely_token_cut",
            wall_ms=wall_ms,
        )
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
        def _run() -> dict[str, Any]:
            return dict(
                lra_kb.compile_tactics(
                    record, body, state_root=state_root, timeout=timeout, restore=restore
                )
            )

        return dict(
            lra_kern.guarded_compile(
                memory,
                name=record.get("name"),
                kind=f"sgd:{label}",
                tactics=body,
                compile_fn=_run,
            )
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
    rng = random.Random(seed)
    from jevops.outer import lookup_named

    _raw, digest, records = lra_splice.load_warmup_records()
    record = lookup_named(
        records, name, error_cls=RuntimeError, miss=f"unknown warm-up problem: {name}"
    )
    reference = lra_fan.tactic_block(record)
    holes = lra_mask.find_holes(reference)
    clone = lra_kb.lra_cw.clone_dir(str(record["url"]), state_root)
    dest = clone / lra_kb.lra_cw.source_relpath(record)
    from jevops.outer import read_bytes_if

    restore = read_bytes_if(dest)
    keep = reference
    keep_tokens = lra_loop.token_count(reference)
    history: list[dict[str, Any]] = []
    dropped: set[str] = set()
    lra_pca.load_keyfile()
    lra_pca.pin_typesafe_path()
    from jevops.search import apply_keepbest, coordinate_rounds, minibatch_ids, strip_tactics

    box = {"tokens": keep_tokens, "keep": keep}
    jevs: list[dict[str, Any]] = []

    def _choose(remaining: Sequence[Any], _dropped: set[str], _round: int) -> list[str]:
        jev = jev_round(record, remaining, history, box["tokens"])
        jevs.append(jev)
        ranked = sorted(
            (jev.get("probabilities") or {}).items(),
            key=lambda item: item[1],
            reverse=True,
        )
        return minibatch_ids(
            [hole.hole_id for hole in remaining],
            choice=jev.get("choice"),
            ranked=ranked,
            rng=rng,
            k=2,
        )

    def _accept(evals: Sequence[Mapping[str, Any]], tokens: int, trial: str) -> tuple[Optional[Mapping[str, Any]], int, str]:
        best, nxt_tokens, body = apply_keepbest(evals, tokens, trial=trial)
        if not best:
            return None, nxt_tokens, box["keep"]
        box["tokens"] = nxt_tokens
        box["keep"] = body
        return strip_tactics([best])[0], nxt_tokens, body

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
        accept_fn=_accept,
        keep_tokens=keep_tokens,
        keep_body=keep,
        history=history,
    )
    keep = str(walked["keep"])
    keep_tokens = int(walked["keep_tokens"])
    dropped = set(walked["dropped"])
    history = list(walked["history"])
    rounds_out = []
    for row, jev in zip(walked["rounds"], jevs):
        item = dict(row)
        item["jev"] = jev
        rounds_out.append(item)
    for row, jev in zip(history, jevs):
        row["jev_choice"] = jev.get("choice")
    leanstral = None
    if use_leanstral and keep_tokens >= lra_loop.token_count(reference):
        lra_mistral.load_keyfiles()
        lra_mistral.pin_paths()
        ledger = lra_t1.ProblemLedger(name=f"{name}#sgd")
        shots = [
            lra_mask.few_shot_example(item)
            for item in records
            if item.get("name") in lra_mask.SHOT_NAMES and item.get("name") != name
        ]
        prompt = lra_mask.few_shot_prompt(record, shots)
        text, identity, _line = lra_mistral.generate_mistral(
            prompt, ledger, max_new_tokens=700, timeout=180.0
        )
        filled = lra_kb.flatten_overindent(
            reference, lra_kb.match_reference_indent(reference, lra_loop.extract_generated_tactics(text))
        )
        evals = evaluate_tactics(
            record, filled, state_root=state_root, timeout=timeout, restore=restore, reference=reference, memory=memory
        )
        hammered = lra_mask.hammer_repair(filled, reference, (evals[0].get("errors") if evals else None) or [])
        evals_h = evaluate_tactics(
            record, hammered, state_root=state_root, timeout=timeout, restore=restore, reference=reference, memory=memory
        )
        leanstral = {
            "identity": identity,
            "ledger": ledger.as_dict(),
            "evals": evals,
            "hammer_evals": evals_h,
        }
        for row in evals + evals_h:
            if row.get("theorem_ok") and int(row.get("token_count") or keep_tokens) < keep_tokens:
                keep = hammered if row in evals_h else filled
                keep_tokens = int(row["token_count"])
    from jevops.search import token_ratio

    ref_tokens = lra_loop.token_count(reference)
    return lra_pca.redact(
        {
            "schema": "lra-sgd-fanout/v1",
            "protocol": PROTOCOL,
            "pr": PR_ID,
            "name": name,
            "warmup_jsonl_sha256": digest,
            "n_holes": len(holes),
            "ref_tokens": ref_tokens,
            "keep_tokens": keep_tokens,
            "ratio": token_ratio(keep_tokens, ref_tokens),
            "dropped": sorted(dropped),
            "rounds": rounds_out,
            "leanstral": leanstral,
            "hardware_class": HARDWARE_CLASS,
            "called_docker0": False,
            "official_track2": False,
            "arena_score": None,
            "note": "Jev-guided stochastic coordinate descent on MCA holes; not neural SGD.",
        }
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

    rng = random.Random(seed)
    from jevops.outer import head_chars, lookup_named

    _raw, digest, records = lra_splice.load_warmup_records()
    record = lookup_named(
        records, name, error_cls=RuntimeError, miss=f"unknown warm-up problem: {name}"
    )
    reference = lra_fan.tactic_block(record)
    holes = lra_mask.find_holes(reference)
    clone = lra_kb.lra_cw.clone_dir(str(record["url"]), state_root)
    dest = clone / lra_kb.lra_cw.source_relpath(record)
    from jevops.outer import read_bytes_if

    restore = read_bytes_if(dest)
    keep = reference
    keep_tokens = lra_loop.token_count(reference)
    dropped: set[str] = set()
    history: list[dict[str, Any]] = []
    rounds_out: list[dict[str, Any]] = []
    lra_pca.load_keyfile()
    lra_pca.pin_typesafe_path()
    if use_leanstral:
        lra_mistral.load_keyfiles()
        lra_mistral.pin_paths()

    def consider(label: str, hole_ids: Sequence[str]) -> dict[str, Any]:
        nonlocal keep, keep_tokens, dropped
        from jevops.search import apply_keepbest
        from jevops.search import strip_tactics

        trial = drop_subset(reference, holes, list(dict.fromkeys(list(dropped) + list(hole_ids))))
        evals = evaluate_tactics(
            record, trial, state_root=state_root, timeout=timeout, restore=restore, reference=reference, memory=memory
        )
        hit, keep_tokens, body = apply_keepbest(evals, keep_tokens, trial=trial)
        if hit:
            keep = body
            dropped.update(hole_ids)
        return {
            "label": label,
            "holes": list(hole_ids),
            "accepted": bool(hit),
            "keep_tokens": keep_tokens,
            "evals": strip_tactics(evals),
        }

    # Exploit jump: delete every MCA hole (the 414 move on CallElimCorrect).
    full = consider("exploit_all_holes", [hole.hole_id for hole in holes])
    rounds_out.append({"round": 0, "phase": "exploit_all", **full})

    for round_i in range(1, max(1, rounds) + 1):
        remaining = [hole for hole in holes if hole.hole_id not in dropped]
        jev: dict[str, Any] = {"skipped": True, "reason": "no_holes"}
        step_exploit: Optional[dict[str, Any]] = None
        step_explore: Optional[dict[str, Any]] = None
        high: list[str] = []
        explore: list[str] = []
        if remaining:
            jev = jev_round(record, remaining, history, keep_tokens)
            from jevops.search import high_p_ids

            high = high_p_ids(jev.get("probabilities") or {}, tau=tau, fallback=jev.get("choice"))
            explore = [rng.choice([hole.hole_id for hole in remaining])]
            step_exploit = consider("exploit_high_p", high)
            step_explore = consider("explore_random", explore)
        noise = None
        if use_leanstral:
            round_ledger = lra_t1.ProblemLedger(name=f"{name}#diffuse-r{round_i}")
            if remaining:
                hole = rng.choice(remaining)
                prompt = lra_mask.one_hole_prompt(record, keep, hole)
                noise_meta = {"hole": hole.hole_id, "mode": "one_hole"}
            else:
                shots = [
                    lra_mask.few_shot_example(item)
                    for item in records
                    if item.get("name") in lra_mask.SHOT_NAMES and item.get("name") != name
                ]
                prompt = (
                    f"Current lake-valid keep is {keep_tokens} tokens "
                    f"(reference {lra_loop.token_count(reference)}). "
                    "Shrink it further. Keep induction and every case arm. "
                    "Delete only residual simp-at/rename_i/have/rw. No sorry.\n\n"
                    + lra_mask.few_shot_prompt(record, shots)
                    + f"\nCURRENT KEEP ({keep_tokens} tokens):\n{head_chars(keep, 1800)}\n"
                )
                noise_meta = {"hole": None, "mode": "shrink_keep"}
            try:
                text, identity, _line = lra_mistral.generate_mistral(
                    prompt, round_ledger, max_new_tokens=400, timeout=120.0
                )
            except (lra_t1.Track1LedgerError, lra_mistral.Track1MistralError):
                text, identity = "", {}
            filled = lra_loop.extract_generated_tactics(text) if text else ""
            if filled:
                noisy = lra_kb.flatten_overindent(
                    keep, lra_kb.match_reference_indent(keep, filled)
                )
                evals_n = evaluate_tactics(
                    record, noisy, state_root=state_root, timeout=timeout, restore=restore, reference=reference, memory=memory
                )
                denoised = lra_mask.hammer_repair(
                    noisy, reference, (evals_n[0].get("errors") if evals_n else None) or []
                )
                evals_d = evaluate_tactics(
                    record, denoised, state_root=state_root, timeout=timeout, restore=restore, reference=reference, memory=memory
                )
                from jevops.search import apply_keepbest
                from jevops.search import strip_tactics

                hit, keep_tokens, body = apply_keepbest(evals_n + evals_d, keep_tokens, trial=denoised)
                if hit:
                    keep = body
                noise = {
                    **noise_meta,
                    "identity": identity,
                    "accepted": bool(hit),
                    "noise_evals": strip_tactics(evals_n),
                    "denoise_evals": strip_tactics(evals_d),
                }
        history.append(
            {
                "round": round_i,
                "high_p": high,
                "explore": explore,
                "keep_tokens": keep_tokens,
                "jev_choice": jev.get("choice"),
            }
        )
        rounds_out.append(
            {
                "round": round_i,
                "jev": jev,
                "exploit": step_exploit,
                "explore": step_explore,
                "diffuse": noise,
                "keep_tokens": keep_tokens,
            }
        )
    from jevops.search import token_ratio

    ref_tokens = lra_loop.token_count(reference)
    return lra_pca.redact(
        {
            "schema": "lra-diffuse-denoise/v1",
            "protocol": PROTOCOL,
            "pr": PR_ID,
            "name": name,
            "warmup_jsonl_sha256": digest,
            "n_holes": len(holes),
            "ref_tokens": ref_tokens,
            "keep_tokens": keep_tokens,
            "ratio": token_ratio(keep_tokens, ref_tokens),
            "dropped": sorted(dropped),
            "rounds": rounds_out,
            "ledger": None,
            "hardware_class": HARDWARE_CLASS,
            "called_docker0": False,
            "official_track2": False,
            "arena_score": None,
            "note": (
                "Exploit=drop high-p and all MCA holes; explore=random hole; "
                "diffuse=Leanstral one-hole noise; denoise=hammer. Not neural SGD."
            ),
        }
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
    args = parser.parse_args(list(argv) if argv is not None else None)
    from jevops.outer import pin_env

    pin_env({"IPFS_ACCELERATE_LLAMA_CPP_AUTOSTART": "0"}, overwrite=False)
    from jevops.outer import split_csv

    names = split_csv(args.names)
    started = time.perf_counter()
    reports = [
        (
            diffuse_search if args.diffuse else sgd_search
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
    from jevops.outer import print_json

    print_json(
        {
            "ok": True,
            "latest": str(latest),
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

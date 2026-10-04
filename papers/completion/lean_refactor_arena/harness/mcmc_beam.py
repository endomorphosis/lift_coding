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
import json
import math
import os
import random
import sys
import time
from pathlib import Path
from typing import Any, Callable, Mapping, Optional, Sequence

HERE = Path(__file__).resolve().parent
PAPER_ROOT = HERE.parent
OUT_DEFAULT = PAPER_ROOT / "evidence" / "canaries"
PR_ID = "PR-9g"

if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
import _jevops_path  # noqa: E402,F401
import constrained_beam as lra_cb  # noqa: E402
import draft_fanout as lra_fan  # noqa: E402
import inits_updates_shorten as lra_ius  # noqa: E402
import pca_mca_fanout as lra_pca  # noqa: E402
import run_warmup as lra_loop  # noqa: E402
import splice as lra_splice  # noqa: E402
import track1_keepbest as lra_kb  # noqa: E402
import track1_ledger as lra_t1  # noqa: E402


from jevops.catalogs import DEFAULT_TRACK1_STATE as DEFAULT_STATE
from jevops.catalogs import HARDWARE_CLASS_SPARK as HARDWARE_CLASS
from jevops.catalogs import MAX_LEANSTRAL
from jevops.catalogs import MAX_MCMC_JEV as MAX_JEV
from jevops.catalogs import MAX_PROPOSALS
from jevops.catalogs import PROTOCOL
from jevops.inits import HND_BLOCK
from jevops.inits import HND_REPLACEMENTS
from jevops.inits import IH_APPLY
from jevops.inits import IH_APPLY_SHORT
from jevops.inits import IH_EXACT
from jevops.inits import REFINE_RFL
from jevops.catalogs import MCMC_CLOSERS as CLOSERS
from jevops.tactics import Chain
from jevops.tactics import LOCKED_HEADS


def locked_have_names(reference: str) -> set[str]:
    from jevops.outer import drive_mapped_lines

    return drive_mapped_lines(
        reference,
        lines_fn=lra_cb.prefix_have_lines,
        name_fn=lra_cb.have_binder_name,
    )


def mutable_indices(tactics: str, locked_haves: set[str]) -> list[int]:
    from jevops.tactics import mutable_line_indices

    return mutable_line_indices(tactics, locked_haves, skip_prefix=LOCKED_HEADS)


def apply_drop(tactics: str, index: int) -> str:
    from jevops.mask import drop_index

    return drop_index(tactics, index)


def apply_replace(tactics: str, index: int, nxt: str) -> str:
    from jevops.mask import replace_index

    return replace_index(tactics, index, nxt)


def join_consecutive_applies(tactics: str) -> str:
    from jevops.tactics import join_consecutive_applies as _fn

    return _fn(tactics)


def drop_last_duplicate_lines(tactics: str, locked_haves: set[str]) -> list[tuple[int, str, str]]:
    """Drop the last extra copy of a stripped line that appears more than once."""

    from jevops.tactics import drop_last_duplicate_lines as _fn

    return _fn(tactics, locked_haves)


def collapse_ih_simps(tactics: str) -> Optional[str]:
    """Fold the two simp bullets after ``apply (ih …).2.2`` into ``<;> simp_all``."""

    from jevops.tactics import collapse_ih_simps as _fn

    return _fn(tactics, needle=IH_APPLY)


def propose_edits(
    tactics: str,
    reference: str,
    rng: random.Random,
    extra: Optional[Sequence[dict[str, str]]] = None,
    limit: Optional[int] = MAX_PROPOSALS,
) -> list[dict[str, str]]:
    from jevops.tactics import drive_propose_edits

    return drive_propose_edits(
        tactics,
        reference,
        rng,
        extra,
        limit=limit,
        propose_fn=lra_ius.propose,
        replay_fn=lra_ius.replay,
        extras_fn=lra_ius.mcmc_extras,
        replay_note="apply the full Core.InitsUpdatesComm 268→139 kernel sequence",
        closers=CLOSERS,
        skip_prefix=LOCKED_HEADS,
    )


def load_typesafe():
    from jevops.jev import typesafe_namespace

    return typesafe_namespace(setup=(lra_pca.load_keyfile, lra_pca.pin_typesafe_path))


def typesafe_rank_proposals(
    record: Mapping[str, Any],
    current: str,
    proposals: Sequence[dict[str, str]],
    *,
    ledger: lra_t1.ProblemLedger,
) -> dict[str, Any]:
    from jevops.jev import drive_mcmc_rank

    return drive_mcmc_rank(
        record,
        current,
        proposals,
        ledger=ledger,
        load_fn=load_typesafe,
        token_fn=lra_loop.token_count,
        shorter_criteria=list(lra_fan.LIKELY_SHORTER_CRITERIA),
        estimate_fn=lra_t1.estimate_tokens,
        model_id=lra_t1.JEV_MODEL_ID,
    )


def metropolis_accept(*, old_tok: int, new_tok: int, temperature: float, rng: random.Random) -> bool:
    from jevops.search import metropolis_token_accept

    return metropolis_token_accept(old_tok=old_tok, new_tok=new_tok, temperature=temperature, rng=rng)


def leanstral_line_swap(
    record: Mapping[str, Any],
    tactics: str,
    rng: random.Random,
    locked_haves: set[str],
) -> Optional[dict[str, str]]:
    import docker0_client as lra_d0
    from jevops.search import drive_line_swap

    return drive_line_swap(
        record,
        tactics,
        rng,
        locked_haves,
        mutable_fn=mutable_indices,
        generate_fn=lra_d0.generate_as_client,
        parse_fn=lra_cb.parse_next_line,
        looks_fn=lra_cb.looks_like_tactic,
        replace_fn=apply_replace,
        stop=lra_cb.STOP_TOKEN,
    )


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
    from jevops.kernel import drive_guarded_compile

    return drive_guarded_compile(
        record,
        tactics,
        state_root=state_root,
        timeout=timeout,
        restore=restore,
        memory=memory,
        compile_fn=lra_kb.compile_tactics,
        guard_fn=lra_kern.guarded_compile,
        kind="mcmc",
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
    from jevops.search import drive_mcmc

    return drive_mcmc(
        record,
        rounds=rounds,
        beam=beam,
        temperature=temperature,
        seed=seed,
        state_root=state_root,
        timeout=timeout,
        init_tactics=init_tactics,
        leanstral=leanstral,
        memory=memory,
        tactic_fn=lra_fan.tactic_block,
        rng_cls=random.Random,
        ledger_cls=lra_t1.ProblemLedger,
        max_jev=MAX_JEV,
        clone_fn=lra_kb.lra_cw.clone_dir,
        relpath_fn=lra_kb.lra_cw.source_relpath,
        compile_fn=compile_one,
        token_fn=lra_loop.token_count,
        chain_cls=Chain,
        locked_fn=locked_have_names,
        failed_kinds={
            "rewrite_refine_constructor",
            "rewrite_ih_short",
            "rewrite_ih_exact",
            "collapse_ih_simps",
            "drop_orphan_hnd",
            "drop_isnotdefined_simp",
            "drop_orphan_intros_hin",
        },
        leanstral_swap_fn=leanstral_line_swap,
        propose_fn=propose_edits,
        rank_fn=typesafe_rank_proposals,
        accept_fn=metropolis_accept,
        max_leanstral=MAX_LEANSTRAL,
        pin_prefixes=("drop_duplicate", "join_applies", "leanstral_"),
        hardware_class=HARDWARE_CLASS,
    )


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
    from jevops.outer import list_or_none

    args = parser.parse_args(list_or_none(argv))
    if args.self_check or not args.live:
        from jevops.outer import print_ok

        return print_ok(self_check())
    from jevops.outer import pin_env

    pin_env({"IPFS_ACCELERATE_LLAMA_CPP_AUTOSTART": "0"}, overwrite=False)
    _raw, digest, records = lra_splice.load_warmup_records()
    from jevops.outer import split_csv

    names = split_csv(args.names)
    started = time.perf_counter()
    problems = []
    for name in names:
        from jevops.outer import lookup_named

        record = lookup_named(
            records, name, error_cls=RuntimeError, miss=f"unknown warm-up problem: {name}"
        )
        init_text = None
        if args.init_file:
            from jevops.outer import read_text

            init_text = read_text(args.init_file)
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
        from jevops.outer import get_str

        clone = lra_kb.lra_cw.clone_dir(get_str(record, "url"), args.state_root)
        dest = clone / lra_kb.lra_cw.source_relpath(record)
        from jevops.outer import read_bytes_if

        restore = read_bytes_if(dest)
        rows = []
        for kind, body in (("reference", reference), ("mcmc_best", None)):
            from jevops.outer import get_str, overlay_map, replace_if

            text = replace_if(kind == "reference", reference, get_str(search, "best_tactics", default=reference))
            compiled = compile_one(
                record,
                text,
                state_root=args.state_root,
                timeout=args.timeout,
                restore=restore,
                memory=None,
            )
            rows.append(
                overlay_map(
                    {"kind": kind, "n_chars": len(text)},
                    **{
                        k: compiled.get(k)
                        for k in ("ok", "theorem_ok", "module_exit_0", "token_count", "errors", "wall_ms")
                    },
                )
            )
        from jevops.search import keep_shortest_ok, kept_view

        kept = keep_shortest_ok(rows)
        ref_tokens = lra_loop.token_count(reference)
        problems.append(
            lra_pca.redact(
                {
                    "name": name,
                    "warmup_jsonl_sha256": digest,
                    "search": search,
                    "candidates": rows,
                    "kept": kept_view(kept),
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
    from jevops.outer import elapsed_ms, utc_stamp, write_json_pair

    payload = {
        "schema": "lra-mcmc-beam/v1",
        "observed_at": utc_stamp(),
        "protocol": PROTOCOL,
        "pr": PR_ID,
        "hardware_class": HARDWARE_CLASS,
        "called_docker0": False,
        "called_hosted_mistral": False,
        "official_track2": False,
        "arena_score": None,
        "wall_ms": elapsed_ms(started),
        "problems": problems,
    }
    latest = write_json_pair(
        args.out,
        payload,
        prefix="mcmc-beam",
        latest="mcmc-beam-latest.json",
        refuse="apikey_",
    )
    from jevops.outer import print_json, text_or

    print_json(
        {
            "ok": True,
            "latest": text_or(latest),
            "kept": [{"name": item.get("name"), "kept": item.get("kept")} for item in problems],
            "arena_score": None,
        }
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

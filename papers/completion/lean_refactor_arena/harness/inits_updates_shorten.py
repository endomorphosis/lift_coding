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
from pathlib import Path
from typing import Optional

HERE = Path(__file__).resolve().parent
PAPER_ROOT = HERE.parent
OUT_DEFAULT = PAPER_ROOT / "evidence" / "canaries"
CANARY_174 = OUT_DEFAULT / "cascade-best-174.lean"
CANARY_BEST = OUT_DEFAULT / "cascade-best-139.lean"

if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
import _jevops_path  # noqa: E402,F401
import draft_fanout as lra_fan  # noqa: E402
import run_warmup as lra_loop  # noqa: E402
import splice as lra_splice  # noqa: E402
from jevops.inits import KERNELS
from jevops.inits import Kernel
from jevops.inits import PROBLEM
from jevops.inits import TARGET_TOKENS
from jevops.inits import apply_kernel
from jevops.inits import family_tree
from jevops.inits import mcmc_extras
from jevops.inits import pca_mca_ops
from jevops.inits import propose
from jevops.inits import replay


def original_tactics() -> str:
    from jevops.outer import drive_named_block

    return drive_named_block(
        lra_splice.load_warmup_records,
        PROBLEM,
        tactic_fn=lra_fan.tactic_block,
        error_cls=RuntimeError,
        miss=f"unknown warm-up problem: {PROBLEM}",
    )


def expected_174() -> str:
    from jevops.outer import drive_prefer_file, read_text

    return drive_prefer_file(
        CANARY_BEST,
        CANARY_174,
        read_fn=read_text,
        missing_fn=lambda: replay(original_tactics()),
    )


def self_check() -> dict[str, object]:
    src = original_tactics()
    got = replay(src)
    from jevops.outer import call_if

    want = call_if(CANARY_174.is_file(), expected_174, default=got)
    src_tok = lra_loop.token_count(src)
    got_tok = lra_loop.token_count(got)
    from jevops.outer import finalize_ok

    return finalize_ok(
        {
            "source_tokens": src_tok,
            "replay_tokens": got_tok,
            "target_tokens": TARGET_TOKENS,
            "matches_canary": got == want,
            "n_kernels": len(KERNELS),
            "kinds": [kernel.kind for kernel in KERNELS],
            "warmup_jsonl_sha256": lra_splice.FROZEN_WARMUP_SHA256,
            "called_llm": False,
            "arena_score": None,
        },
        got == want,
        got_tok == TARGET_TOKENS,
        src_tok == 268,
    )


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-check", action="store_true")
    parser.add_argument("--replay", action="store_true")
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--timeout", type=float, default=180.0)
    parser.add_argument("--out", type=Path, default=OUT_DEFAULT)
    args = parser.parse_args(argv)
    if args.self_check or not args.replay:
        from jevops.outer import print_ok

        payload = self_check()
        code = print_ok(payload)
        if args.self_check and not args.replay:
            return code
        if not args.replay:
            return code
    src = original_tactics()
    got = replay(src)
    from jevops.lean import pack_inits_replay_receipt
    from jevops.outer import utc_stamp, write_text

    write_text(args.out / "inits-updates-replay.lean", got + "\n")

    receipt: dict[str, object] = pack_inits_replay_receipt(
        name=PROBLEM,
        source_tokens=lra_loop.token_count(src),
        replay_tokens=lra_loop.token_count(got),
        target_tokens=TARGET_TOKENS,
        n_kernels=len(KERNELS),
        stamp=utc_stamp(),
        digest=lra_splice.FROZEN_WARMUP_SHA256,
    )
    if args.live:
        import mcmc_beam as lra_mcmc
        import track1_keepbest as lra_kb

        from jevops.outer import get_str, head_seq, lookup_named

        _raw, digest, records = lra_splice.load_warmup_records()
        record = lookup_named(
            records, PROBLEM, error_cls=RuntimeError, miss=f"unknown warm-up problem: {PROBLEM}"
        )
        clone = lra_kb.lra_cw.clone_dir(get_str(record, "url"), lra_mcmc.DEFAULT_STATE)
        dest = clone / lra_kb.lra_cw.source_relpath(record)
        from jevops.outer import read_bytes_if

        restore = read_bytes_if(dest)
        compiled = lra_mcmc.compile_one(
            record, got, state_root=lra_mcmc.DEFAULT_STATE, timeout=args.timeout, restore=restore
        )
        receipt["theorem_ok"] = bool(compiled.get("theorem_ok"))
        receipt["lake_tokens"] = compiled.get("token_count")
        receipt["errors"] = head_seq(compiled.get("errors"), 1)
        receipt["warmup_jsonl_sha256"] = digest
    from jevops.outer import write_json_pair

    write_json_pair(
        args.out,
        receipt,
        prefix="inits-updates-replay",
        latest="inits-updates-replay-latest.json",
    )
    from jevops.outer import print_json

    print_json(receipt)
    if args.live and not receipt.get("theorem_ok"):
        return 1
    if lra_loop.token_count(got) != TARGET_TOKENS:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

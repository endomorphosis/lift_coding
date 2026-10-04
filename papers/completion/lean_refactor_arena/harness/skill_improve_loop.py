#!/usr/bin/env python3
"""Autonomous skill-improve loop.

OUTER: Grok via llm_router.generate_text (closed JSON action).
INNER: TypeSafe keep-loop + recursive skill trees, callable subloops,
static-analysis tools (kg/ast/exports/mcp/diffuse). TypeSafe self-improves
from memory without llm_router; it may optionally invoke the router.

Grok does not write Lean. Jev does not write Lean. Never docker0.
Not Track 2. Not an Arena score.
"""
from __future__ import annotations

import argparse
import json
import sys

from pathlib import Path
from typing import Any, Callable, Mapping, Optional

HERE = Path(__file__).resolve().parent
PAPER_ROOT = HERE.parent
OUT_DEFAULT = PAPER_ROOT / "evidence" / "canaries"
PR_ID = "PR-9h"

if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
import _jevops_path  # noqa: E402,F401
import binder_use as lra_bind  # noqa: E402
import random_canary as lra_rand  # noqa: E402
import track1_ledger as lra_t1  # noqa: E402
import typesafe_inner as lra_inner  # noqa: E402
from jevops.outer import deterministic_route  # noqa: E402
from jevops.outer import nca_status as nca_status_for_router  # noqa: E402
from jevops.outer import parse_action as _parse_action  # noqa: E402
from jevops.catalogs import KEEP_WORDS  # noqa: E402
from jevops.catalogs import OUTER_ACTIONS as ACTIONS  # noqa: E402
from jevops.catalogs import OUTER_ROUTER_EXTRA  # noqa: E402
from jevops.catalogs import OUTER_ROUTER_PREAMBLE  # noqa: E402
from jevops.catalogs import PROTOCOL  # noqa: E402
from jevops.catalogs import ROUTER_MAX_NEW  # noqa: E402
from jevops.catalogs import ROUTER_TIMEOUT  # noqa: E402
from jevops.catalogs import SMALL_CANARY_NAMES as SMALL_NAMES  # noqa: E402


def keep_best_board(out: Path) -> dict[str, int]:
    """Shortest random-best / cascade-best token count per small canary."""

    from jevops.outer import merge_keep_best

    return merge_keep_best(
        out,
        SMALL_NAMES,
        latest_json="random-canary-latest.json",
        extras={"Core.InitsUpdatesComm": ("cascade-best-139.lean", 139)},
    )


def board_total(board: Mapping[str, int]) -> int:
    from jevops.outer import board_total as _fn

    return _fn(board)


def parse_action(text: str) -> dict[str, Any]:
    """First JSON object in grok text; fail closed to action=run."""

    return _parse_action(text, actions=ACTIONS)


def router_prompt(
    board: Mapping[str, int],
    gaps: list[dict[str, Any]],
    last_lake: list[dict[str, Any]],
    *,
    nca_status: Optional[Mapping[str, Any]] = None,
) -> str:
    from jevops.outer import drive_router_text

    return drive_router_text(
        preamble=OUTER_ROUTER_PREAMBLE,
        actions=ACTIONS,
        extra=OUTER_ROUTER_EXTRA,
        board=board,
        gaps=gaps,
        last_lake=last_lake,
        nca_status=nca_status,
        total_fn=board_total,
    )


def route_next_action(
    *,
    board: Mapping[str, int],
    gaps: list[dict[str, Any]],
    last_lake: list[dict[str, Any]],
    stalled: bool,
    llm: bool,
    ledger: Any,
    generate: Optional[Callable[..., str]] = None,
    memory: Optional[Mapping[str, Any]] = None,
) -> dict[str, Any]:
    """llm_router grok when --llm on; else deterministic AutoResearch route."""

    from jevops.outer import drive_route_action

    def _generate(prompt: str) -> str:
        text, _identity, _line = lra_t1.generate_grok(
            prompt,
            ledger,
            max_new_tokens=ROUTER_MAX_NEW,
            timeout=ROUTER_TIMEOUT,
            generate=generate,
            fixture=generate is not None,
        )
        return text

    return drive_route_action(
        board=board,
        gaps=gaps,
        last_lake=last_lake,
        stalled=stalled,
        llm=llm,
        memory=memory,
        ledger=ledger,
        status_fn=nca_status_for_router,
        generate_fn=_generate,
        prompt_fn=lambda board, gaps, last_lake, nca: router_prompt(
            board, gaps, last_lake, nca_status=nca
        ),
    )


def apply_action(memory: dict[str, Any], action: Mapping[str, Any]) -> dict[str, Any]:
    """Mutate memory from a closed action. No Python exec."""

    from jevops.outer import apply_action as _apply

    return _apply(memory, action)


def canary_args(
    *,
    out: Path,
    rounds: int,
    lake_top: int,
    drafts: int,
    timeout: float,
    seed: int,
    nest_depth: int = 3,
) -> argparse.Namespace:
    from jevops.outer import drive_canary_namespace

    return drive_canary_namespace(
        out=out,
        rounds=rounds,
        lake_top=lake_top,
        drafts=drafts,
        timeout=timeout,
        seed=seed,
        nest_depth=nest_depth,
        k=lra_rand.DEFAULT_K,
    )


def self_check() -> dict[str, Any]:
    parsed = parse_action('noise {"action": "install_fold", "stem": "comma", "old": "a,⟩", "new": "a⟩", "keep": ["exact"]} trailing')
    mem: dict[str, Any] = {"skills": [], "blacklist": []}
    installed = apply_action(mem, parsed)
    fold_ok = bool(mem.get("skills"))
    skip = apply_action(mem, {"action": "skip_stem", "stem": "hoist_repeated_simp", "name": "P"})
    det = deterministic_route(
        gaps=[{"name": "P", "keep_structure": ["trailing_tuple_comma"], "proposed": {"mint": ["trailing_tuple_comma"]}}],
        last_lake=[],
        stalled=False,
    )
    board = {"Core.InitsUpdatesComm": 139}
    budget_stop = deterministic_route(
        gaps=[],
        last_lake=[{"name": "P", "skipped": "nca_budget"}, {"name": "Q", "skipped": "nca_budget"}],
        stalled=False,
    )
    import board_graph as lra_board_chk

    seeded = lra_board_chk.seed_nca_from_board({"nca": {"grid": {}}})
    from jevops.outer import finalize_ok

    return finalize_ok(
        {
            "called_docker0": False,
            "arena_score": None,
            "official_track2": False,
            "router": "ipfs_accelerate_py.llm_router.generate_text",
            "jev_writes_lean": False,
            "grok_writes_lean": False,
        },
        parsed.get("action") == "install_fold",
        installed.get("ok") is True,
        fold_ok,
        skip.get("ok") is True,
        det.get("action") == "mint",
        budget_stop.get("action") == "stop",
        budget_stop.get("reason") == "nca_budget",
        board_total(board) == 139,
        seeded.get("campaign_write") is False,
        lra_t1.FAIL_CLOSED_KWARGS.get("provider") == "grok",
        lra_t1.FAIL_CLOSED_KWARGS.get("allow_local_fallback") is False,
    )


def run_loop(
    *,
    outer: int,
    llm: bool,
    out: Path,
    rounds: int,
    lake_top: int,
    drafts: int,
    timeout: float,
    seed: int,
    generate: Optional[Callable[..., str]] = None,
    run_inner: Optional[Callable[[argparse.Namespace], dict[str, Any]]] = None,
    memory: Optional[dict[str, Any]] = None,
    persist_memory: bool = True,
    on_step: Optional[Any] = None,
) -> dict[str, Any]:
    """OUTER Grok (llm_router). INNER TypeSafe keep-loop + recursive skill-tree nests."""

    import board_graph as lra_board_seed
    import typesafe_nca as lra_nca_halt
    from jevops.outer import drive_skill_loop, or_int

    return drive_skill_loop(
        outer=outer,
        llm=llm,
        out=out,
        rounds=rounds,
        lake_top=lake_top,
        drafts=drafts,
        timeout=timeout,
        seed=seed,
        generate=generate,
        run_inner=run_inner,
        memory=memory,
        persist_memory=persist_memory,
        load_memory_fn=lra_bind.load_memory,
        seed_fn=lra_board_seed.seed_nca_from_board,
        overlay_fn=lra_board_seed.overlay_live_board,
        keepbest_fn=lambda mem: lra_board_seed.seed_keepbest_theorems(
            mem, keep_best_board(out), warmup=lra_board_seed.warmup_token_map()
        ),
        ledger_cls=lra_t1.ProblemLedger,
        default_inner=lra_rand.run_live,
        nest_depth=or_int(lra_rand.NEST_MAX_DEPTH, 1, floor=1),
        board_fn=lambda: keep_best_board(out),
        board_total_fn=board_total,
        route_fn=route_next_action,
        canary_args_fn=canary_args,
        apply_fn=apply_action,
        gaps_fn=lra_bind.skill_gap_report,
        save_fn=lra_bind.save_memory,
        memory_default=lra_bind.MEMORY_DEFAULT,
        halt_fn=lra_nca_halt.should_halt,
        flatten_fn=lra_inner.flatten_trace,
        protocol=PROTOCOL,
        pr_id=PR_ID,
        on_step=on_step,
    )


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-check", action="store_true")
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--llm", choices=("on", "off"), default="on")
    parser.add_argument("--outer", type=int, default=3, help="outer skill-improve rounds")
    parser.add_argument("--rounds", type=int, default=1, help="inner AutoResearch denoise rounds")
    parser.add_argument("--lake-top", type=int, default=3)
    parser.add_argument("--drafts", type=int, default=8)
    parser.add_argument("--timeout", type=float, default=180.0)
    parser.add_argument("--seed", type=int, default=lra_rand.DEFAULT_SEED)
    parser.add_argument("--out", type=Path, default=OUT_DEFAULT)
    args = parser.parse_args(argv)
    if args.self_check or not args.live:
        from jevops.outer import print_ok

        return print_ok(self_check())
    from jevops.outer import first_int, or_int

    payload = run_loop(
        outer=or_int(args.outer, 1, floor=1),
        llm=args.llm == "on",
        out=args.out,
        rounds=or_int(args.rounds, 1, floor=1),
        lake_top=first_int(args.lake_top),
        drafts=first_int(args.drafts),
        timeout=float(args.timeout),
        seed=first_int(args.seed),
    )
    from jevops.outer import write_json_pair

    write_json_pair(
        args.out,
        payload,
        prefix="skill-improve-loop",
        latest="skill-improve-loop-latest.json",
    )
    from jevops.outer import print_json

    print_json(payload, default=str)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

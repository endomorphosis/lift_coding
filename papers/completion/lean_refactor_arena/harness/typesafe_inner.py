#!/usr/bin/env python3
"""Recursive TypeSafe inner loop over the skill decision tree.

Outer Grok (llm_router) decides whether to enter. This module is the inner
TypeSafe walker: keep looping at a tree node, and nest a child loop when
compose=nest. Lake is the oracle. Jev does not write Lean. Never docker0.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Mapping, Optional

import _jevops_path  # noqa: F401
import binder_use as lra_bind
import draft_fanout as lra_fan
import mca_mask_replace as lra_mask
import portable_rewrites as lra_port
import random_canary as lra_rand
import track1_keepbest as lra_kb
import typesafe_tools as lra_tools
from jevops.walk import begin_session
from jevops.walk import flatten_trace
from jevops.walk import inner_loop


def apply_lake_round(
    *,
    record: Mapping[str, Any],
    tactics: str,
    analysis: Mapping[str, Any],
    drafts: list[dict[str, Any]],
    intent: Mapping[str, Any],
    ranked: Mapping[str, Any],
    memory: dict[str, Any],
    args: Any,
    restore: bytes,
    round_i: int,
    compile_one: Callable[..., Mapping[str, Any]],
) -> tuple[Optional[str], list[dict[str, Any]]]:
    """Lake up to lake_top drafts. Returns (accepted_body, lake_rows)."""

    import codepath_graph as lra_cp
    import board_graph as lra_board
    from jevops.oracle import drive_lake_round

    return drive_lake_round(
        record=record,
        tactics=tactics,
        analysis=analysis,
        drafts=drafts,
        intent=intent,
        ranked=ranked,
        memory=memory,
        args=args,
        restore=restore,
        round_i=round_i,
        compile_one=compile_one,
        cap=lra_rand.MAX_LIVE_TOKENS,
        state_root=lra_rand.DEFAULT_STATE,
        restore_binders_fn=lra_bind.restore_unknown_binders,
        hammer_fn=lra_mask.hammer_repair,
        success_fn=lra_bind.remember_success,
        failure_fn=lra_bind.remember_failure,
        error_class_fn=lra_bind.error_class,
        sidecar_ready_fn=lra_cp.SIDECAR_DUCKDB.is_file,
        sidecar_build_fn=lra_cp.build_sidecar_duckdb,
        credit_theorem_fn=lra_board.credit_theorem,
    )


def eval_theorem(
    name: str,
    *,
    current: Mapping[str, Any],
    tactics: str,
    compile_fn: Callable[..., Mapping[str, Any]],
    args: Any,
    restore: bytes,
    memory: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Lake a small warmup theorem. Other names fail closed if not small."""

    import draft_fanout as lra_fan
    import splice as lra_splice
    import track1_keepbest as lra_kb
    from jevops.oracle import drive_eval_theorem
    from jevops.outer import read_bytes_if

    def _records() -> list:
        _raw, _digest, records = lra_splice.load_warmup_records()
        return records

    return drive_eval_theorem(
        name,
        current=current,
        tactics=tactics,
        compile_fn=compile_fn,
        args=args,
        restore=restore,
        memory=memory,
        load_records_fn=_records,
        tactic_block_fn=lra_fan.tactic_block,
        clone_dir_fn=lambda url: lra_kb.lra_cw.clone_dir(url, lra_rand.DEFAULT_STATE),
        relpath_fn=lra_kb.lra_cw.source_relpath,
        read_bytes_fn=read_bytes_if,
        cap=lra_rand.MAX_LIVE_TOKENS,
        state_root=lra_rand.DEFAULT_STATE,
    )


def inner_typesafe_walk(
    record: Mapping[str, Any],
    tactics: str,
    *,
    args: Any,
    memory: dict[str, Any],
    ledger: Any,
    rng: Any,
    model: Optional[Mapping[str, Any]],
    restore: bytes,
    depth: int = 0,
    node: str = "root",
    allow_families: Optional[set[str]] = None,
    allow_skills: Optional[set[str]] = None,
    steps: Optional[list[int]] = None,
    max_steps: int = lra_rand.INNER_MAX_STEPS,
    max_depth: int = lra_rand.NEST_MAX_DEPTH,
    compile_one: Optional[Callable[..., Mapping[str, Any]]] = None,
    research_fn: Optional[Callable[..., dict[str, Any]]] = None,
    pick_fn: Optional[Callable[..., dict[str, Any]]] = None,
    router_fn: Optional[Callable[..., dict[str, Any]]] = None,
    tape: Optional[Any] = None,
    stack: Optional[Any] = None,
) -> dict[str, Any]:
    """Keep-looping TypeSafe walker. nest/spawn recurse; analyze/self_improve skip grok."""

    import mcmc_beam as lra_mcmc
    import call_stack as lra_cs
    import neural_tape as lra_tape
    import board_graph as lra_board
    from jevops.outer import first_int, first_truthy, get_str, text_or
    from jevops.walk import drive_inner_walk

    def _credit(mem: dict[str, Any], evaled: Mapping[str, Any], current: Mapping[str, Any]) -> None:
        lra_board.credit_theorem(
            mem,
            text_or(first_truthy(evaled.get("name"), get_str(current, "name"), default="")),
            theorem_ok=bool(evaled.get("theorem_ok")),
            tokens=first_int(evaled.get("tokens")),
        )

    return drive_inner_walk(
        record,
        tactics,
        args=args,
        memory=memory,
        ledger=ledger,
        rng=rng,
        model=model,
        restore=restore,
        depth=depth,
        node=node,
        allow_families=allow_families,
        allow_skills=allow_skills,
        steps=steps,
        max_steps=max_steps,
        max_depth=max_depth,
        compile_one=compile_one,
        research_fn=research_fn,
        pick_fn=pick_fn,
        router_fn=router_fn,
        tape=tape,
        stack=stack,
        walk_fn=inner_typesafe_walk,
        default_compile=lra_mcmc.compile_one,
        default_research=lra_rand.typesafe_autoresearch,
        default_pick=lra_rand.typesafe_pick,
        tape_factory=lambda: lra_tape.Tape.from_memory(memory),
        stack_factory=lra_cs.CallStack,
        link_fn=lra_board.link_current_theorem,
        overlay_fn=lra_board.overlay_live_board,
        analyze_fn=lra_rand.analyze_proof,
        residual_fn=lra_port.analyze_residuals,
        expand_skills_fn=lra_bind.expand_skills_from_memory,
        drafts_fn=lra_rand.random_drafts,
        eval_fn=eval_theorem,
        credit_fn=_credit,
        spawn_subloop_fn=lra_tools.spawn_subloop,
        lake_round_fn=apply_lake_round,
        subloops=lra_tools.SUBLOOPS,
    )


def starting_tactics(record: Mapping[str, Any], *, out: Any = None, from_best: bool = False) -> str:
    """Keep-best body when --from-best, else frozen warmup tactics."""

    from jevops.outer import drive_starting_body

    return drive_starting_body(
        record,
        from_best=from_best,
        block_fn=lra_fan.tactic_block,
        out=out,
        extras={"Core.InitsUpdatesComm": "cascade-best-139.lean"},
    )


def run_nested_canary(
    record: Mapping[str, Any],
    *,
    args: Any,
    memory: dict[str, Any],
    ledger: Any,
    rng: Any,
    model: Optional[Mapping[str, Any]],
    compile_one: Optional[Callable[..., Mapping[str, Any]]] = None,
    research_fn: Optional[Callable[..., dict[str, Any]]] = None,
    pick_fn: Optional[Callable[..., dict[str, Any]]] = None,
    router_fn: Optional[Callable[..., dict[str, Any]]] = None,
) -> dict[str, Any]:
    """Load keep-best tactics, walk the TypeSafe tree, restore the clone."""

    from jevops.walk import drive_nested_canary

    return drive_nested_canary(
        record,
        args=args,
        memory=memory,
        ledger=ledger,
        rng=rng,
        model=model,
        compile_one=compile_one,
        research_fn=research_fn,
        pick_fn=pick_fn,
        router_fn=router_fn,
        start_fn=starting_tactics,
        state_root=lra_rand.DEFAULT_STATE,
        clone_fn=lra_kb.lra_cw.clone_dir,
        relpath_fn=lra_kb.lra_cw.source_relpath,
        analyze_fn=lra_rand.analyze_proof,
        walk_fn=inner_typesafe_walk,
        min_steps=lra_rand.INNER_MAX_STEPS,
        default_depth=lra_rand.NEST_MAX_DEPTH,
    )


def _skill_walk_entry(**kwargs: Any) -> dict[str, Any]:
    from jevops.outer import drive_popped_walk

    return drive_popped_walk(kwargs, walk_fn=inner_typesafe_walk)


lra_tools.register_subloop("skill_walk", _skill_walk_entry)


def _eval_theorem_entry(**kwargs: Any) -> dict[str, Any]:
    from jevops.outer import drive_eval_entry

    return drive_eval_entry(kwargs, eval_fn=eval_theorem)


lra_tools.register_subloop("eval_theorem", _eval_theorem_entry)

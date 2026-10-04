#!/usr/bin/env python3
"""LRA TypeSafe NCA walker: Lean feed/mutate and harness file walk.

Tick, halt, neighborhood, fork, and the cell store live in `jevops.nca`.
Lake and `tasks.json` stay in this harness. Jev does not write Lean.
Never docker0. Not Track 2.
"""
from __future__ import annotations

import ast
import importlib
import unittest
from pathlib import Path
from typing import Any, Mapping, Optional

HERE = Path(__file__).resolve().parent
PAPER_ROOT = HERE.parent

import _jevops_path  # noqa: F401
from jevops.catalogs import WALK_MAX_FILES  # noqa: E402
import typesafe_tools as lra_tools
from jevops.nca import (  # noqa: E402
    BUDGET_PTR,
    ENERGY_CLIP,
    FORK_MAX,
    STALE_SECONDS,
    canonical_cell_id,
    charge_budget,
    fork_cells,
    journal_event,
    merge_alias_cells,
    mutate_energy,
    neighborhood,
    replay_journal,
    should_halt,
    tick,
    upsert_from_event,
    _cell,
    _clip,
    _grid,
)


def feed_state(memory: dict[str, Any], *, tactics: str = "", problem: str = "") -> dict[str, Any]:
    """Overlay memory plus LRA Lean residuals / decision tree."""

    import portable_rewrites as lra_port
    from jevops.nca import drive_feed_state

    return drive_feed_state(
        memory,
        tactics=tactics,
        problem=problem,
        residual_fn=lra_port.analyze_residuals,
        tree_fn=lambda text, mem, name: lra_port.decision_tree(text, memory=mem, name=name),
        inverse_src=lra_port.SKILL_RESIDUAL,
    )


def _safe_path(path: str | Path) -> Optional[Path]:
    from jevops.nca import drive_allowed_pair

    return drive_allowed_pair(path, here=HERE, paper=PAPER_ROOT, base=HERE)


def hook_and_eval(path: str | Path) -> dict[str, Any]:
    """Walk one harness/paper file: AST, import, whether a test module names it."""

    from jevops.nca import drive_here_inspect

    return drive_here_inspect(
        path,
        here=HERE,
        paper=PAPER_ROOT,
        base=HERE,
        import_dir=HERE,
        test_dir=HERE,
    )


def walk_codebase(*, limit: int = WALK_MAX_FILES) -> dict[str, Any]:
    """Hook every harness Python file (bounded)."""

    from jevops.nca import drive_here_walk

    return drive_here_walk(
        HERE,
        limit=limit,
        here=HERE,
        paper=PAPER_ROOT,
        import_dir=HERE,
        test_dir=HERE,
    )


def evaluate_tests(*names: str) -> dict[str, Any]:
    """Run selected harness unit tests in-process (no lake, no docker0)."""

    from jevops.nca import run_unittests

    return run_unittests(*names, root=HERE)


def mutate(
    memory: dict[str, Any],
    *,
    tactics: str = "",
    problem: str = "",
    op: str = "auto",
) -> dict[str, Any]:
    """Gated mutation: energy reorder/skip plus LRA keep-structure folds.

    Does not rewrite arbitrary repo files. Lake remains the Lean oracle.
    """

    import binder_use as lra_bind
    import portable_rewrites as lra_port
    from jevops.nca import drive_mutate

    return drive_mutate(
        memory,
        tactics=tactics,
        problem=problem,
        op=op,
        fold_skill_fn=lra_port.fold_from_memory_skill,
        propose_fn=lra_bind.propose_skill_from_research,
        expand_fn=lra_bind.expand_skills_from_memory,
    )


def nca_tool(name: str, **kwargs: Any) -> dict[str, Any]:
    from jevops.nca import drive_nca_tool

    return drive_nca_tool(
        name,
        walk_fn=walk_codebase,
        hook_fn=hook_and_eval,
        mutate_fn=mutate,
        eval_fn=evaluate_tests,
        **kwargs,
    )


def _nca_tick_entry(**kwargs: Any) -> dict[str, Any]:
    from jevops.nca import drive_tick_kwargs

    return drive_tick_kwargs(kwargs, tick_fn=tick)


def _nca_fork_entry(**kwargs: Any) -> dict[str, Any]:
    from jevops.nca import drive_fork_kwargs

    return drive_fork_kwargs(kwargs, fork_fn=fork_cells)


lra_tools.register_subloop("nca_tick", _nca_tick_entry)
lra_tools.register_subloop("nca_fork", _nca_fork_entry)

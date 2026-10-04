#!/usr/bin/env python3
"""Read-only LRA goal/subgoal/task DAG for the TypeSafe NCA.

Default source is tasks.json (no Quack, no campaign writes). Optional
fetch_board overlay is injected by the caller. Never docker0.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping, Optional

import _jevops_path  # noqa: F401
from jevops.board import board_window as kernel_board_window
from jevops.board import mark_ready_tasks
from jevops.board import overlay_task_status
from jevops.board import refresh_board_window as kernel_refresh_board_window
from jevops.board import seed_grid_from_board

HERE = Path(__file__).resolve().parent
PAPER_ROOT = HERE.parent
TASKS_JSON = PAPER_ROOT / "tasks.json"
from jevops.catalogs import BLOCKED  # noqa: E402
from jevops.catalogs import ROOT_GOAL  # noqa: E402
from jevops.catalogs import THEOREM_TASKS  # noqa: E402


def _ptr(kind: str, ident: str) -> str:
    from jevops.board import ptr

    return ptr(kind, ident)


def _codepath_ptr(path: str) -> str:
    from jevops.outer import drive_harness_ptr

    return drive_harness_ptr(
        path,
        marker="papers/completion/lean_refactor_arena/harness/",
        ptr_fn=_ptr,
    )


def load_lra_board(*, path: Optional[Path] = None) -> dict[str, Any]:
    from jevops.board import drive_load_board
    from jevops.outer import if_none, read_json

    return drive_load_board(
        if_none(path, TASKS_JSON),
        read_fn=read_json,
        root=ROOT_GOAL,
        blocked=BLOCKED,
    )


def board_payload(ident: str, board: Optional[Mapping[str, Any]] = None) -> dict[str, Any]:
    from jevops.board import drive_loaded_payload

    return drive_loaded_payload(
        ident,
        board,
        load_fn=load_lra_board,
        root=ROOT_GOAL,
        path_ptr=_codepath_ptr,
    )


def refresh_board_window(memory: dict[str, Any]) -> list[dict[str, Any]]:
    """Rebuild the compact board_window from current grid energies/status."""

    return kernel_refresh_board_window(memory, root_goal=ROOT_GOAL)


def seed_nca_from_board(memory: dict[str, Any], *, board: Optional[Mapping[str, Any]] = None, force: bool = False) -> dict[str, Any]:
    """Insert goal/subgoal/task/codepath cells and DAG neighbors. No campaign write."""

    from jevops.board import drive_seed_board

    def _sidecar(mem: dict[str, Any], nca: dict[str, Any]) -> None:
        import codepath_graph as lra_cp

        from jevops.outer import call_if, overlay_map, set_if

        built = call_if(
            not nca.get("sidecar_built") and not lra_cp.SIDECAR_DUCKDB.is_file(),
            lra_cp.build_sidecar_duckdb,
        )
        set_if(nca, built is not None, "sidecar_built", bool(overlay_map(built).get("ok")))
        extra = lra_cp.seed_nca_call_edges(mem)
        set_if(nca, extra.get("ok") and extra.get("n_edges"), "call_edges", extra.get("n_edges"))

    return drive_seed_board(
        memory,
        board=board,
        force=force,
        load_fn=load_lra_board,
        root=ROOT_GOAL,
        path_ptr=_codepath_ptr,
        sidecar_fn=_sidecar,
    )


def board_window(memory: Mapping[str, Any]) -> list[dict[str, Any]]:
    return kernel_board_window(memory)


def warmup_token_map() -> dict[str, int]:
    """Frozen warmup body token counts (local tokenizer). Never rewrites JSONL."""

    from jevops.board import drive_warmup_token_map

    import run_warmup as lra_loop
    import splice as lra_splice

    return drive_warmup_token_map(
        load_fn=lra_splice.load_warmup_records,
        token_fn=lra_loop.token_count,
        split_fn=lra_splice.split_statement_body,
    )


def credit_theorem(
    memory: dict[str, Any],
    theorem: str,
    *,
    theorem_ok: bool,
    tokens: int = 0,
) -> dict[str, Any]:
    """Push lake result onto the owning theorem/task/subgoal cells."""

    from jevops.board import credit_mapped
    from jevops.outer import either

    return credit_mapped(
        memory,
        theorem,
        THEOREM_TASKS,
        subgoal_fn=lambda task_id: either(task_id == "LRA-019", lambda: "LRA-S05", lambda: "LRA-S04"),
        theorem_ok=theorem_ok,
        tokens=tokens,
    )


def link_current_theorem(memory: dict[str, Any], theorem: str) -> dict[str, Any]:
    """Ensure the current canary exists as a theorem cell edged to its task."""

    from jevops.board import drive_link_theorem

    return drive_link_theorem(memory, theorem, tasks=THEOREM_TASKS, ptr_fn=_ptr)


def seed_keepbest_theorems(
    memory: dict[str, Any], tokens: Mapping[str, int], *, warmup: Optional[Mapping[str, int]] = None
) -> dict[str, Any]:
    """Upsert theorem cells from keep-best token counts (no lake)."""

    from jevops.board import drive_seed_keep

    return drive_seed_keep(
        memory,
        tokens,
        warmup=warmup,
        load_fn=warmup_token_map,
        link_fn=link_current_theorem,
    )


from jevops.catalogs import LRA_LANE  # noqa: E402
READY_JSON = LRA_LANE / "quack-owner" / "paper-owner.ready.json"


def overlay_live_board(
    memory: dict[str, Any],
    *,
    fetch_fn: Optional[Any] = None,
    ready_fn: Optional[Any] = None,
    lane: Optional[Path] = None,
) -> dict[str, Any]:
    """Read-only status overlay from fetch_board. Never writes campaign DB."""

    from jevops.board import drive_overlay_live, load_campaign_fetch

    def _build(root: Any) -> Any:
        fetch = load_campaign_fetch(scripts_root="/home/barberb/lift_coding/scripts")
        return fetch("lean_refactor_arena", root)

    return drive_overlay_live(
        memory,
        lane=lane,
        default_lane=LRA_LANE,
        fetch_fn=fetch_fn,
        ready_page_fn=lambda: overlay_ready_tasks(memory, ready_fn=ready_fn, lane=lane),
        seed_fn=seed_nca_from_board,
        fetch_builder=_build,
    )


def replica_ready_page(*, lane: Optional[Path] = None) -> dict[str, Any]:
    """Read-only DatabaseTaskSource.ready_tasks. Never CAS, never install_schema."""

    from jevops.board import drive_replica_page

    def _page(endpoint: str) -> Any:
        from jevops.board import load_database_task_source

        DatabaseTaskSource = load_database_task_source()
        with DatabaseTaskSource(
            endpoint,
            owner_id="lra-nca-overlay-readonly",
            install_schema=False,
        ) as source:
            return source.ready_tasks(limit=100)

    return drive_replica_page(lane, default_lane=LRA_LANE, page_fn=_page)


def overlay_ready_tasks(
    memory: dict[str, Any], *, ready_fn: Optional[Any] = None, lane: Optional[Path] = None
) -> dict[str, Any]:
    """Mark Source.ready_tasks as ready. Default is no campaign Source (inject ready_fn)."""

    from jevops.board import drive_ready_overlay

    return drive_ready_overlay(
        memory,
        ready_fn=ready_fn,
        replica_fn=lambda: replica_ready_page(lane=lane),
        prefix="LRA-",
        env_key="LRA_NCA_READY_TASKS",
    )

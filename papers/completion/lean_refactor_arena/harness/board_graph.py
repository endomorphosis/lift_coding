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
    from jevops.outer import call_if, path_to_dots, posix_slash, replace_if, without_prefix

    text = posix_slash(path)
    marker = "papers/completion/lean_refactor_arena/harness/"
    return call_if(
        text,
        lambda: _ptr(
            "codepath",
            path_to_dots(
                replace_if(text.startswith(marker), "harness/" + without_prefix(text, marker), text)
            ),
        ),
        default="",
    )


def load_lra_board(*, path: Optional[Path] = None) -> dict[str, Any]:
    from jevops.board import board_from_payload

    from jevops.outer import if_none

    target = if_none(path, TASKS_JSON)
    from jevops.outer import read_json

    data = read_json(target)

    def _paths(row: Mapping[str, Any]) -> list[str]:
        from jevops.outer import get_list, project_map, text_or

        paths = project_map([p for p in get_list(row, "suggested_code_paths") if p], text_or)
        paths.extend(
            project_map(
                [p for p in get_list(row, "deliverables") if text_or(p).endswith(".py")],
                text_or,
            )
        )
        return paths

    return board_from_payload(data, root=ROOT_GOAL, blocked=BLOCKED, code_paths_fn=_paths)


def board_payload(ident: str, board: Optional[Mapping[str, Any]] = None) -> dict[str, Any]:
    from jevops.board import board_payload as kernel_payload

    from jevops.outer import or_load

    data = or_load(board, load_lra_board)
    data.setdefault("root", ROOT_GOAL)
    return kernel_payload(ident, data, path_ptr=_codepath_ptr)


def refresh_board_window(memory: dict[str, Any]) -> list[dict[str, Any]]:
    """Rebuild the compact board_window from current grid energies/status."""

    return kernel_refresh_board_window(memory, root_goal=ROOT_GOAL)


def seed_nca_from_board(memory: dict[str, Any], *, board: Optional[Mapping[str, Any]] = None, force: bool = False) -> dict[str, Any]:
    """Insert goal/subgoal/task/codepath cells and DAG neighbors. No campaign write."""

    from jevops.outer import or_load

    data = or_load(board, load_lra_board)
    data.setdefault("root", ROOT_GOAL)
    from jevops.board import seed_then_sidecar

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

    return seed_then_sidecar(
        memory, data, force=force, path_ptr=_codepath_ptr, sidecar_fn=_sidecar
    )


def board_window(memory: Mapping[str, Any]) -> list[dict[str, Any]]:
    return kernel_board_window(memory)


def warmup_token_map() -> dict[str, int]:
    """Frozen warmup body token counts (local tokenizer). Never rewrites JSONL."""

    from jevops.outer import token_map

    try:
        import run_warmup as lra_loop
        import splice as lra_splice

        _raw, _digest, records = lra_splice.load_warmup_records()
    except Exception:
        return {}

    def _body(rec: Mapping[str, Any]) -> str:
        try:
            from jevops.outer import text_or

            return text_or(lra_splice.split_statement_body(rec).body_suffix)
        except Exception:
            from jevops.outer import get_str

            return get_str(rec, "src")

    return token_map(records, token_fn=lra_loop.token_count, body_fn=_body)


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

    from jevops.board import link_entity

    from jevops.outer import call_if, first_truthy, text_or

    name = text_or(first_truthy(theorem, default=""))
    task_id = THEOREM_TASKS.get(name)
    parent = call_if(task_id, lambda: _ptr("task", task_id), default="")
    out = link_entity(memory, ident=name, kind="theorem", parent_ptr=parent, energy=0.55)
    return {"ok": out.get("ok"), "theorem": out.get("id"), "task": parent, "reason": out.get("reason")}


def seed_keepbest_theorems(
    memory: dict[str, Any], tokens: Mapping[str, int], *, warmup: Optional[Mapping[str, int]] = None
) -> dict[str, Any]:
    """Upsert theorem cells from keep-best token counts (no lake)."""

    from jevops.board import seed_token_cells

    from jevops.outer import or_load

    warm_map = or_load(warmup, warmup_token_map)
    return seed_token_cells(
        memory,
        tokens,
        warmup=warm_map,
        link_fn=lambda mem, name: link_current_theorem(mem, name),
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

    from jevops.board import overlay_fetch
    from jevops.outer import call_if, either, first_not_none, if_none

    root = if_none(lane, LRA_LANE)
    ready = root / "quack-owner" / "paper-owner.ready.json"

    def _default_fetch() -> Any:
        from jevops.board import load_campaign_fetch

        fetch = load_campaign_fetch(scripts_root="/home/barberb/lift_coding/scripts")
        return fetch("lean_refactor_arena", root)

    injected = fetch_fn is not None
    live_fn = first_not_none(fetch_fn, factory=lambda: call_if(ready.is_file(), lambda: _default_fetch))
    return overlay_fetch(
        memory,
        seed_fn=seed_nca_from_board,
        fetch_fn=live_fn,
        prefix="LRA-",
        cache=fetch_fn is None,
        ready_fn=lambda: overlay_ready_tasks(memory, ready_fn=ready_fn, lane=lane),
        empty_reason="no_ready_owner",
        injected_reason=either(injected, lambda: "injected", lambda: "fetch_board"),
        inject_fail=either(injected, lambda: "closed", lambda: "cache"),
    )


def replica_ready_page(*, lane: Optional[Path] = None) -> dict[str, Any]:
    """Read-only DatabaseTaskSource.ready_tasks. Never CAS, never install_schema."""

    from jevops.board import replica_from_ready
    from jevops.outer import if_none

    def _page(endpoint: str) -> Any:
        from jevops.board import load_database_task_source

        DatabaseTaskSource = load_database_task_source()
        with DatabaseTaskSource(
            endpoint,
            owner_id="lra-nca-overlay-readonly",
            install_schema=False,
        ) as source:
            return source.ready_tasks(limit=100)

    return replica_from_ready(
        if_none(lane, LRA_LANE) / "quack-owner" / "paper-owner.ready.json",
        page_fn=_page,
        prefix="LRA-",
    )


def overlay_ready_tasks(
    memory: dict[str, Any], *, ready_fn: Optional[Any] = None, lane: Optional[Path] = None
) -> dict[str, Any]:
    """Mark Source.ready_tasks as ready. Default is no campaign Source (inject ready_fn)."""

    from jevops.board import overlay_ready
    from jevops.outer import optional_fn

    return overlay_ready(
        memory,
        ready_fn=ready_fn,
        replica_fn=optional_fn(ready_fn is None, lambda: replica_ready_page(lane=lane)),
        prefix="LRA-",
        env_key="LRA_NCA_READY_TASKS",
    )

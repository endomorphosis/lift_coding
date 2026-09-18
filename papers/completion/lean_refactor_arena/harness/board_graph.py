#!/usr/bin/env python3
"""Read-only LRA goal/subgoal/task DAG for the TypeSafe NCA.

Default source is tasks.json (no Quack, no campaign writes). Optional
fetch_board overlay is injected by the caller. Never docker0.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping, Optional

HERE = Path(__file__).resolve().parent
PAPER_ROOT = HERE.parent
TASKS_JSON = PAPER_ROOT / "tasks.json"
ROOT_GOAL = "LRA-G000"
BLOCKED = frozenset({"LRA-S09", "LRA-S10", "LRA-024", "LRA-025", "LRA-027"})
# Small canaries credit the warmup (S04) or TypeSafe (S05) tasks.
THEOREM_TASKS: dict[str, str] = {
    "CallElimCorrect.substOldPostSubset": "LRA-017",
    "CallElimCorrect.extractedOldExprInVars": "LRA-017",
    "Core.InitsUpdatesComm": "LRA-019",
    "Cslib.LambdaCalculus.LocallyNameless.Fsub.Typing.progress": "LRA-017",
    "Cslib.SKI.parallelReduction_diamond": "LRA-017",
    "Cslib.CCS.bisimilarity_congr_choice": "LRA-019",
}


def _ptr(kind: str, ident: str) -> str:
    return f"ptr://{kind}/{ident}"


def _codepath_ptr(path: str) -> str:
    text = str(path or "").replace("\\", "/").strip()
    if not text:
        return ""
    if text.startswith("papers/completion/lean_refactor_arena/harness/"):
        text = "harness/" + text.split("harness/", 1)[-1]
    return _ptr("codepath", text.replace("/", ".").replace(".py", ""))


def load_lra_board(*, path: Optional[Path] = None) -> dict[str, Any]:
    target = path or TASKS_JSON
    data = json.loads(target.read_text(encoding="utf-8"))
    subgoals = [
        {
            "id": str(row.get("id") or ""),
            "title": str(row.get("title") or ""),
            "parent": ROOT_GOAL,
            "blocked": str(row.get("id") or "") in BLOCKED,
        }
        for row in data.get("subgoals") or []
        if row.get("id")
    ]
    tasks = []
    for row in data.get("tasks") or []:
        tid = str(row.get("id") or "")
        if not tid:
            continue
        paths = [str(p) for p in (row.get("suggested_code_paths") or []) if p]
        paths.extend(str(p) for p in (row.get("deliverables") or []) if str(p).endswith(".py"))
        tasks.append(
            {
                "id": tid,
                "title": str(row.get("title") or ""),
                "subgoal_id": str(row.get("subgoal_id") or ""),
                "depends_on": [str(d) for d in (row.get("depends_on") or []) if d],
                "code_paths": paths,
                "blocked": tid in BLOCKED or str(row.get("subgoal_id") or "") in BLOCKED,
                "status": "blocked" if tid in BLOCKED else "todo",
            }
        )
    return {
        "root": ROOT_GOAL,
        "goal_title": str(data.get("goal") or "")[:240],
        "subgoals": subgoals,
        "tasks": tasks,
        "n_subgoals": len(subgoals),
        "n_tasks": len(tasks),
        "called_docker0": False,
        "campaign_write": False,
    }


def board_payload(ident: str, board: Optional[Mapping[str, Any]] = None) -> dict[str, Any]:
    data = dict(board or load_lra_board())
    if ident == data.get("root") or ident == ROOT_GOAL:
        return {
            "kind": "goal",
            "id": ROOT_GOAL,
            "title": data.get("goal_title"),
            "children": [f"ptr://subgoal/{s['id']}" for s in data.get("subgoals") or []],
            "blocked": False,
        }
    for sub in data.get("subgoals") or []:
        if sub["id"] == ident:
            kids = [f"ptr://task/{t['id']}" for t in data.get("tasks") or [] if t.get("subgoal_id") == ident]
            return {
                "kind": "subgoal",
                "id": ident,
                "title": sub.get("title"),
                "parent": f"ptr://goal/{ROOT_GOAL}",
                "children": kids,
                "blocked": bool(sub.get("blocked")),
            }
    for task in data.get("tasks") or []:
        if task["id"] == ident:
            return {
                "kind": "task",
                "id": ident,
                "title": task.get("title"),
                "parent": f"ptr://subgoal/{task.get('subgoal_id')}",
                "depends_on": [f"ptr://task/{d}" for d in task.get("depends_on") or []],
                "code_paths": [_codepath_ptr(p) for p in task.get("code_paths") or [] if _codepath_ptr(p)],
                "blocked": bool(task.get("blocked")),
                "status": task.get("status"),
            }
    return {"ok": False, "reason": "unknown_board_id", "id": ident}


def refresh_board_window(memory: dict[str, Any]) -> list[dict[str, Any]]:
    """Rebuild the compact board_window from current grid energies/status."""

    nca = memory.setdefault("nca", {})
    grid = nca.setdefault("grid", {})
    root = _ptr("goal", ROOT_GOAL)
    window: list[dict[str, Any]] = []
    goal = grid.get(root) if isinstance(grid.get(root), dict) else {}
    if goal:
        window.append({"id": ROOT_GOAL, "kind": "goal", "energy": goal.get("energy")})
    cuts = [
        {
            "id": str(cid).rsplit("/", 1)[-1],
            "kind": "theorem",
            "energy": cell.get("energy"),
            "remaining_cut": int(cell.get("remaining_cut") or 0),
            "tokens": cell.get("tokens"),
        }
        for cid, cell in grid.items()
        if isinstance(cell, dict)
        and (cell.get("kind") in {"theorem", "proof"} or "/theorem/" in str(cid))
        and int(cell.get("remaining_cut") or 0) > 0
    ]
    cuts.sort(key=lambda row: int(row.get("remaining_cut") or 0), reverse=True)
    window.extend(cuts[:3])
    subs = [
        {
            "id": str(cid).rsplit("/", 1)[-1],
            "kind": "subgoal",
            "energy": cell.get("energy"),
            "blocked": bool(cell.get("blocked")),
        }
        for cid, cell in grid.items()
        if isinstance(cell, dict) and cell.get("kind") == "subgoal"
    ]
    subs.sort(key=lambda row: float(row.get("energy") or 0), reverse=True)
    window.extend(subs[:6])
    ready = [
        {
            "id": str(cid).rsplit("/", 1)[-1],
            "kind": "task",
            "energy": cell.get("energy"),
            "status": cell.get("status"),
            "visited": bool(cell.get("visited")),
        }
        for cid, cell in grid.items()
        if isinstance(cell, dict)
        and cell.get("kind") == "task"
        and not cell.get("do_not_fork")
        and str(cell.get("status") or "") in {"ready", "todo", "needed", ""}
    ]
    ready.sort(key=lambda row: (0 if row.get("status") == "ready" else 1, -float(row.get("energy") or 0)))
    window.extend(ready[:6])
    nca["board_window"] = window[:12]
    return window


def seed_nca_from_board(memory: dict[str, Any], *, board: Optional[Mapping[str, Any]] = None, force: bool = False) -> dict[str, Any]:
    """Insert goal/subgoal/task/codepath cells and DAG neighbors. No campaign write."""

    nca = memory.setdefault("nca", {})
    grid = nca.setdefault("grid", {})
    if not force and any(str(cid).startswith("ptr://goal/") for cid in grid):
        window = refresh_board_window(memory)
        return {
            "ok": True,
            "skipped": "already_seeded",
            "n_cells": len(grid),
            "board_window": window,
            "campaign_write": False,
            "called_docker0": False,
        }
    data = dict(board or load_lra_board())
    edges: list[tuple[str, str]] = []

    def _put(cid: str, kind: str, **extra: Any) -> None:
        cell = grid.setdefault(cid, {"id": cid, "kind": kind, "energy": 0.5, "wins": 0, "losses": 0, "help": 0.0, "unsafe": 0.0, "tokens": 0, "tick": 0})
        cell["kind"] = kind
        cell.update({k: v for k, v in extra.items() if v is not None})
        if extra.get("blocked"):
            cell["energy"] = min(float(cell.get("energy") or 0.5), 0.05)
            cell["do_not_fork"] = True

    root = _ptr("goal", ROOT_GOAL)
    _put(root, "goal", title=data.get("goal_title"), blocked=False)
    for sub in data.get("subgoals") or []:
        sid = _ptr("subgoal", sub["id"])
        _put(sid, "subgoal", title=sub.get("title"), blocked=sub.get("blocked"))
        edges.append((root, sid))
    for task in data.get("tasks") or []:
        tid = _ptr("task", task["id"])
        _put(
            tid,
            "task",
            title=task.get("title"),
            blocked=task.get("blocked"),
            status=task.get("status"),
        )
        edges.append((_ptr("subgoal", task["subgoal_id"]), tid))
        for dep in task.get("depends_on") or []:
            edges.append((_ptr("task", dep), tid))
        for path in task.get("code_paths") or []:
            cptr = _codepath_ptr(path)
            if not cptr:
                continue
            _put(cptr, "codepath", path=path, blocked=False)
            edges.append((tid, cptr))
    nca["board_edges"] = [list(edge) for edge in edges]
    try:
        import nca_plan as lra_plan

        lra_plan.seed_plan(memory, board=data, force=force)
    except Exception:
        pass
    try:
        import codepath_graph as lra_cp

        if not nca.get("sidecar_built") and not (lra_cp.SIDECAR_DUCKDB.is_file()):
            built = lra_cp.build_sidecar_duckdb()
            nca["sidecar_built"] = bool(built.get("ok"))
        extra = lra_cp.seed_nca_call_edges(memory)
        if extra.get("ok") and extra.get("n_edges"):
            nca["call_edges"] = extra["n_edges"]
    except Exception:
        pass
    seen_e: set[tuple[str, str]] = set()
    uniq_e: list[list[str]] = []
    for edge in nca.get("board_edges") or []:
        if not isinstance(edge, (list, tuple)) or len(edge) < 2:
            continue
        pair = (str(edge[0]), str(edge[1]))
        if pair in seen_e:
            continue
        seen_e.add(pair)
        uniq_e.append([pair[0], pair[1]])
    nca["board_edges"] = uniq_e
    memory["nca"] = nca
    refresh_board_window(memory)
    return {
        "ok": True,
        "n_cells": len(grid),
        "n_edges": len(edges),
        "n_subgoals": data.get("n_subgoals"),
        "n_tasks": data.get("n_tasks"),
        "campaign_write": False,
        "called_docker0": False,
    }


def board_window(memory: Mapping[str, Any]) -> list[dict[str, Any]]:
    return list(((memory.get("nca") or {}).get("board_window")) or [])[:8]


def warmup_token_map() -> dict[str, int]:
    """Frozen warmup body token counts (local tokenizer). Never rewrites JSONL."""

    try:
        import run_warmup as lra_loop
        import splice as lra_splice

        _raw, _digest, records = lra_splice.load_warmup_records()
    except Exception:
        return {}
    out: dict[str, int] = {}
    for rec in records:
        name = str(rec.get("name") or "")
        if not name:
            continue
        try:
            split = lra_splice.split_statement_body(rec)
            out[name] = int(lra_loop.token_count(split.body_suffix))
        except Exception:
            src = str(rec.get("src") or "")
            if src:
                out[name] = int(lra_loop.token_count(src))
    return out


def credit_theorem(
    memory: dict[str, Any],
    theorem: str,
    *,
    theorem_ok: bool,
    tokens: int = 0,
) -> dict[str, Any]:
    """Push lake result onto the owning theorem/task/subgoal cells."""

    import typesafe_nca as lra_nca

    name = str(theorem or "")
    task_id = THEOREM_TASKS.get(name)
    if not task_id:
        return {"ok": False, "reason": "unmapped_theorem", "theorem": theorem}
    thm_ptr = _ptr("theorem", name)
    task_ptr = _ptr("task", task_id)
    sub_ptr = _ptr("subgoal", "LRA-S05" if task_id == "LRA-019" else "LRA-S04")
    lra_nca.upsert_from_event(
        memory,
        ptr=thm_ptr,
        kind="theorem",
        energy=0.75 if theorem_ok else 0.25,
        theorem_ok=theorem_ok,
        tokens=tokens,
        parent_ptr=task_ptr,
    )
    lra_nca.upsert_from_event(
        memory,
        ptr=task_ptr,
        kind="task",
        energy=0.75 if theorem_ok else 0.25,
        theorem_ok=theorem_ok,
        tokens=tokens,
        parent_ptr=sub_ptr,
    )
    grid = (memory.get("nca") or {}).get("grid") or {}
    if isinstance(grid.get(task_ptr), dict):
        grid[task_ptr]["visited"] = True
    if isinstance(grid.get(thm_ptr), dict) and tokens:
        cell = grid[thm_ptr]
        cell["tokens"] = int(tokens)
        warm = int(cell.get("warmup_tokens") or 0)
        if warm:
            cell["remaining_cut"] = max(0, warm - int(tokens))
    return {"ok": True, "task": task_ptr, "subgoal": sub_ptr, "theorem": thm_ptr, "theorem_ok": theorem_ok}


def link_current_theorem(memory: dict[str, Any], theorem: str) -> dict[str, Any]:
    """Ensure the current canary exists as a theorem cell edged to its task."""

    import typesafe_nca as lra_nca

    name = str(theorem or "")
    if not name:
        return {"ok": False, "reason": "no_theorem"}
    thm_ptr = _ptr("theorem", name)
    lra_nca.upsert_from_event(memory, ptr=thm_ptr, kind="theorem", energy=0.55)
    task_id = THEOREM_TASKS.get(name)
    if task_id:
        task_ptr = _ptr("task", task_id)
        edges = memory.setdefault("nca", {}).setdefault("board_edges", [])
        pair = [thm_ptr, task_ptr]
        if pair not in edges:
            edges.append(pair)
    return {"ok": True, "theorem": thm_ptr, "task": f"ptr://task/{task_id}" if task_id else ""}


def seed_keepbest_theorems(
    memory: dict[str, Any], tokens: Mapping[str, int], *, warmup: Optional[Mapping[str, int]] = None
) -> dict[str, Any]:
    """Upsert theorem cells from keep-best token counts (no lake)."""

    warm_map = dict(warmup or {}) or warmup_token_map()
    n = 0
    for name, tok in (tokens or {}).items():
        if not name:
            continue
        link_current_theorem(memory, str(name))
        cid = _ptr("theorem", str(name))
        grid = (memory.get("nca") or {}).get("grid") or {}
        if isinstance(grid.get(cid), dict):
            grid[cid]["tokens"] = int(tok)
            warm = warm_map.get(name)
            if warm is not None:
                grid[cid]["warmup_tokens"] = int(warm)
                grid[cid]["remaining_cut"] = max(0, int(warm) - int(tok))
            n += 1
    refresh_board_window(memory)
    return {"ok": True, "n_theorems": n, "campaign_write": False}


LRA_LANE = Path.home() / ".local/state/ipfs_accelerate_py/vericodegen-2026-lra/lean_refactor_arena"
READY_JSON = LRA_LANE / "quack-owner" / "paper-owner.ready.json"


def overlay_live_board(
    memory: dict[str, Any],
    *,
    fetch_fn: Optional[Any] = None,
    ready_fn: Optional[Any] = None,
    lane: Optional[Path] = None,
) -> dict[str, Any]:
    """Read-only status overlay from fetch_board. Never writes campaign DB."""

    if not any(str(cid).startswith("ptr://goal/") for cid in ((memory.get("nca") or {}).get("grid") or {})):
        seed_nca_from_board(memory)
    if fetch_fn is None and (memory.get("nca") or {}).get("overlay_done"):
        return {"ok": True, "overlay": True, "reason": "cached", "campaign_write": False, "called_docker0": False}
    live = None
    reason = "no_ready_owner"
    if fetch_fn is not None:
        try:
            live = fetch_fn()
            reason = "injected"
        except Exception as exc:
            return {"ok": False, "overlay": False, "reason": type(exc).__name__, "campaign_write": False, "called_docker0": False}
    else:
        ready = (lane or LRA_LANE) / "quack-owner" / "paper-owner.ready.json"
        if ready.is_file():
            try:
                import importlib
                import sys

                scripts = str(Path("/home/barberb/lift_coding/scripts"))
                if scripts not in sys.path:
                    sys.path.insert(0, scripts)
                campaign = importlib.import_module("paper_supervisor_campaign")
                live = campaign.fetch_board("lean_refactor_arena", lane or LRA_LANE)
                reason = "fetch_board"
            except Exception as exc:
                memory.setdefault("nca", {})["overlay_done"] = True
                return {
                    "ok": True,
                    "overlay": False,
                    "reason": f"fetch_failed:{type(exc).__name__}",
                    "campaign_write": False,
                    "called_docker0": False,
                }
    if not isinstance(live, dict) or not live.get("tasks"):
        if fetch_fn is None:
            memory.setdefault("nca", {})["overlay_done"] = True
        return {"ok": True, "overlay": False, "reason": reason, "campaign_write": False, "called_docker0": False}
    grid = memory.setdefault("nca", {}).setdefault("grid", {})
    n_overlaid = 0
    for task in live.get("tasks") or []:
        if not isinstance(task, dict):
            continue
        alias = str(task.get("task_alias") or task.get("id") or task.get("task_id") or "")
        if not alias.startswith("LRA-"):
            continue
        cid = _ptr("task", alias)
        if cid not in grid or not isinstance(grid[cid], dict):
            continue
        status = str(task.get("status") or task.get("state") or "")
        if status:
            grid[cid]["status"] = status
            n_overlaid += 1
        if status in {"ready", "todo", "needed"}:
            grid[cid]["blocked"] = False
            if status == "ready":
                grid[cid]["energy"] = max(float(grid[cid].get("energy") or 0.5), 0.55)
        if status in {"completed", "done"}:
            grid[cid]["energy"] = min(float(grid[cid].get("energy") or 0.5), 0.15)
        if status in {"blocked"}:
            grid[cid]["blocked"] = True
            grid[cid]["do_not_fork"] = True
            grid[cid]["energy"] = min(float(grid[cid].get("energy") or 0.5), 0.05)
    memory.setdefault("nca", {})["live_overlay"] = {"n_overlaid": n_overlaid, "reason": reason}
    refresh_board_window(memory)
    if fetch_fn is None:
        memory["nca"]["overlay_done"] = True
    extra_ready = overlay_ready_tasks(memory, ready_fn=ready_fn, lane=lane)
    return {
        "ok": True,
        "overlay": True,
        "n_overlaid": n_overlaid,
        "reason": reason,
        "ready_overlay": extra_ready,
        "campaign_write": False,
        "called_docker0": False,
    }


def replica_ready_page(*, lane: Optional[Path] = None) -> dict[str, Any]:
    """Read-only DatabaseTaskSource.ready_tasks. Never CAS, never install_schema."""

    ready_path = (lane or LRA_LANE) / "quack-owner" / "paper-owner.ready.json"
    if not ready_path.is_file():
        return {"ok": False, "reason": "no_ready_json", "tasks": [], "campaign_write": False}
    try:
        blob = json.loads(ready_path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"ok": False, "reason": type(exc).__name__, "tasks": [], "campaign_write": False}
    endpoint = blob.get("quack_endpoint") or blob.get("database_path")
    if not endpoint:
        return {"ok": False, "reason": "no_endpoint", "tasks": [], "campaign_write": False}
    try:
        from ipfs_accelerate_py.agent_supervisor.task_sources.database_task_source import (
            DatabaseTaskSource,
        )

        with DatabaseTaskSource(
            endpoint,
            owner_id="lra-nca-overlay-readonly",
            install_schema=False,
        ) as source:
            page = source.ready_tasks(limit=100)
        tasks: list[dict[str, str]] = []
        for item in getattr(page, "tasks", ()) or ():
            alias = str(getattr(item, "task_alias", "") or getattr(item, "id", "") or "")
            if alias.startswith("LRA-"):
                tasks.append({"task_alias": alias})
        return {"ok": True, "reason": "replica", "tasks": tasks, "campaign_write": False}
    except Exception as exc:
        return {
            "ok": False,
            "reason": f"source_failed:{type(exc).__name__}",
            "tasks": [],
            "campaign_write": False,
        }


def overlay_ready_tasks(
    memory: dict[str, Any], *, ready_fn: Optional[Any] = None, lane: Optional[Path] = None
) -> dict[str, Any]:
    """Mark Source.ready_tasks as ready. Default is no campaign Source (inject ready_fn)."""

    source_reason = "injected"
    if ready_fn is None:
        import os

        if os.environ.get("LRA_NCA_READY_TASKS") != "1":
            return {"ok": True, "n_ready": 0, "reason": "no_ready_fn", "campaign_write": False}
        replica = replica_ready_page(lane=lane)
        if not replica.get("ok"):
            return {
                "ok": True,
                "n_ready": 0,
                "reason": str(replica.get("reason") or "env_set_no_source"),
                "campaign_write": False,
            }
        page = replica
        source_reason = "replica"
    else:
        try:
            page = ready_fn()
        except Exception as exc:
            return {"ok": False, "n_ready": 0, "reason": type(exc).__name__, "campaign_write": False}
    tasks = page.get("tasks") if isinstance(page, dict) else getattr(page, "tasks", ()) or ()
    grid = memory.setdefault("nca", {}).setdefault("grid", {})
    n_ready = 0
    for item in tasks:
        if isinstance(item, dict):
            alias = str(item.get("task_alias") or item.get("id") or "")
        else:
            alias = str(getattr(item, "task_alias", "") or getattr(item, "id", "") or "")
        if not alias.startswith("LRA-"):
            continue
        cid = _ptr("task", alias)
        if cid not in grid or not isinstance(grid[cid], dict):
            continue
        grid[cid]["status"] = "ready"
        grid[cid]["blocked"] = False
        grid[cid]["energy"] = max(float(grid[cid].get("energy") or 0.5), 0.55)
        n_ready += 1
    if n_ready:
        refresh_board_window(memory)
    return {"ok": True, "n_ready": n_ready, "reason": source_reason, "campaign_write": False}

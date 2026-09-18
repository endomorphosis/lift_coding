#!/usr/bin/env python3
"""Neural-cellular-automaton layer for the TypeSafe inner loop.

Each skill/module/proof is a cell. A tick feeds the previous grid into the
next: self-state + neighborhood (KG, AST imports, decision tree) + TypeSafe
help/unsafe + lake win-rate. Cells can hook/walk/evaluate harness files,
fork returnable subloops, and apply gated mutations (memory folds, pipeline
order, skip stems). Jev does not write Lean. Never docker0. Not Track 2.
"""
from __future__ import annotations

import ast
import importlib
import unittest
import time
from pathlib import Path
from typing import Any, Mapping, Optional

HERE = Path(__file__).resolve().parent
PAPER_ROOT = HERE.parent
FORK_MAX = 4
WALK_MAX_FILES = 80
ENERGY_CLIP = (0.0, 1.0)
STALE_SECONDS = 3600.0

import typesafe_tools as lra_tools


BUDGET_PTR = "ptr://tool/budget"


def canonical_cell_id(cid: str, *, kind: str = "") -> str:
    """One id per cell: port_foo and ptr://skill/port_foo are the same."""

    raw = str(cid or "").strip()
    if not raw:
        return raw
    if raw.startswith("ptr://"):
        return raw
    if raw.startswith("port_") or raw.startswith("mem_"):
        return f"ptr://skill/{raw}"
    if raw.startswith("residual:"):
        return f"ptr://residual/{raw.split(':', 1)[-1]}"
    if raw.startswith("proof:"):
        return f"ptr://theorem/{raw.split(':', 1)[-1]}"
    if raw.startswith("family:"):
        return f"ptr://family/{raw.split(':', 1)[-1]}"
    if kind == "skill":
        return f"ptr://skill/{raw}"
    if kind in {"goal", "subgoal", "task", "theorem", "codepath", "tool"}:
        return f"ptr://{kind}/{raw}"
    return raw


def merge_alias_cells(memory: dict[str, Any]) -> dict[str, Any]:
    """Collapse duplicate keys onto canonical ptr:// ids."""

    grid = _grid(memory)
    merged: dict[str, dict[str, Any]] = {}
    for cid, cell in list(grid.items()):
        if not isinstance(cell, dict):
            continue
        canon = canonical_cell_id(cid, kind=str(cell.get("kind") or ""))
        if canon not in merged:
            row = dict(cell)
            row["id"] = canon
            merged[canon] = row
            continue
        dst = merged[canon]
        dst["wins"] = int(dst.get("wins") or 0) + int(cell.get("wins") or 0)
        dst["losses"] = int(dst.get("losses") or 0) + int(cell.get("losses") or 0)
        dst["energy"] = _clip(max(float(dst.get("energy") or 0), float(cell.get("energy") or 0)))
        dst["visited"] = bool(dst.get("visited") or cell.get("visited"))
        dst["tokens"] = max(int(dst.get("tokens") or 0), int(cell.get("tokens") or 0))
        dst["help"] = max(float(dst.get("help") or 0), float(cell.get("help") or 0))
        dst["unsafe"] = max(float(dst.get("unsafe") or 0), float(cell.get("unsafe") or 0))
        dst["count"] = max(int(dst.get("count") or 0), int(cell.get("count") or 0))
        warm = max(int(dst.get("warmup_tokens") or 0), int(cell.get("warmup_tokens") or 0))
        if warm:
            dst["warmup_tokens"] = warm
            dst["remaining_cut"] = max(0, warm - int(dst.get("tokens") or 0))
    grid.clear()
    grid.update(merged)
    edges = memory.setdefault("nca", {}).setdefault("board_edges", [])
    rewritten = []
    seen: set[tuple[str, str]] = set()
    for edge in edges:
        if not isinstance(edge, (list, tuple)) or len(edge) < 2:
            continue
        src, dst = canonical_cell_id(str(edge[0])), canonical_cell_id(str(edge[1]))
        pair = (src, dst)
        if pair in seen or not src or not dst:
            continue
        seen.add(pair)
        rewritten.append([src, dst])
    memory["nca"]["board_edges"] = rewritten
    return {"ok": True, "n_cells": len(grid)}


def charge_budget(
    memory: dict[str, Any],
    *,
    ledger: Any = None,
    jev_calls: int = 0,
    usd: float = 0.0,
    event: str = "charge",
) -> dict[str, Any]:
    """Spend is an NCA cell: remaining_usd/budget_usd when a ledger is present."""

    grid = _grid(memory)
    cell = _cell(grid, BUDGET_PTR, kind="tool")
    if not cell.get("visited") and "jev_calls" not in cell:
        cell["energy"] = 1.0
    old = float(cell.get("energy") or 1.0)
    calls = int(jev_calls)
    spent = float(usd)
    if ledger is not None:
        blob = ledger.as_dict() if hasattr(ledger, "as_dict") else {}
        calls = max(
            calls,
            int(blob.get("jev_calls") or 0)
            + int(blob.get("mistral_calls") or 0)
            + int(blob.get("grok_calls") or 0),
        )
        lines = blob.get("lines") or []
        spent = max(
            spent,
            float(blob.get("spent_usd") or 0),
            sum(float(row.get("usd") or 0) for row in lines if isinstance(row, dict)),
        )
        budget = float(blob.get("budget_usd") or 0)
        remaining = blob.get("remaining_usd")
        if budget > 0 and remaining is not None:
            cell["energy"] = _clip(float(remaining) / budget)
        else:
            cell["energy"] = _clip(old - min(0.25, 0.02 * calls + min(0.2, spent)))
    else:
        cell["energy"] = _clip(old - min(0.25, 0.02 * calls + min(0.2, spent)))
    cell["jev_calls"] = calls
    cell["usd"] = round(spent, 6)
    cell["visited"] = True
    journal_event(
        memory,
        event=event,
        ptr=BUDGET_PTR,
        op="BUDGET",
        energy_delta=float(cell["energy"]) - old,
        extra={"jev_calls": calls},
    )
    return {"ok": True, "energy": cell["energy"], "jev_calls": calls, "usd": spent}


def replay_journal(memory: dict[str, Any], *, last_n: int = 32) -> dict[str, Any]:
    """Re-apply recent journal energy deltas onto canonical cells."""

    nca = memory.setdefault("nca", {})
    journal = list(nca.get("journal") or [])[-max(1, int(last_n)) :]
    grid = _grid(memory)
    n_applied = 0
    for row in journal:
        ptr = canonical_cell_id(str(row.get("ptr") or ""))
        if not ptr:
            continue
        cell = _cell(grid, ptr, kind=str(row.get("op") or "cell"))
        delta = float(row.get("energy_delta") or 0.0)
        cell["energy"] = _clip(float(cell.get("energy") or 0.5) + delta)
        if str(row.get("event") or "") in {"call", "upsert"}:
            cell["visited"] = True
        n_applied += 1
    last_ran = list((nca.get("program_state") or {}).get("last_ran") or [])
    receipts = [
        {"op": row.get("op"), "ptr": row.get("ptr"), "ok": row.get("ok"), "detail_ok": row.get("detail_ok")}
        for row in last_ran
        if isinstance(row, dict)
    ]
    return {
        "ok": True,
        "n_replayed": n_applied,
        "receipts": receipts,
        "n_receipts": len(receipts),
        "called_docker0": False,
    }


def _clip(value: float) -> float:
    lo, hi = ENERGY_CLIP
    try:
        number = float(value)
    except (TypeError, ValueError):
        return 0.5
    if number != number:  # NaN
        return 0.5
    return max(lo, min(hi, number))


def upsert_from_event(
    memory: dict[str, Any],
    *,
    ptr: str = "",
    kind: str = "cell",
    energy: float = 0.5,
    theorem_ok: Optional[bool] = None,
    tokens: int = 0,
    parent_ptr: str = "",
) -> dict[str, Any]:
    """Tape event → grid cell (unify stores) + optional parent backprop."""

    grid = _grid(memory)
    cid = canonical_cell_id(str(ptr or f"event:{kind}"), kind=kind)
    cell_kind = kind if kind in {"skill", "goal", "subgoal", "task", "codepath", "theorem", "proof", "tool", "family", "residual"} else "cell"
    cell = _cell(grid, cid, kind=cell_kind)
    old = float(cell.get("energy") or 0.5)
    mixed = _clip(0.7 * old + 0.3 * float(energy))
    if theorem_ok is True:
        cell["wins"] = int(cell.get("wins") or 0) + 1
        mixed = max(mixed, 0.7)
    elif theorem_ok is False:
        cell["losses"] = int(cell.get("losses") or 0) + 1
        mixed = min(mixed, 0.35)
    cell["energy"] = mixed
    cell["updated_at"] = time.time()
    if tokens:
        cell["tokens"] = int(tokens)
        warm = int(cell.get("warmup_tokens") or 0)
        if warm:
            cell["remaining_cut"] = max(0, warm - int(tokens))
    cell["visited"] = True
    if parent_ptr and parent_ptr != cid:
        parent_ptr = canonical_cell_id(parent_ptr)
        parent = _cell(grid, parent_ptr, kind=str((grid.get(parent_ptr) or {}).get("kind") or "cell"))
        parent["energy"] = _clip(0.8 * float(parent.get("energy") or 0.5) + 0.2 * mixed)
    journal_event(memory, event="upsert", ptr=cid, op=kind, energy_delta=mixed - old)
    return cell


def journal_event(
    memory: dict[str, Any],
    *,
    event: str,
    ptr: str = "",
    op: str = "",
    energy_delta: float = 0.0,
    extra: Optional[Mapping[str, Any]] = None,
) -> None:
    nca = memory.setdefault("nca", {})
    journal = list(nca.get("journal") or [])
    row: dict[str, Any] = {
        "tick": int(nca.get("tick") or 0),
        "event": str(event),
        "ptr": str(ptr or ""),
        "op": str(op or ""),
        "energy_delta": round(float(energy_delta), 4),
    }
    if extra:
        row.update(dict(extra))
    journal.append(row)
    nca["journal"] = journal[-128:]


def should_halt(memory: Mapping[str, Any]) -> dict[str, Any]:
    """Stop when there is nothing left to CALL: no diagnostics, no pending work, tasks blocked or cold."""

    import nca_repair as lra_heal

    issues = lra_heal.diagnose(dict(memory))
    ops = list((((memory.get("nca") or {}).get("program_state") or {}).get("ops")) or [])
    pending = [op for op in ops if str(op.get("op") or "") not in {"KEEP", "RETURN"}]
    grid = (memory.get("nca") or {}).get("grid") or {}
    hot_tasks = [
        cid
        for cid, cell in grid.items()
        if isinstance(cell, dict)
        and cell.get("kind") == "task"
        and cell.get("visited")
        and not cell.get("do_not_fork")
        and not cell.get("blocked")
        and float(cell.get("energy") or 0) > 0.12
    ]
    budget = grid.get("ptr://tool/budget") if isinstance(grid.get("ptr://tool/budget"), dict) else {}
    budget_energy = float(budget.get("energy") or 1.0)
    budget_dead = bool(budget.get("visited")) and budget_energy < 0.1
    journal = list(((memory.get("nca") or {}).get("journal")) or [])
    last_ran = list((((memory.get("nca") or {}).get("program_state") or {}).get("last_ran")) or [])
    ever_ran = bool(last_ran) or any(str(row.get("event") or "") in {"call", "instruct", "jev", "jev_pick", "grok"} for row in journal)
    idle = (not issues) and (not pending) and (not hot_tasks)
    halt = (ever_ran and idle) or budget_dead
    return {
        "halt": halt,
        "n_issues": len(issues),
        "n_pending_ops": len(pending),
        "n_hot_tasks": len(hot_tasks),
        "budget_energy": budget_energy,
        "budget_dead": budget_dead,
        "called_docker0": False,
    }


def _grid(memory: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return memory.setdefault("nca", {}).setdefault("grid", {})


def _cell(grid: dict[str, dict[str, Any]], cid: str, *, kind: str = "skill") -> dict[str, Any]:
    row = grid.setdefault(
        cid,
        {
            "id": cid,
            "kind": kind,
            "energy": 0.5,
            "wins": 0,
            "losses": 0,
            "help": 0.0,
            "unsafe": 0.0,
            "tokens": 0,
            "tick": 0,
        },
    )
    return row


def feed_state(memory: dict[str, Any], *, tactics: str = "", problem: str = "") -> dict[str, Any]:
    """Load previous NCA grid and overlay live memory / residuals (self-feed)."""

    import portable_rewrites as lra_port
    import run_warmup as lra_loop

    grid = _grid(memory)
    for row in memory.get("successes") or []:
        cid = canonical_cell_id(str(row.get("kind") or ""), kind="skill")
        if not cid:
            continue
        cell = _cell(grid, cid, kind="skill")
        cell["wins"] = int(cell.get("wins") or 0) + 1
        cell["tokens"] = int(row.get("to_tokens") or cell.get("tokens") or 0)
    for row in memory.get("failures") or []:
        cid = canonical_cell_id(str(row.get("kind") or ""), kind="skill")
        if not cid:
            continue
        cell = _cell(grid, cid, kind="skill")
        cell["losses"] = int(cell.get("losses") or 0) + 1
    for row in memory.get("research") or []:
        if problem and row.get("name") != problem:
            continue
        for residual, help_score in (row.get("help") or {}).items():
            cid = canonical_cell_id(f"residual:{residual}", kind="residual")
            cell = _cell(grid, cid, kind="residual")
            cell["help"] = float(help_score or 0.0)
            cell["unsafe"] = float((row.get("unsafe") or {}).get(residual) or 0.0)
    if not any(str(cid).startswith("ptr://goal/") for cid in grid):
        try:
            import board_graph as lra_board

            lra_board.seed_nca_from_board(memory)
        except Exception:
            pass
    if tactics:
        proof_id = canonical_cell_id(f"proof:{problem or 'script'}", kind="theorem")
        _cell(grid, proof_id, kind="proof")["tokens"] = lra_loop.token_count(tactics)
        counts = lra_port.analyze_residuals(tactics)
        inverse: dict[str, list[str]] = {}
        for stem, residual in lra_port.SKILL_RESIDUAL.items():
            inverse.setdefault(residual, []).append(stem)
        edges = memory.setdefault("nca", {}).setdefault("board_edges", [])
        for residual, count in counts.items():
            cid = canonical_cell_id(f"residual:{residual}", kind="residual")
            cell = _cell(grid, cid, kind="residual")
            cell["count"] = int(count)
            cell["energy"] = _clip(
                max(float(cell.get("energy") or 0.4), min(0.95, 0.35 + 0.08 * int(count)))
            )
            for stem in inverse.get(residual, ()):
                skill_ptr = canonical_cell_id(f"port_{stem}", kind="skill")
                _cell(grid, skill_ptr, kind="skill")
                pair = [cid, skill_ptr]
                if pair not in edges:
                    edges.append(pair)
        for fam, kids in lra_port.decision_tree(tactics, memory=memory, name=problem).items():
            _cell(grid, canonical_cell_id(f"family:{fam}", kind="family"), kind="family")
            for kid in kids:
                _cell(grid, canonical_cell_id(str(kid), kind="skill"), kind="skill")
    try:
        import nca_repair as lra_heal

        if lra_heal.diagnose(memory):
            lra_heal.heal(memory)
    except Exception:
        pass
    return {"n_cells": len(grid), "grid": grid}


def neighborhood(cid: str, memory: Mapping[str, Any]) -> list[str]:
    """Neighbors from KG edges, decision-tree siblings, and AST fold list."""

    nbrs: list[str] = []
    kg = lra_tools.skill_knowledge_graph(memory)
    for edge in kg.get("edges") or []:
        if edge.get("src") == cid and edge.get("dst"):
            nbrs.append(str(edge["dst"]))
        if edge.get("dst") == cid and edge.get("src"):
            nbrs.append(str(edge["src"]))
    grid = (memory.get("nca") or {}).get("grid") or {}
    kind = (grid.get(cid) or {}).get("kind")
    if kind == "skill":
        nbrs.extend(key for key, row in grid.items() if row.get("kind") == "skill" and key != cid)
    for src, dst in (memory.get("nca") or {}).get("board_edges") or []:
        if src == cid:
            nbrs.append(str(dst))
        if dst == cid:
            nbrs.append(str(src))
    # unique, cap
    out: list[str] = []
    seen: set[str] = set()
    for item in nbrs:
        if item in seen:
            continue
        seen.add(item)
        out.append(item)
        if len(out) >= 12:
            break
    return out


def tick(memory: dict[str, Any], *, tactics: str = "", problem: str = "", focus: Optional[str] = None) -> dict[str, Any]:
    """One NCA update: self-state + neighbors + TypeSafe help/unsafe + lake wins."""

    feed_state(memory, tactics=tactics, problem=problem)
    grid = _grid(memory)
    targets: Optional[set[str]] = None
    if focus:
        fid = canonical_cell_id(str(focus))
        targets = {fid}
        for edge in (memory.get("nca") or {}).get("board_edges") or []:
            if not isinstance(edge, (list, tuple)) or len(edge) < 2:
                continue
            src, dst = str(edge[0]), str(edge[1])
            if src == fid:
                targets.add(dst)
            if dst == fid:
                targets.add(src)
    nxt: dict[str, dict[str, Any]] = {}
    for cid, cell in grid.items():
        if targets is not None and cid not in targets:
            nxt[cid] = dict(cell)
            continue
        wins = int(cell.get("wins") or 0)
        losses = int(cell.get("losses") or 0)
        win_rate = wins / max(1, wins + losses)
        unsafe = float(cell.get("unsafe") or 0.0)
        help_score = float(cell.get("help") or 0.0)
        nbr_e = [
            float((grid.get(nid) or {}).get("energy") or 0.5)
            for nid in neighborhood(cid, memory)
        ]
        mean_n = sum(nbr_e) / len(nbr_e) if nbr_e else float(cell.get("energy") or 0.5)
        energy = _clip(
            0.45 * float(cell.get("energy") or 0.5)
            + 0.20 * mean_n
            + 0.20 * (1.0 - unsafe)
            + 0.10 * win_rate
            + 0.05 * min(1.0, help_score / 2.0)
        )
        energy = _clip(energy * 0.98)
        stale_for = time.time() - float(cell.get("updated_at") or time.time())
        if stale_for > STALE_SECONDS:
            energy = _clip(energy * 0.85)
        if losses > wins:
            energy = _clip(energy - 0.15)
        if cell.get("do_not_fork") or cell.get("blocked"):
            energy = min(energy, 0.05)
        updated = dict(cell)
        updated["energy"] = energy
        updated["tick"] = int(cell.get("tick") or 0) + 1
        nxt[cid] = updated
    memory.setdefault("nca", {})["grid"] = nxt
    memory["nca"]["tick"] = int((memory.get("nca") or {}).get("tick") or 0) + 1
    journal_event(memory, event="tick", op="TICK", extra={"n_cells": len(nxt), "focus": focus or ""})
    ranked = sorted(nxt, key=lambda key: float(nxt[key].get("energy") or 0.0), reverse=True)
    return {
        "ok": True,
        "tick": memory["nca"]["tick"],
        "n_cells": len(nxt),
        "top": [{"id": key, "energy": nxt[key]["energy"], "kind": nxt[key]["kind"]} for key in ranked[:8]],
        "called_docker0": False,
    }


def _safe_path(path: str | Path) -> Optional[Path]:
    raw = Path(path)
    if not raw.is_absolute():
        raw = HERE / raw
    try:
        resolved = raw.resolve()
    except OSError:
        return None
    allowed = (HERE.resolve(), PAPER_ROOT.resolve())
    if not any(resolved == root or root in resolved.parents for root in allowed):
        return None
    return resolved


def hook_and_eval(path: str | Path) -> dict[str, Any]:
    """Walk one harness/paper file: AST, import, whether a test module names it."""

    target = _safe_path(path)
    if target is None or not target.is_file():
        return {"ok": False, "reason": "path_not_allowed", "path": str(path)}
    text = target.read_text(encoding="utf-8")
    functions: list[str] = []
    try:
        tree = ast.parse(text)
        functions = [node.name for node in tree.body if isinstance(node, ast.FunctionDef)]
    except SyntaxError as exc:
        return {"ok": False, "reason": "syntax", "error": str(exc)[:160], "path": str(target)}
    importable = False
    if target.parent == HERE and target.suffix == ".py":
        try:
            importlib.import_module(target.stem)
            importable = True
        except Exception:
            importable = False
    tests = [
        p.name
        for p in HERE.glob("test_*.py")
        if target.stem.replace("typesafe_", "").split("_")[0] in p.read_text(encoding="utf-8")
    ][:8]
    return {
        "ok": True,
        "path": str(target.relative_to(PAPER_ROOT.resolve()) if PAPER_ROOT.resolve() in target.parents or target.parent == PAPER_ROOT.resolve() else target.name),
        "n_functions": len(functions),
        "fold_fns": [name for name in functions if name.startswith("fold_")],
        "importable": importable,
        "tests": tests,
        "n_chars": len(text),
        "called_docker0": False,
    }


def walk_codebase(*, limit: int = WALK_MAX_FILES) -> dict[str, Any]:
    """Hook every harness Python file (bounded)."""

    files = sorted(HERE.glob("*.py"))[: max(1, int(limit))]
    rows = [hook_and_eval(path) for path in files]
    return {
        "ok": True,
        "n_files": len(rows),
        "importable": sum(1 for row in rows if row.get("importable")),
        "n_fold_fns": sum(len(row.get("fold_fns") or []) for row in rows),
        "files": [{"path": row.get("path"), "ok": row.get("ok"), "n_functions": row.get("n_functions")} for row in rows],
        "called_docker0": False,
    }


def evaluate_tests(*names: str) -> dict[str, Any]:
    """Run selected harness unit tests in-process (no lake, no docker0)."""

    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    for name in names or ("test_skill_improve_loop",):
        stem = str(name).replace(".py", "")
        if not stem.startswith("test_"):
            continue
        path = HERE / f"{stem}.py"
        if not path.is_file():
            continue
        try:
            suite.addTests(loader.discover(str(HERE), pattern=f"{stem}.py"))
        except Exception:
            continue
    import io

    result = unittest.TextTestRunner(verbosity=0, stream=io.StringIO()).run(suite)
    return {
        "ok": result.wasSuccessful(),
        "run": result.testsRun,
        "failures": len(result.failures),
        "errors": len(result.errors),
        "called_docker0": False,
    }


def mutate(
    memory: dict[str, Any],
    *,
    tactics: str = "",
    problem: str = "",
    op: str = "auto",
) -> dict[str, Any]:
    """Gated mutation: memory fold, pipeline energy order, or skip a dying stem.

    Does not rewrite arbitrary repo files. Lake remains the Lean oracle.
    """

    import binder_use as lra_bind
    import portable_rewrites as lra_port

    tick(memory, tactics=tactics, problem=problem)
    grid = _grid(memory)
    ranked = sorted(grid, key=lambda key: float(grid[key].get("energy") or 0.0), reverse=True)
    applied: dict[str, Any] = {"op": op}
    if op in {"auto", "reorder"}:
        order = [
            cid[len("port_") :] if cid.startswith("port_") else cid
            for cid in ranked
            if grid[cid].get("kind") == "skill"
        ]
        memory.setdefault("nca", {}).setdefault("pipeline_bias", order[:16])
        applied = {"op": "reorder", "pipeline_bias": order[:8]}
    if op in {"auto", "skip"}:
        dying = [
            cid
            for cid in ranked[::-1]
            if grid[cid].get("kind") == "skill" and int(grid[cid].get("losses") or 0) > int(grid[cid].get("wins") or 0)
        ]
        if dying and problem:
            key = f"{problem}::{dying[0]}"
            bl = memory.setdefault("blacklist", [])
            if key not in bl:
                bl.append(key)
            applied = {"op": "skip", "key": key}
    if op in {"auto", "fold"} and tactics:
        for spec in memory.get("skills") or []:
            nxt = lra_port.fold_from_memory_skill(tactics, spec)
            if nxt != tactics:
                applied = {"op": "fold", "stem": spec.get("stem"), "tactics": nxt}
                break
        else:
            prop = lra_bind.propose_skill_from_research(memory, problem)
            if prop.get("keep_structure") and prop.get("mint"):
                lra_bind.expand_skills_from_memory(memory, name=problem, tactics=tactics)
                applied = {"op": "mint", "proposed": prop}
    mutations = memory.setdefault("nca", {}).setdefault("mutations", [])
    mutations.append(applied)
    memory["nca"]["mutations"] = mutations[-32:]
    return {"ok": True, "applied": applied, "called_docker0": False}


def fork_cells(
    memory: dict[str, Any],
    *,
    cell_ids: Optional[list[str]] = None,
    **spawn_kwargs: Any,
) -> dict[str, Any]:
    """Fork up to FORK_MAX high-energy cells as returnable subloops."""

    tick(memory, tactics=str(spawn_kwargs.get("tactics") or ""), problem=str(spawn_kwargs.get("problem") or ""))
    grid = _grid(memory)
    if not cell_ids:
        cell_ids = [
            key
            for key in sorted(grid, key=lambda cid: float(grid[cid].get("energy") or 0.0), reverse=True)
            if not (grid[key].get("do_not_fork") or grid[key].get("blocked"))
        ][:FORK_MAX]
    launched: list[dict[str, Any]] = []
    for cid in list(cell_ids)[:FORK_MAX]:
        child = dict(spawn_kwargs)
        child["node"] = cid
        if child.get("record") is not None and "skill_walk" in lra_tools.SUBLOOPS:
            payload = lra_tools.spawn_subloop("skill_walk", **child)
        else:
            payload = {
                "ok": True,
                "returned": True,
                "subloop": "nca_cell",
                "node": cid,
                "energy": (grid.get(cid) or {}).get("energy"),
            }
        launched.append({"id": cid, "returned": bool(payload.get("returned")), "ok": payload.get("ok")})
        memory.setdefault("subloop_returns", []).append(
            {"name": cid, "ok": payload.get("ok"), "returned": True, "nca": True}
        )
    return {"ok": True, "n_forked": len(launched), "forks": launched, "called_docker0": False}


def nca_tool(name: str, **kwargs: Any) -> dict[str, Any]:
    key = str(name or "").strip()
    memory = kwargs.get("memory") if isinstance(kwargs.get("memory"), dict) else {}
    tactics = str(kwargs.get("tactics") or "")
    problem = str(kwargs.get("problem") or "")
    if key == "nca_tick":
        return tick(memory, tactics=tactics, problem=problem)
    if key == "nca_walk":
        return walk_codebase()
    if key == "nca_hook":
        return hook_and_eval(str(kwargs.get("path") or "portable_rewrites.py"))
    if key == "nca_mutate":
        return mutate(memory, tactics=tactics, problem=problem, op=str(kwargs.get("op") or "auto"))
    if key == "nca_fork":
        return fork_cells(memory, tactics=tactics, problem=problem, **{k: v for k, v in kwargs.items() if k not in {"memory", "tactics", "problem", "name"}})
    if key == "nca_eval":
        return evaluate_tests(*list(kwargs.get("tests") or ["test_skill_improve_loop"]))
    return {"ok": False, "reason": "unknown_nca_tool", "tool": key}


def _nca_tick_entry(**kwargs: Any) -> dict[str, Any]:
    mem = kwargs.get("memory") if isinstance(kwargs.get("memory"), dict) else {}
    rec = kwargs.get("record") if isinstance(kwargs.get("record"), dict) else {}
    problem = str(kwargs.get("problem") or rec.get("name") or "")
    return tick(mem, tactics=str(kwargs.get("tactics") or ""), problem=problem)


lra_tools.register_subloop("nca_tick", _nca_tick_entry)
lra_tools.register_subloop(
    "nca_fork",
    lambda **kw: fork_cells(
        kw.get("memory") if isinstance(kw.get("memory"), dict) else {},
        **{k: v for k, v in kw.items() if k not in {"name", "memory"}},
    ),
)

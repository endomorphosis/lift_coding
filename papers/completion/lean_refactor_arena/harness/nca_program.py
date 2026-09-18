#!/usr/bin/env python3
"""Program the NCA: IR compile/decompile + Lean-capable LM instructions.

Local closed IR is always produced from tape/board/grid. Optional
ipfs_datasets_py QueryIR / Cypher compiler / modal decompiler / autoencoder
hints enrich it. Hosted Labs Leanstral (never docker0) may emit JSON work
ops. Lean snippets still need lake. Jev does not write Lean.
"""
from __future__ import annotations

import json
import re
from typing import Any, Callable, Mapping, Optional

_JSON_OBJ = re.compile(r"\{.*\}", re.DOTALL)
ALLOWED_OPS = ("CALL", "TICK", "SEARCH", "MUTATE", "BOARD", "SLICE", "KEEP", "RETURN")
_LEAN_MARKERS = ("simp_all", "intros ", "theorem ", "\nby\n", "exact ⟨", "induction ", "have :=")


def _grid(memory: Mapping[str, Any]) -> dict[str, Any]:
    return dict(((memory.get("nca") or {}).get("grid")) or {})


def compile_local_ir(memory: Mapping[str, Any], *, problem: str = "") -> dict[str, Any]:
    """Closed IR: seed high-energy cells, expand board edges, project ids."""

    grid = _grid(memory)
    ranked = sorted(grid, key=lambda cid: float((grid[cid] or {}).get("energy") or 0.0), reverse=True)
    preferred: list[str] = []
    if problem:
        preferred.append(f"ptr://theorem/{problem}")
    cuts: list[tuple[int, str]] = []
    for cid, cell in grid.items():
        if not isinstance(cell, dict):
            continue
        if cell.get("kind") in {"theorem", "proof"} or "/theorem/" in str(cid):
            keep = int(cell.get("tokens") or 0)
            warm = int(cell.get("warmup_tokens") or 0)
            remaining = int(cell.get("remaining_cut") or 0)
            if remaining <= 0 and warm > keep:
                remaining = warm - keep
            if remaining > 0:
                cell["remaining_cut"] = remaining
                cuts.append((remaining, str(cid)))
    for _cut, cid in sorted(cuts, reverse=True):
        if cid not in preferred:
            preferred.append(cid)
    for cid, cell in grid.items():
        if not isinstance(cell, dict):
            continue
        if cell.get("kind") != "task" or cell.get("do_not_fork") or cell.get("blocked"):
            continue
        status = str(cell.get("status") or "")
        if status == "ready":
            preferred.append(str(cid))
        elif not cell.get("visited"):
            preferred.append(str(cid))
    rest = [
        cid
        for cid in ranked
        if cid not in preferred
        and not (grid[cid] or {}).get("do_not_fork")
        and not str(cid).endswith("LRA-G000")
        and "/goal/" not in str(cid)
    ]
    seeds = (preferred + rest)[:8]
    if not seeds:
        seeds = [cid for cid in ranked if not (grid[cid] or {}).get("do_not_fork")][:8]
    edges = list(((memory.get("nca") or {}).get("board_edges")) or [])[:24]
    ops = [
        {"op": "SeedEntities", "entity_ids": seeds, "problem": problem},
        {"op": "Expand", "relationship_types": ["board", "skill"], "direction": "both"},
        {"op": "Project", "fields": ["id", "kind", "energy"]},
        {"op": "Limit", "n": 16},
    ]
    return {
        "ok": True,
        "source": "local",
        "ops": ops,
        "seeds": seeds,
        "n_edges": len(edges),
        "called_docker0": False,
    }


def compile_datasets_ir(memory: Mapping[str, Any]) -> dict[str, Any]:
    """ipfs_datasets_py QueryIR pipeline over NCA cell ids."""

    try:
        from ipfs_datasets_py.search.graph_query.ir import Expand, Limit, Project, QueryIR, SeedEntities
    except Exception as exc:
        return {"ok": False, "source": "datasets_query_ir", "reason": type(exc).__name__, "called_docker0": False}
    local = compile_local_ir(memory)
    seeds = list(local.get("seeds") or [])
    ir = QueryIR.from_ops(
        [
            SeedEntities(entity_ids=tuple(seeds)),
            Expand(relationship_types=("board", "calls"), direction="both", max_per_node=12),
            Project(fields=("id", "kind", "energy")),
            Limit(n=16),
        ]
    )
    return {
        "ok": True,
        "source": "datasets_query_ir",
        "ops": [{"op": type(op).__name__, **{k: getattr(op, k, None) for k in ()}} for op in ir.ops],
        "n_ops": len(ir.ops),
        "seeds": seeds,
        "called_docker0": False,
    }


def decompile_ir(ir: Mapping[str, Any]) -> dict[str, Any]:
    """Turn IR ops into natural-language work instructions (datasets decompiler if present)."""

    ops = list(ir.get("ops") or [])
    lines = []
    for op in ops:
        name = str(op.get("op") or "")
        if name == "SeedEntities":
            lines.append("inspect cells " + ", ".join(str(x) for x in (op.get("entity_ids") or [])[:6]))
        elif name == "Expand":
            lines.append("walk neighbors on the board and skill graph")
        elif name == "CALL":
            lines.append(f"CALL {op.get('ptr')}")
        elif name:
            lines.append(name.lower())
    text = "; ".join(lines) or "TICK then KEEP"
    extra: dict[str, Any] = {}
    try:
        from ipfs_datasets_py.logic.modal.decompiler_repairs import decompile_modal_ir_structure

        extra["datasets_decompiler"] = {
            "ok": True,
            "note": "modal decompiler imported; NCA IR is not a legal sample so not executed",
        }
    except Exception as exc:
        extra["datasets_decompiler"] = {"ok": False, "reason": type(exc).__name__}
    return {"ok": True, "instructions": text, "n_ops": len(ops), "called_docker0": False, **extra}


def autoencoder_hints(memory: Mapping[str, Any]) -> dict[str, Any]:
    """Optional AdaptiveModalAutoencoder synthesis hints. No model weights required."""

    try:
        from ipfs_datasets_py.optimizers.logic import synthesis_hints_from_autoencoder_introspection
    except Exception as exc:
        return {"ok": False, "source": "autoencoder", "reason": type(exc).__name__, "called_docker0": False}
    window = list(((memory.get("nca") or {}).get("board_window")) or [])[:8]
    fake = {
        "synthesis_focus": tuple(str(row.get("id") or "") for row in window if row.get("id")),
        "ranked_guidance_features": (),
        "legal_ir_view_metrics": {},
    }
    try:
        hints = synthesis_hints_from_autoencoder_introspection(fake)
    except Exception:
        hints = {"focus": fake["synthesis_focus"], "imported": True}
    return {"ok": True, "source": "autoencoder", "hints": hints, "called_docker0": False}


def ir_to_work_ops(
    ir: Mapping[str, Any],
    *,
    decompiled: Optional[Mapping[str, Any]] = None,
    problem: str = "",
) -> list[dict[str, Any]]:
    """Map compiled IR to closed NCA work: current theorem and unvisited tasks first."""

    ops: list[dict[str, Any]] = []
    if problem:
        ops.append({"op": "CALL", "ptr": f"ptr://theorem/{problem}"})
    # IR seeds are already remaining-cut ranked; CALL those next.
    for seed in ir.get("seeds") or []:
        text = str(seed)
        if "/goal/" in text or text.endswith("LRA-G000"):
            continue
        if text.startswith("ptr://"):
            ops.append({"op": "CALL", "ptr": text})
        elif text.startswith("port_"):
            ops.append({"op": "CALL", "ptr": f"ptr://skill/{text}"})
        if len([op for op in ops if op.get("op") == "CALL"]) >= 4:
            break
    ops.append({"op": "SLICE"})
    ops.append({"op": "TICK"})
    ops.append({"op": "KEEP"})
    if decompiled and decompiled.get("instructions"):
        ops.insert(0, {"op": "SEARCH", "query": str(decompiled["instructions"])[:80]})
    seen_ptr: set[str] = set()
    out: list[dict[str, Any]] = []
    for op in ops:
        if op.get("op") not in ALLOWED_OPS:
            continue
        ptr = str(op.get("ptr") or "")
        if ptr:
            if ptr in seen_ptr:
                continue
            seen_ptr.add(ptr)
        out.append(op)
    return out[:12]


def compile_program(
    memory: Mapping[str, Any],
    *,
    tactics: str = "",
    problem: str = "",
) -> dict[str, Any]:
    local = compile_local_ir(memory, problem=problem)
    datasets = compile_datasets_ir(memory)
    decoded = decompile_ir(local)
    hints = autoencoder_hints(memory)
    work = ir_to_work_ops(
        local if not datasets.get("ok") else {**local, **{k: datasets.get(k) for k in ("seeds",) if datasets.get(k)}},
        decompiled=decoded,
        problem=problem,
    )
    return {
        "ok": True,
        "local_ir": local,
        "datasets_ir": datasets,
        "decompiled": decoded,
        "autoencoder": hints,
        "work_ops": work,
        "tactics_head": str(tactics or "")[:120],
        "called_docker0": False,
        "used_prototype_endpoint": False,
        "hardware_class": "nca_local_ir",
    }


def parse_work_ops(text: str) -> list[dict[str, Any]]:
    blob = str(text or "")
    match = _JSON_OBJ.search(blob)
    if not match:
        return []
    try:
        raw = json.loads(match.group(0))
    except json.JSONDecodeError:
        return []
    if isinstance(raw, dict) and raw.get("tactics") and any(marker in str(raw.get("tactics")) for marker in _LEAN_MARKERS):
        raw = {k: v for k, v in raw.items() if k != "tactics"}
    rows = raw.get("ops") if isinstance(raw, dict) else raw
    if not isinstance(rows, list):
        return []
    out: list[dict[str, Any]] = []
    for item in rows:
        if not isinstance(item, dict):
            continue
        op = str(item.get("op") or "").upper()
        if op not in ALLOWED_OPS:
            continue
        packed = json.dumps(item)
        if any(marker in packed for marker in _LEAN_MARKERS):
            continue
        row = {"op": op}
        if item.get("ptr"):
            row["ptr"] = str(item["ptr"])
        if item.get("query"):
            row["query"] = str(item["query"])[:80]
        out.append(row)
    return out[:12]


def leanstral_instruct(
    program: Mapping[str, Any],
    *,
    generate: Optional[Callable[..., str]] = None,
    ledger: Any = None,
) -> dict[str, Any]:
    """Hosted Labs Leanstral (or fixture) emits JSON work ops. Never docker0."""

    prompt = (
        "You program a TypeSafe neural cellular automaton. Do not write Lean.\n"
        "Never call docker0 or the prototype local endpoint. Reply with JSON {\"ops\":[{\"op\":\"CALL|TICK|SEARCH|BOARD|SLICE|MUTATE|KEEP\",\"ptr\":\"ptr://...\"}]}.\n"
        f"work_ops={json.dumps(program.get('work_ops') or [], sort_keys=True)}\n"
        f"seeds={json.dumps((program.get('local_ir') or {}).get('seeds') or [], sort_keys=True)}\n"
        f"decompiled={json.dumps((program.get('decompiled') or {}).get('instructions') or '', sort_keys=True)}\n"
    )
    if generate is not None:
        text = generate(prompt)
        ops = parse_work_ops(text) or list(program.get("work_ops") or [])
        return {
            "ok": True,
            "ops": ops,
            "provider": "fixture",
            "called_docker0": False,
            "used_prototype_endpoint": False,
            "hardware_class": "fixture",
        }
    if ledger is None:
        return {
            "ok": True,
            "ops": list(program.get("work_ops") or []),
            "provider": "local_ir",
            "called_docker0": False,
            "used_prototype_endpoint": False,
            "hardware_class": "nca_local_ir",
        }
    import track1_ledger as lra_t1
    import track1_mistral_leanstral as lra_mistral

    text, identity, _line = lra_mistral.generate_mistral(
        prompt,
        ledger,
        max_new_tokens=192,
        fixture=False,
    )
    if identity.get("used_prototype_endpoint") or identity.get("url_host") in {"172.17.0.1", "127.0.0.1"}:
        raise lra_t1.Track1LedgerError("leanstral_instruct refused docker0")
    ops = parse_work_ops(text) or list(program.get("work_ops") or [])
    return {
        "ok": True,
        "ops": ops,
        "provider": identity.get("resolved_provider") or "mistral",
        "model": identity.get("resolved_model") or lra_mistral.REQUESTED_MODEL,
        "hardware_class": identity.get("hardware_class") or lra_mistral.HARDWARE_CLASS,
        "called_docker0": False,
        "used_prototype_endpoint": False,
        "raw_head": str(text)[:240],
    }


MAX_EXECUTE = 8


def execute_program_ops(
    memory: dict[str, Any],
    *,
    tactics: str = "",
    problem: str = "",
    max_ops: int = MAX_EXECUTE,
    compile_fn: Optional[Callable[..., Mapping[str, Any]]] = None,
    record: Optional[Mapping[str, Any]] = None,
    args: Any = None,
    restore: bytes = b"",
) -> dict[str, Any]:
    """Run closed work ops. Theorem CALLs lake; docker0 codepaths are inspect-only."""

    import board_graph as lra_board
    import call_stack as lra_cs
    import codepath_graph as lra_cp
    import symbol_search as lra_ss
    import typesafe_nca as lra_nca
    import typesafe_tools as lra_tools

    state = memory.setdefault("nca", {}).setdefault("program_state", {})
    ops = list(state.get("ops") or [])
    ran: list[dict[str, Any]] = []
    remaining: list[dict[str, Any]] = []
    body = str(tactics or "")
    for index, op in enumerate(ops):
        if len(ran) >= max_ops:
            remaining = ops[index:]
            break
        name = str(op.get("op") or "")
        if name in {"KEEP", "RETURN"}:
            ran.append({**op, "ok": True, "stop": True})
            remaining = ops[index + 1 :]
            break
        ok = True
        detail: Any = None
        if name == "TICK":
            detail = lra_nca.tick(memory, tactics=tactics, problem=problem)
        elif name == "BOARD":
            detail = lra_board.seed_nca_from_board(memory)
            overlay = lra_board.overlay_live_board(memory)
            if isinstance(detail, dict):
                detail["overlay"] = overlay
        elif name == "SLICE":
            detail = lra_cp.slice_cross_module("harness.portable_rewrites:fold_hoist_repeated_simp")
            if isinstance(detail, dict):
                src = str(detail.get("symbol") or "portable_rewrites:fold_hoist_repeated_simp")
                src_ptr = src if src.startswith("ptr://") else f"ptr://codepath/{src}"
                edges = memory.setdefault("nca", {}).setdefault("board_edges", [])
                for callee in (detail.get("callees") or [])[:12]:
                    dst = str(callee)
                    dst_ptr = dst if dst.startswith("ptr://") else f"ptr://codepath/{dst}"
                    pair = [src_ptr, dst_ptr]
                    if pair not in edges:
                        edges.append(pair)
        elif name == "SEARCH":
            detail = lra_ss.search_symbols(str(op.get("query") or problem or "fold_"), memory=memory, tactics=tactics)
        elif name == "MUTATE":
            detail = lra_nca.mutate(memory, tactics=tactics, problem=problem)
        elif name == "CALL":
            ptr = str(op.get("ptr") or "")
            resolved = lra_cs.resolve_ptr(ptr, memory=memory, tools=lra_tools.TOOL_CRITERIA)
            if not resolved.get("ok"):
                ok = False
                detail = resolved
            else:
                kind = str(resolved.get("kind") or "")
                if kind == "theorem":
                    import typesafe_inner as lra_inner

                    detail = lra_inner.eval_theorem(
                        str(resolved.get("theorem") or resolved.get("name") or ""),
                        current=dict(record or {"name": problem}),
                        tactics=tactics,
                        compile_fn=compile_fn,
                        args=args or type("A", (), {"timeout": 180.0})(),
                        restore=restore,
                    )
                    if isinstance(detail, dict) and detail.get("name"):
                        lra_board.credit_theorem(
                            memory,
                            str(detail.get("name") or ""),
                            theorem_ok=bool(detail.get("theorem_ok")),
                            tokens=int(detail.get("tokens") or 0),
                        )
                elif kind in {"goal", "subgoal", "task"}:
                    detail = lra_board.board_payload(str(resolved.get("name") or ""))
                elif kind == "codepath":
                    cname = str(resolved.get("codepath") or resolved.get("name") or "")
                    detail = lra_cp.slice_cross_module(cname)
                    if lra_cp.is_inspect_only(cname):
                        detail["invoked"] = False
                elif kind == "skill":
                    import portable_rewrites as lra_port
                    import typesafe_inner as lra_inner

                    stem = str(resolved.get("name") or "")
                    match = None
                    if "pipeline" in stem.lower():
                        piped, applied = lra_port.compose_pipeline(
                            body, memory=memory, name=str(problem or (record or {}).get("name") or "")
                        )
                        if piped and piped.strip("\n") != body.strip("\n"):
                            import run_warmup as lra_loop

                            match = {
                                "kind": "port_pipeline",
                                "tactics": piped,
                                "token_count": lra_loop.token_count(piped),
                                "family": "search_space",
                            }
                    if match is None:
                        drafts = lra_port.portable_drafts(
                            body, memory=memory, name=str(problem or (record or {}).get("name") or "")
                        )
                        for item in drafts:
                            kind_name = str(item.get("kind") or "")
                            bare = stem.replace("port_", "")
                            if kind_name in {stem, f"port_{bare}", f"port_{stem}"} or kind_name.endswith(bare):
                                match = item
                                break
                    if not match:
                        ok = False
                        detail = {"ok": False, "reason": "no_fold", "stem": stem}
                    elif compile_fn is None:
                        body = str(match.get("tactics") or body)
                        detail = {
                            "ok": True,
                            "kind": match.get("kind"),
                            "laked": False,
                            "tokens": match.get("token_count"),
                        }
                    else:
                        accepted, rows = lra_inner.apply_lake_round(
                            record=dict(record or {"name": problem}),
                            tactics=body,
                            analysis={"n_tokens": max(int(match.get("token_count") or 0) + 1, 8)},
                            drafts=[match],
                            intent={"skill": match.get("kind"), "compose": "single"},
                            ranked={"beam_kinds": [match.get("kind")], "fired": False, "fired_leaves": []},
                            memory=memory,
                            args=args or type("A", (), {"timeout": 180.0, "lake_top": 1, "out": None})(),
                            restore=restore,
                            round_i=0,
                            compile_one=compile_fn,
                        )
                        lake_ok = bool(accepted) or any(r.get("ok") for r in rows)
                        if accepted:
                            body = accepted
                        detail = {
                            "ok": lake_ok,
                            "kind": match.get("kind"),
                            "laked": True,
                            "theorem_ok": lake_ok,
                            "tokens": (rows[0].get("tokens") if rows else match.get("token_count")),
                        }
                elif kind == "mcpplusplus":
                    detail = lra_tools.mcpplusplus_call(str(resolved.get("mcpplusplus") or "catalog"), problem=problem, tactics=tactics)
                elif kind == "tool":
                    tool = str(resolved.get("tool") or resolved.get("name") or "")
                    if tool in {"nca_heal", "symbol_search", "board_walk", "codepath_slice"}:
                        detail = lra_tools.run_tool(tool, memory=memory, tactics=tactics, problem=problem)
                    else:
                        detail = {"ok": True, "tool": tool, "skipped": "no_nested_walk"}
                else:
                    detail = {"ok": True, "kind": kind, "skipped": "no_nested_walk"}
                lra_nca.upsert_from_event(
                    memory,
                    ptr=ptr,
                    kind=kind or "cell",
                    energy=0.6 if (isinstance(detail, dict) and detail.get("ok", True)) else 0.25,
                    theorem_ok=detail.get("theorem_ok") if isinstance(detail, dict) else None,
                )
                lra_nca.journal_event(memory, event="call", ptr=ptr, op=kind, extra={"ok": ok})
        else:
            ok = False
            detail = {"reason": "unknown_op"}
        ran.append({**op, "ok": ok, "detail_ok": bool(isinstance(detail, dict) and detail.get("ok", True))})
    else:
        remaining = []
    state["ops"] = remaining
    state["last_ran"] = ran
    state["tactics"] = body
    memory["nca"]["program_state"] = state
    return {"ok": True, "ran": ran, "remaining": remaining, "tactics": body, "called_docker0": False}


def program_nca(
    memory: dict[str, Any],
    *,
    tactics: str = "",
    problem: str = "",
    llm: str = "off",
    generate: Optional[Callable[..., str]] = None,
    ledger: Any = None,
    compile_fn: Optional[Callable[..., Mapping[str, Any]]] = None,
    record: Optional[Mapping[str, Any]] = None,
    args: Any = None,
    restore: bytes = b"",
) -> dict[str, Any]:
    """Compile IR, optionally ask Leanstral, write program_state onto memory/tape-facing dict."""

    compiled = compile_program(memory, tactics=tactics, problem=problem)
    if llm == "leanstral" or generate is not None:
        instructed = leanstral_instruct(compiled, generate=generate, ledger=ledger)
    else:
        instructed = {
            "ok": True,
            "ops": compiled.get("work_ops") or [],
            "provider": "local_ir",
            "called_docker0": False,
            "used_prototype_endpoint": False,
        }
    state = {
        "ops": instructed.get("ops") or [],
        "ir": compiled.get("local_ir"),
        "datasets_ir_ok": bool((compiled.get("datasets_ir") or {}).get("ok")),
        "autoencoder_ok": bool((compiled.get("autoencoder") or {}).get("ok")),
        "decompiled": (compiled.get("decompiled") or {}).get("instructions"),
        "provider": instructed.get("provider"),
        "hardware_class": instructed.get("hardware_class") or "nca_local_ir",
        "called_docker0": False,
    }
    memory.setdefault("nca", {}).setdefault("program_state", state)
    grid = memory["nca"].setdefault("grid", {})
    cell = grid.setdefault(
        "ptr://tool/nca_program",
        {"id": "ptr://tool/nca_program", "kind": "tool", "energy": 0.55, "wins": 0, "losses": 0, "tick": 0},
    )
    cell["energy"] = min(1.0, float(cell.get("energy") or 0.5) + 0.05)
    executed = execute_program_ops(
        memory,
        tactics=tactics,
        problem=problem,
        compile_fn=compile_fn,
        record=record,
        args=args,
        restore=restore,
    )
    try:
        import typesafe_nca as lra_nca

        lra_nca.charge_budget(memory, ledger=ledger, event="instruct")
    except Exception:
        pass
    state["ops"] = executed.get("remaining") or []
    memory["nca"]["program_state"] = state
    return {
        "ok": True,
        "program_state": state,
        "compiled": compiled,
        "instructed": instructed,
        "executed": executed,
        "called_docker0": False,
        "used_prototype_endpoint": False,
        "jev_writes_lean": False,
    }

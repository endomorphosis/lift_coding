#!/usr/bin/env python3
"""Recursive TypeSafe inner loop over the skill decision tree.

Outer Grok (llm_router) decides whether to enter. This module is the inner
TypeSafe walker: keep looping at a tree node, and nest a child loop when
compose=nest. Lake is the oracle. Jev does not write Lean. Never docker0.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Mapping, Optional

import binder_use as lra_bind
import draft_fanout as lra_fan
import mca_mask_replace as lra_mask
import portable_rewrites as lra_port
import random_canary as lra_rand
import track1_keepbest as lra_kb
import typesafe_tools as lra_tools


def _no_drafts_flag(memory: dict[str, Any], record: Mapping[str, Any], key: str) -> bool:
    obs = memory.setdefault("observations", {})
    name = str(record.get("name") or "")
    by = obs.get(f"{key}_by") or {}
    return bool(by.get(name))


def _set_no_drafts_flag(memory: dict[str, Any], record: Mapping[str, Any], key: str, value: bool = True) -> None:
    obs = memory.setdefault("observations", {})
    name = str(record.get("name") or "")
    obs.setdefault(f"{key}_by", {})[name] = value


def flatten_trace(trace: list[Any]) -> list[dict[str, Any]]:
    """Unroll nested_trace children so depth is visible to the outer Grok loop."""

    rows: list[dict[str, Any]] = []
    for event in trace or []:
        if not isinstance(event, dict):
            continue
        rows.append(event)
        rows.extend(flatten_trace(list(event.get("nested_trace") or [])))
    return rows


def _restrict_drafts(
    drafts: list[dict[str, Any]],
    *,
    skip_port: set[str],
    allow_skills: Optional[set[str]],
) -> list[dict[str, Any]]:
    rows = list(drafts)
    if skip_port:
        blocked = {f"port_{name}" for name in skip_port} | set(skip_port)
        rows = [
            item
            for item in rows
            if str(item.get("kind") or "") not in blocked
            and not any(
                str(item.get("kind") or "").endswith(name) or name in str(item.get("kind") or "")
                for name in skip_port
            )
        ]
    if allow_skills:
        want = set(allow_skills) | {f"port_{s}" for s in allow_skills} | {s.replace("port_", "") for s in allow_skills}
        rows = [
            item
            for item in rows
            if str(item.get("kind") or "") in want
            or str(item.get("kind") or "").replace("port_", "") in want
            or str(item.get("kind") or "").startswith("port_pipeline")
        ]
    return rows


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

    lake: list[dict[str, Any]] = []
    too_big = int(analysis.get("n_tokens") or 0) > lra_rand.MAX_LIVE_TOKENS
    preferred: list[str] = []
    seen_pref: set[str] = set()
    for item in memory.get("successes") or []:
        kind = str(item.get("kind") or "").split("#")[0]
        if kind and kind not in seen_pref:
            seen_pref.add(kind)
            preferred.append(kind)
    order: list[str] = []
    skill = str(intent.get("skill") or "")
    if intent.get("compose") == "pipeline":
        order.extend(
            str(item["kind"])
            for item in drafts
            if str(item.get("kind") or "").startswith("port_pipeline")
        )
    if skill and skill not in {"keep", "None"}:
        order.append(skill)
    order.extend(list(ranked.get("beam_kinds") or []))
    order.extend(preferred)
    if ranked.get("best_draft"):
        order.append(str(ranked.get("best_draft")))
    if too_big:
        order = [
            kind
            for kind in ("collapse_rw", "drop_unused_binders", "collapse_simp_at")
            if any(item["kind"] == kind for item in drafts)
        ] + [str(ranked.get("best_draft") or "")]
    order.extend(str(item["kind"]) for item in drafts)
    by_kind = {item["kind"]: item for item in drafts if "tactics" in item}
    fired_skip = set(ranked.get("fired_leaves") or [])
    unfired = [kind for kind in by_kind if kind not in fired_skip]
    if ranked.get("fired") and not unfired:
        lake.append(
            {
                "name": record.get("name"),
                "round": round_i,
                "skipped": "noul_fire_all",
                "fired_leaves": sorted(fired_skip),
            }
        )
        return None, lake
    tried = 0
    seen: set[str] = set()
    lake_budget = 1 if too_big else int(getattr(args, "lake_top", 3) or 3)
    accepted_body = None
    accepted_tok = int(analysis.get("n_tokens") or 10**9)
    timeout = float(getattr(args, "timeout", 180.0) or 180.0)
    out_dir = getattr(args, "out", None)
    import nca_kernel as lra_kern

    lra_kern.bump_tick(memory)
    lra_kern.sweep_negative(memory)
    for kind in order:
        if kind in seen or kind not in by_kind:
            continue
        if kind in fired_skip and unfired:
            continue
        seen.add(str(kind))
        body = str(by_kind[kind]["tactics"])
        lake_id = lra_kern.lake_key(record.get("name"), kind, body)
        if lra_kern.negative_hit(memory, lake_id):
            lake.append(
                {
                    "name": record.get("name"),
                    "round": round_i,
                    "kind": kind,
                    "skipped": "negative_ttl",
                    "ok": False,
                }
            )
            continue
        begun = lra_kern.flight_begin(memory, lake_id)
        if not begun.get("ok"):
            lake.append(
                {
                    "name": record.get("name"),
                    "round": round_i,
                    "kind": kind,
                    "skipped": "in_flight",
                    "ok": False,
                }
            )
            continue
        try:
            compiled = dict(
                compile_one(
                    record,
                    body,
                    state_root=lra_rand.DEFAULT_STATE,
                    timeout=timeout,
                    restore=restore,
                )
            )
            row: dict[str, Any] = {
                "name": record.get("name"),
                "round": round_i,
                "kind": kind,
                "ok": bool(compiled.get("theorem_ok")),
                "tokens": compiled.get("token_count"),
                "repaired": False,
                "error_class": None
                if compiled.get("theorem_ok")
                else lra_bind.error_class(compiled.get("errors") or []),
                "errors": (compiled.get("errors") or [])[:1],
                "depth": intent.get("tree_node"),
            }
            if not row["ok"]:
                repaired_body = str(by_kind[kind]["tactics"])
                if row.get("error_class") == "unknown_identifier":
                    repaired_body = lra_bind.restore_unknown_binders(
                        repaired_body, tactics, compiled.get("errors") or []
                    )
                    repaired_body = lra_mask.hammer_repair(
                        repaired_body, tactics, compiled.get("errors") or []
                    )
                if repaired_body.strip("\n") != str(by_kind[kind]["tactics"]).strip("\n"):
                    repaired = dict(
                        compile_one(
                            record,
                            repaired_body,
                            state_root=lra_rand.DEFAULT_STATE,
                            timeout=timeout,
                            restore=restore,
                        )
                    )
                    row = {
                        "name": record.get("name"),
                        "round": round_i,
                        "kind": f"{kind}#repair",
                        "ok": bool(repaired.get("theorem_ok")),
                        "tokens": repaired.get("token_count"),
                        "repaired": True,
                        "error_class": None
                        if repaired.get("theorem_ok")
                        else lra_bind.error_class(repaired.get("errors") or []),
                        "errors": (repaired.get("errors") or [])[:1],
                        "depth": intent.get("tree_node"),
                    }
                    if row["ok"]:
                        by_kind[kind]["tactics"] = repaired_body
            lake.append(row)
            if row["ok"]:
                lra_bind.remember_success(
                    memory,
                    name=str(record.get("name") or ""),
                    kind=str(row["kind"]),
                    family=str(by_kind[kind].get("family") or ""),
                    from_tokens=int(analysis.get("n_tokens") or 0),
                    to_tokens=int(row["tokens"] or analysis.get("n_tokens") or 0),
                )
                try:
                    import typesafe_nca as lra_nca

                    lra_nca.upsert_from_event(
                        memory,
                        ptr=str(row["kind"]),
                        kind="skill",
                        energy=0.7,
                        theorem_ok=True,
                        tokens=int(row["tokens"] or 0),
                    )
                except Exception:
                    pass
                if int(row["tokens"] or 10**9) < accepted_tok:
                    accepted_tok = int(row["tokens"])
                    accepted_body = str(by_kind[kind].get("tactics") or "")
                    try:
                        import codepath_graph as lra_cp

                        if (memory.get("nca") or {}).get("sidecar_built") and lra_cp.SIDECAR_DUCKDB.is_file():
                            lra_cp.build_sidecar_duckdb()
                    except Exception:
                        pass
                    try:
                        import board_graph as lra_board

                        lra_board.credit_theorem(
                            memory,
                            str(record.get("name") or ""),
                            theorem_ok=True,
                            tokens=int(row["tokens"] or 0),
                        )
                    except Exception:
                        pass
                    if out_dir is not None:
                        safe = str(record.get("name") or "canary").replace("/", "_")[:80]
                        best_path = out_dir / f"random-best-{safe}-{row['tokens']}.lean"
                        best_path.write_text(accepted_body + "\n")
                        row["best_path"] = str(best_path)
            else:
                lra_bind.remember_failure(
                    memory,
                    name=str(record.get("name") or ""),
                    kind=str(kind),
                    errors=row.get("errors") or compiled.get("errors") or [],
                    tactics=str(by_kind[kind].get("tactics") or ""),
                )
                lra_kern.negative_put(memory, lake_id, reason=str(row.get("error_class") or "lake_fail"))
                lra_kern.cache_put(
                    memory,
                    {"kind": kind, "tactics": body[:400]},
                    kind="draft",
                    ns="draft",
                )
                try:
                    import typesafe_nca as lra_nca

                    lra_nca.upsert_from_event(
                        memory,
                        ptr=str(kind),
                        kind="skill",
                        energy=0.25,
                        theorem_ok=False,
                    )
                except Exception:
                    pass
            tried += 1
        finally:
            lra_kern.flight_end(memory, lake_id)
        if tried >= lake_budget:
            break
    return accepted_body, lake


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

    if compile_fn is None:
        return {"ok": False, "reason": "no_compile_fn", "name": name, "theorem_ok": False}
    target = str(name or current.get("name") or "")
    rec: Mapping[str, Any] = current
    body = tactics
    restore_bytes = restore
    if target and target != str(current.get("name") or ""):
        try:
            _raw, _digest, records = lra_splice.load_warmup_records()
        except Exception:
            return {"ok": False, "reason": "warmup_unreadable", "name": target, "theorem_ok": False}
        match = next((item for item in records if str(item.get("name") or "") == target), None)
        if not match:
            return {"ok": False, "reason": "not_small_or_unknown", "name": target, "theorem_ok": False}
        n_tok = int(match.get("n_tokens") or 0)
        if n_tok > lra_rand.MAX_LIVE_TOKENS:
            return {"ok": False, "reason": "not_small_or_unknown", "name": target, "theorem_ok": False, "tokens": n_tok}
        rec = match
        body = lra_fan.tactic_block(match)
        clone = lra_kb.lra_cw.clone_dir(str(match["url"]), lra_rand.DEFAULT_STATE)
        dest = clone / lra_kb.lra_cw.source_relpath(match)
        restore_bytes = dest.read_bytes() if dest.is_file() else b""
        if not dest.is_file():
            return {"ok": False, "reason": "no_clone", "name": target, "theorem_ok": False}
    lake_id = ""
    if isinstance(memory, dict):
        import nca_kernel as lra_kern

        lra_kern.bump_tick(memory)
        lra_kern.sweep_negative(memory)
        lake_id = lra_kern.lake_key(rec.get("name"), "eval_theorem", body)
        if lra_kern.negative_hit(memory, lake_id):
            return {
                "ok": False,
                "name": rec.get("name"),
                "theorem_ok": False,
                "tactics": body,
                "energy": 0.25,
                "reason": "negative_ttl",
                "skipped": "negative_ttl",
            }
        begun = lra_kern.flight_begin(memory, lake_id)
        if not begun.get("ok"):
            return {
                "ok": False,
                "name": rec.get("name"),
                "theorem_ok": False,
                "tactics": body,
                "energy": 0.25,
                "reason": "in_flight",
                "skipped": "in_flight",
            }
    try:
        compiled = dict(
            compile_fn(
                rec,
                body,
                state_root=lra_rand.DEFAULT_STATE,
                timeout=float(getattr(args, "timeout", 180.0) or 180.0),
                restore=restore_bytes,
            )
        )
        ok = bool(compiled.get("theorem_ok"))
        if isinstance(memory, dict) and not ok:
            import nca_kernel as lra_kern

            lra_kern.negative_put(memory, lake_id, reason="lake_failed")
            lra_kern.cache_put(
                memory,
                {"name": rec.get("name"), "tactics": str(body)[:400]},
                kind="eval_theorem",
                ns="draft",
            )
        return {
            "ok": ok,
            "name": rec.get("name"),
            "theorem_ok": ok,
            "tokens": compiled.get("token_count"),
            "tactics": body,
            "energy": 0.75 if ok else 0.25,
            "reason": None if ok else "lake_failed",
        }
    finally:
        if isinstance(memory, dict) and lake_id:
            import nca_kernel as lra_kern

            lra_kern.flight_end(memory, lake_id)


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
    import typesafe_nca as lra_nca

    raw_compile = compile_one or lra_mcmc.compile_one

    def compile_fn(record: Mapping[str, Any], tactics: str, **kwargs: Any) -> Mapping[str, Any]:
        if compile_one is None:
            kwargs.setdefault("memory", memory)
        return raw_compile(record, tactics, **kwargs)
    research = research_fn or lra_rand.typesafe_autoresearch
    pick = pick_fn or lra_rand.typesafe_pick
    counter = steps if steps is not None else [0]
    lake: list[dict[str, Any]] = []
    ranked: dict[str, Any] = {}
    drafts: list[dict[str, Any]] = []
    analysis: dict[str, Any] = {}
    trace: list[dict[str, Any]] = []
    body = str(tactics or "").strip("\n")
    tape = tape if tape is not None else lra_tape.Tape.from_memory(memory)
    stack = stack if stack is not None else lra_cs.CallStack()
    if depth == 0 and stack.depth() == 0:
        stack.call(
            f"ptr://theorem/{record.get('name') or 'goal'}",
            compose="root",
            node="root",
            locals_={"tactics": body},
        )
        tape.write("theorem", str(record.get("name") or ""), ptr=f"ptr://theorem/{record.get('name')}", tokens=0)
        tape.persist(memory)
        try:
            import nca_kernel as lra_kern

            lra_kern.apply_context_budget(memory)
            tape = lra_tape.Tape.from_memory(memory)
        except Exception:
            pass
        try:
            import board_graph as lra_board

            lra_board.link_current_theorem(memory, str(record.get("name") or ""))
        except Exception:
            pass

    def _after(kind: str, payload: Any, *, ptr: str = "", energy: float = 0.5, theorem_ok: Optional[bool] = None, tokens: int = 0) -> None:
        tape.write(
            kind,
            payload,
            ptr=ptr,
            parent_frame=str((stack.top() or {}).get("frame_id") or ""),
            energy=energy,
            theorem_ok=theorem_ok,
            tokens=tokens,
        )
        lra_nca.tick(memory, tactics=body, problem=str(record.get("name") or ""), focus=ptr or None)
        parent_ptr = str((stack.parent() or {}).get("ptr") or "")
        lra_nca.upsert_from_event(
            memory,
            ptr=ptr or f"ptr://cell/{kind}",
            kind=kind,
            energy=energy,
            theorem_ok=theorem_ok,
            tokens=tokens,
            parent_ptr=parent_ptr,
        )
        memory["_tape_window"] = tape.window()
        memory["_stack_top"] = stack.tops(3)
        memory["_stack"] = stack.to_dict()
        memory["_stack_walk"] = [
            {
                "frame_id": frame.get("frame_id"),
                "parent_id": frame.get("parent_id"),
                "ptr": frame.get("ptr"),
                "node": frame.get("node"),
                "child_ids": list(frame.get("child_ids") or []),
                "args": list((frame.get("locals") or {}).keys()),
            }
            for frame in stack.walk()
        ]
        tape.persist(memory)

    memory["_tape_window"] = tape.window()
    memory["_stack_top"] = stack.tops(3)
    memory["_stack"] = stack.to_dict()
    if depth == 0:
        try:
            import board_graph as lra_board

            lra_board.overlay_live_board(memory)
        except Exception:
            pass
    while counter[0] < max_steps:
        halt = lra_nca.should_halt(memory)
        if halt.get("halt"):
            trace.append({"depth": depth, "action": "nca_halt", **{k: halt[k] for k in ("n_issues", "n_pending_ops", "n_hot_tasks")}})
        if halt.get("budget_dead"):
            trace.append({"depth": depth, "action": "nca_budget", "budget_energy": halt.get("budget_energy")})
            lake.append({"name": record.get("name"), "skipped": "nca_budget", "round": counter[0]})
            break
        counter[0] += 1
        analysis = lra_rand.analyze_proof(record, tactics=body, model=model)
        intent = research(
            record,
            analysis,
            tactics=body,
            ledger=ledger,
            memory=memory,
            allow_families=allow_families,
            allow_skills=allow_skills,
            tree_node=node,
        )
        lra_bind.remember_research(
            memory,
            name=str(record.get("name") or ""),
            residuals=lra_port.analyze_residuals(body),
            unsafe=intent.get("residual_unsafe") or {},
            help_scores=intent.get("residual_help") or {},
            skill=str(intent.get("skill") or "keep"),
            compose=str(intent.get("compose") or "single"),
        )
        lra_bind.expand_skills_from_memory(
            memory, name=str(record.get("name") or ""), tactics=body
        )
        if ledger is not None:
            lra_nca.charge_budget(memory, ledger=ledger, event="jev")
        compose = str(intent.get("compose") or "single")
        nest_child = str(intent.get("nest_child") or "")
        tool_name = str(intent.get("tool_name") or "")
        trace.append(
            {
                "depth": depth,
                "node": node,
                "step": counter[0] - 1,
                "compose": compose,
                "nest_child": nest_child,
                "tool_name": tool_name,
                "skill": intent.get("skill"),
                "intent": intent.get("intent"),
            }
        )
        CONTROL = {
            "nest",
            "spawn",
            "analyze",
            "self_improve",
            "invoke_router",
            "return",
            "tick",
            "fork",
            "mutate",
            "hook",
            "call",
            "instruct",
            "heal",
        }
        if compose == "return":
            popped = stack.ret(
                {
                    "tactics": body,
                    "ok": True,
                    "node": node,
                    "observations": dict(memory.get("observations") or {}),
                    "n_steps": counter[0],
                }
            )
            tape.splice_return(popped.get("payload") or {}, ptr=str((popped.get("child") or {}).get("ptr") or ""), parent_frame=str((popped.get("parent") or {}).get("frame_id") or ""))
            _after("return", {"node": node}, ptr=str((popped.get("child") or {}).get("ptr") or ""))
            trace.append({"depth": depth, "action": "return", "node": node, "stack": popped.get("ok")})
            break
        if compose == "analyze":
            obs = lra_tools.run_tool(
                tool_name or nest_child or "decision_tree",
                tactics=body,
                memory=memory,
                problem=str(record.get("name") or ""),
                observations=memory.get("observations") or {},
            )
            memory.setdefault("observations", {})[str(obs.get("tool") or "analyze")] = obs
            _after("tool", {"tool": obs.get("tool"), "ok": obs.get("ok")}, ptr=f"ptr://tool/{obs.get('tool') or 'analyze'}")
            trace.append({"depth": depth, "action": "analyze", "tool": obs.get("tool"), "ok": obs.get("ok")})
            continue
        if compose == "self_improve":
            improved = lra_tools.self_improve(
                memory, name=str(record.get("name") or ""), tactics=body
            )
            memory.setdefault("observations", {})["self_improve"] = improved
            trace.append(
                {
                    "depth": depth,
                    "action": "self_improve",
                    "proposed": improved.get("proposed"),
                    "router": None,
                }
            )
            continue
        if compose in {"tick", "fork", "mutate", "hook"}:
            import typesafe_nca as lra_nca

            nca_key = {
                "tick": "nca_tick",
                "fork": "nca_fork",
                "mutate": "nca_mutate",
                "hook": "nca_hook",
            }[compose]
            extra: dict[str, Any] = {}
            if compose == "fork":
                extra = {
                    "record": record,
                    "tactics": body,
                    "args": args,
                    "memory": memory,
                    "ledger": ledger,
                    "rng": rng,
                    "model": model,
                    "restore": restore,
                    "depth": depth + 1,
                    "steps": counter,
                    "max_steps": max_steps,
                    "max_depth": max_depth,
                    "compile_one": compile_fn,
                    "research_fn": research,
                    "pick_fn": pick,
                    "router_fn": router_fn,
                    "problem": str(record.get("name") or ""),
                }
            elif compose == "hook":
                extra = {"path": nest_child or tool_name or "portable_rewrites.py"}
            payload = lra_nca.nca_tool(
                nca_key,
                memory=memory,
                tactics=body,
                problem=str(record.get("name") or ""),
                **extra,
            )
            memory.setdefault("observations", {})[nca_key] = payload
            if compose == "mutate" and isinstance((payload.get("applied") or {}).get("tactics"), str):
                body = str(payload["applied"]["tactics"]).strip("\n")
            _after(compose, payload, ptr=f"ptr://tool/nca_{compose}")
            trace.append({"depth": depth, "action": compose, "nca": payload})
            continue
        if compose == "heal":
            import nca_repair as lra_heal

            healed = lra_heal.heal(memory, ledger=ledger)
            memory.setdefault("observations", {})["nca_heal"] = healed
            _after("heal", healed, ptr="ptr://tool/nca_heal", energy=0.7 if healed.get("ok") else 0.3)
            trace.append({"depth": depth, "action": "heal", "applied": healed.get("applied"), "ok": healed.get("ok")})
            continue
        if compose == "instruct":
            import nca_program as lra_prog

            programmed = lra_prog.program_nca(
                memory,
                tactics=body,
                problem=str(record.get("name") or ""),
                llm="off",
                ledger=ledger,
                compile_fn=compile_fn,
                record=record,
                args=args,
                restore=restore,
            )
            memory.setdefault("observations", {})["nca_program"] = programmed
            before = body
            nxt = str((programmed.get("executed") or {}).get("tactics") or (programmed.get("program_state") or {}).get("tactics") or "")
            if nxt.strip():
                body = nxt.strip("\n")
            already_laked = any(
                str(op.get("op")) == "CALL"
                and str(op.get("ptr") or "").startswith("ptr://skill/")
                and op.get("ok")
                for op in ((programmed.get("executed") or {}).get("ran") or [])
            )
            if compile_fn is not None and body.strip("\n") != before.strip("\n") and not already_laked:
                accepted, rows = apply_lake_round(
                    record=record,
                    tactics=before,
                    analysis={"n_tokens": max(8, len(before.split()))},
                    drafts=[
                        {
                            "kind": "nca_instruct",
                            "tactics": body,
                            "family": "search_space",
                            "token_count": max(1, len(body.split())),
                        }
                    ],
                    intent={"skill": "nca_instruct", "compose": "single"},
                    ranked={"beam_kinds": ["nca_instruct"], "fired": False, "fired_leaves": []},
                    memory=memory,
                    args=args,
                    restore=restore,
                    round_i=counter[0] - 1,
                    compile_one=compile_fn,
                )
                lake.extend(rows)
                if accepted:
                    body = accepted.strip("\n")
            _after("instruct", programmed.get("program_state") or {}, ptr="ptr://tool/nca_program")
            trace.append({"depth": depth, "action": "instruct", "ops": (programmed.get("program_state") or {}).get("ops")})
            continue
        if compose == "invoke_router":
            action = None
            if router_fn is not None:
                action = router_fn(intent=intent, memory=memory, ledger=ledger)
            if isinstance(action, dict) and action.get("action"):
                import skill_improve_loop as lra_loop_sk

                applied = lra_loop_sk.apply_action(memory, action)
                trace.append(
                    {
                        "depth": depth,
                        "action": "invoke_router",
                        "router_action": action.get("action"),
                        "applied": applied,
                    }
                )
            else:
                improved = lra_tools.self_improve(
                    memory, name=str(record.get("name") or ""), tactics=body
                )
                trace.append(
                    {
                        "depth": depth,
                        "action": "invoke_router_fallback_self_improve",
                        "proposed": improved.get("proposed"),
                    }
                )
            continue
        if (intent.get("skip_lake") or compose == "keep") and compose not in CONTROL:
            lake.append(
                {
                    "name": record.get("name"),
                    "round": counter[0] - 1,
                    "skipped": "intent_minimal" if intent.get("skip_lake") else "compose_keep",
                    "depth": depth,
                    "node": node,
                }
            )
            break
        if compose == "call" or str(nest_child).startswith("ptr://"):
            ptr = lra_cs.coerce_ptr(nest_child or tool_name or node, tools=lra_tools.TOOL_CRITERIA)
            resolved = lra_cs.resolve_ptr(
                ptr,
                memory=memory,
                record=record,
                tools=lra_tools.TOOL_CRITERIA,
                subloops=lra_tools.SUBLOOPS,
            )
            if not resolved.get("ok"):
                _after("error", resolved, ptr=ptr, energy=0.2)
                trace.append({"depth": depth, "action": "call_fail", "ptr": ptr, "reason": resolved.get("reason")})
                continue
            pushed = stack.call(
                ptr,
                compose="call",
                node=str(resolved.get("name") or ""),
                locals_={
                    "tactics": body,
                    "problem": str(record.get("name") or ""),
                    "tape_window": tape.window(),
                },
                resolved=resolved,
            )
            if not pushed.get("ok"):
                _after("error", pushed, ptr=ptr, energy=0.2)
                continue
            child_args = dict(pushed.get("args") or {})
            lra_tape.populate_tape(
                tape,
                stack,
                tactics=body,
                problem=str(record.get("name") or ""),
                observations=memory.get("observations") or {},
                ptr=ptr,
            )
            child_payload: dict[str, Any] = {"ok": True, "ptr": ptr, "kind": resolved.get("kind"), "args": child_args}
            kind = str(resolved.get("kind") or "")
            if kind == "theorem":
                evaled = eval_theorem(
                    str(resolved.get("theorem") or resolved.get("name") or ""),
                    current=record,
                    tactics=str(child_args.get("tactics") or body),
                    compile_fn=compile_fn,
                    args=args,
                    restore=restore,
                    memory=memory,
                )
                child_payload.update(evaled)
                try:
                    import board_graph as lra_board

                    lra_board.credit_theorem(
                        memory,
                        str(evaled.get("name") or record.get("name") or ""),
                        theorem_ok=bool(evaled.get("theorem_ok")),
                        tokens=int(evaled.get("tokens") or 0),
                    )
                except Exception:
                    pass
                lake.append(
                    {
                        "name": evaled.get("name") or record.get("name"),
                        "kind": "ptr_theorem",
                        "ok": evaled.get("theorem_ok"),
                        "tokens": evaled.get("tokens"),
                        "round": counter[0] - 1,
                        "skipped": evaled.get("reason"),
                    }
                )
            elif kind == "tool":
                obs = lra_tools.run_tool(
                    str(child_args.get("tool") or resolved.get("tool") or ""),
                    tactics=str(child_args.get("tactics") or body),
                    memory=memory,
                    problem=str(child_args.get("problem") or record.get("name") or ""),
                )
                memory.setdefault("observations", {})[str(obs.get("tool") or "tool")] = obs
                child_payload["observations"] = {obs.get("tool"): obs}
            elif kind == "mcpplusplus":
                envelope = lra_tools.mcpplusplus_call(
                    str(child_args.get("mcpplusplus") or resolved.get("mcpplusplus") or "catalog"),
                    problem=str(child_args.get("problem") or record.get("name") or ""),
                    tactics=str(child_args.get("tactics") or body),
                )
                memory.setdefault("observations", {})["mcpplusplus"] = envelope
                child_payload["observations"] = {"mcpplusplus": envelope}
                child_payload["protocol"] = "MCP++"
                child_payload["energy"] = 0.6 if envelope.get("ok") else 0.2
            elif kind in {"goal", "subgoal", "task"}:
                import board_graph as lra_board

                payload = lra_board.board_payload(str(resolved.get("name") or ""), lra_board.load_lra_board())
                memory.setdefault("observations", {})["board"] = payload
                child_payload["observations"] = {"board": payload}
                child_payload["energy"] = 0.2 if payload.get("blocked") else 0.6
            elif kind == "codepath":
                import codepath_graph as lra_cp

                sliced = lra_cp.slice_cross_module(str(child_args.get("codepath") or resolved.get("codepath") or resolved.get("name") or ""))
                memory.setdefault("observations", {})["codepath"] = sliced
                child_payload["observations"] = {"codepath": sliced}
                child_payload["energy"] = 0.6 if sliced.get("ok") else 0.2
            elif kind == "module":
                hook = lra_nca.hook_and_eval(str(resolved.get("path") or "portable_rewrites.py"))
                memory.setdefault("observations", {})["hook"] = hook
                child_payload["observations"] = {"hook": hook}
            elif depth < max_depth:
                nested = inner_typesafe_walk(
                    record,
                    str(child_args.get("tactics") or body),
                    args=args,
                    memory=memory,
                    ledger=ledger,
                    rng=rng,
                    model=model,
                    restore=restore,
                    depth=depth + 1,
                    node=str(child_args.get("node") or resolved.get("name") or node),
                    allow_families=set(child_args.get("allow_families") or resolved.get("allow_families") or []) or allow_families,
                    allow_skills=set(child_args.get("allow_skills") or resolved.get("allow_skills") or []) or allow_skills,
                    steps=counter,
                    max_steps=max_steps,
                    max_depth=max_depth,
                    compile_one=compile_fn,
                    research_fn=research,
                    pick_fn=pick,
                    router_fn=router_fn,
                    tape=tape,
                    stack=stack,
                )
                lake.extend(list(nested.get("lake") or []))
                if nested.get("tactics"):
                    body = str(nested["tactics"]).strip("\n")
                child_payload.update(
                    {
                        "tactics": nested.get("tactics"),
                        "observations": nested.get("observations"),
                        "n_steps": nested.get("n_steps"),
                    }
                )
            popped = stack.ret(child_payload)
            tape.splice_return(
                popped.get("payload") or child_payload,
                ptr=ptr,
                parent_frame=str((popped.get("parent") or {}).get("frame_id") or ""),
            )
            _after(
                "call_return",
                child_payload,
                ptr=ptr,
                energy=float(child_payload.get("energy") or 0.5),
                theorem_ok=child_payload.get("theorem_ok"),
                tokens=int(child_payload.get("tokens") or 0),
            )
            trace.append({"depth": depth, "action": "call_return", "ptr": ptr, "kind": kind, "injected": True})
            continue
        tree = dict(intent.get("tree") or {})
        if compose in {"nest", "spawn"} and depth < max_depth:
            child = nest_child or ("skill_walk" if compose == "spawn" else "")
            nested: dict[str, Any] = {}
            if not child:
                nested = {}
            elif compose == "spawn" and child in lra_tools.SUBLOOPS and child not in tree:
                nested = lra_tools.spawn_subloop(
                    child,
                    record=record,
                    tactics=body,
                    args=args,
                    memory=memory,
                    ledger=ledger,
                    rng=rng,
                    model=model,
                    restore=restore,
                    depth=depth + 1,
                    node=child,
                    steps=counter,
                    max_steps=max_steps,
                    max_depth=max_depth,
                    compile_one=compile_fn,
                    research_fn=research,
                    pick_fn=pick,
                    router_fn=router_fn,
                )
            else:
                if child in tree:
                    child_fam: Optional[set[str]] = {child}
                    child_sk: Optional[set[str]] = None
                else:
                    child_fam = allow_families
                    child_sk = {child}
                nested = inner_typesafe_walk(
                    record,
                    body,
                    args=args,
                    memory=memory,
                    ledger=ledger,
                    rng=rng,
                    model=model,
                    restore=restore,
                    depth=depth + 1,
                    node=child,
                    allow_families=child_fam,
                    allow_skills=child_sk,
                    steps=counter,
                    max_steps=max_steps,
                    max_depth=max_depth,
                    compile_one=compile_fn,
                    research_fn=research,
                    pick_fn=pick,
                    router_fn=router_fn,
                    tape=tape,
                    stack=stack,
                )
            if nested:
                lake.extend(list(nested.get("lake") or []))
                if nested.get("tactics"):
                    body = str(nested["tactics"]).strip("\n")
                returns = memory.setdefault("subloop_returns", [])
                returns.append(
                    {
                        "name": child,
                        "ok": nested.get("ok", True),
                        "n_steps": nested.get("n_steps"),
                        "returned": True,
                    }
                )
                trace.append(
                    {
                        "depth": depth,
                        "action": "spawn_return" if compose == "spawn" else "nest_return",
                        "child": child,
                        "nested_trace": nested.get("trace") or [],
                    }
                )
                continue
        allow = set(allow_families or intent.get("allow_families") or [])
        drafts = lra_rand.random_drafts(
            body,
            rng,
            n=max(2, int(getattr(args, "drafts", 6) or 6)),
            families=analysis.get("families") or [],
            counts=analysis.get("counts"),
            name=str(record.get("name") or ""),
            memory=memory,
            allow_families=allow,
        )
        drafts = _restrict_drafts(
            drafts,
            skip_port=set(intent.get("skip_skills") or []),
            allow_skills=allow_skills,
        )
        if not drafts:
            if _no_drafts_flag(memory, record, "no_drafts_tree"):
                halt = lra_nca.should_halt(memory)
                if not halt.get("budget_dead") and not _no_drafts_flag(memory, record, "no_drafts_instructed"):
                    _set_no_drafts_flag(memory, record, "no_drafts_instructed")
                    import nca_program as lra_prog

                    programmed = lra_prog.program_nca(
                        memory,
                        tactics=body,
                        problem=str(record.get("name") or ""),
                        llm="off",
                        ledger=ledger,
                        compile_fn=compile_fn,
                        record=record,
                        args=args,
                        restore=restore,
                    )
                    nxt = str((programmed.get("executed") or {}).get("tactics") or "")
                    if nxt.strip():
                        body = nxt.strip("\n")
                    trace.append({"depth": depth, "action": "no_drafts_instruct", "ops": (programmed.get("executed") or {}).get("ran")})
                    continue
                lake.append(
                    {
                        "name": record.get("name"),
                        "round": counter[0] - 1,
                        "skipped": "no_drafts_after_self_improve",
                        "depth": depth,
                        "node": node,
                    }
                )
                break
            improved = lra_tools.self_improve(
                memory, name=str(record.get("name") or ""), tactics=body
            )
            tree_obs = lra_tools.run_tool(
                "decision_tree",
                tactics=body,
                memory=memory,
                problem=str(record.get("name") or ""),
                observations=memory.get("observations") or {},
            )
            _set_no_drafts_flag(memory, record, "no_drafts_tree")
            memory.setdefault("observations", {})["no_drafts_tree"] = tree_obs
            memory["observations"]["self_improve"] = improved
            ranked = {
                "skipped": True,
                "reason": "no_drafts_self_improve",
                "intent": intent,
                "jev_generated_lean": False,
                "arena_score": None,
            }
            lake.append(
                {
                    "name": record.get("name"),
                    "round": counter[0] - 1,
                    "skipped": "no_drafts_self_improve",
                    "depth": depth,
                    "node": node,
                    "proposed": improved.get("proposed"),
                }
            )
            trace.append({"depth": depth, "action": "no_drafts_self_improve", "proposed": improved.get("proposed")})
            continue
        ranked = pick(record, analysis, drafts, ledger=ledger, memory=memory)
        ranked["intent"] = intent
        if ledger is not None:
            lra_nca.charge_budget(memory, ledger=ledger, event="jev_pick")
        accepted, lake_step = apply_lake_round(
            record=record,
            tactics=body,
            analysis=analysis,
            drafts=drafts,
            intent=intent,
            ranked=ranked,
            memory=memory,
            args=args,
            restore=restore,
            round_i=counter[0] - 1,
            compile_one=compile_fn,
        )
        lake.extend(lake_step)
        ok_any = any(item.get("ok") for item in lake_step)
        _after(
            "lake",
            {"n": len(lake_step), "ok": ok_any},
            energy=0.7 if ok_any else 0.3,
            theorem_ok=ok_any,
            tokens=int(analysis.get("n_tokens") or 0),
        )
        if accepted:
            body = accepted.strip("\n")
            continue
        break
    tape.persist(memory)
    return {
        "tactics": body,
        "lake": lake,
        "ranked": ranked,
        "drafts": drafts,
        "analysis": analysis,
        "trace": trace,
        "n_steps": counter[0],
        "depth": depth,
        "node": node,
        "jev_generated_lean": False,
        "called_docker0": False,
        "returned": True,
        "observations": dict(memory.get("observations") or {}),
        "tape": tape.to_dict(),
        "stack": stack.to_dict(),
    }


def starting_tactics(record: Mapping[str, Any], *, out: Any = None, from_best: bool = False) -> str:
    """Keep-best body when --from-best, else frozen warmup tactics."""

    tactics = lra_fan.tactic_block(record)
    if not from_best or out is None:
        return tactics
    safe = str(record.get("name") or "canary").replace("/", "_")[:80]
    bests = sorted(
        Path(out).glob(f"random-best-{safe}-*.lean"),
        key=lambda path: int(path.stem.rsplit("-", 1)[-1])
        if path.stem.rsplit("-", 1)[-1].isdigit()
        else 10**9,
    )
    if bests:
        return bests[0].read_text(encoding="utf-8").strip("\n")
    if str(record.get("name") or "") == "Core.InitsUpdatesComm":
        cascade = Path(out) / "cascade-best-139.lean"
        if cascade.is_file():
            return cascade.read_text(encoding="utf-8").strip("\n")
    return tactics


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

    tactics = starting_tactics(
        record, out=getattr(args, "out", None), from_best=bool(getattr(args, "from_best", False))
    )
    clone = lra_kb.lra_cw.clone_dir(str(record["url"]), lra_rand.DEFAULT_STATE)
    dest = clone / lra_kb.lra_cw.source_relpath(record)
    restore = dest.read_bytes() if dest.is_file() else b""
    if not dest.is_file():
        analysis = lra_rand.analyze_proof(record, tactics=tactics, model=model)
        return {
            "analysis": {k: analysis[k] for k in analysis if k != "tactics"},
            "n_drafts": 0,
            "draft_kinds": [],
            "ranked": {},
            "lake": [{"name": record.get("name"), "skipped": "no_clone"}],
            "trace": [],
            "clone_exists": False,
        }
    max_steps = max(int(getattr(args, "rounds", 1) or 1), lra_rand.INNER_MAX_STEPS)
    walked = inner_typesafe_walk(
        record,
        tactics,
        args=args,
        memory=memory,
        ledger=ledger,
        rng=rng,
        model=model,
        restore=restore,
        max_steps=max_steps,
        max_depth=int(getattr(args, "nest_depth", lra_rand.NEST_MAX_DEPTH) or lra_rand.NEST_MAX_DEPTH),
        compile_one=compile_one,
        research_fn=research_fn,
        pick_fn=pick_fn,
        router_fn=router_fn,
    )
    if dest.is_file() and restore:
        dest.write_bytes(restore)
    analysis = walked.get("analysis") or {}
    drafts = list(walked.get("drafts") or [])
    return {
        "analysis": {k: analysis[k] for k in analysis if k != "tactics"} if analysis else {},
        "n_drafts": len(drafts),
        "draft_kinds": [item.get("kind") for item in drafts],
        "ranked": walked.get("ranked") or {},
        "lake": walked.get("lake") or [],
        "trace": walked.get("trace") or [],
        "clone_exists": True,
        "tactics": walked.get("tactics"),
        "n_steps": walked.get("n_steps"),
        "returned": True,
        "observations": walked.get("observations") or {},
    }


def _skill_walk_entry(**kwargs: Any) -> dict[str, Any]:
    record = kwargs.pop("record")
    tactics = str(kwargs.pop("tactics", "") or "")
    return inner_typesafe_walk(record, tactics, **kwargs)


lra_tools.register_subloop("skill_walk", _skill_walk_entry)


def _eval_theorem_entry(**kwargs: Any) -> dict[str, Any]:
    record = kwargs.get("record") or {}
    return eval_theorem(
        str(kwargs.get("name") or kwargs.get("theorem") or record.get("name") or ""),
        current=record if isinstance(record, dict) else {},
        tactics=str(kwargs.get("tactics") or ""),
        compile_fn=kwargs.get("compile_one") or kwargs.get("compile_fn"),
        args=kwargs.get("args"),
        restore=kwargs.get("restore") or b"",
        memory=kwargs.get("memory") if isinstance(kwargs.get("memory"), dict) else None,
    )


lra_tools.register_subloop("eval_theorem", _eval_theorem_entry)

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
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping, Optional

HERE = Path(__file__).resolve().parent
PAPER_ROOT = HERE.parent
OUT_DEFAULT = PAPER_ROOT / "evidence" / "canaries"
PROTOCOL = "LRA/v1"
PR_ID = "PR-9h"
ACTIONS = ("run", "nest_inner", "mint", "skip_stem", "install_fold", "stop")
KEEP_WORDS = ("intro", "intros", "constructor", "grind", "induction", "exact", "use")
_JSON_OBJ = re.compile(r"\{.*\}", re.DOTALL)
ROUTER_MAX_NEW = 256
ROUTER_TIMEOUT = 90.0

if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
import binder_use as lra_bind  # noqa: E402
import random_canary as lra_rand  # noqa: E402
import track1_ledger as lra_t1  # noqa: E402
import typesafe_inner as lra_inner  # noqa: E402

SMALL_NAMES = (
    "CallElimCorrect.substOldPostSubset",
    "CallElimCorrect.extractedOldExprInVars",
    "Core.InitsUpdatesComm",
    "Cslib.LambdaCalculus.LocallyNameless.Fsub.Typing.progress",
    "Cslib.SKI.parallelReduction_diamond",
    "Cslib.CCS.bisimilarity_congr_choice",
)


def keep_best_board(out: Path) -> dict[str, int]:
    """Shortest random-best / cascade-best token count per small canary."""

    board: dict[str, int] = {}
    latest = out / "random-canary-latest.json"
    if latest.is_file():
        try:
            payload = json.loads(latest.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            payload = {}
        for row in payload.get("canaries") or []:
            name = str((row.get("analysis") or {}).get("name") or "")
            tok = (row.get("analysis") or {}).get("n_tokens")
            if name in SMALL_NAMES and tok:
                board[name] = int(tok)
    for name in SMALL_NAMES:
        safe = name.replace("/", "_")[:80]
        bests = sorted(
            out.glob(f"random-best-{safe}-*.lean"),
            key=lambda path: int(path.stem.rsplit("-", 1)[-1])
            if path.stem.rsplit("-", 1)[-1].isdigit()
            else 10**9,
        )
        if bests:
            file_tok = int(bests[0].stem.rsplit("-", 1)[-1])
            board[name] = min(int(board.get(name) or file_tok), file_tok)
            continue
        if name == "Core.InitsUpdatesComm" and (out / "cascade-best-139.lean").is_file():
            board[name] = min(int(board.get(name) or 139), 139)
    return board


def board_total(board: Mapping[str, int]) -> int:
    return int(sum(board.values()))


def parse_action(text: str) -> dict[str, Any]:
    """First JSON object in grok text; fail closed to action=run."""

    match = _JSON_OBJ.search(str(text or ""))
    if not match:
        return {"action": "run", "reason": "no_json"}
    try:
        raw = json.loads(match.group(0))
    except json.JSONDecodeError:
        return {"action": "run", "reason": "bad_json"}
    if not isinstance(raw, dict):
        return {"action": "run", "reason": "not_object"}
    action = str(raw.get("action") or "run").strip()
    if action not in ACTIONS:
        return {"action": "run", "reason": "unknown_action"}
    out = {"action": action, "reason": str(raw.get("reason") or "router")}
    for key in ("stem", "name", "old", "new", "family"):
        if key in raw:
            out[key] = str(raw.get(key) or "")
    if "keep" in raw and isinstance(raw["keep"], list):
        out["keep"] = [str(item) for item in raw["keep"]]
    if "count" in raw:
        try:
            out["count"] = int(raw["count"])
        except (TypeError, ValueError):
            out["count"] = 1
    return out


def deterministic_route(
    *,
    gaps: list[dict[str, Any]],
    last_lake: list[dict[str, Any]],
    stalled: bool,
) -> dict[str, Any]:
    """Closed-vocab next action from AutoResearch gaps + last lake (no grok)."""

    failed = [
        row
        for row in last_lake
        if row.get("ok") is False and str(row.get("kind") or "").startswith("port_")
    ]
    if failed:
        kind = str(failed[0].get("kind") or "")
        stem = kind[len("port_") :] if kind.startswith("port_") else kind
        return {
            "action": "skip_stem",
            "stem": stem.split("_pipeline")[0],
            "name": str(failed[0].get("name") or ""),
            "reason": "lake_failed_port",
        }
    for gap in gaps:
        mints = list((gap.get("proposed") or {}).get("mint") or gap.get("keep_structure") or [])
        if mints:
            return {
                "action": "mint",
                "stem": str(mints[0]),
                "name": str(gap.get("name") or ""),
                "reason": "autoresearch_mint",
            }
    if last_lake and all(str(row.get("skipped") or "") == "nca_budget" for row in last_lake):
        return {"action": "stop", "reason": "nca_budget"}
    if stalled:
        return {"action": "stop", "reason": "no_token_cut"}
    return {"action": "nest_inner", "reason": "continue_typesafe"}


def nca_status_for_router(memory: Optional[Mapping[str, Any]] = None) -> dict[str, Any]:
    """Compact NCA snapshot for the outer Grok prompt."""

    mem = dict(memory or {})
    try:
        import typesafe_nca as lra_nca
        import board_graph as lra_board

        halt = lra_nca.should_halt(mem)
        window = lra_board.board_window(mem)
    except Exception:
        halt, window = {}, []
    budget = (((mem.get("nca") or {}).get("grid") or {}).get("ptr://tool/budget") or {})
    return {
        "halt": bool(halt.get("halt")),
        "budget_dead": bool(halt.get("budget_dead")),
        "budget_energy": halt.get("budget_energy", budget.get("energy")),
        "n_hot_tasks": halt.get("n_hot_tasks"),
        "board_window": window[:6],
    }


def router_prompt(
    board: Mapping[str, int],
    gaps: list[dict[str, Any]],
    last_lake: list[dict[str, Any]],
    *,
    nca_status: Optional[Mapping[str, Any]] = None,
) -> str:
    compact_gaps = [
        {
            "name": item.get("name"),
            "proposed": item.get("proposed"),
            "keep_structure": item.get("keep_structure"),
            "top_help": (item.get("top_help") or [])[:2],
        }
        for item in gaps
    ]
    compact_lake = [
        {
            "name": row.get("name"),
            "kind": row.get("kind"),
            "ok": row.get("ok"),
            "tokens": row.get("tokens"),
            "skipped": row.get("skipped"),
            "error_class": row.get("error_class"),
        }
        for row in last_lake[:12]
    ]
    return (
        "You are the OUTER Grok loop. Do not write Lean. TypeSafe is the INNER loop.\n"
        "Reply with one JSON object only, keys: action, stem, name, old, new, keep, reason.\n"
        f"action must be one of: {', '.join(ACTIONS)}.\n"
        "nest_inner: enter the TypeSafe inner loop, which keep-loops and recursively nests skill decision-tree children.\n"
        "run: same as nest_inner (TypeSafe still nests).\n"
        "install_fold: literal old→new substring fold that keeps intro/constructor/grind/exact/use.\n"
        "skip_stem: ban a port_ skill that lake-failed.\n"
        "mint: enable a keep-structure stem already in the harness.\n"
        "stop: no remaining lake-valid cut. If nca.halt or nca.budget_dead is true, action must be stop.\n"
        f"keep_best_tokens={json.dumps(dict(board), sort_keys=True)}\n"
        f"total={board_total(board)}\n"
        f"gaps={json.dumps(compact_gaps, sort_keys=True)}\n"
        f"last_lake={json.dumps(compact_lake, sort_keys=True)}\n"
        f"nca={json.dumps(dict(nca_status or {}), sort_keys=True)}\n"
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

    nca = nca_status_for_router(memory)
    if nca.get("budget_dead"):
        return {"action": "stop", "reason": "nca_budget", "router": "nca"}
    if nca.get("halt"):
        return {"action": "stop", "reason": "nca_halt", "router": "nca"}
    fallback = deterministic_route(gaps=gaps, last_lake=last_lake, stalled=stalled)
    if not llm:
        fallback["router"] = "deterministic"
        return fallback
    prompt = router_prompt(board, gaps, last_lake, nca_status=nca)
    try:
        text, _identity, _line = lra_t1.generate_grok(
            prompt,
            ledger,
            max_new_tokens=ROUTER_MAX_NEW,
            timeout=ROUTER_TIMEOUT,
            generate=generate,
            fixture=generate is not None,
        )
    except Exception as exc:
        fallback["router"] = "llm_router_error"
        fallback["error"] = str(exc)[:240]
        return fallback
    action = parse_action(text)
    action["router"] = "llm_router"
    action["raw_head"] = str(text)[:240]
    if memory is not None and isinstance(memory, dict):
        try:
            import typesafe_nca as lra_nca

            lra_nca.charge_budget(memory, ledger=ledger, event="grok")
        except Exception:
            pass
    return action


def apply_action(memory: dict[str, Any], action: Mapping[str, Any]) -> dict[str, Any]:
    """Mutate memory from a closed action. No Python exec."""

    kind = str(action.get("action") or "run")
    if kind == "skip_stem":
        stem = str(action.get("stem") or "")
        name = str(action.get("name") or "")
        if not stem:
            return {"ok": False, "reason": "no_stem"}
        key = f"{name}::port_{stem}" if name else f"*::port_{stem}"
        blacklist = memory.setdefault("blacklist", [])
        if key not in blacklist:
            blacklist.append(key)
        return {"ok": True, "applied": "skip_stem", "key": key}
    if kind == "mint":
        stem = str(action.get("stem") or "")
        name = str(action.get("name") or "")
        if not stem:
            return {"ok": False, "reason": "no_stem"}
        memory.setdefault("expanded", []).append(
            {
                "name": name,
                "notes": [{"action": "keep_structure", "mint": [stem], "source": "loop"}],
            }
        )
        return {"ok": True, "applied": "mint", "stem": stem}
    if kind == "install_fold":
        installed = lra_bind.install_memory_skill(memory, action)
        return {"ok": bool(installed.get("ok")), **installed}
    return {"ok": True, "applied": kind}


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
    return argparse.Namespace(
        live=True,
        all_small=True,
        from_best=True,
        rounds=int(rounds),
        lake_top=int(lake_top),
        drafts=int(drafts),
        timeout=float(timeout),
        init_139=True,
        seed=int(seed),
        k=lra_rand.DEFAULT_K,
        out=out,
        include_inits=False,
        quiet=True,
        nest_depth=int(nest_depth),
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
    return {
        "ok": (
            parsed.get("action") == "install_fold"
            and installed.get("ok") is True
            and fold_ok
            and skip.get("ok") is True
            and det.get("action") == "mint"
            and budget_stop.get("action") == "stop"
            and budget_stop.get("reason") == "nca_budget"
            and board_total(board) == 139
            and seeded.get("campaign_write") is False
            and lra_t1.FAIL_CLOSED_KWARGS.get("provider") == "grok"
            and lra_t1.FAIL_CLOSED_KWARGS.get("allow_local_fallback") is False
        ),
        "called_docker0": False,
        "arena_score": None,
        "official_track2": False,
        "router": "ipfs_accelerate_py.llm_router.generate_text",
        "jev_writes_lean": False,
        "grok_writes_lean": False,
    }


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
) -> dict[str, Any]:
    """OUTER Grok (llm_router). INNER TypeSafe keep-loop + recursive skill-tree nests."""

    memory = memory if memory is not None else lra_bind.load_memory()
    try:
        import board_graph as lra_board_seed

        lra_board_seed.seed_nca_from_board(memory)
        lra_board_seed.overlay_live_board(memory)
        try:
            lra_board_seed.seed_keepbest_theorems(
                memory,
                keep_best_board(out),
                warmup=lra_board_seed.warmup_token_map(),
            )
        except Exception:
            pass
    except Exception:
        pass
    ledger = lra_t1.ProblemLedger(
        name="warmup#skill-improve-loop",
        max_jev_calls=max(8, 6 * int(rounds) * int(outer) * 3 + 2),
        max_grok_calls=max(1, int(outer) if llm else 0),
        max_mistral_calls=0,
    )
    inner = run_inner or lra_rand.run_live
    history: list[dict[str, Any]] = []
    board = keep_best_board(out)
    best_total = board_total(board)
    stalled_rounds = 0
    stop_reason = ""
    last_lake: list[dict[str, Any]] = []
    gaps = lra_bind.skill_gap_report(memory)
    nest_depth = max(1, int(lra_rand.NEST_MAX_DEPTH))
    for step in range(max(1, int(outer))):
        # OUTER: Grok / llm_router. INNER: TypeSafe nested skill-tree walk.
        action = route_next_action(
            board=board,
            gaps=gaps,
            last_lake=last_lake,
            stalled=stalled_rounds >= 2,
            llm=True if llm else False,
            ledger=ledger,
            generate=generate,
            memory=memory,
        )
        applied = apply_action(memory, action)
        if persist_memory:
            lra_bind.save_memory(memory)
        payload: dict[str, Any] = {}
        traces: list[Any] = []
        if str(action.get("action") or "") != "stop":
            (memory.get("nca") or {}).pop("overlay_done", None)
            payload = inner(
                canary_args(
                    out=out,
                    rounds=rounds,
                    lake_top=lake_top,
                    drafts=drafts,
                    timeout=timeout,
                    seed=seed + step,
                    nest_depth=nest_depth,
                )
            )
            gaps = list(payload.get("skill_analysis") or lra_bind.skill_gap_report(memory))
            last_lake = list(payload.get("lake") or [])
            traces = [row.get("trace") for row in payload.get("canaries") or [] if row.get("trace")]
        board = keep_best_board(out)
        total = board_total(board)
        improved = total < best_total and total > 0
        if improved:
            best_total = total
            stalled_rounds = 0
        else:
            stalled_rounds += 1
        row = {
            "step": step,
            "outer": "grok" if llm else "deterministic",
            "inner": "typesafe_nested",
            "board": dict(board),
            "total": total,
            "improved": improved,
            "n_lake": len(last_lake),
            "n_ok": sum(1 for item in last_lake if item.get("ok")),
            "action": action,
            "applied": applied,
            "n_traces": len(traces),
            "max_trace_depth": max(
                (
                    int(ev.get("depth") or 0)
                    for tr in traces
                    for ev in lra_inner.flatten_trace(list(tr or []))
                ),
                default=0,
            ),
            "jev_calls": (payload.get("ledger") or {}).get("jev_calls"),
        }
        history.append(row)
        if action.get("action") == "stop" or applied.get("applied") == "stop":
            stop_reason = str(action.get("reason") or "stop")
            break
        if ledger.hard_stopped:
            stop_reason = "ledger_hard_stop"
            break
        if stalled_rounds >= 2:
            stop_reason = "no_token_cut"
            break
        try:
            import typesafe_nca as lra_nca_halt

            halt = lra_nca_halt.should_halt(memory)
            row["nca_halt"] = halt
            if halt.get("budget_dead"):
                stop_reason = "nca_budget"
                break
            if halt.get("halt"):
                stop_reason = "nca_halt"
                break
        except Exception:
            pass
    mem_path = lra_bind.save_memory(memory) if persist_memory else lra_bind.MEMORY_DEFAULT
    return {
        "schema": "lra-skill-improve-loop/v1",
        "protocol": PROTOCOL,
        "pr_id": PR_ID,
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "outer": int(outer),
        "llm": bool(llm),
        "outer": "grok",
        "inner": "typesafe_nested",
        "router": "ipfs_accelerate_py.llm_router.generate_text" if llm else "deterministic",
        "history": history,
        "board": dict(keep_best_board(out)),
        "total": board_total(keep_best_board(out)),
        "best_total": best_total,
        "stop_reason": stop_reason,
        "memory_path": str(mem_path),
        "memory_skills": list(memory.get("skills") or []),
        "called_docker0": False,
        "official_track2": False,
        "arena_score": None,
        "jev_writes_lean": False,
        "grok_writes_lean": False,
        "ledger": ledger.as_dict() if hasattr(ledger, "as_dict") else {"grok_calls": ledger.grok_calls},
    }


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
        payload = self_check()
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0 if payload["ok"] else 1
    payload = run_loop(
        outer=max(1, int(args.outer)),
        llm=args.llm == "on",
        out=args.out,
        rounds=max(1, int(args.rounds)),
        lake_top=int(args.lake_top),
        drafts=int(args.drafts),
        timeout=float(args.timeout),
        seed=int(args.seed),
    )
    args.out.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    text = json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n"
    (args.out / f"skill-improve-loop-{stamp}.json").write_text(text)
    (args.out / "skill-improve-loop-latest.json").write_text(text)
    print(json.dumps(payload, indent=2, sort_keys=True, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

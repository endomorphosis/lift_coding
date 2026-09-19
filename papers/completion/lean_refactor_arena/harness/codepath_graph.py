#!/usr/bin/env python3
"""Allowlisted code-path slices for the NCA (ids/spans, no source bodies).

Roots: LRA harness and ipfs_accelerate_py. Campaign DuckDB is never opened.
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path
from typing import Any, Optional

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
import _jevops_path  # noqa: E402,F401
PAPER_ROOT = HERE.parent
ACCEL = Path("/home/barberb/lift_coding/external/ipfs_accelerate/ipfs_accelerate_py")
SIDECAR = PAPER_ROOT / "evidence" / "canaries" / "nca-ast-sidecar.json"
SIDECAR_DUCKDB = PAPER_ROOT / "evidence" / "canaries" / "nca-ast.duckdb"
MAX_NEIGHBORS = 12
_CROSS: dict[str, Any] | None = None
_HARNESS_CROSS: dict[str, Any] | None = None
INSPECT_ONLY_MARKERS = ("generate_text", "docker0", "leanstral_local", "172.17")


def is_inspect_only(name: str) -> bool:
    from jevops.outer import contains_any

    if contains_any(name, INSPECT_ONLY_MARKERS):
        return True
    path = resolve_codepath(name)
    if path is None or not path.is_file():
        return False
    try:
        head = path.read_text(encoding="utf-8", errors="ignore")[:8000]
    except OSError:
        return False
    return contains_any(head, ("172.17.0.1",))


def _roots() -> tuple[Path, ...]:
    roots = [HERE.resolve(), PAPER_ROOT.resolve()]
    if ACCEL.is_dir():
        roots.append(ACCEL.resolve())
    return tuple(roots)


def resolve_codepath(name: str) -> Optional[Path]:
    raw = str(name or "").strip().replace("ptr://codepath/", "")
    if not raw or ".." in raw or raw.startswith("/"):
        return None
    # harness.portable_rewrites:fold_hoist → portable_rewrites.py
    module = raw.split(":")[0]
    rel = module.replace("harness.", "").replace(".", "/")
    candidates = [
        HERE / f"{Path(rel).name}.py" if "/" not in rel.replace("harness/", "") else HERE / Path(rel).name,
        HERE / Path(rel).with_suffix(".py").name,
        HERE / f"{rel.split('/')[-1]}.py",
        ACCEL / Path(*rel.split("/")).with_suffix(".py"),
    ]
    if rel.endswith(".py"):
        candidates.append(HERE / Path(rel).name)
        candidates.append(ACCEL / rel)
    from jevops.nca import first_existing_file

    return first_existing_file(candidates, roots=_roots())


def slice_codepath(name: str) -> dict[str, Any]:
    """Callers/callees-style slice from Python AST. No source bodies."""

    path = resolve_codepath(name)
    if path is None:
        return {"ok": False, "reason": "codepath_not_allowed", "name": name, "called_docker0": False, "inspect_only": is_inspect_only(name)}
    symbol = ""
    if ":" in str(name):
        symbol = str(name).rsplit(":", 1)[-1]
    try:
        from jevops.nca import function_call_map

        defs, calls_by = function_call_map(path.read_text(encoding="utf-8"))
    except (OSError, SyntaxError) as exc:
        return {"ok": False, "reason": "parse_failed", "error": str(exc)[:160], "called_docker0": False}
    focus = symbol if symbol in calls_by or symbol in defs else (defs[0] if defs else "")
    callees = (calls_by.get(focus) or [])[:MAX_NEIGHBORS]
    callers = [fn for fn, kids in calls_by.items() if focus and focus in kids][:MAX_NEIGHBORS]
    return {
        "ok": True,
        "path": path.name,
        "symbol": focus,
        "definitions": defs[:40],
        "callees": callees,
        "callers": callers,
        "complete": True,
        "source_bodies": False,
        "called_docker0": False,
        "campaign_write": False,
        "inspect_only": is_inspect_only(name),
        "invoked": False if is_inspect_only(name) else True,
    }


def _iter_allowlisted_py() -> list[Path]:
    from jevops.outer import existing_files

    files = sorted(HERE.glob("*.py"))[:40]
    files.extend(
        existing_files(
            (
                ACCEL / "llm_router.py",
                ACCEL / "agent_supervisor" / "analysis" / "program_graph_queries.py",
                ACCEL / "agent_supervisor" / "analysis" / "duckdb_ast_index.py",
                ACCEL / "agent_supervisor" / "task_sources" / "database_task_source.py",
            )
        )
    )
    return files


def build_sidecar_index(*, root: Optional[Path] = None, write: bool = True) -> dict[str, Any]:
    """JSON AST sidecar of harness (+ allowlisted) files. Never campaign DuckDB."""

    from jevops.nca import sidecar_files

    base = root or HERE
    files_payload = sidecar_files(sorted(base.glob("*.py")), cap_files=80, cap_symbols=80)
    payload = {
        "schema": "lra-nca-ast-sidecar/v1",
        "n_files": len(files_payload),
        "files": files_payload,
        "campaign_write": False,
        "called_docker0": False,
        "control_duckdb": False,
    }
    if write:
        from jevops.outer import write_json

        write_json(SIDECAR, payload)
        payload["path"] = str(SIDECAR)
    return payload


def build_sidecar_duckdb(*, path: Optional[Path] = None, refresh: bool = True) -> dict[str, Any]:
    """Symbols+calls DuckDB next to evidence/. Refuses campaign control.duckdb."""

    from jevops.outer import path_refused, try_import

    dest = Path(path or SIDECAR_DUCKDB)
    if path_refused(dest, names=("control.duckdb",), needles=("control.duckdb",)):
        return {"ok": False, "reason": "campaign_db_refused", "control_duckdb": True, "called_docker0": False}
    duckdb = try_import("duckdb")
    if duckdb is None:
        return {"ok": False, "reason": "duckdb_unavailable", "control_duckdb": False, "called_docker0": False}
    dest.parent.mkdir(parents=True, exist_ok=True)
    graph = harness_call_graph(refresh=refresh)
    con = duckdb.connect(str(dest))
    try:
        con.execute(
            "CREATE TABLE IF NOT EXISTS symbols (qualified_name VARCHAR, path VARCHAR, symbol_kind VARCHAR)"
        )
        con.execute("CREATE TABLE IF NOT EXISTS calls (caller VARCHAR, callee VARCHAR, path VARCHAR)")
        con.execute("DELETE FROM symbols")
        con.execute("DELETE FROM calls")
        for _bare, qnames in (graph.get("defs") or {}).items():
            for qname in qnames:
                con.execute(
                    "INSERT INTO symbols VALUES (?, ?, ?)",
                    [qname, f"{str(qname).split(':', 1)[0]}.py", "function"],
                )
        for caller, callees in (graph.get("calls") or {}).items():
            for callee in callees:
                con.execute(
                    "INSERT INTO calls VALUES (?, ?, ?)",
                    [caller, callee, f"{str(caller).split(':', 1)[0]}.py"],
                )
        n_sym = int(con.execute("SELECT COUNT(*) FROM symbols").fetchone()[0])
        n_calls = int(con.execute("SELECT COUNT(*) FROM calls").fetchone()[0])
    finally:
        con.close()
    return {
        "ok": True,
        "n_symbols": n_sym,
        "n_calls": n_calls,
        "path": str(dest),
        "control_duckdb": False,
        "called_docker0": False,
        "campaign_write": False,
    }


def query_sidecar_duckdb(query: str, *, db_path: Optional[Path] = None) -> list[dict[str, Any]]:
    from jevops.outer import query_engine

    needle = f"%{str(query or '').casefold()}%"
    return query_engine(
        Path(db_path or SIDECAR_DUCKDB),
        "SELECT qualified_name, path, symbol_kind FROM symbols "
        "WHERE lower(CAST(qualified_name AS VARCHAR)) LIKE ? LIMIT 20",
        [needle],
        refuse_names=("control.duckdb",),
        row_fn=lambda row: (
            {
                "symbol": str(row[0]),
                "path": str(row[1] or ""),
                "kind": str(row[2] or ""),
                "source": "sidecar_duckdb",
            }
            if row and row[0]
            else None
        ),
    )


def query_calls_duckdb(
    symbol: str,
    *,
    db_path: Optional[Path] = None,
    direction: str = "callees",
) -> list[str]:
    from jevops.outer import query_engine, without_prefix

    name = without_prefix(str(symbol or ""), "ptr://codepath/")
    column = "caller" if direction == "callers" else "callee"
    match_on = "callee" if direction == "callers" else "caller"
    return query_engine(
        Path(db_path or SIDECAR_DUCKDB),
        f"SELECT {column} FROM calls WHERE {match_on} = ? OR {match_on} LIKE ? LIMIT 12",
        [name, f"%:{name.rsplit(':', 1)[-1]}"],
        refuse_names=("control.duckdb",),
        row_fn=lambda row: str(row[0]) if row and row[0] else None,
    )


def harness_call_graph(*, refresh: bool = False) -> dict[str, Any]:
    """Call graph over harness/*.py only (no accelerate parse)."""

    global _HARNESS_CROSS
    if _HARNESS_CROSS is not None and not refresh:
        return _HARNESS_CROSS
    try:
        from jevops.nca import call_graph_from_paths

        _HARNESS_CROSS = call_graph_from_paths(
            sorted(HERE.glob("*.py")),
            cap_files=40,
            cap_neighbors=MAX_NEIGHBORS,
        )
    except Exception:
        _HARNESS_CROSS = {"defs": {}, "calls": {}, "n_defs": 0}
    return _HARNESS_CROSS


def seed_nca_call_edges(memory: dict[str, Any], *, db_path: Optional[Path] = None, limit: int = 48) -> dict[str, Any]:
    """Attach caller→callee pairs as NCA board_edges. DuckDB sidecar or harness AST."""

    from jevops.nca import append_board_edges
    from jevops.outer import path_refused

    dest = Path(db_path or SIDECAR_DUCKDB)
    if path_refused(dest, names=("control.duckdb",)):
        return {"ok": False, "reason": "campaign_db_refused", "n_edges": 0, "control_duckdb": True}
    from jevops.outer import query_engine

    rows: list[tuple[str, str]] = []
    source = "harness_ast"
    fetched = query_engine(
        dest,
        "SELECT caller, callee FROM calls LIMIT ?",
        [int(limit)],
        refuse_names=("control.duckdb",),
        row_fn=lambda row: (str(row[0]), str(row[1])) if row and row[0] and row[1] else None,
    )
    if fetched:
        rows = fetched
        source = "sidecar_duckdb"
    if not rows:
        graph = harness_call_graph()
        added_pairs = 0
        for caller, callees in (graph.get("calls") or {}).items():
            for callee in callees:
                rows.append((str(caller), str(callee)))
                added_pairs += 1
                if added_pairs >= int(limit):
                    break
            if added_pairs >= int(limit):
                break
        source = "harness_ast"
    added = append_board_edges(memory, rows, limit=limit)
    return {"ok": True, "n_edges": added, "source": source, "control_duckdb": False, "called_docker0": False}


def query_sidecar(query: str, *, payload: Optional[dict[str, Any]] = None) -> list[dict[str, Any]]:
    from jevops.nca import query_sidecar_symbols

    from jevops.outer import load_json_object

    data = payload
    if data is None and SIDECAR.is_file():
        data = load_json_object(SIDECAR)
    if not data:
        data = build_sidecar_index(write=False)
    return query_sidecar_symbols(data.get("files") or [], query, limit=24)


def allowlist_call_graph(*, refresh: bool = False) -> dict[str, Any]:
    """Cross-module name→qualified-def graph on allowlisted roots."""

    global _CROSS
    if _CROSS is not None and not refresh:
        return _CROSS
    from jevops.nca import call_graph_from_paths

    _CROSS = call_graph_from_paths(_iter_allowlisted_py(), cap_neighbors=MAX_NEIGHBORS)
    return _CROSS


def slice_cross_module(name: str, *, db_path: Optional[Path] = None) -> dict[str, Any]:
    """Callers/callees across allowlisted modules. Ids only; no source bodies."""

    if is_inspect_only(name):
        sliced = slice_codepath(name)
        sliced["cross_module"] = False
        return sliced
    from jevops.nca import first_matching_symbol

    raw_name = str(name or "").replace("ptr://codepath/", "")
    db_hits = query_sidecar_duckdb(raw_name.rsplit(":", 1)[-1], db_path=db_path)
    q_db = first_matching_symbol(db_hits, raw_name)
    if q_db:
        db_callees = query_calls_duckdb(q_db, db_path=db_path, direction="callees")
        db_callers = query_calls_duckdb(q_db, db_path=db_path, direction="callers")
        if db_callees or db_callers:
            return {
                "ok": True,
                "symbol": q_db,
                "callees": db_callees,
                "callers": db_callers,
                "cross_module": any(":" in item and item.split(":")[0] != q_db.split(":")[0] for item in db_callees + db_callers),
                "source": "sidecar_duckdb",
                "source_bodies": False,
                "called_docker0": False,
                "campaign_write": False,
                "complete": True,
            }
    from jevops.nca import pick_qualified

    graph = allowlist_call_graph()
    qname = pick_qualified(
        name,
        graph.get("defs") or {},
        graph.get("calls") or {},
        strip_prefixes=("harness.",),
    )
    if not qname:
        local = slice_codepath(name)
        local["cross_module"] = False
        return local
    calls = graph.get("calls") or {}
    callees = list(calls.get(qname) or [])[:MAX_NEIGHBORS]
    callers = [fn for fn, kids in calls.items() if qname in kids or qname.rsplit(":", 1)[-1] in kids][:MAX_NEIGHBORS]
    cross = any(":" in item and not item.startswith(qname.split(":")[0] + ":") for item in callees + callers)
    return {
        "ok": True,
        "symbol": qname,
        "callees": callees,
        "callers": callers,
        "cross_module": bool(cross) or any(":" in item for item in callees),
        "n_defs": graph.get("n_defs"),
        "source_bodies": False,
        "called_docker0": False,
        "campaign_write": False,
        "complete": True,
    }

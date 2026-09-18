#!/usr/bin/env python3
"""Allowlisted code-path slices for the NCA (ids/spans, no source bodies).

Roots: LRA harness and ipfs_accelerate_py. Campaign DuckDB is never opened.
"""
from __future__ import annotations

import ast
from pathlib import Path
from typing import Any, Optional

HERE = Path(__file__).resolve().parent
PAPER_ROOT = HERE.parent
ACCEL = Path("/home/barberb/lift_coding/external/ipfs_accelerate/ipfs_accelerate_py")
SIDECAR = PAPER_ROOT / "evidence" / "canaries" / "nca-ast-sidecar.json"
SIDECAR_DUCKDB = PAPER_ROOT / "evidence" / "canaries" / "nca-ast.duckdb"
MAX_NEIGHBORS = 12
_CROSS: dict[str, Any] | None = None
_HARNESS_CROSS: dict[str, Any] | None = None
INSPECT_ONLY_MARKERS = ("generate_text", "docker0", "leanstral_local", "172.17")


def is_inspect_only(name: str) -> bool:
    blob = str(name or "").casefold()
    if any(marker in blob for marker in INSPECT_ONLY_MARKERS):
        return True
    path = resolve_codepath(name)
    if path is None or not path.is_file():
        return False
    try:
        head = path.read_text(encoding="utf-8", errors="ignore")[:8000].casefold()
    except OSError:
        return False
    return "172.17.0.1" in head


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
    for cand in candidates:
        try:
            resolved = cand.resolve()
        except OSError:
            continue
        if not resolved.is_file():
            continue
        if any(resolved == root or root in resolved.parents for root in _roots()):
            return resolved
    return None


def slice_codepath(name: str) -> dict[str, Any]:
    """Callers/callees-style slice from Python AST. No source bodies."""

    path = resolve_codepath(name)
    if path is None:
        return {"ok": False, "reason": "codepath_not_allowed", "name": name, "called_docker0": False, "inspect_only": is_inspect_only(name)}
    symbol = ""
    if ":" in str(name):
        symbol = str(name).rsplit(":", 1)[-1]
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (OSError, SyntaxError) as exc:
        return {"ok": False, "reason": "parse_failed", "error": str(exc)[:160], "called_docker0": False}
    defs: list[str] = []
    calls_by: dict[str, list[str]] = {}
    current = ""

    class Visitor(ast.NodeVisitor):
        def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
            nonlocal current
            defs.append(node.name)
            prev, current = current, node.name
            calls_by.setdefault(node.name, [])
            self.generic_visit(node)
            current = prev

        visit_AsyncFunctionDef = visit_FunctionDef

        def visit_Call(self, node: ast.Call) -> None:
            func = node.func
            called = ""
            if isinstance(func, ast.Name):
                called = func.id
            elif isinstance(func, ast.Attribute):
                called = func.attr
            if current and called:
                bucket = calls_by.setdefault(current, [])
                if called not in bucket:
                    bucket.append(called)
            self.generic_visit(node)

    Visitor().visit(tree)
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
    files = sorted(HERE.glob("*.py"))[:40]
    extras = [
        ACCEL / "llm_router.py",
        ACCEL / "agent_supervisor" / "analysis" / "program_graph_queries.py",
        ACCEL / "agent_supervisor" / "analysis" / "duckdb_ast_index.py",
        ACCEL / "agent_supervisor" / "task_sources" / "database_task_source.py",
    ]
    for path in extras:
        if path.is_file():
            files.append(path)
    return files


def build_sidecar_index(*, root: Optional[Path] = None, write: bool = True) -> dict[str, Any]:
    """JSON AST sidecar of harness (+ allowlisted) files. Never campaign DuckDB."""

    base = root or HERE
    files_payload: list[dict[str, Any]] = []
    for path in sorted(base.glob("*.py"))[:80]:
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except (OSError, SyntaxError):
            continue
        symbols = [n.name for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))]
        files_payload.append({"path": path.name, "symbols": symbols[:80], "n_symbols": len(symbols)})
    payload = {
        "schema": "lra-nca-ast-sidecar/v1",
        "n_files": len(files_payload),
        "files": files_payload,
        "campaign_write": False,
        "called_docker0": False,
        "control_duckdb": False,
    }
    if write:
        SIDECAR.parent.mkdir(parents=True, exist_ok=True)
        SIDECAR.write_text(__import__("json").dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        payload["path"] = str(SIDECAR)
    return payload


def build_sidecar_duckdb(*, path: Optional[Path] = None, refresh: bool = True) -> dict[str, Any]:
    """Symbols+calls DuckDB next to evidence/. Refuses campaign control.duckdb."""

    dest = Path(path or SIDECAR_DUCKDB)
    if dest.name == "control.duckdb" or "control.duckdb" in str(dest):
        return {"ok": False, "reason": "campaign_db_refused", "control_duckdb": True, "called_docker0": False}
    try:
        import duckdb  # type: ignore[import-not-found]
    except Exception:
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
    dest = Path(db_path or SIDECAR_DUCKDB)
    if dest.name == "control.duckdb" or not dest.is_file():
        return []
    try:
        import duckdb  # type: ignore[import-not-found]
    except Exception:
        return []
    needle = f"%{str(query or '').casefold()}%"
    con = duckdb.connect(str(dest), read_only=True)
    try:
        rows = con.execute(
            "SELECT qualified_name, path, symbol_kind FROM symbols "
            "WHERE lower(CAST(qualified_name AS VARCHAR)) LIKE ? LIMIT 20",
            [needle],
        ).fetchall()
    except Exception:
        rows = []
    finally:
        con.close()
    return [
        {"symbol": str(row[0]), "path": str(row[1] or ""), "kind": str(row[2] or ""), "source": "sidecar_duckdb"}
        for row in rows
        if row and row[0]
    ]


def query_calls_duckdb(
    symbol: str,
    *,
    db_path: Optional[Path] = None,
    direction: str = "callees",
) -> list[str]:
    dest = Path(db_path or SIDECAR_DUCKDB)
    if dest.name == "control.duckdb" or not dest.is_file():
        return []
    try:
        import duckdb  # type: ignore[import-not-found]
    except Exception:
        return []
    name = str(symbol or "").replace("ptr://codepath/", "")
    con = duckdb.connect(str(dest), read_only=True)
    try:
        if direction == "callers":
            rows = con.execute(
                "SELECT caller FROM calls WHERE callee = ? OR callee LIKE ? LIMIT 12",
                [name, f"%:{name.rsplit(':', 1)[-1]}"],
            ).fetchall()
        else:
            rows = con.execute(
                "SELECT callee FROM calls WHERE caller = ? OR caller LIKE ? LIMIT 12",
                [name, f"%:{name.rsplit(':', 1)[-1]}"],
            ).fetchall()
    except Exception:
        rows = []
    finally:
        con.close()
    return [str(row[0]) for row in rows if row and row[0]]


def harness_call_graph(*, refresh: bool = False) -> dict[str, Any]:
    """Call graph over harness/*.py only (no accelerate parse)."""

    global _HARNESS_CROSS
    if _HARNESS_CROSS is not None and not refresh:
        return _HARNESS_CROSS
    try:
        local_defs: dict[str, list[str]] = {}
        local_calls: dict[str, list[str]] = {}
        for path in sorted(HERE.glob("*.py"))[:40]:
            module = path.stem
            try:
                tree = ast.parse(path.read_text(encoding="utf-8"))
            except (OSError, SyntaxError):
                continue
            current = ""

            class Visitor(ast.NodeVisitor):
                def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
                    nonlocal current
                    qname = f"{module}:{node.name}"
                    local_defs.setdefault(node.name, [])
                    if qname not in local_defs[node.name]:
                        local_defs[node.name].append(qname)
                    prev_fn, current = current, qname
                    local_calls.setdefault(qname, [])
                    self.generic_visit(node)
                    current = prev_fn

                visit_AsyncFunctionDef = visit_FunctionDef

                def visit_Call(self, node: ast.Call) -> None:
                    func = node.func
                    called = func.id if isinstance(func, ast.Name) else (func.attr if isinstance(func, ast.Attribute) else "")
                    if current and called:
                        bucket = local_calls.setdefault(current, [])
                        if called not in bucket:
                            bucket.append(called)
                    self.generic_visit(node)

            Visitor().visit(tree)
        resolved: dict[str, list[str]] = {}
        for qname, raw in local_calls.items():
            out: list[str] = []
            for callee in raw:
                targets = local_defs.get(callee) or []
                out.append(targets[0] if len(targets) == 1 else callee)
            resolved[qname] = out[:MAX_NEIGHBORS]
        _HARNESS_CROSS = {"defs": local_defs, "calls": resolved, "n_defs": sum(len(v) for v in local_defs.values())}
    except Exception:
        _HARNESS_CROSS = {"defs": {}, "calls": {}, "n_defs": 0}
    return _HARNESS_CROSS


def seed_nca_call_edges(memory: dict[str, Any], *, db_path: Optional[Path] = None, limit: int = 48) -> dict[str, Any]:
    """Attach caller→callee pairs as NCA board_edges. DuckDB sidecar or harness AST."""

    dest = Path(db_path or SIDECAR_DUCKDB)
    if dest.name == "control.duckdb":
        return {"ok": False, "reason": "campaign_db_refused", "n_edges": 0, "control_duckdb": True}
    rows: list[tuple[str, str]] = []
    source = "harness_ast"
    if dest.is_file():
        try:
            import duckdb  # type: ignore[import-not-found]

            con = duckdb.connect(str(dest), read_only=True)
            try:
                fetched = con.execute("SELECT caller, callee FROM calls LIMIT ?", [int(limit)]).fetchall()
                rows = [(str(a), str(b)) for a, b in fetched if a and b]
                source = "sidecar_duckdb"
            except Exception:
                rows = []
            finally:
                con.close()
        except Exception:
            rows = []
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
    edges = memory.setdefault("nca", {}).setdefault("board_edges", [])
    added = 0
    for caller, callee in rows[: int(limit)]:
        src = f"ptr://codepath/{caller}"
        dst = f"ptr://codepath/{callee}"
        pair = [src, dst]
        if pair in edges:
            continue
        edges.append(pair)
        added += 1
    return {"ok": True, "n_edges": added, "source": source, "control_duckdb": False, "called_docker0": False}


def query_sidecar(query: str, *, payload: Optional[dict[str, Any]] = None) -> list[dict[str, Any]]:
    data = payload
    if data is None and SIDECAR.is_file():
        data = __import__("json").loads(SIDECAR.read_text(encoding="utf-8"))
    if not data:
        data = build_sidecar_index(write=False)
    q = str(query or "").casefold()
    hits: list[dict[str, Any]] = []
    for row in data.get("files") or []:
        for symbol in row.get("symbols") or []:
            if q and q in str(symbol).casefold():
                hits.append({"symbol": symbol, "path": row.get("path"), "source": "sidecar"})
    return hits[:24]


def allowlist_call_graph(*, refresh: bool = False) -> dict[str, Any]:
    """Cross-module name→qualified-def graph on allowlisted roots."""

    global _CROSS
    if _CROSS is not None and not refresh:
        return _CROSS
    defs: dict[str, list[str]] = {}
    calls: dict[str, list[str]] = {}
    for path in _iter_allowlisted_py():
        module = path.stem
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except (OSError, SyntaxError):
            continue
        current = ""

        class Visitor(ast.NodeVisitor):
            def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
                nonlocal current
                qname = f"{module}:{node.name}"
                defs.setdefault(node.name, [])
                if qname not in defs[node.name]:
                    defs[node.name].append(qname)
                prev, current = current, qname
                calls.setdefault(qname, [])
                self.generic_visit(node)
                current = prev

            visit_AsyncFunctionDef = visit_FunctionDef

            def visit_Call(self, node: ast.Call) -> None:
                func = node.func
                called = func.id if isinstance(func, ast.Name) else (func.attr if isinstance(func, ast.Attribute) else "")
                if current and called:
                    bucket = calls.setdefault(current, [])
                    if called not in bucket:
                        bucket.append(called)
                self.generic_visit(node)

        Visitor().visit(tree)

    resolved: dict[str, list[str]] = {}
    for qname, raw in calls.items():
        out: list[str] = []
        for callee in raw:
            targets = defs.get(callee) or []
            if len(targets) == 1:
                out.append(targets[0])
            else:
                out.append(callee)
        resolved[qname] = out[:MAX_NEIGHBORS]
    _CROSS = {"defs": defs, "calls": resolved, "n_defs": sum(len(v) for v in defs.values())}
    return _CROSS


def slice_cross_module(name: str, *, db_path: Optional[Path] = None) -> dict[str, Any]:
    """Callers/callees across allowlisted modules. Ids only; no source bodies."""

    if is_inspect_only(name):
        sliced = slice_codepath(name)
        sliced["cross_module"] = False
        return sliced
    raw_name = str(name or "").replace("ptr://codepath/", "")
    db_hits = query_sidecar_duckdb(raw_name.rsplit(":", 1)[-1], db_path=db_path)
    q_db = ""
    for hit in db_hits:
        if raw_name in str(hit.get("symbol") or "") or str(hit.get("symbol") or "").endswith(":" + raw_name.rsplit(":", 1)[-1]):
            q_db = str(hit["symbol"])
            break
    if not q_db and db_hits:
        q_db = str(db_hits[0]["symbol"])
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
    graph = allowlist_call_graph()
    symbol = str(name or "").replace("ptr://codepath/", "")
    if ":" not in symbol and "." in symbol:
        # harness.portable_rewrites:fold_x or portable_rewrites.fold_x
        if symbol.startswith("harness."):
            symbol = symbol[len("harness.") :]
        if ":" not in symbol:
            parts = symbol.replace("/", ".").rsplit(".", 1)
            symbol = f"{parts[0]}:{parts[1]}" if len(parts) == 2 else symbol
    defs = graph.get("defs") or {}
    calls = graph.get("calls") or {}
    qname = symbol if symbol in calls else ""
    if not qname:
        bare = symbol.rsplit(":", 1)[-1]
        matches = defs.get(bare) or []
        qname = matches[0] if len(matches) == 1 else (matches[0] if matches else "")
    if not qname:
        local = slice_codepath(name)
        local["cross_module"] = False
        return local
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

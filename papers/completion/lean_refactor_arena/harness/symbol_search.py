#!/usr/bin/env python3
"""Ranked symbol search for TypeSafe: DuckDB / vector index, KG, AST, ripgrep.

Order: ipfs_accelerate_py DuckDB AST index (if present) → code-symbol vector
index (if a snapshot is supplied) → skill knowledge graph → Python ``ast``
on the harness → ripgrep. Hits are merged and ranked. Never docker0. Does
not write Lean. Paths outside the paper harness are refused for AST/rg.
"""
from __future__ import annotations

import ast
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any, Callable, Mapping, Optional

HERE = Path(__file__).resolve().parent
PAPER_ROOT = HERE.parent
LRA_STATE = Path.home() / ".local/state/ipfs_accelerate_py/vericodegen-2026-lra"
MAX_HITS = 24
RG_TIMEOUT = 4.0

_IDENT = re.compile(r"[A-Za-z_][A-Za-z0-9_.']*")

SOURCE_WEIGHT = {
    "duckdb": 1.0,
    "sidecar_duckdb": 0.9,
    "vector": 0.95,
    "kg": 0.85,
    "ast": 0.7,
    "rg": 0.5,
}


def _score(query: str, symbol: str, source: str) -> float:
    q = query.casefold()
    s = symbol.casefold()
    if s == q:
        base = 1.0
    elif s.endswith("." + q) or s.endswith("/" + q) or s.rsplit(".", 1)[-1] == q:
        base = 0.9
    elif s.startswith(q):
        base = 0.8
    elif q in s:
        base = 0.55
    else:
        base = 0.15
    return round(base * SOURCE_WEIGHT.get(source, 0.4), 4)


def _hit(symbol: str, *, source: str, query: str, path: str = "", extra: Optional[Mapping[str, Any]] = None) -> dict[str, Any]:
    row = {
        "symbol": symbol,
        "source": source,
        "path": path,
        "score": _score(query, symbol, source),
        "ptr": f"ptr://skill/{symbol}" if symbol.startswith("port_") else "",
    }
    if extra:
        row.update(dict(extra))
    return row


def _candidate_duckdb_paths() -> list[Path]:
    paths: list[Path] = []
    env = os.environ.get("LRA_DUCKDB_AST_INDEX")
    if env:
        paths.append(Path(env))
    for rel in (
        PAPER_ROOT / "evidence" / "canaries" / "nca-ast.duckdb",
        LRA_STATE / "ast_index.duckdb",
        LRA_STATE / "code_symbols.duckdb",
    ):
        paths.append(rel)
    return [path for path in paths if path.is_file() and path.name != "control.duckdb"]


def search_duckdb(query: str, *, db_path: Optional[Path] = None) -> tuple[list[dict[str, Any]], str]:
    """Query ipfs_accelerate DuckDB AST/symbol tables if a DB exists."""

    try:
        import duckdb  # type: ignore[import-not-found]
    except Exception:
        return [], "duckdb_unavailable"
    paths = [db_path] if db_path is not None else _candidate_duckdb_paths()
    paths = [path for path in paths if path is not None and path.is_file()]
    if not paths:
        return [], "no_duckdb_index"
    needle = f"%{query.casefold()}%"
    hits: list[dict[str, Any]] = []
    used = ""
    for path in paths:
        try:
            con = duckdb.connect(str(path), read_only=True)
        except Exception:
            continue
        try:
            tables = {str(row[0]).casefold() for row in con.execute("SHOW TABLES").fetchall()}
            sql = None
            if "symbols" in tables:
                sql = (
                    "SELECT qualified_name, path, symbol_kind FROM symbols "
                    "WHERE lower(CAST(qualified_name AS VARCHAR)) LIKE ? LIMIT 20"
                )
            elif "code_symbols" in tables:
                sql = (
                    "SELECT name, path, kind FROM code_symbols "
                    "WHERE lower(CAST(name AS VARCHAR)) LIKE ? LIMIT 20"
                )
            if not sql:
                continue
            rows = con.execute(sql, [needle]).fetchall()
            used = str(path)
            for row in rows:
                name = str(row[0] or "")
                if not name:
                    continue
                hits.append(
                    _hit(
                        name,
                        source="duckdb",
                        query=query,
                        path=str(row[1] or ""),
                        extra={"kind": str(row[2] or "") if len(row) > 2 else ""},
                    )
                )
        except Exception:
            continue
        finally:
            try:
                con.close()
            except Exception:
                pass
        if hits:
            break
    return hits, (used or "duckdb_no_symbols")


def search_vector_index(
    query: str,
    *,
    snapshot: Optional[Mapping[str, Any]] = None,
    search_fn: Optional[Callable[..., Any]] = None,
) -> tuple[list[dict[str, Any]], str]:
    """ipfs_accelerate_py code-symbol vector index. Advisory only."""

    if snapshot is None:
        return [], "no_vector_snapshot"
    fn = search_fn
    if fn is None:
        try:
            from ipfs_accelerate_py.agent_supervisor.analysis.code_symbol_vector_index import (
                search_code_symbol_vector_index,
            )

            fn = search_code_symbol_vector_index
        except Exception:
            return [], "vector_index_unavailable"
    try:
        result = fn(snapshot, {"query_text": query, "max_results": 12})
    except Exception as exc:
        return [], f"vector_search_failed:{type(exc).__name__}"
    hits: list[dict[str, Any]] = []
    rows = getattr(result, "hits", None) or (result.get("hits") if isinstance(result, Mapping) else []) or []
    for item in list(rows)[:12]:
        row = getattr(item, "row", item)
        symbol = str(getattr(row, "qualified_symbol", None) or getattr(row, "symbol", None) or (row.get("qualified_symbol") if isinstance(row, Mapping) else "") or "")
        path = str(getattr(row, "path", None) or (row.get("path") if isinstance(row, Mapping) else "") or "")
        score = float(getattr(item, "score", None) or (item.get("score") if isinstance(item, Mapping) else 0.0) or 0.0)
        if symbol:
            hit = _hit(symbol, source="vector", query=query, path=path)
            hit["score"] = round(max(hit["score"], score * SOURCE_WEIGHT["vector"]), 4)
            hits.append(hit)
    return hits, "vector"


def search_kg(query: str, memory: Optional[Mapping[str, Any]] = None) -> list[dict[str, Any]]:
    import typesafe_tools as lra_tools

    graph = lra_tools.skill_knowledge_graph(memory)
    q = query.casefold()
    hits: list[dict[str, Any]] = []
    for node in graph.get("nodes") or []:
        nid = str(node.get("id") or "")
        if q and q in nid.casefold():
            hits.append(_hit(nid, source="kg", query=query, extra={"kind": node.get("kind")}))
    return hits[:MAX_HITS]


def search_ast(query: str, *, root: Optional[Path] = None) -> list[dict[str, Any]]:
    base = root or HERE
    hits: list[dict[str, Any]] = []
    q = query.casefold()
    for path in sorted(base.glob("*.py"))[:80]:
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except (OSError, SyntaxError):
            continue
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                name = node.name
                if q in name.casefold():
                    hits.append(
                        _hit(
                            name,
                            source="ast",
                            query=query,
                            path=path.name,
                            extra={"lineno": int(getattr(node, "lineno", 0) or 0)},
                        )
                    )
    return hits[:MAX_HITS]


def search_rg(query: str, *, root: Optional[Path] = None) -> tuple[list[dict[str, Any]], str]:
    base = root or HERE
    rg = shutil.which("rg")
    if not rg:
        return [], "rg_missing"
    pattern = _IDENT.search(query)
    needle = pattern.group(0) if pattern else query[:40]
    if not needle:
        return [], "empty_query"
    try:
        proc = subprocess.run(
            [rg, "-n", "--glob", "*.py", "--glob", "*.lean", "-e", needle, str(base)],
            capture_output=True,
            text=True,
            timeout=RG_TIMEOUT,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return [], "rg_failed"
    hits: list[dict[str, Any]] = []
    for line in (proc.stdout or "").splitlines()[:MAX_HITS]:
        parts = line.split(":", 2)
        path = Path(parts[0]).name if parts else ""
        snippet = parts[-1].strip() if parts else line
        ident = _IDENT.search(snippet)
        symbol = ident.group(0) if ident else needle
        hits.append(_hit(symbol, source="rg", query=query, path=path, extra={"line": snippet[:160]}))
    return hits, "rg"


def rank_hits(hits: list[dict[str, Any]], *, limit: int = 16) -> list[dict[str, Any]]:
    seen: set[tuple[str, str]] = set()
    ranked = sorted(hits, key=lambda row: (-float(row.get("score") or 0.0), str(row.get("symbol") or "")))
    out: list[dict[str, Any]] = []
    for row in ranked:
        key = (str(row.get("symbol") or ""), str(row.get("source") or ""))
        if key in seen:
            continue
        seen.add(key)
        out.append(row)
        if len(out) >= limit:
            break
    return out


def search_symbols(
    query: str,
    *,
    memory: Optional[Mapping[str, Any]] = None,
    tactics: str = "",
    duckdb_path: Optional[Path] = None,
    vector_snapshot: Optional[Mapping[str, Any]] = None,
    vector_search: Optional[Callable[..., Any]] = None,
    root: Optional[Path] = None,
) -> dict[str, Any]:
    """Search/rank symbols. DuckDB → vector → KG → ast → ripgrep."""

    q = str(query or "").strip()
    if not q and tactics:
        found = _IDENT.findall(tactics)
        q = found[0] if found else ""
    sources: dict[str, str] = {}
    hits: list[dict[str, Any]] = []
    if q:
        db_hits, db_note = search_duckdb(q, db_path=duckdb_path)
        sources["duckdb"] = db_note
        hits.extend(db_hits)
        vec_hits, vec_note = search_vector_index(q, snapshot=vector_snapshot, search_fn=vector_search)
        sources["vector"] = vec_note
        hits.extend(vec_hits)
        hits.extend(search_kg(q, memory))
        sources["kg"] = "ok"
        hits.extend(search_ast(q, root=root))
        sources["ast"] = "ok"
        try:
            import codepath_graph as lra_cp

            for row in lra_cp.query_sidecar(q, payload=None if root is None else lra_cp.build_sidecar_index(root=root, write=False)):
                hits.append(
                    {
                        "symbol": row.get("symbol"),
                        "source": "sidecar",
                        "path": row.get("path"),
                        "score": 0.72,
                        "ptr": "",
                    }
                )
            sources["sidecar"] = "ok"
        except Exception:
            sources["sidecar"] = "sidecar_failed"
        rg_hits, rg_note = search_rg(q, root=root)
        sources["rg"] = rg_note
        hits.extend(rg_hits)
    ranked = rank_hits(hits)
    if isinstance(memory, dict) and ranked:
        grid = memory.setdefault("nca", {}).setdefault("grid", {})
        for hit in ranked[:8]:
            cid = str(hit.get("ptr") or "")
            if not cid.startswith("ptr://"):
                symbol = str(hit.get("symbol") or "hit")
                cid = f"ptr://skill/{symbol}" if symbol.startswith("port_") else f"ptr://codepath/{symbol}"
            cell = grid.setdefault(
                cid,
                {
                    "id": cid,
                    "kind": "codepath" if "codepath" in cid else "skill",
                    "energy": 0.4,
                    "wins": 0,
                    "losses": 0,
                    "tick": 0,
                },
            )
            cell["energy"] = min(1.0, float(cell.get("energy") or 0.4) + 0.05 * float(hit.get("score") or 0.0))
            cell["path"] = hit.get("path")
            edges = memory.setdefault("nca", {}).setdefault("board_edges", [])
            owners = [
                key
                for key in grid
                if str(key).startswith("ptr://task/") or str(key).startswith("ptr://theorem/")
            ]
            if owners:
                pair = [str(owners[0]), cid]
                if pair not in edges:
                    edges.append(pair)
    return {
        "ok": True,
        "query": q,
        "n_hits": len(ranked),
        "hits": ranked,
        "sources": sources,
        "called_docker0": False,
        "semantic_authority": False,
        "n_cells_promoted": min(8, len(ranked)) if isinstance(memory, dict) else 0,
    }

#!/usr/bin/env python3
"""Ranked symbol search for TypeSafe.

Order: JSON-LD graph (if present) → optional DuckDB adapter → vector → KG →
AST → ripgrep. DuckDB is never required. Never docker0. Does not write Lean.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any, Callable, Mapping, Optional

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
import _jevops_path  # noqa: E402,F401
PAPER_ROOT = HERE.parent
from jevops.catalogs import LRA_STATE_ROOT as LRA_STATE
from jevops.catalogs import RG_TIMEOUT_SECONDS as RG_TIMEOUT
from jevops.catalogs import SYMBOL_MAX_HITS as MAX_HITS

_IDENT = re.compile(r"[A-Za-z_][A-Za-z0-9_.']*")

from jevops.catalogs import SOURCE_WEIGHT


def _ptr(symbol: str) -> str:
    from jevops.outer import call_if, text_or

    return call_if(text_or(symbol).startswith("port_"), lambda: f"ptr://skill/{symbol}", default="")


def _score(query: str, symbol: str, source: str) -> float:
    from jevops.search import name_match_score

    return name_match_score(query, symbol, source=source, weights=SOURCE_WEIGHT)


def _hit(symbol: str, *, source: str, query: str, path: str = "", extra: Optional[Mapping[str, Any]] = None) -> dict[str, Any]:
    from jevops.search import hit_row

    return hit_row(
        symbol,
        source=source,
        query=query,
        path=path,
        extra=extra,
        weights=SOURCE_WEIGHT,
        ptr_fn=_ptr,
    )


def _candidate_duckdb_paths() -> list[Path]:
    from jevops.outer import append_if, existing_files, optional_env_path

    env_path = optional_env_path("LRA_DUCKDB_AST_INDEX")
    paths = append_if([], env_path is not None, env_path)
    paths.extend(
        (
            PAPER_ROOT / "evidence" / "canaries" / "nca-ast.duckdb",
            LRA_STATE / "ast_index.duckdb",
            LRA_STATE / "code_symbols.duckdb",
        )
    )
    return existing_files(paths, exclude_names=("control.duckdb",))


def search_duckdb(query: str, *, db_path: Optional[Path] = None) -> tuple[list[dict[str, Any]], str]:
    """Query ipfs_accelerate DuckDB AST/symbol tables if a DB exists."""

    from jevops.outer import call_if, first_not_none, query_first_engine, replace_if, row_cell, text_or, try_import

    if try_import("duckdb") is None:
        return [], "duckdb_unavailable"
    paths = [
        path
        for path in first_not_none(
            call_if(db_path is not None, lambda: [db_path]), factory=_candidate_duckdb_paths
        )
        if path is not None and path.is_file()
    ]
    if not paths:
        return [], "no_duckdb_index"
    needle = f"%{query.casefold()}%"
    from jevops.catalogs import CODE_SYMBOLS_SQL, SYMBOLS_SQL

    table_sql = {
        "symbols": SYMBOLS_SQL,
        "code_symbols": CODE_SYMBOLS_SQL,
    }
    hits, used = query_first_engine(
        paths,
        table_sql,
        [needle],
        refuse_names=("control.duckdb",),
        row_fn=lambda row: call_if(
            row and row[0],
            lambda: _hit(
                text_or(row[0]),
                source="duckdb",
                query=query,
                path=text_or(row[1]),
                extra={"kind": text_or(row_cell(row, 2, default=""))},
            ),
        ),
    )
    return hits, replace_if(used in {"no_index", "no_matching_table", "query_failed"}, "duckdb_no_symbols", used)


def search_vector_index(
    query: str,
    *,
    snapshot: Optional[Mapping[str, Any]] = None,
    search_fn: Optional[Callable[..., Any]] = None,
) -> tuple[list[dict[str, Any]], str]:
    """ipfs_accelerate_py code-symbol vector index. Advisory only."""

    from jevops.search import run_vector_search

    def _load() -> Any:
        from jevops.search import load_code_symbol_vector_index

        return load_code_symbol_vector_index()

    return run_vector_search(
        query,
        snapshot=snapshot,
        search_fn=search_fn,
        load_fn=_load,
        hit_fn=_hit,
        cap=12,
        vector_weight=SOURCE_WEIGHT["vector"],
    )


def search_kg(query: str, memory: Optional[Mapping[str, Any]] = None) -> list[dict[str, Any]]:
    import typesafe_tools as lra_tools

    from jevops.outer import get_list, get_str, map_hits, matching_nodes

    graph = lra_tools.skill_knowledge_graph(memory)
    return map_hits(
        matching_nodes(get_list(graph, "nodes"), query, cap=MAX_HITS),
        lambda node: _hit(
            get_str(node, "id"), source="kg", query=query, extra={"kind": node.get("kind")}
        ),
    )


def search_ast(query: str, *, root: Optional[Path] = None) -> list[dict[str, Any]]:
    from jevops.nca import matching_top_level
    from jevops.outer import first_int, get_str, if_none, map_hits

    rows = matching_top_level(if_none(root, HERE), query, cap_hits=MAX_HITS)
    return map_hits(
        rows,
        lambda row: _hit(
            get_str(row, "name"),
            source="ast",
            query=query,
            path=get_str(row, "path"),
            extra={"lineno": first_int(row.get("lineno"))},
        ),
    )


def search_rg(query: str, *, root: Optional[Path] = None) -> tuple[list[dict[str, Any]], str]:
    from jevops.outer import if_none
    from jevops.search import search_rg as _search_rg

    return _search_rg(
        query,
        root=if_none(root, HERE),
        ident_re=_IDENT,
        timeout=RG_TIMEOUT,
        cap=MAX_HITS,
        globs=("*.py", "*.lean"),
        hit_fn=lambda symbol, path="", snippet="", **_k: _hit(
            symbol, source="rg", query=query, path=path, extra={"line": snippet}
        ),
    )


def rank_hits(hits: list[dict[str, Any]], *, limit: int = 16) -> list[dict[str, Any]]:
    from jevops.search import rank_hits as _rank_hits

    return _rank_hits(hits, limit=limit)


def search_symbols(
    query: str,
    *,
    memory: Optional[Mapping[str, Any]] = None,
    tactics: str = "",
    duckdb_path: Optional[Path] = None,
    use_duckdb: bool = True,
    vector_snapshot: Optional[Mapping[str, Any]] = None,
    vector_search: Optional[Callable[..., Any]] = None,
    root: Optional[Path] = None,
) -> dict[str, Any]:
    """Search/rank symbols. JSON-LD → optional DuckDB → vector → KG → ast → rg."""

    from jevops.search import collect_source_hits, credit_search_hits, first_ident, pack_symbol_search

    from jevops.outer import as_dict, call_if, either, or_call, text_or

    q = or_call(text_or(query).strip(), first_ident, tactics, _IDENT)
    sources: dict[str, str] = {}
    hits: list[dict[str, Any]] = []
    if q:

        def _jsonld() -> list[dict[str, Any]]:
            import nca_jsonld as lra_ld

            from jevops.outer import get_str, if_none

            doc = lra_ld.memory_jsonld(if_none(memory, default={}))

            return [
                _hit(get_str(hit, "symbol"), source="jsonld", query=q)
                for hit in lra_ld.search_jsonld(doc, q)
            ]

        def _sidecar() -> list[dict[str, Any]]:
            import codepath_graph as lra_cp

            from jevops.search import sidecar_hit_row

            return [
                sidecar_hit_row(row)
                for row in lra_cp.query_sidecar(
                    q, payload=call_if(root is not None, lambda: lra_cp.build_sidecar_index(root=root, write=False))
                )
            ]

        hits, sources = collect_source_hits(
            (
                ("jsonld", _jsonld),
                (
                    "duckdb",
                    either(
                        use_duckdb,
                        lambda: (lambda: search_duckdb(q, db_path=duckdb_path)),
                        lambda: (lambda: ([], "skipped_optional")),
                    ),
                ),
                ("vector", lambda: search_vector_index(q, snapshot=vector_snapshot, search_fn=vector_search)),
                ("kg", lambda: search_kg(q, memory)),
                ("ast", lambda: search_ast(q, root=root)),
                ("sidecar", _sidecar),
                ("rg", lambda: search_rg(q, root=root)),
            ),
            fail_notes={"sidecar": "sidecar_failed"},
        )
    ranked = rank_hits(hits)
    promoted = credit_search_hits(as_dict(memory), ranked)
    return pack_symbol_search(query=q, ranked=ranked, sources=sources, promoted=promoted)

#!/usr/bin/env python3
"""Ranked symbol search for TypeSafe.

Order: JSON-LD graph (if present) → optional DuckDB adapter → vector → KG →
AST → ripgrep. DuckDB is never required. Never docker0. Does not write Lean.
"""
from __future__ import annotations

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
from jevops.tactics import SEARCH_IDENT as _IDENT

from jevops.catalogs import SOURCE_WEIGHT


def _ptr(symbol: str) -> str:
    from jevops.outer import drive_prefixed_when

    return drive_prefixed_when(symbol, needle="port_", prefix="ptr://skill/")


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
    from jevops.outer import drive_env_existing

    return drive_env_existing(
        "LRA_DUCKDB_AST_INDEX",
        (
            PAPER_ROOT / "evidence" / "canaries" / "nca-ast.duckdb",
            LRA_STATE / "ast_index.duckdb",
            LRA_STATE / "code_symbols.duckdb",
        ),
        exclude=("control.duckdb",),
    )


def search_duckdb(query: str, *, db_path: Optional[Path] = None) -> tuple[list[dict[str, Any]], str]:
    """Query ipfs_accelerate DuckDB AST/symbol tables if a DB exists."""

    from jevops.catalogs import CODE_SYMBOLS_SQL, SYMBOLS_SQL
    from jevops.outer import drive_duckdb_search

    return drive_duckdb_search(
        query,
        db_path=db_path,
        candidate_fn=_candidate_duckdb_paths,
        table_sql={"symbols": SYMBOLS_SQL, "code_symbols": CODE_SYMBOLS_SQL},
        hit_fn=_hit,
    )


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
    from jevops.outer import drive_kg_search

    return drive_kg_search(
        query,
        memory,
        graph_fn=lra_tools.skill_knowledge_graph,
        hit_fn=_hit,
        cap=MAX_HITS,
    )


def search_ast(query: str, *, root: Optional[Path] = None) -> list[dict[str, Any]]:
    from jevops.nca import drive_ast_hits
    from jevops.outer import first_int, get_str, if_none

    return drive_ast_hits(
        if_none(root, HERE),
        query,
        cap=MAX_HITS,
        hit_fn=lambda row: _hit(
            get_str(row, "name"),
            source="ast",
            query=query,
            path=get_str(row, "path"),
            extra={"lineno": first_int(row.get("lineno"))},
        ),
    )


def search_rg(query: str, *, root: Optional[Path] = None) -> tuple[list[dict[str, Any]], str]:
    from jevops.outer import drive_search_at
    from jevops.search import search_rg as _search_rg

    return drive_search_at(
        query,
        root,
        HERE,
        _search_rg,
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

    import nca_jsonld as lra_ld
    import codepath_graph as lra_cp
    from jevops.search import drive_symbol_search, sidecar_hit_row

    return drive_symbol_search(
        query,
        memory=memory,
        tactics=tactics,
        duckdb_path=duckdb_path,
        use_duckdb=use_duckdb,
        vector_snapshot=vector_snapshot,
        vector_search=vector_search,
        root=root,
        ident_re=_IDENT,
        jsonld_fn=lra_ld.memory_jsonld,
        jsonld_search_fn=lra_ld.search_jsonld,
        hit_fn=_hit,
        sidecar_query_fn=lra_cp.query_sidecar,
        sidecar_build_fn=lra_cp.build_sidecar_index,
        sidecar_row_fn=sidecar_hit_row,
        duckdb_fn=search_duckdb,
        vector_fn=search_vector_index,
        kg_fn=search_kg,
        ast_fn=search_ast,
        rg_fn=search_rg,
        rank_fn=rank_hits,
    )

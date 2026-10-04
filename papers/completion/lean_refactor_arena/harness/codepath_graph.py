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
from jevops.catalogs import ACCEL_PY as ACCEL  # noqa: E402
SIDECAR = PAPER_ROOT / "evidence" / "canaries" / "nca-ast-sidecar.json"
SIDECAR_DUCKDB = PAPER_ROOT / "evidence" / "canaries" / "nca-ast.duckdb"
from jevops.catalogs import INSPECT_ONLY_MARKERS  # noqa: E402
from jevops.catalogs import MAX_CODEPATH_NEIGHBORS as MAX_NEIGHBORS  # noqa: E402
_CROSS: dict[str, Any] | None = None
_HARNESS_CROSS: dict[str, Any] | None = None


def is_inspect_only(name: str) -> bool:
    from jevops.outer import inspect_only

    return inspect_only(
        name,
        markers=INSPECT_ONLY_MARKERS,
        needles=("172.17.0.1",),
        resolve_fn=resolve_codepath,
    )


def _roots() -> tuple[Path, ...]:
    from jevops.outer import drive_root_tuple

    return drive_root_tuple((HERE, PAPER_ROOT), ACCEL)


def resolve_codepath(name: str) -> Optional[Path]:
    from jevops.nca import codepath_rel_candidates, drive_module_file, first_existing_file
    from jevops.outer import module_stem

    # harness.portable_rewrites:fold_hoist → portable_rewrites.py
    return drive_module_file(
        name,
        stem_fn=lambda text: module_stem(text, strip_prefix="ptr://codepath/"),
        candidates_fn=lambda module: codepath_rel_candidates(module, here=HERE, accel=ACCEL),
        roots_fn=_roots,
        first_fn=first_existing_file,
    )


def slice_codepath(name: str) -> dict[str, Any]:
    """Callers/callees-style slice from Python AST. No source bodies."""

    from jevops.nca import drive_codepath_slice
    from jevops.outer import read_text

    return drive_codepath_slice(
        name,
        resolve_fn=resolve_codepath,
        inspect_fn=is_inspect_only,
        read_fn=read_text,
        max_neighbors=MAX_NEIGHBORS,
    )


def _iter_allowlisted_py() -> list[Path]:
    from jevops.outer import drive_allow_files

    return drive_allow_files(
        HERE.glob("*.py"),
        (
            ACCEL / "llm_router.py",
            ACCEL / "agent_supervisor" / "analysis" / "program_graph_queries.py",
            ACCEL / "agent_supervisor" / "analysis" / "duckdb_ast_index.py",
            ACCEL / "agent_supervisor" / "task_sources" / "database_task_source.py",
        ),
    )


def build_sidecar_index(*, root: Optional[Path] = None, write: bool = True) -> dict[str, Any]:
    """JSON AST sidecar of harness (+ allowlisted) files. Never campaign DuckDB."""

    from jevops.nca import drive_sidecar_index

    return drive_sidecar_index(root=root, default_root=HERE, write=write, dest=SIDECAR)


def build_sidecar_duckdb(*, path: Optional[Path] = None, refresh: bool = True) -> dict[str, Any]:
    """Symbols+calls DuckDB next to evidence/. Refuses campaign control.duckdb."""

    from jevops.nca import drive_sidecar_db
    from jevops.outer import connect_engine, exec_many, path_refused, table_count, try_import

    return drive_sidecar_db(
        path,
        default_db=SIDECAR_DUCKDB,
        refresh=refresh,
        graph_fn=harness_call_graph,
        connect_fn=connect_engine,
        exec_fn=exec_many,
        count_fn=table_count,
        try_import_fn=try_import,
        refuse_fn=path_refused,
    )


def query_sidecar_duckdb(query: str, *, db_path: Optional[Path] = None) -> list[dict[str, Any]]:
    from jevops.catalogs import SIDECAR_SYMBOLS_SQL
    from jevops.nca import drive_query_symbols

    return drive_query_symbols(
        query,
        db_path=db_path,
        default_db=SIDECAR_DUCKDB,
        sql=SIDECAR_SYMBOLS_SQL,
    )


def query_calls_duckdb(
    symbol: str,
    *,
    db_path: Optional[Path] = None,
    direction: str = "callees",
) -> list[str]:
    from jevops.catalogs import SIDECAR_CALLS_SQL
    from jevops.nca import drive_query_calls

    return drive_query_calls(
        symbol,
        db_path=db_path,
        default_db=SIDECAR_DUCKDB,
        direction=direction,
        sql=SIDECAR_CALLS_SQL,
    )


def harness_call_graph(*, refresh: bool = False) -> dict[str, Any]:
    """Call graph over harness/*.py only (no accelerate parse)."""

    global _HARNESS_CROSS
    from jevops.nca import call_graph_from_paths, memo_build
    from jevops.outer import ignore_error

    def _build() -> dict[str, Any]:
        global _HARNESS_CROSS
        _HARNESS_CROSS = ignore_error(
            lambda: call_graph_from_paths(
                sorted(HERE.glob("*.py")),
                cap_files=40,
                cap_neighbors=MAX_NEIGHBORS,
            ),
            default={"defs": {}, "calls": {}, "n_defs": 0},
        )
        return _HARNESS_CROSS

    return memo_build(_HARNESS_CROSS, refresh=refresh, build_fn=_build)


def seed_nca_call_edges(memory: dict[str, Any], *, db_path: Optional[Path] = None, limit: int = 48) -> dict[str, Any]:
    """Attach caller→callee pairs as NCA board_edges. DuckDB sidecar or harness AST."""

    from jevops.catalogs import SIDECAR_EDGES_SQL
    from jevops.nca import call_pairs_from_graph, drive_seed_edges

    return drive_seed_edges(
        memory,
        db_path=db_path,
        default_db=SIDECAR_DUCKDB,
        limit=limit,
        sql=SIDECAR_EDGES_SQL,
        graph_fn=lambda cap: call_pairs_from_graph(harness_call_graph(), limit=cap),
    )


def query_sidecar(query: str, *, payload: Optional[dict[str, Any]] = None) -> list[dict[str, Any]]:
    from jevops.nca import drive_sidecar_query
    from jevops.outer import load_json_object

    return drive_sidecar_query(
        query,
        payload,
        present_fn=SIDECAR.is_file,
        load_fn=lambda: load_json_object(SIDECAR),
        build_fn=lambda: build_sidecar_index(write=False),
        limit=24,
    )


def allowlist_call_graph(*, refresh: bool = False) -> dict[str, Any]:
    """Cross-module name→qualified-def graph on allowlisted roots."""

    global _CROSS
    from jevops.nca import call_graph_from_paths, memo_build

    def _build() -> dict[str, Any]:
        global _CROSS
        _CROSS = call_graph_from_paths(_iter_allowlisted_py(), cap_neighbors=MAX_NEIGHBORS)
        return _CROSS

    return memo_build(_CROSS, refresh=refresh, build_fn=_build)


def slice_cross_module(name: str, *, db_path: Optional[Path] = None) -> dict[str, Any]:
    """Callers/callees across allowlisted modules. Ids only; no source bodies."""

    from jevops.nca import first_matching_symbol, pick_qualified, slice_cross_or_local

    return slice_cross_or_local(
        name,
        inspect_fn=slice_codepath,
        inspect_only_fn=is_inspect_only,
        db_hits_fn=lambda query: query_sidecar_duckdb(query, db_path=db_path),
        match_fn=first_matching_symbol,
        callees_fn=lambda symbol: query_calls_duckdb(symbol, db_path=db_path, direction="callees"),
        callers_fn=lambda symbol: query_calls_duckdb(symbol, db_path=db_path, direction="callers"),
        graph_fn=allowlist_call_graph,
        pick_fn=pick_qualified,
        local_fn=slice_codepath,
        cap=MAX_NEIGHBORS,
        strip_prefixes=("harness.",),
    )

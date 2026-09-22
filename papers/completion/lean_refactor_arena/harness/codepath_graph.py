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
    from jevops.outer import append_if

    return tuple(append_if([HERE.resolve(), PAPER_ROOT.resolve()], ACCEL.is_dir(), ACCEL.resolve()))


def resolve_codepath(name: str) -> Optional[Path]:
    from jevops.nca import codepath_rel_candidates, first_existing_file
    from jevops.outer import call_if, module_stem

    module = module_stem(name, strip_prefix="ptr://codepath/")
    # harness.portable_rewrites:fold_hoist → portable_rewrites.py
    return call_if(
        module is not None,
        lambda: first_existing_file(
            codepath_rel_candidates(module, here=HERE, accel=ACCEL),
            roots=_roots(),
        ),
    )


def slice_codepath(name: str) -> dict[str, Any]:
    """Callers/callees-style slice from Python AST. No source bodies."""

    from jevops.nca import pack_codepath_slice

    from jevops.outer import either

    path = resolve_codepath(name)

    def _missing() -> dict[str, Any]:
        return pack_codepath_slice(
            ok=False,
            name=name,
            reason="codepath_not_allowed",
            inspect_only=is_inspect_only(name),
        )

    def _present() -> dict[str, Any]:
        try:
            from jevops.nca import function_call_map
            from jevops.outer import exc_head, head_seq, read_text

            defs, calls_by = function_call_map(read_text(path))
        except (OSError, SyntaxError) as exc:
            from jevops.outer import exc_head

            return pack_codepath_slice(ok=False, reason="parse_failed", error=exc_head(exc, 160))
        from jevops.nca import focus_symbol
        from jevops.outer import head_seq

        focus = focus_symbol(name, defs, calls_by)
        inspect = is_inspect_only(name)
        return pack_codepath_slice(
            ok=True,
            path=path.name,
            symbol=focus,
            definitions=head_seq(defs, 40),
            callees=head_seq(calls_by.get(focus), MAX_NEIGHBORS),
            callers=head_seq(
                [fn for fn, kids in calls_by.items() if focus and focus in kids], MAX_NEIGHBORS
            ),
            inspect_only=inspect,
        )

    return either(path is None, _missing, _present)


def _iter_allowlisted_py() -> list[Path]:
    from jevops.outer import existing_files, head_seq

    files = head_seq(sorted(HERE.glob("*.py")), 40)
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

    from jevops.outer import if_none

    base = if_none(root, HERE)
    files_payload = sidecar_files(sorted(base.glob("*.py")), cap_files=80, cap_symbols=80)
    from jevops.nca import pack_sidecar_index

    payload = pack_sidecar_index(files_payload)
    from jevops.outer import call_if, set_if, text_or, write_json

    call_if(write, lambda: write_json(SIDECAR, payload))
    return set_if(payload, write, "path", text_or(SIDECAR))


def build_sidecar_duckdb(*, path: Optional[Path] = None, refresh: bool = True) -> dict[str, Any]:
    """Symbols+calls DuckDB next to evidence/. Refuses campaign control.duckdb."""

    from jevops.outer import connect_engine, exec_many, path_refused, table_count, try_import

    from jevops.outer import if_none

    dest = Path(if_none(path, SIDECAR_DUCKDB))
    graph = harness_call_graph(refresh=refresh)
    from jevops.nca import fill_sidecar_duckdb

    return fill_sidecar_duckdb(
        dest,
        graph,
        connect_fn=connect_engine,
        exec_fn=exec_many,
        count_fn=table_count,
        try_import_fn=try_import,
        refuse_fn=path_refused,
        refuse_names=("control.duckdb",),
    )


def query_sidecar_duckdb(query: str, *, db_path: Optional[Path] = None) -> list[dict[str, Any]]:
    from jevops.outer import call_if, if_none, query_engine, text_or

    needle = f"%{text_or(query).casefold()}%"
    from jevops.catalogs import SIDECAR_SYMBOLS_SQL

    return query_engine(
        Path(if_none(db_path, SIDECAR_DUCKDB)),
        SIDECAR_SYMBOLS_SQL,
        [needle],
        refuse_names=("control.duckdb",),
        row_fn=lambda row: call_if(
            row and row[0],
            lambda: {
                "symbol": text_or(row[0]),
                "path": text_or(row[1]),
                "kind": text_or(row[2]),
                "source": "sidecar_duckdb",
            },
        ),
    )


def query_calls_duckdb(
    symbol: str,
    *,
    db_path: Optional[Path] = None,
    direction: str = "callees",
) -> list[str]:
    from jevops.outer import call_if, either, if_none, query_engine, text_or, without_prefix

    name = without_prefix(text_or(symbol), "ptr://codepath/")
    column = either(direction == "callers", lambda: "caller", lambda: "callee")
    match_on = either(direction == "callers", lambda: "callee", lambda: "caller")
    from jevops.catalogs import SIDECAR_CALLS_SQL

    return query_engine(
        Path(if_none(db_path, SIDECAR_DUCKDB)),
        SIDECAR_CALLS_SQL.format(column=column, match_on=match_on),
        [name, f"%:{name.rsplit(':', 1)[-1]}"],
        refuse_names=("control.duckdb",),
        row_fn=lambda row: call_if(row and row[0], lambda: text_or(row[0])),
    )


def harness_call_graph(*, refresh: bool = False) -> dict[str, Any]:
    """Call graph over harness/*.py only (no accelerate parse)."""

    global _HARNESS_CROSS
    from jevops.outer import call_if, first_not_none, ignore_error

    def _build() -> dict[str, Any]:
        from jevops.nca import call_graph_from_paths

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

    return first_not_none(call_if(not refresh, lambda: _HARNESS_CROSS), factory=_build)


def seed_nca_call_edges(memory: dict[str, Any], *, db_path: Optional[Path] = None, limit: int = 48) -> dict[str, Any]:
    """Attach caller→callee pairs as NCA board_edges. DuckDB sidecar or harness AST."""

    from jevops.catalogs import SIDECAR_EDGES_SQL
    from jevops.nca import call_pairs_from_graph, seed_edges_from_query
    from jevops.outer import call_if, first_int, if_none, path_refused, query_engine, text_or

    dest = Path(if_none(db_path, SIDECAR_DUCKDB))
    return seed_edges_from_query(
        memory,
        refused=path_refused(dest, names=("control.duckdb",)),
        query_fn=lambda: query_engine(
            dest,
            SIDECAR_EDGES_SQL,
            [first_int(limit)],
            refuse_names=("control.duckdb",),
            row_fn=lambda row: call_if(
                row and row[0] and row[1],
                lambda: (text_or(row[0]), text_or(row[1])),
            ),
        ),
        graph_fn=lambda: call_pairs_from_graph(harness_call_graph(), limit=limit),
        limit=limit,
    )


def query_sidecar(query: str, *, payload: Optional[dict[str, Any]] = None) -> list[dict[str, Any]]:
    from jevops.nca import query_sidecar_symbols

    from jevops.outer import call_if, get_list, if_none, load_json_object, or_call

    data = or_call(
        if_none(payload, factory=lambda: call_if(SIDECAR.is_file(), lambda: load_json_object(SIDECAR))),
        lambda: build_sidecar_index(write=False),
    )
    return query_sidecar_symbols(get_list(data, "files"), query, limit=24)


def allowlist_call_graph(*, refresh: bool = False) -> dict[str, Any]:
    """Cross-module name→qualified-def graph on allowlisted roots."""

    global _CROSS
    from jevops.outer import call_if, first_not_none

    def _build() -> dict[str, Any]:
        from jevops.nca import call_graph_from_paths

        global _CROSS
        _CROSS = call_graph_from_paths(_iter_allowlisted_py(), cap_neighbors=MAX_NEIGHBORS)
        return _CROSS

    return first_not_none(call_if(not refresh, lambda: _CROSS), factory=_build)


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
